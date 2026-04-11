"""
api/auth.py — Authentication Endpoints
──────────────────────────────────────
Handles user authentication using Supabase Auth.
Provides login, logout, token refresh, and current user endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import httpx
import logging

from config.settings import settings

logger = logging.getLogger("gigkavach.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


# ─── Request/Response Models ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    role: Optional[str] = "user"
    created_at: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── Helper Functions ───────────────────────────────────────────────────────

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify JWT token with Supabase.
    Returns user data if valid, raises 401 if invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.SUPABASE_ANON_KEY,
            },
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return response.json()


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
async def login(credentials: LoginRequest):
    """
    Authenticate user with email/password.
    Returns access token, refresh token, and user data.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            json={
                "email": credentials.email,
                "password": credentials.password,
            },
        )
        
        if response.status_code != 200:
            error_data = response.json()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_data.get("error_description", "Invalid credentials"),
            )
        
        data = response.json()
        return AuthResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data["token_type"],
            expires_in=data["expires_in"],
            user=data["user"],
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            json={"refresh_token": request.refresh_token},
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        data = response.json()
        return AuthResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data["token_type"],
            expires_in=data["expires_in"],
            user=data["user"],
        )


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout user by invalidating token.
    """
    if not credentials:
        return {"message": "No active session"}
    
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{settings.SUPABASE_URL}/auth/v1/logout",
            headers={
                "Authorization": f"Bearer {credentials.credentials}",
                "apikey": settings.SUPABASE_ANON_KEY,
            },
        )
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(user: dict = Depends(verify_token)):
    """
    Get current authenticated user info.
    """
    return UserResponse(
        id=user.get("id"),
        email=user.get("email"),
        role=user.get("user_metadata", {}).get("role", "user"),
        created_at=user.get("created_at"),
    )


async def verify_admin(user: dict = Depends(verify_token)) -> dict:
    """
    Verify that the authenticated user has the 'admin' role.
    Raises 403 Forbidden if the user is not an admin.
    """
    role = user.get("user_metadata", {}).get("role", "user")
    if role != "admin":
        logger.warning(f"🚫 Unauthorized admin access attempt by {user.get('email')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this operation",
        )
    return user


@router.get("/verify")
async def verify_auth(user: dict = Depends(verify_token)):
    """
    Verify if token is valid (returns 200 if valid, 401 if not).
    Useful for frontend route protection.
    """
    return {"valid": True, "user_id": user.get("id")}
