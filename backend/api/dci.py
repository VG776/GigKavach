"""
api/dci.py — DCI Engine Endpoints (City-Aware)
────────────────────────────────────────────────────
Exposes the Disruption Composite Index (DCI) for external systems
(frontend dashboards, analytics tools).

Endpoints:
  GET /api/v1/dci/{pincode}              — Current DCI + 24h history
  GET /api/v1/dci/latest-alerts          — Latest high-DCI alert zones
  GET /api/v1/dci/city-weights           — Full city weight table (all 5 cities)
  GET /api/v1/dci/city-weights/{city}    — Weight profile for a specific city
  POST /api/v1/dci/calculate             — Ad-hoc DCI calculation with city weights
"""

from fastapi import APIRouter, HTTPException, Depends, Path, Request, Response
from typing import Dict, Any, List, Optional
import datetime
import json
import asyncio
from pydantic import BaseModel, Field

from utils.redis_client import get_redis
from utils.supabase_client import get_supabase
from config.settings import settings
from config.city_dci_weights import (
    get_all_city_weights,
    get_city_weights,
    resolve_city_from_pincode,
    list_supported_cities,
    normalise_city_name,
    GLOBAL_FALLBACK_WEIGHTS,
)
from services.dci_engine import (
    calculate_dci,
    get_severity_tier,
    is_payout_triggered,
    get_city_dci_profile,
    get_dominant_risk_component,
    get_dynamic_weights,
)
from api.auth import verify_admin
from utils.audit_logger import log_audit_event
import logging

logger = logging.getLogger("gigkavach.api.dci")

router = APIRouter(tags=["DCI Engine"])


# ─── Utilities ────────────────────────────────────────────────────────────────

def fetch_history_sync(pincode: str) -> list:
    """Fetches last 24h of DCI logs from Supabase (blocking — run in thread)."""
    sb = get_supabase()
    if not sb or not settings.SUPABASE_URL:
        return []

    time_threshold = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
    ).isoformat()

    try:
        response = (
            sb.table("dci_logs")
              .select("*")
              .eq("pincode", pincode)
              .gte("created_at", time_threshold)
              .order("created_at", desc=True)
              .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"Failed fetching DCI history: {e}")
        return []


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class LatestDCIAlert(BaseModel):
    pincode: str
    area_name: str
    dci_score: float
    triggered_at: str


class CityWeightProfile(BaseModel):
    city: str
    weights: Dict[str, float]
    dominant_risk: str
    description: str
    is_supported: bool
    global_fallback_used: bool = False


class AdHocDCIRequest(BaseModel):
    weather_score: float = Field(ge=0, le=100, description="Rainfall/flood score 0-100")
    aqi_score: float = Field(ge=0, le=100, description="Air quality score 0-100")
    heat_score: float = Field(ge=0, le=100, description="Heat stress score 0-100")
    social_score: float = Field(ge=0, le=100, description="Social disruption score 0-100")
    platform_score: float = Field(ge=0, le=100, description="Platform signal score 0-100")
    city: Optional[str] = Field(default="default", description="City name for weight profile")
    pincode: Optional[str] = Field(default=None, description="Pincode (used to resolve city if city not provided)")
    ndma_override: bool = Field(default=False, description="Force catastrophic DCI (95)")


class AdHocDCIResponse(BaseModel):
    dci_score: int
    severity_tier: str
    payout_triggered: bool
    city: str
    weights_used: Dict[str, float]
    dominant_risk: str
    component_contributions: Dict[str, float]

class PincodeWeightResponse(BaseModel):
    pincode: str
    city: str
    weights: Dict[str, float]
    cached_status: bool
    last_updated: str
    model_r2_score: float = 0.85
    limit_remaining: int


class RecomputeRequest(BaseModel):
    pincode: str = Field(..., pattern=r"^\d{6}$")
    force_recompute: bool = True


class RecomputeResponse(BaseModel):
    pincode: str
    city: str
    updated_weights: Dict[str, float]
    timestamp: str
    status: str = "success"


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/dci/{pincode}", response_model=Dict[str, Any])
async def get_dci_status(pincode: str):
    """
    Returns the current DCI score breakdown and 24h historical data for a pincode.

    Response includes:
      - current: Full latest DCI data with city + weights_used fields
      - history_24h: Condensed time-series for charts
      - city: Resolved city for this pincode
      - weights: City-specific weights applied to this zone

    Raises 404 if the poller has not yet run for this zone.
    """
    rc = await get_redis()

    cache_key = f"dci:score:{pincode}"
    current_raw = await rc.get(cache_key)

    if not current_raw:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No active DCI data for pin code {pincode}. "
                f"Ensure the cron poller is tracking this zone."
            ),
        )

    current_data = json.loads(current_raw)

    # Fetch history in a thread to keep event loop free
    history_data = await asyncio.to_thread(fetch_history_sync, pincode)

    condensed_history = [
        {
            "timestamp": row["created_at"],
            "score":     row["total_score"],
            "severity":  row["severity_tier"],
            "city":      row.get("city", "default"),
        }
        for row in history_data
    ]

    # Resolve city for the response envelope (may already be in cache)
    city = current_data.get("city") or resolve_city_from_pincode(pincode)
    weights = get_city_weights(city)

    return {
        "pincode":    pincode,
        "city":       city,
        "weights":    weights,
        "current":    current_data,
        "history_24h": condensed_history,
    }


@router.get("/dci/latest-alerts", response_model=List[LatestDCIAlert])
async def get_latest_high_dci_alerts():
    """
    Returns latest 4 DCI events where score > 65.
    Used by the dashboard 'Active Zones' panel.
    """
    try:
        sb = get_supabase()

        result = (
            sb.table("dci_events")
              .select("pin_code, city, dci_score, triggered_at")
              .order("triggered_at", desc=True)
              .limit(50)
              .execute()
        )

        rows = result.data or []
        alerts = []

        for row in rows:
            try:
                dci = float(row.get("dci_score") or 0)
                if dci > 65:
                    alerts.append(
                        LatestDCIAlert(
                            pincode=row.get("pin_code"),
                            area_name=row.get("city") or "Unknown",
                            dci_score=dci,
                            triggered_at=str(row.get("triggered_at")),
                        )
                    )
                if len(alerts) == 4:
                    break
            except Exception as e:
                logger.warning(f"Failed to parse DCI alert row: {e}")
                continue

        return alerts

    except Exception as e:
        logger.error(f"Error fetching latest DCI alerts: {e}")
        raise HTTPException(status_code=503, detail="Failed to fetch DCI alerts")


@router.get("/dci/city-weights", response_model=Dict[str, Any])
async def get_all_city_weight_profiles():
    """
    Returns the complete DCI weight configuration for all supported cities.

    This is used by:
      - The admin dashboard weight-profile widget
      - Client apps that display city-specific risk explanations
      - QA teams verifying the correct weights are deployed

    Response shape:
      {
        "supported_cities": ["Mumbai", "Delhi", ...],
        "global_fallback": {...},
        "profiles": {
          "Mumbai": { weights: {...}, dominant_risk: "weather", ... },
          ...
        }
      }
    """
    supported = list_supported_cities()
    all_weights = get_all_city_weights()

    profiles = {}
    for city in supported:
        profiles[city] = get_city_dci_profile(city)

    return {
        "supported_cities":   supported,
        "global_fallback":    dict(GLOBAL_FALLBACK_WEIGHTS),
        "profiles":           profiles,
        "note": (
            "Weights are climate-calibrated per city. Cities not in "
            "'supported_cities' list use 'global_fallback' weights."
        ),
    }


@router.get("/dci/city-weights/{city}", response_model=CityWeightProfile)
async def get_city_weight_profile(city: str):
    """
    Returns the DCI weight profile for a specific city.

    Accepts canonical names and common aliases:
      /dci/city-weights/Mumbai
      /dci/city-weights/bangalore  (alias → Bengaluru)
      /dci/city-weights/bombay     (alias → Mumbai)

    Returns 404 if city is completely unknown (not a supported city or alias).
    """
    canonical = normalise_city_name(city)

    if canonical is None and city not in ("default", ""):
        supported = list_supported_cities()
        raise HTTPException(
            status_code=404,
            detail=(
                f"City '{city}' not recognised. "
                f"Supported cities: {supported}. "
                f"Common aliases like 'bangalore', 'bombay', 'calcutta' are also accepted."
            ),
        )

    resolved = canonical or "default"
    profile = get_city_dci_profile(resolved)
    weights = get_city_weights(resolved)

    return CityWeightProfile(
        city=resolved,
        weights=weights,
        dominant_risk=profile["dominant_risk"],
        description=profile["description"],
        is_supported=profile["is_supported"],
        global_fallback_used=profile["fallback_used"],
    )


@router.post("/dci/calculate", response_model=AdHocDCIResponse)
async def calculate_dci_adhoc(request: AdHocDCIRequest):
    """
    Ad-hoc DCI calculation endpoint — useful for:
      - Dashboard 'what-if' simulations
      - Judge console disruption scenarios
      - Testing city weight behaviour without triggering a full poller cycle

    Accepts component scores (0–100 each) plus optional city/pincode.
    Returns calculated DCI using the city's specific weight profile.
    """
    # Resolve city: prefer explicit city param; fall back to pincode resolution
    city = request.city or "default"
    if (city == "default" or not city) and request.pincode:
        city = resolve_city_from_pincode(request.pincode)

    weights = get_city_weights(city)

    dci_score = calculate_dci(
        weather_score=request.weather_score,
        aqi_score=request.aqi_score,
        heat_score=request.heat_score,
        social_score=request.social_score,
        platform_score=request.platform_score,
        ndma_override=request.ndma_override,
        city=city,
    )

    # Compute individual weighted contributions for breakdown transparency
    contributions = {
        "weather":  round(request.weather_score * weights["weather"], 2),
        "aqi":      round(request.aqi_score * weights["aqi"], 2),
        "heat":     round(request.heat_score * weights["heat"], 2),
        "social":   round(request.social_score * weights["social"], 2),
        "platform": round(request.platform_score * weights["platform"], 2),
    }

    logger.info(
        f"[DCI ADHOC] city={city} | "
        f"DCI={dci_score} | contributions={contributions}"
    )

    return AdHocDCIResponse(
        dci_score=dci_score,
        severity_tier=get_severity_tier(dci_score),
        payout_triggered=is_payout_triggered(dci_score),
        city=city,
        weights_used=weights,
        dominant_risk=get_dominant_risk_component(city),
        component_contributions=contributions,
    )
@router.get("/dci/weights/{pincode}", response_model=PincodeWeightResponse)
async def get_pincode_weights(
    request: Request,
    pincode: str = Path(..., pattern=r"^\d{6}$", description="Exactly 6 digits")
):
    """
    Returns the specific climate weights applied to a 6-digit pincode.
    Includes rate limiting (100 req/min) and cache status.
    """
    rc = await get_redis()
    client_ip = request.client.host
    rl_key = f"rl:weights:{client_ip}"

    # 1. Rate Limiting Logic (100 req / minute)
    try:
        req_count = await rc.incr(rl_key)
        await rc.expire(rl_key, 60)
        
        if req_count > 100:
            logger.warning(f"[RATE LIMIT] IP {client_ip} exceeded weight lookup quota")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Maximum 100 requests per minute allowed."
            )
    except (ValueError, TypeError):
        req_count = 1

    # 2. Check Cache Status
    cache_key = f"dci:score:{pincode}"
    cached_data = await rc.get(cache_key)
    is_cached = cached_data is not None
    
    last_updated = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if is_cached:
        try:
            parsed = json.loads(cached_data)
            last_updated = parsed.get("updated_at", last_updated)
        except:
            pass

    # 3. Resolve City and Weights
    city = resolve_city_from_pincode(pincode)
    weights = get_city_weights(city)

    logger.info(f"[WEIGHT LOOKUP] ip={client_ip} | pincode={pincode} | city={city}")

    return PincodeWeightResponse(
        pincode=pincode,
        city=city,
        weights=weights,
        cached_status=is_cached,
        last_updated=last_updated,
        model_r2_score=0.85,  # Placeholder per requirements
        limit_remaining=max(0, 100 - req_count)
    )


@router.post("/dci/weights/recompute", response_model=RecomputeResponse)
async def recompute_weights(
    request: RecomputeRequest,
    user: dict = Depends(verify_admin)
):
    """
    Force recomputation of DCI weights for a zone.
    RESTRICTED: Admin role only. Generates audit trail.
    """
    pincode = request.pincode
    
    # 1. Resolve & Recompute
    result = get_dynamic_weights(pincode, force_recompute=request.force_recompute)
    
    # 2. Audit Trail Logging
    log_audit_event(
        user_id=user.get("id"),
        action="RECOMPUTE_WEIGHTS",
        details={
            "pincode": pincode,
            "force": request.force_recompute,
            "city_resolved": result["city"],
            "weights_applied": result["weights"]
        }
    )
    
    logger.info(f"🔨 ADMIN ACTION: Weights recomputed for {pincode} by {user.get('email')}")
    
    return RecomputeResponse(
        pincode=pincode,
        city=result["city"],
        updated_weights=result["weights"],
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
