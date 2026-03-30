"""
services/eligibility_service.py
──────────────────────────────
Enforces strict policy and fraud eligibility rules before allowing a payout.
"""

from datetime import datetime, timezone, timedelta
import logging
from config.settings import settings

logger = logging.getLogger("gigkavach.eligibility")

# --- STUBS (Acting as Supabase) ---
WORKER_POLICIES_DB = {
    # Active policy, bought 3 days ago. Shift is Morning. Last active 10 mins ago.
    "W100": {
        "status": "active",
        "coverage_start": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        "shift": "Morning", 
        "last_active": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    },
    # Active policy, but bought 5 hours ago (Under 24h delay lock)
    "W101": {
        "status": "active",
        "coverage_start": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
        "shift": "Morning",
        "last_active": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    },
    # Active policy, older than 24 hr, but hasn't been active in 6 hours (Inactive)
    "W102": {
        "status": "active",
        "coverage_start": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        "shift": "Night",
        "last_active": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
    }
}

def check_eligibility(worker_id: str, dci_event: dict) -> tuple[bool, str]:
    """
    Core gatekeeper function. Validates 4 strict rules before payout pipeline begins.
    """
    policy = WORKER_POLICIES_DB.get(worker_id)
    
    # RULE 1: Active Policy Exists
    if not policy or policy.get("status") != "active":
        return False, "NO_ACTIVE_POLICY"
        
    disruption_time_str = dci_event.get("disruption_start")
    if not disruption_time_str:
        return False, "INVALID_DCI_EVENT"
        
    disruption_time = datetime.fromisoformat(disruption_time_str)
    coverage_start = datetime.fromisoformat(policy["coverage_start"])
    
    # RULE 2: 24-hr Coverage Delay Enforcement
    # To stop workers from buying policies exactly when they see rain starting
    coverage_age = (disruption_time - coverage_start).total_seconds() / 3600.0
    if coverage_age < settings.COVERAGE_DELAY_HOURS:
        return False, f"COVERAGE_DELAY_LOCK_{settings.COVERAGE_DELAY_HOURS}H"
        
    # RULE 3: Shift Window Alignment
    from utils.datetime_utils import is_within_shift
    if not is_within_shift(policy["shift"], disruption_time):
        return False, f"SHIFT_MISMATCH_FOR_{policy['shift']}"
        
    # RULE 4: Recent Platform Activity OR Catastrophic Override
    last_active = datetime.fromisoformat(policy.get("last_active"))
    time_since_active_hours = (disruption_time - last_active).total_seconds() / 3600.0
    
    # NDMA/Catastrophic Override (Bypass activity check)
    ndma_active = dci_event.get("ndma_override_active", False)
    dci_score = dci_event.get("dci_score", 0)
    is_catastrophic = (dci_score >= settings.DCI_CATASTROPHIC_THRESHOLD) or ndma_active
    
    if not is_catastrophic and time_since_active_hours > 2.0:
        return False, "NO_RECENT_PLATFORM_ACTIVITY"
        
    return True, "ELIGIBLE_FOR_PAYOUT"
