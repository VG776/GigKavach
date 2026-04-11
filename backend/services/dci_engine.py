"""
services/dci_engine.py — Disruption Composite Index Engine
──────────────────────────────────────────────────────────────
Core business logic for computing the DCI composite score from
5 weighted environmental and social components.

DCI Formula (5 components, max 100):
  DCI = weather * W_w + aqi * W_aqi + heat * W_h + social * W_s + platform * W_p

Weights are now CITY-SPECIFIC — not global — and loaded from
config/city_dci_weights.py. This allows the engine to correctly
reflect that:
  - Mumbai risk is dominated by extreme rainfall (monsoon)
  - Delhi risk is dominated by AQI + extreme heat
  - Kolkata/Chennai risk is dominated by cyclone rainfall
  - Bengaluru risk has balanced rain + social disruption components

Severity Tiers:
  0-29   → none
  30-49  → low
  50-64  → moderate
  65-79  → high
  80-94  → critical
  ≥ 95   → catastrophic  (NDMA override also forces this)

The DCI poller calls calculate_dci() after collecting individual
component scores, then persists the result to Redis + Supabase.
"""

import logging
from typing import Dict, Optional

from config.city_dci_weights import (
    get_city_weights,
    resolve_city_from_pincode,
    GLOBAL_FALLBACK_WEIGHTS,
    list_supported_cities,
)

logger = logging.getLogger("gigkavach.dci_engine")

# ─── Severity Tier Thresholds ────────────────────────────────────────────────
SEVERITY_TIERS = [
    (95, "catastrophic"),   # NDMA override also forces ≥95
    (80, "critical"),
    (65, "high"),
    (50, "moderate"),
    (30, "low"),
    (0,  "none"),
]

# ─── Legacy Constant (kept for import-backward-compat) ───────────────────────
# Old code that imported COMPONENT_WEIGHTS from this module will still get the
# global fallback dict. But all internal DCI computation now uses city weights.
COMPONENT_WEIGHTS = dict(GLOBAL_FALLBACK_WEIGHTS)


def calculate_dci(
    weather_score: float,
    aqi_score: float,
    heat_score: float,
    social_score: float,
    platform_score: float,
    ndma_override: bool = False,
    city: str = "default",
    pincode: Optional[str] = None,
) -> int:
    """
    Computes the composite DCI score (0–100) from 5 component scores.

    City-specific weights are applied automatically — if both `city` and
    `pincode` are provided, `city` takes precedence. If only `pincode` is
    provided, the city is resolved automatically from the pincode.

    Args:
        weather_score:  0–100 rainfall/flood signal
        aqi_score:      0–100 air quality disruption
        heat_score:     0–100 temperature stress (38–42°C gradient)
        social_score:   0–100 social unrest / bandh from NLP classifier
        platform_score: 0–100 platform-reported delivery blocks
        ndma_override:  If True, DCI is forced to 95 (catastrophic override)
        city:           Canonical city name ("Mumbai", "Delhi", etc.) or "default"
        pincode:        Optional pincode — used to resolve city if city="default"

    Returns:
        int: composite DCI score clamped to [0, 100]
    """
    if ndma_override:
        logger.warning("[DCI ENGINE] NDMA catastrophic override active — forcing DCI = 95")
        return 95

    # Resolve city if only pincode provided
    resolved_city = city
    if (resolved_city == "default" or not resolved_city) and pincode:
        resolved_city = resolve_city_from_pincode(pincode)

    weights = get_city_weights(resolved_city)

    composite = (
        weather_score  * weights["weather"]  +
        aqi_score      * weights["aqi"]      +
        heat_score     * weights["heat"]      +
        social_score   * weights["social"]   +
        platform_score * weights["platform"]
    )

    final_score = min(100, max(0, round(composite)))

    logger.debug(
        f"[DCI ENGINE] city={resolved_city} | "
        f"W={weather_score:.1f}×{weights['weather']} "
        f"AQI={aqi_score:.1f}×{weights['aqi']} "
        f"H={heat_score:.1f}×{weights['heat']} "
        f"S={social_score:.1f}×{weights['social']} "
        f"P={platform_score:.1f}×{weights['platform']} "
        f"→ DCI={final_score}"
    )

    return final_score


def get_severity_tier(score: int) -> str:
    """
    Maps a numeric DCI score to a named severity tier.

    Args:
        score: DCI score (0–100)

    Returns:
        str: one of 'none', 'low', 'moderate', 'high', 'critical', 'catastrophic'
    """
    for threshold, tier in SEVERITY_TIERS:
        if score >= threshold:
            return tier
    return "none"


def is_payout_triggered(score: int) -> bool:
    """
    Returns True if DCI score is at or above the 65-point payout trigger threshold.
    This is the minimum score required for a worker to become eligible for a payout.

    The threshold of 65 (≥ 'high') is specified in the GigKavach requirements.
    """
    return score >= 65


def get_dominant_risk_component(city: str) -> str:
    """
    Returns the name of the highest-weighted DCI component for a given city.
    Useful for logging, dashboard display, and alert messaging.

    Args:
        city: Canonical city name

    Returns:
        Component name: "weather" | "aqi" | "heat" | "social" | "platform"

    Examples:
        get_dominant_risk_component("Mumbai") → "weather"   (0.40)
        get_dominant_risk_component("Delhi")  → "aqi"       (0.30, tied with heat)
    """
    weights = get_city_weights(city)
    return max(weights, key=weights.get)


def get_city_dci_profile(city: str) -> Dict:
    """
    Returns the full DCI weight profile for a city, including the dominant
    risk component and a human-readable description for dashboard rendering.

    Args:
        city: Canonical city name

    Returns:
        Dict with keys: city, weights, dominant_risk, description
    """
    weights = get_city_weights(city)
    dominant = get_dominant_risk_component(city)

    descriptions = {
        "weather":  "Extreme rainfall / flooding risk (monsoon / cyclone dominant)",
        "aqi":      "Severe air quality disruption (particulate / smog dominant)",
        "heat":     "Extreme temperature stress (Loo / coastal humidity dominant)",
        "social":   "Civic disruption risk (bandhs / protests / strikes dominant)",
        "platform": "Platform-level delivery block signal dominant",
    }

    supported = list_supported_cities()

    return {
        "city":          city,
        "weights":       weights,
        "dominant_risk": dominant,
        "description":   descriptions.get(dominant, "Multi-factor risk profile"),
        "is_supported":  city in supported,
        "fallback_used": city not in supported,
    }


def build_dci_log_payload(
    pincode: str,
    dci_score: int,
    weather: Dict,
    aqi: Dict,
    heat: Dict,
    social: Dict,
    platform: Dict,
    ndma_override: bool = False,
    shift_active: str = None,
    city: str = "default",
) -> Dict:
    """
    Builds the full DB row payload for the `dci_logs` Supabase table.

    Now includes `city` and `weights_used` fields for audit transparency —
    so that anyone inspecting a past DCI score can see exactly which city
    weight profile was active at the time of calculation.

    Args:
        pincode:        Zone pin code being tracked
        dci_score:      Final composite score from calculate_dci()
        weather/aqi/heat/social/platform: Raw component dicts with {score, ...}
        ndma_override:  Whether NDMA catastrophic override was active
        shift_active:   Name of the currently active shift window
        city:           The city whose weights were applied

    Returns:
        Dict ready for sb.table("dci_logs").insert(payload)
    """
    weights_used = get_city_weights(city)

    return {
        "pincode":              pincode,
        "city":                 city,
        "total_score":          dci_score,
        "rainfall_score":       int(weather.get("score", 0)),
        "aqi_score":            int(aqi.get("score", 0)),
        "heat_score":           int(heat.get("score", 0)),
        "social_score":         int(social.get("score", 0)),
        "platform_score":       int(platform.get("score", 0)),
        "severity_tier":        get_severity_tier(dci_score),
        "ndma_override_active": ndma_override,
        "shift_active":         shift_active,
        "is_shift_window_active": shift_active is not None,
        "weights_used":         weights_used,          # Audit field — full weight snapshot
        "dominant_risk":        get_dominant_risk_component(city),
    }


def get_dynamic_weights(pincode: str, force_recompute: bool = False) -> Dict:
    """
    Resolves the weight profile for a specific zone.
    
    If force_recompute is True, it simulates a refresh of the city mapping
    and metadata (e.g. from a remote configuration store or database).
    
    Returns:
        Dict: weights snapshot plus city metadata
    """
    city = resolve_city_from_pincode(pincode)
    weights = get_city_weights(city)
    
    if force_recompute:
        logger.info(f"[DCI ENGINE] Force-recomputing weights for zone {pincode} (City: {city})")
        # In a real system, this would invalidate caches or re-run a k-means clustering.
        # For our MVP, we return the canonical weights but with a 'refreshed' flag.
    
    return {
        "city": city,
        "weights": weights,
        "recomputed": force_recompute,
        "supported": city != "default"
    }
