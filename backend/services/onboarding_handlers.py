"""
services/onboarding_handlers.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Handles WhatsApp onboarding commands and multi-step conversation flow.

The onboarding flow:
  Step 0: Language selection
  Step 1: Platform selection (Zomato/Swiggy)
  Step 2: Shift selection (Morning/Day/Night/Flexible)
    Step 3: Gig score collection
    Step 4: Portfolio score collection (from delivery count)
    Step 5: Digilocker verification (mock for sandbox)
    Step 6: UPI ID collection
    Step 7: Pin codes collection
    Step 8: Plan selection (Shield Basic/Plus/Pro)

State is persisted in Redis with key format: `onboarding:{phone}:{step}`
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional
from utils.redis_client import get_redis
from utils.db import get_supabase
from .whatsapp_service import notify_worker, MESSAGES
from .share_tokens_service import generate_share_token

logger = logging.getLogger("gigkavach.onboarding")

# ─── Config ───────────────────────────────────────────────────────────────────
REDIS_EXPIRY = 7 * 24 * 3600  # 7 days — keep context stable if worker returns later
ONBOARDING_TIMEOUT = 7 * 24 * 3600  # Worker has up to 7 days to complete onboarding

# ─── Step Definitions ──────────────────────────────────────────────────────────

STEPS = {
    0: "language",
    1: "platform",
    2: "shift",
    3: "gig_score",
    4: "portfolio_score",
    5: "verification",
    6: "upi",
    7: "pin_codes",
    8: "plan",
}

LANGUAGE_MAP = {"1": "en", "2": "kn", "3": "hi", "4": "ta", "5": "te"}
PLATFORM_MAP = {"1": "zomato", "2": "swiggy"}
SHIFT_MAP = {"1": "morning", "2": "day", "3": "night", "4": "flexible"}
PLAN_MAP = {"1": "basic", "2": "plus", "3": "pro"}


def parse_gig_score(raw: str) -> Optional[float]:
    """
    Accepts either 0-100 numeric score or star ratings like 4.8/5.
    Returns normalized 0-100 score.
    """
    txt = (raw or "").strip().lower().replace(" ", "")
    if not txt:
        return None

    if "/" in txt:
        try:
            left, right = txt.split("/", 1)
            left_v = float(left)
            right_v = float(right)
            if right_v <= 0:
                return None
            normalized = (left_v / right_v) * 100
            return max(0.0, min(100.0, round(normalized, 2)))
        except ValueError:
            return None

    try:
        value = float(txt)
        if 0 <= value <= 5:
            return max(0.0, min(100.0, round((value / 5.0) * 100, 2)))
        if 0 <= value <= 100:
            return round(value, 2)
    except ValueError:
        return None
    return None


def deliveries_to_portfolio_score(deliveries: int) -> float:
    """Maps deliveries completed into 0-100 portfolio score with a 50 baseline for new workers."""
    if deliveries <= 0:
        return 50.0
    if deliveries < 100:
        return 55.0
    if deliveries < 500:
        return 65.0
    if deliveries < 1500:
        return 78.0
    if deliveries < 3000:
        return 88.0
    return 95.0


def recommend_plan(gig_score: float, portfolio_score: float) -> str:
    if gig_score >= 80 and portfolio_score >= 70:
        return "pro"
    if gig_score >= 70 and portfolio_score >= 50:
        return "plus"
    return "basic"


def normalize_shift_for_storage(shift_value: str) -> str:
    """Keep compatibility with existing backend that uses 'day' internally."""
    val = (shift_value or "").strip().lower()
    if val == "evening":
        return "day"
    return val


async def get_worker_by_phone(phone: str) -> Optional[dict]:
    """Fetch worker record by normalized phone across known phone columns."""
    sb = get_supabase()
    result = sb.table("workers").select("*").eq("phone", phone).execute()
    if result.data:
        return result.data[0]

    result_alt = sb.table("workers").select("*").eq("phone_number", phone).execute()
    if result_alt.data:
        return result_alt.data[0]
    return None


async def is_whatsapp_session_active(phone: str) -> bool:
    """Checks if a worker has an active PWA-authenticated WhatsApp session."""
    try:
        rc = await get_redis()
        value = await rc.get(f"wa_session:{phone}")
        return value == "active"
    except Exception as e:
        logger.warning(f"Session check failed for {phone}: {e}")
        return False


def format_session_login_prompt(share_url: str) -> str:
    return (
        "🔐 Please start this WhatsApp session by logging in via your worker link:\n"
        f"{share_url}\n\n"
        "Demo note: DigiLocker verification is mocked and no DigiLocker data is stored."
    )


def get_or_create_worker_share_url(worker_id: str, reason: str) -> str:
    token_data = generate_share_token(worker_id, expires_in_days=7, max_uses=200, reason=reason)
    return token_data.get("share_url", "")


# ─── Redis Helpers ────────────────────────────────────────────────────────────

async def get_onboarding_state(phone: str) -> Optional[dict]:
    """Retrieve worker's onboarding state from Redis"""
    try:
        rc = await get_redis()
        key = f"onboarding:{phone}"
        data = await rc.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"Error getting onboarding state for {phone}: {e}")
        return None


async def set_onboarding_state(phone: str, state: dict) -> bool:
    """Save worker's onboarding state to Redis"""
    try:
        rc = await get_redis()
        key = f"onboarding:{phone}"
        await rc.setex(key, REDIS_EXPIRY, json.dumps(state))
        return True
    except Exception as e:
        logger.error(f"Error setting onboarding state for {phone}: {e}")
        return False


async def clear_onboarding_state(phone: str) -> bool:
    """Clear worker's onboarding state after successful completion"""
    try:
        rc = await get_redis()
        key = f"onboarding:{phone}"
        await rc.delete(key)
        return True
    except Exception as e:
        logger.error(f"Error clearing onboarding state for {phone}: {e}")
        return False


# ─── Handler Functions ────────────────────────────────────────────────────────

async def handle_join(phone: str, message: str) -> str:
    """
    START of onboarding — Step 0: Language selection
    Worker sends "JOIN" → Ask for language preference
    """
    # Check if already onboarded
    existing_worker = await get_worker_by_phone(phone)
    if existing_worker:
        share_url = get_or_create_worker_share_url(existing_worker["id"], "WhatsApp JOIN session login")
        return format_session_login_prompt(share_url)
    
    # Initialize onboarding state
    state = {
        "phone": phone,
        "step": 0,
        "started_at": datetime.now().isoformat(),
        "language": "en",  # default
    }
    await set_onboarding_state(phone, state)
    
    logger.info(f"🎯 Onboarding started for {phone}")
    return MESSAGES["welcome"]["en"]


async def handle_language_selection(phone: str, message: str, state: dict) -> str:
    """
    STEP 0 → STEP 1: Process language choice (1-5)
    """
    choice = message.strip().split()[0] if message.strip() else ""
    
    if choice not in LANGUAGE_MAP:
        return "❌ Invalid choice. Reply with a number (1-5):\n" + MESSAGES["welcome"]["en"]
    
    language = LANGUAGE_MAP[choice]
    state["language"] = language
    state["step"] = 1
    await set_onboarding_state(phone, state)
    
    logger.info(f"📱 {phone} selected language: {language}")
    return MESSAGES["ask_platform"][language]


async def handle_platform_selection(phone: str, message: str, state: dict) -> str:
    """
    STEP 1 → STEP 2: Process platform choice (1-2)
    """
    choice = message.strip().split()[0] if message.strip() else ""
    lang = state.get("language", "en")
    
    if choice not in PLATFORM_MAP:
        return f"❌ Invalid choice. {MESSAGES['ask_platform'][lang]}"
    
    platform = PLATFORM_MAP[choice]
    state["platform"] = platform
    state["step"] = 2
    await set_onboarding_state(phone, state)
    
    logger.info(f"📱 {phone} selected platform: {platform}")
    return MESSAGES["ask_shift"][lang]


async def handle_shift_selection(phone: str, message: str, state: dict) -> str:
    """
    STEP 2 → STEP 4: Process shift choice (1-4), skip verification for sandbox
    """
    choice = message.strip().split()[0] if message.strip() else ""
    lang = state.get("language", "en")
    
    if choice not in SHIFT_MAP:
        return f"❌ Invalid choice. {MESSAGES['ask_shift'][lang]}"
    
    shift = SHIFT_MAP[choice]
    state["shift"] = normalize_shift_for_storage(shift)
    state["step"] = 3
    await set_onboarding_state(phone, state)
    
    logger.info(f"📱 {phone} selected shift: {shift}")
    return (
        "What's your typical gig economy rating?\n"
        "Examples: 4.8/5, 4.5, or 90"
    )


async def handle_gig_score_entry(phone: str, message: str, state: dict) -> str:
    """STEP 3: Collect and normalize gig score to 0-100."""
    score = parse_gig_score(message)
    if score is None:
        return "❌ Please enter a valid rating like 4.8/5, 4.7, or a score between 0 and 100."

    state["gig_score"] = score
    state["step"] = 4
    await set_onboarding_state(phone, state)

    if score >= 85:
        intro = "⭐ Superb rating. You're performing like a pro."
    elif score < 60:
        intro = "📈 No worries, we can help improve your score over time."
    else:
        intro = "✅ Great, thanks for sharing your rating."

    return (
        f"{intro}\n"
        "How many deliveries have you completed so far?\n"
        "If you're new, reply 0."
    )


async def handle_portfolio_score_entry(phone: str, message: str, state: dict) -> str:
    """STEP 4: Collect delivery count and convert to portfolio score."""
    raw = (message or "").strip()
    if not raw.isdigit():
        return "❌ Please enter delivery count as a number, for example 0, 250, or 2500."

    deliveries = int(raw)
    portfolio_score = deliveries_to_portfolio_score(deliveries)

    state["deliveries_completed"] = deliveries
    state["portfolio_score"] = portfolio_score
    state["step"] = 5
    await set_onboarding_state(phone, state)

    return (
        f"👍 Portfolio score set to {int(portfolio_score)}/100 based on your history.\n"
        f"{MESSAGES['ask_verification'][state.get('language', 'en')]}"
    )

async def handle_verification(phone: str, message: str, state: dict) -> str:
    """
    STEP 3 → STEP 4: Process Identity Vetting
    Workers provide Aadhaar/DL for manual or automated KYC vetting.
    Sets status to 'pending' to maintain production realism.
    """
    lang = state.get("language", "en")
    id_number = message.strip()
    
    # Validation: must be at least 8 chars
    if len(id_number) < 8:
        return f"❌ Please enter a valid ID number (Aadhaar/DL). {MESSAGES['ask_verification'][lang]}"
    
    # In production, we would trigger an external KYC API here.
    # For the hackathon synthesis, we set it to 'verified' but with a "vetting" message.
    state["id_verified"] = True 
    state["id_number"] = id_number
    state["step"] = 6
    await set_onboarding_state(phone, state)
    
    logger.info(f"📱 {phone} provided ID for verification: {id_number[:4]}****")
    
    pending_msg = {
        "en": "⏳ Thank you. Your identity is being verified via DigiLocker. You can continue onboarding while we process this in the background.\n\nWhat is your UPI ID for payouts?",
        "kn": "⏳ ಧನ್ಯವಾದಗಳು. ನಿಮ್ಮ ಗುರುತನ್ನು ಡಿಜಿಲಾಕರ್ ಮೂಲಕ ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ...",
        "hi": "⏳ धन्यवाद। आपकी पहचान की जांच की जा रही है...",
        "ta": "⏳ நன்றி. உங்கள் அடையாளம் சரிபார்க்கப்படுகிறது...",
        "te": "⏳ ధన్యవాదాలు. మీ గుర్తింపు ధృవీకరించబడుతోంది...",
    }
    
    return pending_msg.get(lang, pending_msg["en"])


async def handle_upi_entry(phone: str, message: str, state: dict) -> str:
    """
    STEP 4: Collect UPI ID and validate format (basic)
    """
    lang = state.get("language", "en")
    upi_id = message.strip()
    
    # Basic validation: must contain @
    if "@" not in upi_id:
        return f"❌ Invalid UPI format. Please use format like 'ravi@upi'. {MESSAGES['ask_upi'][lang]}"
    
    state["upi_id"] = upi_id
    state["step"] = 7
    await set_onboarding_state(phone, state)
    
    logger.info(f"📱 {phone} entered UPI: {upi_id}")
    return MESSAGES["ask_pincode"][lang]


async def handle_pincode_entry(phone: str, message: str, state: dict) -> str:
    """
    STEP 5: Collect pin codes (1-5, comma-separated)
    """
    lang = state.get("language", "en")
    pin_input = message.strip()
    
    # Parse pin codes
    pin_codes = [p.strip() for p in pin_input.split(",")]
    
    # Validate: 1-5 codes, each 6 digits
    if not (1 <= len(pin_codes) <= 5):
        return f"❌ Please provide 1-5 pin codes (comma-separated). {MESSAGES['ask_pincode'][lang]}"
    
    for pin in pin_codes:
        if not pin.isdigit() or len(pin) != 6:
            return f"❌ Each pin code must be 6 digits. You entered: {pin}. {MESSAGES['ask_pincode'][lang]}"
    
    state["pin_codes"] = pin_codes
    state["step"] = 8
    await set_onboarding_state(phone, state)
    
    logger.info(f"📱 {phone} entered pin codes: {pin_codes}")
    suggested = recommend_plan(float(state.get("gig_score", 50)), float(state.get("portfolio_score", 50)))
    suggested_plan_name = "Shield Pro" if suggested == "pro" else "Shield Plus" if suggested == "plus" else "Shield Basic"
    return (
        f"{MESSAGES['ask_plan'][lang]}\n\n"
        f"🤖 Recommended for you: {suggested_plan_name} "
        f"(Gig Score {int(float(state.get('gig_score', 50)))}, Portfolio {int(float(state.get('portfolio_score', 50)))})"
    )


async def handle_plan_selection(phone: str, message: str, state: dict) -> str:
    """
    STEP 6 (FINAL): Process plan choice (1-3), create worker, activate coverage
    """
    choice = message.strip().split()[0] if message.strip() else ""
    lang = state.get("language", "en")
    
    if choice not in PLAN_MAP:
        return f"❌ Invalid choice. {MESSAGES['ask_plan'][lang]}"
    
    plan = PLAN_MAP[choice]
    state["plan"] = plan
    
    # Save worker to Supabase
    try:
        sb = get_supabase()
        worker_data = {
            "phone": phone,
            "phone_number": phone,
            "platform": state.get("platform"),
            "gig_platform": str(state.get("platform", "zomato")).capitalize(),
            "shift": state.get("shift"),
            "upi_id": state.get("upi_id"),
            "pin_codes": state.get("pin_codes", []),
            "language": lang,
            "plan": plan,
            "gig_score": float(state.get("gig_score", 50)),
            "portfolio_score": float(state.get("portfolio_score", 50)),
            "coverage_pct": 40 if plan == "basic" else 50 if plan == "plus" else 70,
            "is_active": True,
            "last_seen_at": datetime.now().isoformat(),
        }
        
        response = sb.table("workers").insert(worker_data).execute()
        
        if not response.data:
            logger.error(f"Failed to insert worker {phone} into Supabase")
            return f"⚠️ Registration failed. Please try again."
        
        worker_id = response.data[0]["id"]
        
        # Create initial policy (coverage starts tomorrow)
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        policy_data = {
            "worker_id": worker_id,
            "plan": plan,
            "status": "active",
            "week_start": str(tomorrow),
            "coverage_pct": worker_data["coverage_pct"],
            "weekly_premium": 30 if plan == "basic" else 37 if plan == "plus" else 44,
        }
        
        sb.table("policies").insert(policy_data).execute()
        
        token_data = generate_share_token(
            worker_id,
            expires_in_days=7,
            max_uses=200,
            reason="WhatsApp onboarding complete"
        )

        # Clear onboarding state
        await clear_onboarding_state(phone)
        
        logger.info(f"✅ Worker {phone} onboarded successfully with plan {plan}")
        return (
            MESSAGES["onboarding_complete"][lang].format(
                plan=f"Shield {'Basic' if plan == 'basic' else 'Plus' if plan == 'plus' else 'Pro'}"
            )
            + f"\n\n📱 Your worker app link: {token_data.get('share_url')}"
        )
        
    except Exception as e:
        logger.error(f"Error completing onboarding for {phone}: {e}")
        return f"⚠️ Error during registration: {str(e)}"


async def handle_status(phone: str, message: str) -> str:
    """
    STATUS command — Show worker's current coverage and zone DCI
    """
    try:
        sb = get_supabase()

        worker = await get_worker_by_phone(phone)
        if not worker:
            return "❌ Not registered yet. Reply with JOIN to start."

        lang = worker.get("language", "en")
        
        # Get active policy
        policy_response = (
            sb.table("policies")
            .select("*")
            .eq("worker_id", worker["id"])
            .eq("status", "active")
            .execute()
        )
        
        policy = policy_response.data[0] if policy_response.data else None
        plan = policy.get("plan") if policy else worker.get("plan", "unknown")
        pin_codes = worker.get("pin_codes", []) or []
        pin_code = pin_codes[0] if pin_codes else "N/A"

        # ── Real-time DCI lookup ──────────────────────────────────────────────
        # Priority: Redis cache (updated every 5 min by DCI poller) →
        #           Supabase dci_logs (last persisted reading) →
        #           Safe display fallback
        dci_score = 0
        severity = "none"

        try:
            from utils.redis_client import get_dci_cache
            if pin_code != "N/A":
                cached_dci = await get_dci_cache(pin_code)
                if cached_dci and "dci_score" in cached_dci:
                    dci_score = int(cached_dci["dci_score"])
                    severity = cached_dci.get("severity_tier", "none")
                else:
                    # Fallback to most recent dci_logs entry
                    dci_result = (
                        sb.table("dci_logs")
                        .select("total_score, severity_tier")
                        .eq("pincode", pin_code)
                        .order("created_at", desc=True)
                        .limit(1)
                        .execute()
                    )
                    if dci_result.data:
                        row = dci_result.data[0]
                        dci_score = int(row.get("total_score", 0))
                        severity = row.get("severity_tier", "none")
        except Exception as dci_err:
            logger.warning(f"Real-time DCI fetch failed for STATUS ({phone}): {dci_err}")
            dci_score = 0
            severity = "unknown"

        return MESSAGES["status_response"][lang].format(
            pin_code=pin_code,
            dci=dci_score,
            severity=severity,
            plan=f"Shield {'Basic' if plan == 'basic' else 'Plus' if plan == 'plus' else 'Pro'}",
            shift=worker.get("shift", "N/A").title()
        )

        
    except Exception as e:
        logger.error(f"Error in STATUS for {phone}: {e}")
        return "⚠️ Error fetching status. Please try again."


async def handle_renew(phone: str, message: str) -> str:
    """
    RENEW command — Extend coverage for next week
    """
    try:
        sb = get_supabase()

        worker = await get_worker_by_phone(phone)
        if not worker:
            return "❌ Not registered. Reply with JOIN."

        lang = worker.get("language", "en")
        plan = worker.get("plan")
        
        # Create new policy for next week
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        policy_data = {
            "worker_id": worker["id"],
            "plan": plan,
            "status": "active",
            "week_start": str(tomorrow),
            "coverage_pct": 40 if plan == "basic" else 50 if plan == "plus" else 70,
            "weekly_premium": 30 if plan == "basic" else 37 if plan == "plus" else 44,
        }
        
        sb.table("policies").insert(policy_data).execute()
        
        # INTEGRATION: Clean Renewal Boost (+2 pts)
        from services.gigscore_service import update_gig_score, GigScoreEvent
        update_gig_score(worker["id"], GigScoreEvent.CLEAN_RENEWAL)
        
        messages = {
            "en": f"✅ Renewed for next week! Your {plan.title()} plan is active from {tomorrow}.",
            "kn": f"✅ ಮುಂದಿನ ವಾರಕ್ಕೆ ನವೀಕರಿಸಲಾಯಿತು!",
            "hi": f"✅ अगले सप्ताह के लिए नवीनीकृत! आपकी योजना सक्रिय है।",
            "ta": f"✅ அடுத்த வாரத்திற்கு புதுப்பிக்கப்பட்டது!",
            "te": f"✅ వచ్చే వారం కోసం రెన్యూ చేసారు!",
        }
        
        return messages.get(lang, messages["en"])
        
    except Exception as e:
        logger.error(f"Error in RENEW for {phone}: {e}")
        return "⚠️ Renewal failed. Please try again."


async def handle_shift_update(phone: str, message: str) -> str:
    """
    SHIFT command — Update working hours
    """
    try:
        sb = get_supabase()

        worker = await get_worker_by_phone(phone)
        if not worker:
            return "❌ Not registered. Reply with JOIN."

        lang = worker.get("language", "en")
        
        # Parse shift choice from message
        parts = message.strip().split()
        if len(parts) < 2:
            return MESSAGES["ask_shift"][lang]
        
        choice = parts[1]
        if choice not in SHIFT_MAP:
            return f"Invalid choice. {MESSAGES['ask_shift'][lang]}"
        
        new_shift = SHIFT_MAP[choice]
        sb.table("workers").update({"shift": new_shift}).eq("id", worker["id"]).execute()
        
        messages = {
            "en": f"✅ Shift updated to {new_shift.title()}!",
            "kn": f"✅ ಶಿಫ್ಟ್ {new_shift} ಆಗಿ ನವೀಕರಿಸಲಾಗಿದೆ!",
            "hi": f"✅ शिफ्ट बदल दिया गया है!",
            "ta": f"✅ ஷிப்ட் புதுப்பிக்கப்பட்டது!",
            "te": f"✅ Shift నవీకరించబడింది!",
        }
        
        return messages.get(lang, messages["en"])
        
    except Exception as e:
        logger.error(f"Error in SHIFT for {phone}: {e}")
        return "⚠️ Update failed. Please try again."


async def handle_language_change(phone: str, message: str) -> str:
    """
    LANG command — Change preferred language
    """
    try:
        sb = get_supabase()

        worker = await get_worker_by_phone(phone)
        if not worker:
            return "❌ Not registered. Reply with JOIN."
        
        # Parse language choice
        parts = message.strip().split()
        if len(parts) < 2:
            return MESSAGES["welcome"]["en"]
        
        choice = parts[1]
        if choice not in LANGUAGE_MAP:
            return "Invalid choice (1-5)."
        
        new_lang = LANGUAGE_MAP[choice]
        sb.table("workers").update({"language": new_lang}).eq("id", worker["id"]).execute()
        
        messages = {
            "en": "✅ Language changed to English!",
            "kn": "✅ ಭಾಷೆ ಕನ್ನಡಕ್ಕೆ ಬದಲಾಗಿದೆ!",
            "hi": "✅ भाषा हिंदी में बदल गई!",
            "ta": "✅ மொழி தமிழ் க்கு மாற்றப்பட்டது!",
            "te": "✅ భాష తెలుగుకు మార్చిన!",
        }
        
        return messages.get(new_lang, messages["en"])
        
    except Exception as e:
        logger.error(f"Error in LANG for {phone}: {e}")
        return "⚠️ Language change failed. Please try again."


async def handle_help(phone: str, message: str) -> str:
    """
    HELP command — Show all available commands
    """
    try:
        worker = await get_worker_by_phone(phone)
        lang = worker.get("language", "en") if worker else "en"
        
        return MESSAGES["help"][lang]
        
    except Exception as e:
        logger.error(f"Error in HELP for {phone}: {e}")
        return MESSAGES["help"]["en"]


async def handle_appeal(phone: str, message: str) -> str:
    """
    APPEAL command — Worker contests a fraud decision or payout issue
    Opens 48-hour appeal window for dispute resolution
    """
    try:
        sb = get_supabase()

        worker = await get_worker_by_phone(phone)
        if not worker:
            return "❌ Not registered. Reply with JOIN."

        lang = worker.get("language", "en")
        
        # Create appeal record
        appeal_data = {
            "worker_id": worker["id"],
            "phone": phone,
            "reason": message,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=48)).isoformat(),
        }
        
        sb.table("appeals").insert(appeal_data).execute()
        
        messages = {
            "en": "✅ Appeal submitted. We'll review within 48 hours and get back to you.",
            "kn": "✅ ಮನವಿ ಸರಾಗ್ರಹಿಸಲಾಗಿದೆ. ನಾವು ಪರಿಶೀಲಿಸುತ್ತೇವೆ.",
            "hi": "✅ अपील दर्ज की गई। हम 48 घंटे में जांच करेंगे।",
            "ta": "✅ மேல்முறையீடு சமர்ப்பிக்கப்பட்டது! 48 மணி நேரத்தில் பதிலளிப்போம்.",
            "te": "✅ అభ్యర్థన చేర్చారు. 48 గంటలలో సమీక్ష చేస్తాం.",
        }
        
        logger.info(f"📋 Appeal created for {phone}")
        return messages.get(lang, messages["en"])
        
    except Exception as e:
        logger.error(f"Error in APPEAL for {phone}: {e}")
        return "⚠️ Appeal submission failed. Please try again."


async def handle_profile(phone: str, message: str) -> str:
    """
    PROFILE command — Generate a secure PWA link for the worker's profile
    """
    try:
        worker = await get_worker_by_phone(phone)
        if not worker:
            return "❌ Not registered. Reply with JOIN."

        wid = worker["id"]
        lang = worker.get("language", "en")
        
        # Generate token (valid for 7 days)
        token_data = generate_share_token(wid, expires_in_days=7, max_uses=50, reason="WhatsApp PROFILE command")
        
        share_url = token_data.get("share_url")
        
        msgs = {
            "en": f"📱 *Your GigKavach Profile*\n\nView your GigScore, zone info, and premium details:\n\n{share_url}\n\n⏰ Link expires in 7 days.",
            "hi": f"📱 *आपकी GigKavach प्रोफाइल*\n\nअपनी जानकारी देखने के लिए यहाँ क्लिक करें:\n\n{share_url}",
        }
        return msgs.get(lang, msgs["en"])
        
    except Exception as e:
        logger.error(f"Error in PROFILE for {phone}: {e}")
        return "⚠️ Error generating profile link."


async def handle_history(phone: str, message: str) -> str:
    """
    HISTORY command — Generate a secure PWA link for the worker's transaction history
    """
    try:
        worker = await get_worker_by_phone(phone)
        if not worker:
            return "❌ Not registered. Reply with JOIN."

        wid = worker["id"]
        lang = worker.get("language", "en")
        
        token_data = generate_share_token(wid, expires_in_days=7, max_uses=50, reason="WhatsApp HISTORY command")
        
        share_url = token_data.get("share_url")
        
        msgs = {
            "en": f"💰 *Your GigKavach Worker App*\n\nOpen your profile, plan details, and latest preferences:\n\n{share_url}\n\n⏰ Link expires in 7 days.",
            "hi": f"💰 *आपका लेनदेन इतिहास*\n\nयहाँ देखें:\n\n{share_url}",
        }
        return msgs.get(lang, msgs["en"])
        
    except Exception as e:
        logger.error(f"Error in HISTORY for {phone}: {e}")
        return "⚠️ Error generating history link."


# ─── Main Router ──────────────────────────────────────────────────────────────

async def route_message(phone: str, body: str) -> str:
    """
    Main router — dispatch to appropriate handler based on message content and current step
    """
    keyword = body.strip().upper().split()[0] if body.strip() else ""

    # If worker is already registered, require a PWA login link at the start of each session.
    worker = await get_worker_by_phone(phone)
    if worker and keyword in {"LOGIN", "START", "SESSION"}:
        share_url = get_or_create_worker_share_url(worker["id"], "WhatsApp explicit session login")
        return format_session_login_prompt(share_url)

    if worker and keyword not in {"HELP", "PROFILE", "HISTORY", "LOGIN", "START", "SESSION", "JOIN"}:
        session_active = await is_whatsapp_session_active(phone)
        if not session_active:
            share_url = get_or_create_worker_share_url(worker["id"], "WhatsApp auto session login")
            return format_session_login_prompt(share_url)
    
    # Commands that work anytime for registered users
    if keyword == "STATUS":
        return await handle_status(phone, body)
    elif keyword == "RENEW":
        return await handle_renew(phone, body)
    elif keyword == "SHIFT":
        return await handle_shift_update(phone, body)
    elif keyword == "LANG":
        return await handle_language_change(phone, body)
    elif keyword == "APPEAL":
        return await handle_appeal(phone, body)
    elif keyword == "HELP":
        return await handle_help(phone, body)
    elif keyword == "JOIN":
        return await handle_join(phone, body)
    elif keyword == "PROFILE":
        return await handle_profile(phone, body)
    elif keyword == "HISTORY":
        return await handle_history(phone, body)
    
    # Check if user is in middle of onboarding
    state = await get_onboarding_state(phone)
    if state:
        step = state.get("step", 0)
        
        if step == 0:
            return await handle_language_selection(phone, body, state)
        elif step == 1:
            return await handle_platform_selection(phone, body, state)
        elif step == 2:
            return await handle_shift_selection(phone, body, state)
        elif step == 3:
            return await handle_gig_score_entry(phone, body, state)
        elif step == 4:
            return await handle_portfolio_score_entry(phone, body, state)
        elif step == 5:
            return await handle_verification(phone, body, state)
        elif step == 6:
            return await handle_upi_entry(phone, body, state)
        elif step == 7:
            return await handle_pincode_entry(phone, body, state)
        elif step == 8:
            return await handle_plan_selection(phone, body, state)
    
    # Default — ask for valid command
    return MESSAGES["help"]["en"]

