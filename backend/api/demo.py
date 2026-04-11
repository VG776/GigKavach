"""
api/demo.py — Judge's Demo Mode Router (City-Aware)
──────────────────────────────────────────────────────
Provides a safe, non-blocking interface to manually trigger disruption sequences.
Offloads all database writes to a separate thread to prevent event-loop freezing.

Now city-aware: the demo DCI score is computed using the correct city-specific
weight profile so the injected log accurately reflects what a real disruption
event would look like in that city.
"""

import asyncio
import datetime
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from utils.supabase_client import get_supabase
from config.settings import settings
from config.city_dci_weights import (
    resolve_city_from_pincode,
    get_city_weights,
    list_supported_cities,
)
from services.dci_engine import calculate_dci, get_severity_tier

logger = logging.getLogger("gigkavach.demo")
router = APIRouter(tags=["Judge Demo Mode"])

# Default testing worker and zone
DEMO_WORKER_ID = "49766c71-ebb8-42b6-b090-e57502b142ec"  # Admin user as demo worker
DEMO_PINCODE = "560001"

# Canonical factor → weight key mapping
FACTOR_TO_COMPONENT = {
    "rainfall": "weather",
    "weather":  "weather",
    "aqi":      "aqi",
    "heat":     "heat",
    "social":   "social",
    "platform": "platform",
}

class DemoTriggerRequest(BaseModel):
    factor: str = Field(description="Component to spike: rainfall/aqi/heat/social/platform")
    score: Optional[float] = Field(default=85.0, ge=0, le=100, description="Component score 0-100")
    city: Optional[str] = Field(
        default=None,
        description=(
            "City for weight profile (Mumbai/Delhi/Bengaluru/Chennai/Kolkata). "
            "If omitted, city is resolved from pincode."
        )
    )
    pincode: Optional[str] = Field(
        default=None,
        description="Override pincode for demo (defaults to Bengaluru 560001)"
    )

def trigger_disruption_sync(factor: str, score: float, city: str, pincode: str):
    """
    Synchronous DB injection logic — runs in a thread to keep FastAPI responsive.

    Computes a properly weighted DCI score using the city's weight profile:
      - Sets the triggered factor's component score to `score`
      - Sets all other components to a baseline of 10 (background noise)
      - Applies city-specific weights via calculate_dci()

    This means a 'rainfall' trigger in Mumbai produces a much higher DCI than
    the same trigger in Delhi (because Mumbai's rainfall weight is 0.40 vs
    Delhi's 0.15), accurately simulating real city-specific risk.
    """
    sb = get_supabase()

    weights = get_city_weights(city)
    component_key = FACTOR_TO_COMPONENT.get(factor, "weather")

    # Background baseline (other components not at zero — represents ambient conditions)
    BASELINE = 10.0
    comp_scores = {
        "weather":  BASELINE,
        "aqi":      BASELINE,
        "heat":     BASELINE,
        "social":   BASELINE,
        "platform": BASELINE,
    }
    comp_scores[component_key] = float(score)

    # Compute properly weighted DCI using city weights
    total_score = calculate_dci(
        weather_score=comp_scores["weather"],
        aqi_score=comp_scores["aqi"],
        heat_score=comp_scores["heat"],
        social_score=comp_scores["social"],
        platform_score=comp_scores["platform"],
        city=city,
    )

    severity = get_severity_tier(total_score)

    # Individual contributions (for dashboard display transparency)
    contributions = {
        k: round(v * weights[k], 2) for k, v in comp_scores.items()
    }

    logger.info(
        f"⚖️ JUDGE CONSOLE | city={city} | pincode={pincode} | factor={factor} "
        f"| raw_score={score} | weighted_DCI={total_score} | severity={severity}"
    )

    try:
        # Insert into dci_logs with city + weights snapshot
        sb.table("dci_logs").insert({
            "pincode":              pincode,
            "city":                 city,
            "total_score":          total_score,
            "rainfall_score":       int(comp_scores["weather"]),
            "aqi_score":            int(comp_scores["aqi"]),
            "heat_score":           int(comp_scores["heat"]),
            "social_score":         int(comp_scores["social"]),
            "platform_score":       int(comp_scores["platform"]),
            "severity_tier":        severity,
            "ndma_override_active": False,
            "weights_used":         weights,
            "dominant_risk":        component_key,
        }).execute()

        logger.info(f"✅ Demo: Inserted DCI log | DCI={total_score} | city={city} | pincode={pincode}")

        # Insert simulated payout (non-blocking failure)
        try:
            sb.table("payouts").insert({
                "worker_id":    DEMO_WORKER_ID,
                "dci_event_id": None,
                "final_amount": round(450.0 + (total_score * 2), 2),
                "status":       "completed",
                "fraud_score":  0.05,
            }).execute()
            logger.info(f"✅ Demo: Inserted payout for worker {DEMO_WORKER_ID}")
        except Exception as pe:
            logger.warning(f"Demo: Payout insert failed (non-critical): {pe}")

        return {
            "success":       True,
            "total_dci":     total_score,
            "severity":      severity,
            "contributions": contributions,
            "weights":       weights,
        }

    except Exception as e:
        logger.error(f"Demo Injection Failed: {e}")
        return None


@router.post("/demo/trigger-disruption")
async def trigger_demo_disruption(req: DemoTriggerRequest):
    """
    Entry point for the Judge Console.

    Async wrapper around the threaded DB injection worker.
    Supports optional city and pincode — if omitted, defaults to Bengaluru (560001).

    Supported cities: Mumbai | Delhi | Bengaluru | Chennai | Kolkata
    Supported factors: rainfall | aqi | heat | social | platform
    """
    # Resolve city from request or pincode
    pincode = req.pincode or DEMO_PINCODE
    city = req.city
    if city:
        from config.city_dci_weights import normalise_city_name
        city = normalise_city_name(city) or resolve_city_from_pincode(pincode)
    else:
        city = resolve_city_from_pincode(pincode)

    factor = req.factor.lower().strip()
    if factor not in FACTOR_TO_COMPONENT:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown factor '{factor}'. "
                f"Valid options: {list(FACTOR_TO_COMPONENT.keys())}"
            ),
        )

    logger.info(
        f"⚖️ JUDGE CONSOLE: Triggering '{factor}' disruption | "
        f"city={city} | pincode={pincode} | score={req.score}"
    )

    result = await asyncio.to_thread(
        trigger_disruption_sync, factor, req.score, city, pincode
    )

    if result is None:
        raise HTTPException(status_code=500, detail="Database injection failed")

    return {
        "status":          "success",
        "factor":          factor,
        "city":            city,
        "pincode":         pincode,
        "raw_score":       req.score,
        "weighted_dci":    result["total_dci"],
        "severity":        result["severity"],
        "weights_applied": result["weights"],
        "contributions":   result["contributions"],
        "message": (
            f"Simulated '{factor}' disruption injected for {city} (pincode {pincode}). "
            f"Weighted DCI = {result['total_dci']} ({result['severity']})."
        ),
        "supported_cities": list_supported_cities(),
    }
