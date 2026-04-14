"""
api/share_tokens.py — Share Token Management for WhatsApp Integration
───────────────────────────────────────────────────────────────────
Handles generation and verification of share tokens for worker PWA links.
Used by WhatsApp bot to send shareable links to workers.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone
import secrets
import jwt
import logging

from config.settings import settings
from utils.db import get_supabase

logger = logging.getLogger("gigkavach.share_tokens")
router = APIRouter(prefix="/share-tokens", tags=["Share Tokens"])

# ─── Models ────────────────────────────────────────────────────────────

class GenerateShareTokenRequest(BaseModel):
    """Generate a share token for a worker"""
    worker_id: str
    expires_in_days: Optional[int] = 7
    max_uses: Optional[int] = None  # None = unlimited uses
    reason: Optional[str] = "whatsapp"  # 'whatsapp', 'email', 'manual'

class GenerateShareTokenResponse(BaseModel):
    """Response with generated share token"""
    share_token: str
    share_url: str
    worker_id: str
    expires_at: str
    created_at: str

class VerifyShareTokenRequest(BaseModel):
    """Verify a share token"""
    share_token: str

class VerifyShareTokenResponse(BaseModel):
    """Response with token verification result"""
    is_valid: bool
    worker_id: Optional[str] = None
    expires_at: Optional[str] = None
    expires_in_seconds: Optional[int] = None
    message: str

class UpdateSharedWorkerProfileRequest(BaseModel):
    gig_platform: Optional[str] = None
    shift: Optional[str] = None
    gig_score: Optional[float] = None
    portfolio_score: Optional[float] = None


ALLOWED_PLATFORMS = {"zomato", "swiggy"}
ALLOWED_SHIFTS = {"flexible", "morning", "day", "evening", "night"}

# ─── Helper Functions ───────────────────────────────────────────────────

def generate_secure_random_token() -> str:
    """
    Generate a secure share token.
    Uses URL-safe random bytes encoded as hex.
    """
    return secrets.token_urlsafe(24)

def create_share_token_jwt(worker_id: str, token_id: str, expires_at: datetime) -> str:
    """
    Create a JWT payload for the share token.
    This allows verification without database lookup.
    """
    payload = {
        "sub": worker_id,  # Subject: worker ID
        "token_id": token_id,  # Token record ID
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
        "type": "share_token",
    }
    
    secret = settings.SECRET_KEY or "your-secret-key"
    return jwt.encode(payload, secret, algorithm="HS256")

async def verify_share_token_jwt(share_token: str) -> dict:
    """
    Verify JWT-based share token.
    Returns decoded payload if valid.
    """
    try:
        secret = settings.SECRET_KEY or "your-secret-key"
        payload = jwt.decode(share_token, secret, algorithms=["HS256"])
        
        if payload.get("type") != "share_token":
            raise ValueError("Invalid token type")
            
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Share token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid share token: {str(e)}"
        )

# ─── Endpoints ─────────────────────────────────────────────────────────

@router.post("/generate", response_model=GenerateShareTokenResponse)
async def generate_share_token(
    request: GenerateShareTokenRequest,
    supabase = Depends(get_supabase)
):
    """
    Generate a shareable token for a worker.
    This token can be shared via WhatsApp to allow workers to access their profile.
    
    Args:
        worker_id: ID of the worker
        expires_in_days: Token expiry duration (default: 7 days)
        max_uses: Maximum number of uses (None = unlimited)
        reason: Why the token is being generated ('whatsapp', 'email', 'manual')
    
    Returns:
        share_token: The token to use in URL
        share_url: Full URL for easy sharing
        expires_at: ISO timestamp when token expires
    """
    try:
        # Verify worker exists
        logger.info(f"[SHARE_TOKEN] Generating for worker: {request.worker_id}")
        
        worker_result = supabase.table("workers").select("id").eq("id", request.worker_id).execute()
        
        if not worker_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker {request.worker_id} not found"
            )
        
        # Generate token
        token = generate_secure_random_token()
        
        # Calculate expiry
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)
        
        # Store in database
        share_token_data = {
            "worker_id": request.worker_id,
            "token": token,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat(),
            "is_used": False,
            "use_count": 0,
            "max_uses": request.max_uses,
            "created_by": request.reason,
            "notes": f"Generated via {request.reason}"
        }
        
        result = supabase.table("share_tokens").insert(share_token_data).execute()
        
        if not result.data:
            raise Exception("Failed to store share token")
        
        logger.info(f"[SHARE_TOKEN] Generated: {token[:8]}... for worker {request.worker_id}")
        
        worker_pwa_url = settings.WORKER_PWA_URL or settings.WORKER_PWA_LOCAL_URL or "http://localhost:4173"
        share_url = f"{worker_pwa_url}/share/worker/{token}"
        
        return GenerateShareTokenResponse(
            share_token=token,
            share_url=share_url,
            worker_id=request.worker_id,
            expires_at=expires_at.isoformat(),
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SHARE_TOKEN] Error generating token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate share token: {str(e)}"
        )

@router.post("/verify", response_model=VerifyShareTokenResponse)
async def verify_share_token(
    request: VerifyShareTokenRequest,
    supabase = Depends(get_supabase)
):
    """
    Verify a share token is valid and not expired.
    used by frontend to authenticate share link access.
    
    Args:
        share_token: The token from URL parameter
    
    Returns:
        is_valid: Whether token is valid and not expired
        worker_id: Worker ID if token is valid
        expires_at: Token expiry timestamp
        expires_in_seconds: Seconds until expiry
    """
    try:
        logger.info(f"[SHARE_TOKEN_VERIFY] Verifying token: {request.share_token[:8]}...")
        
        # Look up token in database
        result = supabase.table("share_tokens")\
            .select("*")\
            .eq("token", request.share_token)\
            .execute()
        
        if not result.data:
            logger.warn(f"[SHARE_TOKEN_VERIFY] Token not found in database")
            return VerifyShareTokenResponse(
                is_valid=False,
                message="Share token not found or has been revoked"
            )
        
        token_record = result.data[0]
        worker_id = token_record["worker_id"]
        expires_at = datetime.fromisoformat(token_record["expires_at"])
        now = datetime.now(timezone.utc)
        
        # Check expiry
        if now > expires_at:
            logger.warn(f"[SHARE_TOKEN_VERIFY] Token expired for worker {worker_id}")
            return VerifyShareTokenResponse(
                is_valid=False,
                worker_id=worker_id,
                message="Share token has expired"
            )
        
        # Check max uses
        if token_record.get("max_uses") is not None:
            if token_record["use_count"] >= token_record["max_uses"]:
                logger.warn(f"[SHARE_TOKEN_VERIFY] Token max uses exceeded for worker {worker_id}")
                return VerifyShareTokenResponse(
                    is_valid=False,
                    worker_id=worker_id,
                    message="Share token use limit exceeded"
                )
        
        # Increment use count
        supabase.table("share_tokens")\
            .update({"use_count": token_record["use_count"] + 1})\
            .eq("token", request.share_token)\
            .execute()
        
        expires_in = (expires_at - now).total_seconds()
        
        logger.info(f"[SHARE_TOKEN_VERIFY] Valid token for worker {worker_id}")
        
        return VerifyShareTokenResponse(
            is_valid=True,
            worker_id=worker_id,
            expires_at=expires_at.isoformat(),
            expires_in_seconds=int(expires_in),
            message="Share token is valid"
        )
        
    except Exception as e:
        logger.error(f"[SHARE_TOKEN_VERIFY] Error verifying token: {str(e)}")
        return VerifyShareTokenResponse(
            is_valid=False,
            message=f"Error verifying token: {str(e)}"
        )

@router.get("/by-worker/{worker_id}")
async def get_worker_share_tokens(
    worker_id: str,
    supabase = Depends(get_supabase)
):
    """
    Get all active share tokens for a worker.
    Used for token management in admin/worker dashboard.
    """
    try:
        result = supabase.table("share_tokens")\
            .select("*")\
            .eq("worker_id", worker_id)\
            .order("created_at", desc=True)\
            .execute()
        
        # Filter out expired tokens
        now = datetime.now(timezone.utc)
        active_tokens = [
            t for t in result.data 
            if datetime.fromisoformat(t["expires_at"]) > now
        ]
        
        return {
            "worker_id": worker_id,
            "active_tokens_count": len(active_tokens),
            "tokens": active_tokens
        }
        
    except Exception as e:
        logger.error(f"[SHARE_TOKEN] Error fetching tokens for worker {worker_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/profile/{token}")
async def get_shared_worker_profile(
    token: str,
    supabase = Depends(get_supabase)
):
    """
    Get public worker profile using a share token.
    Returns LIMITED public information about the worker.
    Does NOT require authentication.
    """
    try:
        logger.info(f"[SHARE_TOKEN] Fetching profile for token: {token[:8]}...")
        
        # Look up token in database
        result = supabase.table("share_tokens")\
            .select("*")\
            .eq("token", token)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share token not found"
            )
        
        token_record = result.data[0]
        worker_id = token_record["worker_id"]
        expires_at = datetime.fromisoformat(token_record["expires_at"])
        now = datetime.now(timezone.utc)
        
        # Check expiry
        if now > expires_at:
            logger.warn(f"[SHARE_TOKEN] Token expired for worker {worker_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Share token has expired"
            )
        
        # Check max uses
        if token_record.get("max_uses") is not None:
            if token_record["use_count"] >= token_record["max_uses"]:
                logger.warn(f"[SHARE_TOKEN] Token max uses exceeded for worker {worker_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Share token use limit exceeded"
                )
        
        # Fetch worker data (only PUBLIC fields)
        worker_result = supabase.table("workers")\
            .select("id, name, gig_platform, shift,plan, gig_score, portfolio_score")\
            .eq("id", worker_id)\
            .execute()
        
        if not worker_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Worker not found"
            )
        
        worker = worker_result.data[0]
        
        # Increment use count
        supabase.table("share_tokens")\
            .update({"use_count": token_record["use_count"] + 1})\
            .eq("token", token)\
            .execute()
        
        logger.info(f"[SHARE_TOKEN] Profile fetched for worker {worker_id}")
        
        shift_value = worker.get("shift", "flexible")
        shift_display = "Evening" if str(shift_value).lower() == "day" else str(shift_value).capitalize()
        platform_value = worker.get("gig_platform") or worker.get("platform") or "zomato"

        # Return PUBLIC profile only (no phone, email, UPI, etc)
        return {
            "name": worker.get("name", "Unknown"),
            "platform": str(platform_value).capitalize(),
            "shift": shift_display,
            "plan": worker.get("plan", "—"),
            "gig_score": worker.get("gig_score", 0),
            "portfolio_score": worker.get("portfolio_score", 0),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SHARE_TOKEN] Error fetching profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching profile: {str(e)}"
        )


@router.patch("/profile/{token}")
async def update_shared_worker_profile(
    token: str,
    request: UpdateSharedWorkerProfileRequest,
    supabase = Depends(get_supabase)
):
    """
    Update worker preferences using share token authentication.
    This is used by the worker PWA to keep bot and dashboard data in sync.
    """
    try:
        token_result = (
            supabase.table("share_tokens")
            .select("worker_id, expires_at")
            .eq("token", token)
            .execute()
        )

        if not token_result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share token not found")

        token_record = token_result.data[0]
        expires_at = datetime.fromisoformat(token_record["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Share token has expired")

        updates = {}

        if request.gig_platform is not None:
            platform_norm = request.gig_platform.strip().lower()
            if platform_norm not in ALLOWED_PLATFORMS:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Platform must be Zomato or Swiggy")
            updates["gig_platform"] = platform_norm.capitalize()
            updates["platform"] = platform_norm

        if request.shift is not None:
            shift_norm = request.shift.strip().lower()
            if shift_norm not in ALLOWED_SHIFTS:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Shift must be Flexible, Morning, Evening, or Night")
            if shift_norm == "evening":
                shift_norm = "day"
            updates["shift"] = shift_norm

        if request.gig_score is not None:
            gig_score = float(request.gig_score)
            if gig_score < 0 or gig_score > 100:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="gig_score must be between 0 and 100")
            updates["gig_score"] = gig_score

        if request.portfolio_score is not None:
            portfolio_score = float(request.portfolio_score)
            if portfolio_score < 0 or portfolio_score > 100:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="portfolio_score must be between 0 and 100")
            updates["portfolio_score"] = portfolio_score

        if not updates:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No valid fields provided")

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        worker_id = token_record["worker_id"]
        supabase.table("workers").update(updates).eq("id", worker_id).execute()

        refreshed = (
            supabase.table("workers")
            .select("name, gig_platform, shift, plan, gig_score, portfolio_score")
            .eq("id", worker_id)
            .execute()
        )

        worker = (refreshed.data or [{}])[0]
        shift_value = worker.get("shift", "flexible")
        shift_display = "Evening" if str(shift_value).lower() == "day" else str(shift_value).capitalize()

        return {
            "message": "Profile updated",
            "profile": {
                "name": worker.get("name", "Unknown"),
                "platform": worker.get("gig_platform", "—"),
                "shift": shift_display,
                "plan": worker.get("plan", "—"),
                "gig_score": worker.get("gig_score", 0),
                "portfolio_score": worker.get("portfolio_score", 0),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SHARE_TOKEN] Error updating profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )

@router.delete("/{token_id}")
async def revoke_share_token(
    token_id: str,
    supabase = Depends(get_supabase)
):
    """
    Revoke/delete a share token.
    Used to invalidate a previously shared link.
    """
    try:
        result = supabase.table("share_tokens")\
            .delete()\
            .eq("id", token_id)\
            .execute()
        
        logger.info(f"[SHARE_TOKEN] Revoked token: {token_id}")
        
        return {"message": "Share token revoked successfully"}
        
    except Exception as e:
        logger.error(f"[SHARE_TOKEN] Error revoking token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
