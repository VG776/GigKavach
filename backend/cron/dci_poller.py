"""
cron/dci_poller.py — DCI Engine Poller (City-Aware)
────────────────────────────────────────────────────
Runs every 5 minutes driven by APScheduler.
Iterates over active zones (pin codes), fetches their Weather, AQI,
Heat, Social and Platform scores, computes the final Disruption
Composite Index (DCI) using CITY-SPECIFIC weights, and stores the
result in Redis and Supabase.

City resolution: Each pincode is resolved to its canonical city via
`resolve_city_from_pincode()` from config/city_dci_weights.py.  The
city is then passed through the full calculation chain so the correct
climate-appropriate weights are applied.
"""

import logging
import asyncio
import datetime
from typing import List

from services.weather_service import get_weather_score
from services.aqi_service import get_aqi_score
from services.heat_service import get_heat_score
from services.social_service import get_social_score
from services.platform_service import get_platform_score
from services.eligibility_service import check_eligibility
from services.dci_engine import (
    calculate_dci,
    get_severity_tier,
    build_dci_log_payload,
    is_payout_triggered,
)
from config.city_dci_weights import (
    resolve_city_from_pincode,
    get_city_weights,
)
from utils.redis_client import set_dci_cache
from utils.supabase_client import get_supabase
from utils.datetime_utils import get_current_shift_name
from config.settings import settings

logger = logging.getLogger("gigkavach.dci_poller")

# ─── Active Zones ─────────────────────────────────────────────────────────────
# In production this would be fetched dynamically from Supabase (all distinct
# pincodes from the workers table).  For the hackathon demo, we include 5 zones
# — one representative pincode per supported city.
DEMO_ACTIVE_ZONES: List[str] = [
    # Bengaluru zones (original demo)
    "560001",   # Bangalore Bazaar (city centre)
    "560037",   # Doddanekkundi (East Bengaluru)
    "560034",   # Agara
    "560038",   # Indiranagar
    "560068",   # Bommanahalli (South Bengaluru)
    # Mumbai zone
    "400001",   # Fort / CST (Mumbai city centre)
    "400050",   # Bandra West (popular delivery zone)
    "400097",   # Thane
    # Delhi zones
    "110001",   # Connaught Place (Delhi centre)
    "110019",   # Hauz Khas / South Delhi
    "110092",   # East Delhi
    # Chennai zones
    "600001",   # Parry's Corner (Chennai centre)
    "600020",   # T. Nagar (high-density)
    "600042",   # Anna Nagar
    # Kolkata zones
    "700001",   # BBD Bagh (Kolkata centre)
    "700019",   # Park Street
    "700091",   # Salt Lake (Bidhannagar)
]


async def get_active_zones() -> List[str]:
    """
    Returns the list of active pincodes to poll.

    Priority:
      1. Fetch distinct pincodes from live workers table in Supabase.
      2. Fall back to hard-coded DEMO_ACTIVE_ZONES if DB unavailable.
    """
    try:
        sb = get_supabase()
        if sb and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
            result = sb.table("workers").select("pincode").execute()
            pincodes = list({
                row["pincode"] for row in (result.data or [])
                if row.get("pincode")
            })
            if pincodes:
                logger.info(f"[DCI POLLER] Polling {len(pincodes)} live worker zones from DB.")
                return pincodes
    except Exception as e:
        logger.warning(f"[DCI POLLER] DB zone fetch failed: {e}. Using demo zones.")

    logger.info(f"[DCI POLLER] Using {len(DEMO_ACTIVE_ZONES)} demo zones.")
    return DEMO_ACTIVE_ZONES


def _insert_log_to_db(payload: dict) -> None:
    """Synchronous helper — executes Supabase insert in calling thread."""
    sb = get_supabase()
    if sb and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            sb.table("dci_logs").insert(payload).execute()
        except Exception as e:
            logger.error(f"[DCI POLLER] Failed to insert DCI log into Supabase: {e}")


async def trigger_recovery_alerts(pincode: str, dci_data: dict, final_dci: float) -> None:
    from api.whatsapp import send_whatsapp_alert
    sb = get_supabase()
    result = sb.table("workers").select("id").contains("pin_codes", [pincode]).eq("is_active", True).execute()
    active_workers_in_zone = [w["id"] for w in (result.data or [])]

    for worker_id in active_workers_in_zone:
        # Check eligibility and trigger alert
        logger.debug(f"[RECOVERY ALERT] Notifying worker={worker_id}")
        await send_whatsapp_alert(worker_id, "dci_recovery", {"pin_code": pincode, "dci": final_dci, "severity": dci_data.get("severity_tier", "normal")})


async def trigger_claims_pipeline(pincode: str, dci_data: dict, final_dci: float) -> None:
    """
    Evaluates all workers in the affected zone against the eligibility firewall,
    records valid claims for the claims_trigger pipeline, and fires WhatsApp alerts.
    """
    city = dci_data.get("city", "default")
    from api.whatsapp import send_whatsapp_alert
    from utils.supabase_client import get_supabase

    try:
        sb = get_supabase()
        # Query distinct workers who have this pincode in their pin_codes array and are active
        # Supabase syntax for 'array contains'
        result = (
            sb.table("workers")
            .select("id")
            .contains("pin_codes", [pincode])
            .eq("is_active", True)
            .execute()
        )
        active_workers_in_zone = [w["id"] for w in (result.data or [])]
    except Exception as e:
        logger.error(f"[CLAIMS PIPELINE] Worker lookup failed for {pincode}: {e}")
        active_workers_in_zone = []

    logger.info(
        f"[CLAIMS PIPELINE] Evaluating {len(active_workers_in_zone)} workers in "
        f"zone {pincode} / city={city} (DCI: {final_dci})"
    )

    for worker_id in active_workers_in_zone:
        eligible, reason = check_eligibility(worker_id, dci_event={
            "disruption_start": dci_data.get("updated_at"),
            "shift_affected":   dci_data.get("shift_active", "All"),
            "dci_score":        final_dci,
            "ndma_override_active": dci_data.get("ndma_override_active", False),
        })

        if eligible:
            logger.info(f"✅ PAYOUT APPROVED for Worker {worker_id} | DCI: {final_dci} | City: {city}")
            send_whatsapp_alert(worker_id, "disruption_alert", {"dci": final_dci})
        else:
            logger.warning(f"❌ PAYOUT REJECTED for Worker {worker_id} | Reason: {reason}")


async def process_zone(pincode: str) -> dict:
    """
    Fetches components and calculates DCI for a single zone.

    Resolution order:
      1. Resolve city from pincode (via city_dci_weights config)
      2. Fetch all 5 component scores concurrently
      3. calculate_dci() applies city-specific weights
      4. Persist to Redis + Supabase with city field
      5. Trigger claims pipeline if DCI ≥ threshold
    """
    # ── 1. Resolve city ───────────────────────────────────────────────────────
    city = resolve_city_from_pincode(pincode)
    weights = get_city_weights(city)

    logger.info(
        f"[DCI POLLER] Processing zone {pincode} | city={city} | "
        f"weights=W:{weights['weather']}/AQI:{weights['aqi']}/"
        f"H:{weights['heat']}/S:{weights['social']}/P:{weights['platform']}"
    )

    # ── 2. Fetch all 5 component scores concurrently ─────────────────────────
    results = await asyncio.gather(
        get_weather_score(pincode),
        get_aqi_score(pincode),
        get_social_score(pincode),
        get_platform_score(pincode),
        return_exceptions=True,
    )

    def _safe(result, default_score=0, default_extra=None):
        """Unwraps gather result; returns safe default on exceptions."""
        if isinstance(result, Exception):
            return {"score": default_score, **(default_extra or {})}
        return result

    weather_result  = _safe(results[0])
    aqi_result      = _safe(results[1])
    social_result   = _safe(results[2], default_extra={"ndma_active": False})
    platform_result = _safe(results[3])

    # Log exceptions
    for idx, label in enumerate(["Weather", "AQI", "Social", "Platform"]):
        if isinstance(results[idx], Exception):
            logger.error(f"[DCI POLLER] {label} error for {pincode}: {results[idx]}")

    # Heat score is derived from the now-cached weather data (avoids second HTTP hit)
    heat_result = await get_heat_score(pincode)

    w_score = float(weather_result.get("score", 0))
    a_score = float(aqi_result.get("score", 0))
    h_score = float(heat_result.get("score", 0))
    s_score = float(social_result.get("score", 0))
    p_score = float(platform_result.get("score", 0))

    # ── 3. Compute DCI using city-specific weights ────────────────────────────
    ndma_override = social_result.get("ndma_active", False)
    final_dci = calculate_dci(
        weather_score=w_score,
        aqi_score=a_score,
        heat_score=h_score,
        social_score=s_score,
        platform_score=p_score,
        ndma_override=ndma_override,
        city=city,
    )

    severity = get_severity_tier(final_dci)
    active_shift = get_current_shift_name()

    dci_data = {
        "pincode":             pincode,
        "city":                city,
        "dci_score":           final_dci,
        "severity_tier":       severity,
        "ndma_override_active": ndma_override,
        "shift_active":        active_shift,
        "weights_used":        weights,
        "components": {
            "rainfall": weather_result,
            "aqi":      aqi_result,
            "heat":     heat_result,
            "social":   social_result,
            "platform": platform_result,
        },
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    # ── 4. Persist ────────────────────────────────────────────────────────────
    await set_dci_cache(pincode, dci_data, settings.DCI_CACHE_TTL_SECONDS)

    # Build DB payload using engine helper (includes city + weights_used fields)
    db_payload = build_dci_log_payload(
        pincode=pincode,
        dci_score=final_dci,
        weather=weather_result,
        aqi=aqi_result,
        heat=heat_result,
        social=social_result,
        platform=platform_result,
        ndma_override=ndma_override,
        shift_active=active_shift,
        city=city,
    )
    _insert_log_to_db(db_payload)

    # ── 5. Trigger claims if DCI threshold crossed ────────────────────────────
    if is_payout_triggered(final_dci):
        trigger_claims_pipeline(pincode, final_dci, dci_data)

    return dci_data


async def run_dci_cycle() -> None:
    """Main job triggered by APScheduler every 5 minutes."""
    logger.info("=" * 60)
    logger.info("  DCI Polling Cycle Starting...")
    logger.info("=" * 60)

    start_time = datetime.datetime.now()
    active_zones = await get_active_zones()

    # Semaphore limits concurrent HTTP calls per cycle to avoid rate-limiting
    semaphore = asyncio.Semaphore(5)

    async def _process_with_semaphore(pincode: str):
        async with semaphore:
            return await process_zone(pincode)

    tasks = [_process_with_semaphore(pin) for pin in active_zones]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(1 for r in results if not isinstance(r, Exception))
    elapsed = (datetime.datetime.now() - start_time).total_seconds()

    # Log per-city summary
    city_scores: dict[str, list[int]] = {}
    for r in results:
        if isinstance(r, dict):
            c = r.get("city", "default")
            city_scores.setdefault(c, []).append(r.get("dci_score", 0))

    for city, scores in city_scores.items():
        avg = sum(scores) / len(scores)
        logger.info(f"  [{city}] zones={len(scores)} | avg_DCI={avg:.1f}")

    logger.info(
        f"DCI cycle complete | success={success_count}/{len(active_zones)} | "
        f"elapsed={elapsed:.2f}s"
    )
