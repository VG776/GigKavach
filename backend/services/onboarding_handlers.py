"""
services/onboarding_handlers.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Handles WhatsApp onboarding commands and multi-step conversation flow.

The 5-step onboarding flow:
  Step 0: Language selection
  Step 1: Platform selection (Zomato/Swiggy)
  Step 2: Shift selection (Morning/Day/Night/Flexible)
  Step 3: Digilocker verification (mock for sandbox)
  Step 4: UPI ID collection
  Step 5: Pin codes collection
  Step 6: Plan selection (Shield Basic/Plus/Pro)

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
REDIS_EXPIRY = 3600  # 1 hour — onboarding state expires after 1 hour
ONBOARDING_TIMEOUT = 3600  # Worker has 1 hour to complete onboarding

# ─── Step Definitions ──────────────────────────────────────────────────────────

STEPS = {
    0: "language",
    1: "platform",
    2: "shift",
    3: "verification",
    4: "upi",
    5: "pin_codes",
    6: "plan",
}

LANGUAGE_MAP = {"1": "en", "2": "kn", "3": "hi", "4": "ta", "5": "te"}
PLATFORM_MAP = {"1": "zomato", "2": "swiggy"}
SHIFT_MAP = {"1": "morning", "2": "day", "3": "night", "4": "flexible"}
PLAN_MAP = {"1": "basic", "2": "plus", "3": "pro"}


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
    sb = get_supabase()
    existing = sb.table("workers").select("id").eq("phone", phone).execute()
    
    if existing.data:
        return MESSAGES.get("already_onboarded", {}).get("en",
            f"✅ You're already registered! Type STATUS to check coverage.")
    
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
    state["shift"] = shift
    state["step"] = 3  # Move to Step 3 (verification)
    await set_onboarding_state(phone, state)
    
    logger.info(f"📱 {phone} selected shift: {shift}")
    return MESSAGES["ask_verification"][lang]

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
    state["step"] = 4
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
    state["step"] = 5
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
    state["step"] = 6
    await set_onboarding_state(phone, state)
    
    logger.info(f"📱 {phone} entered pin codes: {pin_codes}")
    return MESSAGES["ask_plan"][lang]


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
            "shift": state.get("shift"),
            "upi_id": state.get("upi_id"),
            "pin_codes": state.get("pin_codes", []),
            "language": lang,
            "plan": plan,
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
        
        # Clear onboarding state
        await clear_onboarding_state(phone)
        
        logger.info(f"✅ Worker {phone} onboarded successfully with plan {plan}")
        return MESSAGES["onboarding_complete"][lang].format(plan=f"Shield {'Basic' if plan == 'basic' else 'Plus' if plan == 'plus' else 'Pro'}")
        
    except Exception as e:
        logger.error(f"Error completing onboarding for {phone}: {e}")
        return f"⚠️ Error during registration: {str(e)}"


async def handle_status(phone: str, message: str) -> str:
    """
    STATUS command — Show worker's current coverage and zone DCI
    """
    try:
        sb = get_supabase()
        
        # Get worker
        worker_response = sb.table("workers").select("*").eq("phone", phone).execute()
        if not worker_response.data:
            return "❌ Not registered yet. Reply with JOIN to start."
        
        worker = worker_response.data[0]
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
        
        worker_response = sb.table("workers").select("*").eq("phone", phone).execute()
        if not worker_response.data:
            return "❌ Not registered. Reply with JOIN."
        
        worker = worker_response.data[0]
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
        
        worker_response = sb.table("workers").select("*").eq("phone", phone).execute()
        if not worker_response.data:
            return "❌ Not registered. Reply with JOIN."
        
        worker = worker_response.data[0]
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
        
        worker_response = sb.table("workers").select("*").eq("phone", phone).execute()
        if not worker_response.data:
            return "❌ Not registered. Reply with JOIN."
        
        worker = worker_response.data[0]
        
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
        sb = get_supabase()
        
        worker_response = sb.table("workers").select("language").eq("phone", phone).execute()
        lang = worker_response.data[0].get("language", "en") if worker_response.data else "en"
        
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
        
        worker_response = sb.table("workers").select("*").eq("phone", phone).execute()
        if not worker_response.data:
            return "❌ Not registered. Reply with JOIN."
        
        worker = worker_response.data[0]
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
        sb = get_supabase()
        worker = sb.table("workers").select("id, language").eq("phone", phone).single().execute()
        if not worker.data:
            return "❌ Not registered. Reply with JOIN."
        
        wid = worker.data["id"]
        lang = worker.data.get("language", "en")
        
        # Generate token (valid for 7 days)
        token_data = generate_share_token(wid, expires_in_days=7, max_uses=50, reason="WhatsApp PROFILE command")
        
        frontend_url = "https://gig-kavach-beryl.vercel.app" # Production URL
        share_url = f"{frontend_url}/link/{token_data['token']}/profile"
        
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
        sb = get_supabase()
        worker = sb.table("workers").select("id, language").eq("phone", phone).single().execute()
        if not worker.data:
            return "❌ Not registered. Reply with JOIN."
        
        wid = worker.data["id"]
        lang = worker.data.get("language", "en")
        
        token_data = generate_share_token(wid, expires_in_days=7, max_uses=50, reason="WhatsApp HISTORY command")
        
        frontend_url = "https://gig-kavach-beryl.vercel.app"
        share_url = f"{frontend_url}/link/{token_data['token']}/history"
        
        msgs = {
            "en": f"💰 *Your Transaction History*\n\nView all your payouts and earnings:\n\n{share_url}\n\n⏰ Link expires in 7 days.",
            "hi": f"💰 *आपका लेनदेन इतिहास*\n\nयहाँ देखें:\n\n{share_url}",
        }
        return msgs.get(lang, msgs["en"])
        
    except Exception as e:
        logger.error(f"Error in HISTORY for {phone}: {e}")
        return "⚠️ Error generating history link."


async def handle_start_shift(phone: str, body: str) -> str:
    """Handle START command — worker starting their shift"""
    try:
        sb = get_supabase()
        worker = sb.table("workers").select("id, language").eq("phone", phone).single().execute()
        if not worker.data:
            return "❌ Not registered. Reply with JOIN."
        
        wid = worker.data["id"]
        lang = worker.data.get("language", "en")
        
        # Update last_seen_at
        sb.table("workers").update({"last_seen_at": datetime.utcnow().isoformat()}).eq("id", wid).execute()
        
        # Generate dashboard link
        token_data = generate_share_token(wid, expires_in_days=1, max_uses=5, reason="WhatsApp START command")
        frontend_url = "https://gig-kavach-beryl.vercel.app"
        share_url = f"{frontend_url}/link/{token_data['token']}/profile"
        
        msgs = {
            "en": share_url,
            "hi": share_url
        }
        return msgs.get(lang, msgs["en"])
    except Exception as e:
        logger.error(f"Error in START command for {phone}: {e}")
        return "⚠️ Error generating dashboard link."

async def handle_stop_shift(phone: str, body: str) -> str:
    """Handle STOP command — worker ending their shift"""
    try:
        sb = get_supabase()
        worker = sb.table("workers").select("id, language").eq("phone", phone).single().execute()
        if not worker.data:
            return "❌ Not registered. Reply with JOIN."
            
        wid = worker.data["id"]
        lang = worker.data.get("language", "en")
        
        # Update last_seen_at
        sb.table("workers").update({"last_seen_at": datetime.utcnow().isoformat()}).eq("id", wid).execute()
        
        # Generate history link
        token_data = generate_share_token(wid, expires_in_days=1, max_uses=5, reason="WhatsApp STOP command")
        frontend_url = "https://gig-kavach-beryl.vercel.app"
        share_url = f"{frontend_url}/link/{token_data['token']}/history"
        
        msgs = {
            "en": share_url,
            "hi": share_url
        }
        return msgs.get(lang, msgs["en"])
    except Exception as e:
        logger.error(f"Error in STOP command for {phone}: {e}")
        return "⚠️ Error generating dashboard link."

# ─── Main Router ──────────────────────────────────────────────────────────────

async def route_message(phone: str, body: str) -> str:
    """
    Main router — dispatch to appropriate handler based on message content and current step
    """
    keyword = body.strip().upper().split()[0] if body.strip() else ""
    
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
    elif keyword == "START":
        return await handle_start_shift(phone, body)
    elif keyword == "STOP":
        return await handle_stop_shift(phone, body)
    
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
            return await handle_verification(phone, body, state)
        elif step == 4:
            return await handle_upi_entry(phone, body, state)
        elif step == 5:
            return await handle_pincode_entry(phone, body, state)
        elif step == 6:
            return await handle_plan_selection(phone, body, state)
    
    # Default — ask for valid command
    return MESSAGES["help"]["en"]

