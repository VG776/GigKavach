"""
api/telemetry.py
━━━━━━━━━━━━━━━━
FastAPI router for receiving real-time worker telemetry.
"""

from fastapi import APIRouter, HTTPException, Depends
from models.telemetry import TelemetrySubmission, TelemetryResponse
from services.telemetry_service import telemetry_processor
from utils.redis_client import get_redis
import json

router = APIRouter(prefix="/telemetry", tags=["Fraud Detection"])

@router.post("/submit", response_model=TelemetryResponse)
async def submit_telemetry(submission: TelemetrySubmission):
    """
    Ingests raw location data from the worker PWA.
    Ensures the worker is currently 'on shift' in Redis before processing.
    """
    redis = await get_redis()
    
    # 1. Verification: Is the worker on an active shift?
    shift_status = await redis.get(f"shift_active:{submission.worker_id}")
    if not shift_status:
        raise HTTPException(status_code=403, detail="Telemetry rejected: No active shift found.")
        
    # 2. Persist raw data for window analysis
    await telemetry_processor.save_telemetry(
        submission.worker_id,
        submission.coordinates,
        submission.speed
    )
    
    # 3. Trigger immediate behavioral scan
    analysis = await telemetry_processor.analyze_movement(submission.worker_id)
    
    return {
        "status": "success",
        "is_suspicious": analysis["is_suspicious"],
        "teleportation_detected": analysis.get("teleportation_jumps", 0) > 0
    }
