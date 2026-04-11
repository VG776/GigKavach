"""
utils/audit_logger.py — Administrative Audit Logging
─────────────────────────────────────────────────────
Provides a centralized way to log administrative actions to the `audit_logs` 
Supabase table for compliance and security monitoring.
"""

import logging
import datetime
from typing import Dict, Any, Optional
from utils.supabase_client import get_supabase

logger = logging.getLogger("gigkavach.audit")

def log_audit_event(
    user_id: str, 
    action: str, 
    details: Dict[str, Any],
    resource_type: str = "dci_weights"
) -> None:
    """
    Records an administrative action to the audit_logs table.
    Bails out gracefully if database is unavailable to prevent API failure.
    
    Args:
        user_id: ID of the admin user who performed the action
        action: Short string describing the action (e.g. 'RECOMPUTE_WEIGHTS')
        details: JSON-serializable dict with contextual info
        resource_type: The domain being audited
    """
    sb = get_supabase()
    
    payload = {
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "details": details,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    try:
        # Non-blocking sync insert (Supabase client currently sync in this project)
        sb.table("audit_logs").insert(payload).execute()
        logger.info(f"📝 AUDIT LOGGED: user={user_id} action={action}")
    except Exception as e:
        # If the table doesn't exist or DB is down, log to console but don't crash
        logger.error(f"❌ AUDIT LOG FAILED for action {action}: {e}")
        logger.info(f"   FALLBACK PAYLOAD: {payload}")
