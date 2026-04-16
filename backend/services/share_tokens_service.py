import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from utils.db import get_supabase
from config.settings import settings

logger = logging.getLogger("gigkavach.share_tokens_service")

def generate_share_token(worker_id: str, expires_in_days: int = 7, max_uses: Optional[int] = None, reason: str = "whatsapp") -> dict:
    """
    Generates a PWA share token and stores it in the database.
    """
    try:
        supabase = get_supabase()
        
        # Verify worker exists
        worker_result = supabase.table("workers").select("id").eq("id", worker_id).execute()
        if not worker_result.data:
            raise ValueError(f"Worker {worker_id} not found")
            
        token = secrets.token_urlsafe(24)
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        share_token_data = {
            "worker_id": worker_id,
            "token": token,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "is_used": False,
            "use_count": 0,
            "max_uses": max_uses,
            "created_by": reason,
            "notes": f"Generated via {reason}"
        }
        
        result = supabase.table("share_tokens").insert(share_token_data).execute()
        
        if not result.data:
            raise Exception("Failed to store share token in database")
            
        worker_pwa_url = settings.WORKER_PWA_URL or settings.WORKER_PWA_LOCAL_URL or "http://localhost:4173"
        share_url = f"{worker_pwa_url}/share/worker/{token}"
        
        return {
            "share_token": token,
            "token": token,
            "share_url": share_url,
            "worker_id": worker_id,
            "expires_at": expires_at.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"[SHARE_TOKEN_SERVICE] Error generating token: {str(e)}")
        # Provide a fallback mock token if DB fails so the bot flow doesn't break
        worker_pwa_url = settings.WORKER_PWA_URL or settings.WORKER_PWA_LOCAL_URL or "http://localhost:4173"
        fallback_token = f"fallback_{secrets.token_urlsafe(8)}"
        return {
            "share_token": fallback_token,
            "token": fallback_token,
            "share_url": f"{worker_pwa_url}/share/worker/{fallback_token}",
            "worker_id": worker_id,
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
