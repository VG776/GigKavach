import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from utils.db import get_supabase
from config.settings import settings

logger = logging.getLogger("gigkavach.share_tokens_service")

async def generate_share_token(worker_id: str, expires_in_days: int = 7, max_uses: Optional[int] = None, reason: str = "whatsapp") -> dict:
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
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=expires_in_days)
        
        share_token_data = {
            "worker_id": worker_id,
            "token": token,
            "created_at": now.isoformat(),
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
            
        frontend_url = settings.FRONTEND_URL or "https://gig-kavach-beryl.vercel.app"
        share_url = f"{frontend_url}/link/{token}/profile"
        
        return {
            "share_token": token,
            "share_url": share_url,
            "worker_id": worker_id,
            "expires_at": expires_at.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"[SHARE_TOKEN_SERVICE] Error generating token: {str(e)}")
        # Provide a fallback mock token if DB fails so the bot flow doesn't break
        frontend_url = settings.FRONTEND_URL or "https://gig-kavach-beryl.vercel.app"
        fallback_token = f"fallback_{secrets.token_urlsafe(8)}"
        fallback_expires = datetime.now(timezone.utc) + timedelta(days=1)
        return {
            "share_token": fallback_token,
            "share_url": f"{frontend_url}/link/{fallback_token}/profile",
            "worker_id": worker_id,
            "expires_at": fallback_expires.isoformat()
        }
