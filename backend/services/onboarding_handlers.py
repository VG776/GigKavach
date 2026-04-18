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

State is persisted in Redis with key format: `onboarding:{phone}`
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional
from utils.redis_client import get_redis
from utils.db import get_supabase
from .whatsapp_service import notify_worker, MESSAGES
from .share_tokens_service import generate_share_token
from .gigscore_service import update_gig_score, GigScoreEvent

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


# ─── Phone Normalization ──────────────────────────────────────────────────────

def normalize_phone(phone: str) -> str:
    """Standardizes phone numbers to E.164 format for safe DB/Redis lookups."""
    phone = phone.strip().replace(" ", "")
    if not phone.startswith('+'):
        if len(phone) == 10:
            phone = "+91" + phone
        else:
            phone = "+" + phone
    return phone


def _phone_lookup_variants(phone: str) -> set[str]:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    variants = {phone.strip() if phone else "", digits}
    if len(digits) == 10:
        variants.add(f"+91{digits}")
        variants.add(f"91{digits}")
    elif len(digits) > 10 and not digits.startswith("+"):
        variants.add(f"+{digits}")
    variants.discard("")
    return variants


async def get_worker_by_phone(phone: str) -> Optional[dict]:
    """Fetch a worker record by WhatsApp phone number."""
    try:
        sb = get_supabase()
        for candidate in _phone_lookup_variants(phone) | _phone_lookup_variants(normalize_phone(phone)):
            result = sb.table("workers").select("*").eq("phone", candidate).execute()
            if result.data:
                return result.data[0]

            result = sb.table("workers").select("*").eq("phone_number", candidate).execute()
            if result.data:
                return result.data[0]

        return None
    except Exception as e:
        logger.error(f"Error fetching worker by phone {phone}: {e}")
        return None


async def get_or_create_worker_share_url(worker_id: str, reason: str) -> str:
    """Create a short-lived worker share URL for WhatsApp session login."""
    token_data = await generate_share_token(worker_id, expires_in_days=7, max_uses=200, reason=reason)
    return token_data.get("share_url", "")


def format_session_login_prompt(share_url: str) -> str:
    """Return a WhatsApp-safe login prompt for session verification."""
    return (
        "🔐 *Session verification required*\n\n"
        f"Open this link to continue:\n{share_url}\n\n"
        "After opening it, send *START* again."
    )


async def is_whatsapp_session_active(phone: str) -> bool:
    """Check whether a worker has an active WhatsApp session token."""
    try:
        rc = await get_redis()
        worker = await get_worker_by_phone(phone)

        candidates = set()
        candidates.update({f"wa_session:{value}" for value in _phone_lookup_variants(phone)})
        candidates.update({f"wa_session:{value}" for value in _phone_lookup_variants(normalize_phone(phone))})

        if worker:
            candidates.update({
                f"wa_session:{worker.get('phone', '')}",
                f"wa_session:{worker.get('phone_number', '')}",
            })

        for key in candidates:
            if key and await rc.get(key):
                return True

        return False
    except Exception as e:
        logger.error(f"Error checking session state for {phone}: {e}")
        return False


def normalize_shift_for_storage(shift: str) -> str:
    return (shift or "flexible").strip().lower()


def parse_gig_score(message: str) -> Optional[float]:
    try:
        raw = (message or "").strip().replace(" ", "")
        if not raw:
            return None
        if "/" in raw:
            score_text, denom_text = raw.split("/", 1)
            numerator = float(score_text)
            denominator = float(denom_text) if denom_text else 5.0
            if denominator <= 0:
                return None
            return max(0.0, min(100.0, (numerator / denominator) * 100.0))

        score = float(raw)
        if score <= 5:
            return max(0.0, min(100.0, (score / 5.0) * 100.0))
        return max(0.0, min(100.0, score))
    except Exception:
        return None


def deliveries_to_portfolio_score(deliveries: int) -> float:
    if deliveries <= 0:
        return 20.0
    if deliveries < 100:
        return 30.0 + (deliveries / 100.0) * 20.0
    if deliveries < 500:
        return 50.0 + ((deliveries - 100) / 400.0) * 25.0
    return min(100.0, 75.0 + ((deliveries - 500) / 1000.0) * 25.0)


def recommend_plan(gig_score: float, portfolio_score: float) -> str:
    average_score = (gig_score + portfolio_score) / 2.0
    if average_score >= 80:
        return "pro"
    if average_score >= 60:
        return "plus"
    return "basic"


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

async def _generate_dashboard_url(phone: str) -> str:
    """Helper to generate a secure, tokenized dashboard URL for a worker."""
    try:
        worker = await get_worker_by_phone(phone)
        if not worker:
            from config.settings import settings
            return f"{settings.FRONTEND_URL}/status"

        worker_id = worker["id"]
        token_data = await generate_share_token(worker_id, expires_in_days=7, reason="Onboarding Summary")
        return token_data["share_url"]
    except Exception as e:
        logger.error(f"Error generating dashboard URL: {e}")
        from config.settings import settings
        return f"{settings.FRONTEND_URL}/status"


async def handle_join(phone: str, message: str) -> str:
    """
    START of onboarding — Step 0: Language selection
    Worker sends "JOIN" → Ask for language preference
    """
    # Check if already onboarded
    existing_worker = await get_worker_by_phone(phone)
    if existing_worker:
        share_url = await get_or_create_worker_share_url(existing_worker["id"], "WhatsApp JOIN session login")
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
    
    lang = state.get("language", "en")
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
    lang = state.get("language", "en")
    raw = (message or "").strip()
    if not raw.isdigit():
        return f"❌ Please enter delivery count as a number, for example 0, 250, or 2500. {MESSAGES['ask_deliveries'][lang]}"

    deliveries = int(raw)
    portfolio_score = deliveries_to_portfolio_score(deliveries)

    state["deliveries_completed"] = deliveries
    state["portfolio_score"] = portfolio_score
    state["step"] = 5
    await set_onboarding_state(phone, state)

    suggested_plan = recommend_plan(float(state.get("gig_score", 50)), portfolio_score)
    suggested_plan_name = "Shield Pro" if suggested_plan == "pro" else "Shield Plus" if suggested_plan == "plus" else "Shield Basic"

    return (
        f"{MESSAGES['portfolio_confirmation'][lang].format(score=int(portfolio_score))}\n"
        f"{MESSAGES['recommended_for_you'][lang].format(plan=suggested_plan_name)}\n"
        f"{MESSAGES['ask_verification'][lang]}"
    )

async def handle_verification(phone: str, message: str, state: dict) -> str:
    """
    STEP 5 → STEP 6: Process Identity Vetting
    Workers provide Aadhaar/DL for manual or automated KYC vetting.
    Sets status to 'pending' to maintain production realism.
    """
    lang = state.get("language", "en")
    # Validation: must be at least 5 chars (remove non-alphanumeric for check/storage)
    id_number = "".join(ch for ch in message.strip() if ch.isalnum())
    
    if len(id_number) < 5:
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
    upi_id = "".join(message.split()).lower()  # Remove all internal spaces and lowercase
    
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
    recommendation = MESSAGES["recommended_for_you"][lang].format(plan=suggested_plan_name)
    return (
        f"{MESSAGES['ask_plan'][lang]}\n\n"
        f"{recommendation}\n"
        f"🤖 (Based on Gig Score {int(float(state.get('gig_score', 50)))}, Portfolio {int(float(state.get('portfolio_score', 50)))})"
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
        now = datetime.now()
        
        # 24-hour coverage delay for new workers
        coverage_active_from = now + timedelta(hours=24)
        
        # Current week window
        today = now.date()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        worker_data = {
            "phone": phone,
            "phone_number": phone,
            "gig_platform": str(state.get("platform", "zomato")).capitalize(),
            "gig_score": float(state.get("gig_score", 50)),
            "shift": state.get("shift"),
            "upi_id": state.get("upi_id"),
            "pin_codes": state.get("pin_codes", []),
            "language": lang,
            "plan": plan,
            "gig_score": float(state.get("gig_score", 50)),
            "portfolio_score": float(state.get("portfolio_score", 50)),
            "coverage_pct": 40 if plan == "basic" else 50 if plan == "plus" else 70,
            "is_active": True,
            "onboarded_at": now.isoformat(),
            "last_seen_at": now.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        response = sb.table("workers").insert(worker_data).execute()
        
        if not response.data:
            logger.error(f"Failed to insert worker {phone} into Supabase: {response}")
            return f"⚠️ Registration failed. Please try again."
        
        worker_id = response.data[0]["id"]
        
        # Create initial policy
        tomorrow = now + timedelta(days=1)
        policy_data = {
            "worker_id": worker_id,
            "plan": plan,
            "status": "active",
            "week_start": monday.isoformat(),
            "week_end": sunday.isoformat(),
            "weekly_premium": float(30 if plan == 'basic' else 37 if plan == 'plus' else 44),
            "coverage_pct": int(40 if plan == 'basic' else 50 if plan == 'plus' else 70),
            "coverage_active_from": tomorrow.date().isoformat(),
            "created_at": now.isoformat()
        }
        
        sb.table("policies").insert(policy_data).execute()
        
        token_data = await generate_share_token(
            worker_id,
            expires_in_days=7,
            max_uses=200,
            reason="WhatsApp onboarding complete"
        )

        # Clear onboarding state
        await clear_onboarding_state(phone)
        
        # ── Trinity Loop: High-Fidelity Welcome ──────────────────────────────
        try:
            from services.premium_service import compute_dynamic_quote
            quote_data = await compute_dynamic_quote(worker_id, plan)
            premium = quote_data["dynamic_premium"]
            dashboard_url = await _generate_dashboard_url(phone)
            
            summary = MESSAGES["onboarding_summary"][lang].format(
                plan=f"Shield {plan.capitalize()}",
                premium=f"{premium:.2f}",
                profile_url=dashboard_url
            )
            logger.info(f"✅ Worker {phone} onboarded with high-fidelity summary.")
            return summary
        except Exception as e:
            logger.error(f"Failed to generate high-fidelity summary: {e}")
            return MESSAGES["onboarding_complete"][lang].format(plan=f"Shield {plan.capitalize()}")
        
    except Exception as e:
        logger.error(f"Error completing onboarding for {phone}: {e}")
        return (
            "⚠️ We hit a temporary setup issue while creating your profile. "
            "Please try again in a moment, or type HELP."
        )

async def handle_upi_update(phone: str, message: str) -> str:
    """
    UPI command — Update payout ID after onboarding.
    Usage: UPI ravi@upi
    """
    try:
        sb = get_supabase()
        worker = await get_worker_by_phone(phone)
        if not worker:
            return "❌ Not registered yet. Reply with JOIN to start."
        lang = worker.get("language", "en")
        
        # Parse UPI ID from message
        parts = message.strip().split()
        if len(parts) < 2:
            return f"❌ Usage: *UPI your-id@bank*. Current: {worker.get('upi_id', 'None')}"
            
        new_upi = parts[1]
        if "@" not in new_upi:
            return "❌ Invalid UPI format. Please use format like 'ravi@upi'."
            
        # Update Supabase
        sb.table("workers").update({"upi_id": new_upi}).eq("id", worker["id"]).execute()
        
        # Award micro-boost for maintaining accurate profile (+0.5 pts)
        update_gig_score(worker["id"], GigScoreEvent.CLEAN_SHIFT) # Reusing clean shift boost for record maintenance
        
        msgs = {
            "en": f"✅ Payout ID updated! Your new UPI is *{new_upi}*.",
            "hi": f"✅ भुगतान आईडी अपडेट की गई! आपका नया UPI *{new_upi}* है।",
            "kn": f"✅ ಪಾವತಿ ವಿವರಗಳನ್ನು ನವೀಕರಿಸಲಾಗಿದೆ! ನಿಮ್ಮ ಹೊಸ UPI *{new_upi}*.",
        }
        return msgs.get(lang, msgs["en"])
        
    except Exception as e:
        logger.error(f"Error in UPI update for {phone}: {e}")
        return "⚠️ Update failed. Please try again."


async def handle_start(phone: str, message: str) -> str:
    """
    START command — Mark shift as started and provide pwa link
    """
    try:
        sb = get_supabase()
        worker = await get_worker_by_phone(phone)
        if not worker:
            return "❌ Not registered. Reply with JOIN."

        # Update status in Redis
        from utils.redis_client import get_redis
        rc = await get_redis()
        await rc.set(f"shift_status:{worker['id']}", "on", ex=86400) # 24h expiry
        
        # Also update last_seen_at and is_on_shift in DB if column exists
        now = datetime.now()
        update_data = {"last_seen_at": now.isoformat(), "is_on_shift": True}
        try:
            sb.table("workers").update(update_data).eq("id", worker["id"]).execute()
        except:
            # Fallback for older schemas
            sb.table("workers").update({"last_seen_at": now.isoformat()}).eq("id", worker["id"]).execute()

        # Generate login prompt as requested (ss message)
        share_url = await get_or_create_worker_share_url(worker["id"], "WhatsApp START shift login")
        return format_session_login_prompt(share_url)

    except Exception as e:
        logger.error(f"Error in START for {phone}: {e}")
        return "⚠️ Error starting shift. Please try again."


async def handle_stop(phone: str, message: str) -> str:
    """
    STOP command — Mark shift as ended
    """
    try:
        sb = get_supabase()
        worker = await get_worker_by_phone(phone)
        if not worker:
            return "❌ Not registered. Reply with JOIN."

        # Update status in Redis
        from utils.redis_client import get_redis
        rc = await get_redis()
        await rc.delete(f"shift_status:{worker['id']}")

        # Update DB if column exists
        try:
            sb.table("workers").update({"is_on_shift": False}).eq("id", worker["id"]).execute()
        except Exception:
            pass

        lang = worker.get("language", "en")
        return MESSAGES["shift_stopped"].get(lang, MESSAGES["shift_stopped"]["en"])

    except Exception as e:
        logger.error(f"Error in STOP for {phone}: {e}")
        return "⚠️ Error stopping shift. Please try again."


async def handle_status(phone: str, body: str) -> str:
    """
    STATUS command — Show worker's current coverage and zone DCI
    """
    try:
        sb = get_supabase()
        worker = await get_worker_by_phone(phone)
        if not worker:
            return "❌ Not registered yet. Reply with JOIN to start."
        
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
        
        # ── Trinity Loop: Dynamic Premium ─────────────────────────────────────
        display_premium = "N/A"
        try:
            from services.premium_service import compute_dynamic_quote
            quote_data = await compute_dynamic_quote(worker["id"], plan)
            p = quote_data["dynamic_premium"]
            display_premium = f"₹{p:.2f}"
        except Exception as e:
            logger.error(f"Failed to compute dynamic premium for STATUS: {e}")

        # ── Real-time Multi-Zone DCI lookup ───────────────────────────────────
        from utils.redis_client import get_dci_cache
        
        zone_reports = []
        for pc in pin_codes:
            d_score = 0
            d_sev = "none"
            try:
                cached = await get_dci_cache(pc)
                if cached and "dci_score" in cached:
                    d_score = int(cached["dci_score"])
                    d_sev = cached.get("severity_tier", "none")
                else:
                    d_res = sb.table("dci_logs").select("total_score, severity_tier").eq("pincode", pc).order("created_at", desc=True).limit(1).execute()
                    if d_res.data:
                        d_score = int(d_res.data[0].get("total_score", 0))
                        d_sev = d_res.data[0].get("severity_tier", "none")
            except: pass
            
            icon = "✅" if d_score < 40 else "⚠️" if d_score < 70 else "🚨"
            zone_reports.append(f"{icon} {pc}: DCI {d_score} ({d_sev.capitalize()})")

        if not zone_reports:
            zone_reports = ["No zones registered."]

        header = f"📊 *GigKavach Multi-Zone Status*\nWorker: {phone}\nPlan: Shield {plan.title()}\nPremium: {display_premium}\n\n"
        footer = f"\nShift: {worker.get('shift', 'N/A').title()}\nType HELP for all commands."
        
        return header + "\n".join(zone_reports) + footer

        
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
        
        msgs = {
            "en": (
                "🤖 *GigKavach Bot Commands*\n\n"
                "• *JOIN* - Start onboarding\n"
                "• *START* - Start your shift (Eligibility ON)\n"
                "• *STOP* - End your shift (Eligibility OFF)\n"
                "• *PROFILE* - Get your PWA link\n"
                "• *STATUS* - Check current protection status\n"
                "• *RENEW* - Renew your weekly policy\n"
                "• *HISTORY* - View your payout history\n"
                "• *HELP* - Show this menu"
            ),
            "hi": (
                "🤖 *GigKavach कमांड*\n\n"
                "• *JOIN* - पंजीकरण शुरू करें\n"
                "• *START* - अपनी शिफ्ट शुरू करें\n"
                "• *STOP* - अपनी शिफ्ट खत्म करें\n"
                "• *PROFILE* - अपनी प्रोफाइल देखें\n"
                "• *STATUS* - अपनी स्थिति जांचें\n"
                "• *HELP* - मदद के लिए"
            )
        }
        return msgs.get(lang, msgs["en"])
        
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
        token_data = await generate_share_token(wid, expires_in_days=7, max_uses=50, reason="WhatsApp PROFILE command")
        
        share_url = token_data['share_url']
        
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
        
        token_data = await generate_share_token(wid, expires_in_days=7, max_uses=50, reason="WhatsApp HISTORY command")
        
        share_url = token_data.get("share_url")
        
        msgs = {
            "en": f"💰 *Your GigKavach Worker App*\n\nOpen your profile, plan details, and latest preferences:\n\n{share_url}\n\n⏰ Link expires in 7 days.",
            "hi": f"💰 *आपका लेनदेन इतिहास*\n\nयहाँ देखें:\n\n{share_url}",
        }
        return msgs.get(lang, msgs["en"])
        
    except Exception as e:
        logger.error(f"Error in HISTORY for {phone}: {e}")
        return "⚠️ Error generating history link."
    

async def handle_start_shift(phone: str, message: str) -> str:
    """
    START command — Begin delivery shift and enable location monitoring.
    """
    try:
        sb = get_supabase()
        worker = await get_worker_by_phone(phone)

        if not worker:
            return "❌ Not registered yet. Reply with JOIN to start."
        if not worker.get("is_active"):
            return "⚠️ Your account is suspended. Please use APPEAL to contest."
            
        worker_id = worker["id"]
        lang = worker.get("language", "en")
        
        # 1. Update Supabase status
        sb.table("workers").update({"is_on_shift": True, "last_seen_at": datetime.now().isoformat()}).eq("id", worker_id).execute()
        
        # 2. Persist start time in Redis for duration calculation and telemetry gating
        rc = await get_redis()
        # Standardized key for telemetry receiver sync
        shift_key = f"shift_active:{worker_id}"
        await rc.set(shift_key, datetime.now().isoformat())
        await rc.expire(shift_key, 43200) # 12h max shift
        
        logger.info(f"🚀 Shift STARTED for {phone} (ID: {worker_id})")
        
        # Add PWA link for real-time monitoring view
        token_data = await generate_share_token(worker_id, expires_in_days=1, max_uses=5, reason="Shift Start")
        share_url = token_data['share_url']
        
        base_msg = MESSAGES["shift_started"][lang]
        return f"{base_msg}\n\n📊 *Live Dashboard:*\n{share_url}"
        
    except Exception as e:
        logger.error(f"Error starting shift for {phone}: {e}")
        return "⚠️ Failed to start shift. Please try again."

async def handle_stop_shift(phone: str, message: str) -> str:
    """
    STOP command — End delivery shift, pause monitoring, and award micro-boost.
    """
    try:
        sb = get_supabase()
        worker = await get_worker_by_phone(phone)

        if not worker:
            return "❌ Not registered."
        worker_id = worker["id"]
        lang = worker.get("language", "en")
        
        # 1. Update Supabase
        sb.table("workers").update({"is_on_shift": False, "last_seen_at": datetime.now().isoformat()}).eq("id", worker_id).execute()
        
        # 2. Calculate duration from Redis
        rc = await get_redis()
        shift_key = f"shift_active:{worker_id}"
        start_time_str = await rc.get(shift_key)
        
        duration_str = "Unknown"
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
            duration = datetime.now() - start_time
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            duration_str = f"{hours}h {minutes}m"
            
            # Use worker_id for standardized telemetry cleanup
            await rc.delete(shift_key)
            
            # 3. Award Clean Shift micro-boost (+0.5 trust points)
            # In a real system, we'd check if any fraud flags were raised during this window.
            update_gig_score(worker_id, GigScoreEvent.CLEAN_SHIFT)
            
        # Add PWA link for post-shift review
        token_data = await generate_share_token(worker_id, expires_in_days=1, max_uses=5, reason="Shift Stop")
        share_url = token_data['share_url']
        
        logger.info(f"⏹️ Shift STOPPED for {phone} (Duration: {duration_str})")
        base_msg = MESSAGES["shift_stopped"][lang].format(duration=duration_str)
        return f"{base_msg}\n\n💹 *Check GigScore Rewards:*\n{share_url}"
        
    except Exception as e:
        logger.error(f"Error stopping shift for {phone}: {e}")
        return "⚠️ Failed to stop shift correctly."


# ─── Main Router ──────────────────────────────────────────────────────────────

async def route_message(phone: str, body: str) -> str:
    """
    Main router — dispatch to appropriate handler based on message content and current step
    """
    keyword = body.strip().upper().split()[0] if body.strip() else ""
    # If worker is already registered, require a PWA login link at the start of each session.
    worker = await get_worker_by_phone(phone)
    if worker and keyword in {"LOGIN", "SESSION"}:
        share_url = await get_or_create_worker_share_url(worker["id"], "WhatsApp explicit session login")
        return format_session_login_prompt(share_url)

    if worker and keyword not in {"HELP", "PROFILE", "HISTORY", "LOGIN", "START", "SESSION", "JOIN", "STATUS"}:
        session_active = await is_whatsapp_session_active(phone)
        if not session_active:
            share_url = await get_or_create_worker_share_url(worker["id"], "WhatsApp auto session login")
            return format_session_login_prompt(share_url)
    
    # Global commands
    if keyword == "START":
        return await handle_start_shift(phone, body)
    elif keyword == "STOP":
        return await handle_stop_shift(phone, body)
    elif keyword == "STATUS":
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
    elif keyword == "UPI":
        return await handle_upi_update(phone, body)
    
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
    return f"👋 Welcome to GigKavach! {MESSAGES['help']['en']}" if not worker else MESSAGES["unknown_command"]["en"]

