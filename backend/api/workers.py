"""
api/workers.py
━━━━━━━━━━━━━━
FastAPI router for worker management, registration, and profile queries.
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field

from config.settings import settings
from utils.db import get_supabase
from services.share_tokens_service import generate_share_token
from models.worker import (
    WorkerCreate, 
    WorkerUpdate, 
    RegistrationResponse, 
    WorkerProfile,
    PlanType as WorkerPlanType,
    ShiftType
)

router = APIRouter(prefix="/workers", tags=["Workers"])
logger = logging.getLogger("gigkavach.api.workers")

# ─── Config ───────────────────────────────────────────────────────────────────

# Mapping of PlanType to (Weekly Premium in ₹, Daily Coverage %)
PLAN_PREMIUMS = {
    WorkerPlanType.BASIC: (30.0, 40.0),
    WorkerPlanType.PLUS:  (37.0, 50.0),
    WorkerPlanType.PRO:   (44.0, 70.0)
}

def normalize_phone(phone: str) -> str:
    """Standardizes phone numbers for DB lookups."""
    phone = phone.strip().replace(" ", "")
    if not phone.startswith('+'):
        if len(phone) == 10:
            phone = "+91" + phone
        else:
            phone = "+" + phone
    return phone

@router.post("/register", response_model=RegistrationResponse)
async def register_worker(worker: WorkerCreate):
    """Registers a new worker and activates Shield Basic coverage."""
    sb = get_supabase()
    
    # 1. Standardize Phone & Platform
    worker.phone_number = normalize_phone(worker.phone_number)
    
    # 2. Check for duplicate
    existing = sb.table("workers").select("id").eq("phone", worker.phone_number).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # 3. Create Worker Record
    worker_id = str(uuid.uuid4())
    worker_data = {
        "id": worker_id,
        "name": worker.name,
        "phone": worker.phone_number,
        "gig_platform": worker.platform.value,
        "shift": worker.shift.value,
        "upi_id": worker.upi_id,
        "pin_codes": worker.pin_codes,
        "gig_score": 95.0,
        "is_active": True
    }
    
    res = sb.table("workers").insert(worker_data).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create worker")
    
    # 4. Activate Coverage (24h delay logic)
    now = datetime.now(timezone.utc)
    week_end = (now + timedelta(days=7)).replace(hour=23, minute=59, second=59).isoformat()
    active_from = (now + timedelta(hours=24)).isoformat()
    
    policy_data = {
        "worker_id": worker_id,
        "plan": worker.plan.value if hasattr(worker, 'plan') else "basic",
        "status": "active",
        "coverage_active_from": active_from,
        "week_end": week_end
    }
    sb.table("policies").insert(policy_data).execute()

    # 5. Generate Access Token
    token_data = await generate_share_token(worker_id)
    
    mask_phone = f"+91******{worker.phone_number[-4:]}"
    message = (
        f"✅ Registration Complete!\n\n"
        f"Worker ID: {worker_id[:8]}...\n"
        f"Phone: {mask_phone}\n\n"
        f"🛡️ Shield Basic Activated (Waiting 24h wait period)\n"
        f"Access Dashboard: {token_data['share_url']}"
    )
    
    return RegistrationResponse(
        message=message,
        worker_id=worker_id,
        share_token=token_data["share_token"],
        share_url=token_data["share_url"],
        phone_number=worker.phone_number,
        plan=worker.plan if hasattr(worker, 'plan') else WorkerPlanType.BASIC,
        coverage_active_from=datetime.fromisoformat(active_from),
        policy_id=str(uuid.uuid4()) # Mock policy ID for response consistency
    )

@router.get("/profile/{worker_id}", response_model=WorkerProfile)
async def get_worker_profile(worker_id: str):
    """Fetches full worker profile including GigScore and active policies."""
    sb = get_supabase()
    
    worker_res = sb.table("workers").select("*, policies(*)").eq("id", worker_id).single().execute()
    if not worker_res.data:
        raise HTTPException(status_code=404, detail="Worker not found")
        
    return worker_res.data

@router.patch("/shift-status", status_code=status.HTTP_200_OK)
async def update_shift_status(worker_id: str, is_working: bool):
    """
    PWA Endpoint: Manually toggle shift state.
    Synchronizes DB status and Redis telemetry gait.
    """
    sb = get_supabase()
    rc = await get_redis()
    
    # 1. Update Database
    res = sb.table("workers").update({"is_working": is_working, "last_seen_at": datetime.now().isoformat()}).eq("id", worker_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Worker not found")
        
    # 2. Update Redis Gate
    shift_key = f"shift_active:{worker_id}"
    if is_working:
        await rc.set(shift_key, datetime.now().isoformat())
        await rc.expire(shift_key, 43200)
    else:
        await rc.delete(shift_key)
        
    return {"status": "success", "is_working": is_working}
