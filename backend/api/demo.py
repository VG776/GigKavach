"""
api/demo.py — Judge's Demo Mode Router
──────────────────────────────────────
Provides a safe, non-blocking interface to manually trigger disruption sequences.
Offloads all database writes to a separate thread to prevent event-loop freezing.
"""

import asyncio
import datetime
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.supabase_client import get_supabase
from config.settings import settings

logger = logging.getLogger("gigkavach.demo")
router = APIRouter(tags=["Judge Demo Mode"])

# Default testing worker and zone
DEMO_WORKER_ID = "49766c71-ebb8-42b6-b090-e57502b142ec"  # Admin user as demo worker
DEMO_PINCODE = "560001"

class DemoTriggerRequest(BaseModel):
    factor: str  # rainfall, aqi, heat, social, platform
    score: Optional[float] = 85.0

def trigger_disruption_sync(factor: str, score: float):
    """
    Synchronous DB injection logic. 
    Runs in a separate thread to keep FastAPI responsive.
    """
    sb = get_supabase()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # 1. Map factor to component scores
    components = {
        "rainfall_score": 10,
        "aqi_score": 10,
        "heat_score": 10,
        "social_score": 10,
        "platform_score": 10
    }
    
    factor_map = {
        "rainfall": "rainfall_score",
        "aqi": "aqi_score",
        "heat": "heat_score",
        "social": "social_score",
        "platform": "platform_score"
    }
    
    target_key = factor_map.get(factor, "rainfall_score")
    components[target_key] = int(score)
    
    # Calculate weighted total (approximation for demo clarity)
    total_score = int(score) 
    
    try:
        # A. Insert into dci_logs  
        sb.table("dci_logs").insert({
            "pincode": DEMO_PINCODE,
            "total_score": total_score,
            "rainfall_score": 10,
            "aqi_score": 10,
            "heat_score": 10,
            "social_score": 10,
            "platform_score": 10,
            "severity_tier": "catastrophic" if total_score >= 85 else ("moderate" if total_score >= 65 else "none"),
            "ndma_override_active": False,
        }).execute()
        
        logger.info(f"✅ Demo: Inserted DCI log with score {total_score} for pincode {DEMO_PINCODE}")
        
        # C. Insert simulated Payout (optional - don't fail if this fails)
        try:
            sb.table("payouts").insert({
                "worker_id": DEMO_WORKER_ID,
                "dci_event_id": None, 
                "final_amount": 450.0 + (score * 2),
                "status": "completed",
                "fraud_score": 0.05,
            }).execute()
            logger.info(f"✅ Demo: Inserted payout for worker {DEMO_WORKER_ID}")
        except Exception as pe:
            logger.warning(f"Demo: Payout insert failed (non-critical): {pe}")
        
        return True
    except Exception as e:
        logger.error(f"Demo Injection Failed: {e}")
        return False

@router.post("/demo/trigger-disruption")
async def trigger_demo_disruption(req: DemoTriggerRequest):
    """
    Entry point for the Judge Console. 
    Async wrapper around the threaded DB worker.
    """
    logger.info(f"⚖️ JUDGE CONSOLE: Triggering disruption sequence for factor: {req.factor}")
    
    # Hand off blocking DB work to a thread
    success = await asyncio.to_thread(trigger_disruption_sync, req.factor, req.score)
    
    if not success:
        raise HTTPException(status_code=500, detail="Database injection failed")
        
    return {
        "status": "success",
        "factor": req.factor,
        "message": f"Simulated {req.factor} disruption injected successfully.",
        "pincode": DEMO_PINCODE
    }
