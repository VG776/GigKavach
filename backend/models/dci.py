"""
models/dci.py — DCI Engine Data Models
───────────────────────────────────────
Pydantic models for the Disruption Composite Index engine:
  - DCIComponentScores: Individual scores from each data source
  - DCIEvent: A full DCI calculation result stored in the database
  - DCIStatus: What the /status endpoint returns to workers
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class DCISeverity(str, Enum):
    """
    DCI Severity tiers — determines payout eligibility logic.
      - NONE: No disruption. No payout.
      - MODERATE (65–84): Worker must have logged in recently.
      - CATASTROPHIC (85–100): Active policy sufficient — login impossible.
    """
    NONE = "none"
    MODERATE = "moderate"
    CATASTROPHIC = "catastrophic"


class DCIComponentScores(BaseModel):
    """
    Individual scores for each of the 5 DCI components.
    Each is a 0–100 sub-score before weighting.

    DCI Formula (city-specific weights determined by XGBoost):
        DCI = (rainfall × 0.30) + (aqi × 0.20) + (heat × 0.20)
            + (social × 0.20) + (platform × 0.10)
    NOTE: The 0.30, 0.20... weights above are defaults for Bengaluru.
          XGBoost model adjusts these per city during training.
    """
    rainfall_score: float = Field(0.0, ge=0, le=100, description="Rainfall intensity score (0-100)")
    aqi_score: float = Field(0.0, ge=0, le=100, description="Air quality index score (0-100)")
    heat_score: float = Field(0.0, ge=0, le=100, description="Extreme heat score (0-100)")
    social_score: float = Field(0.0, ge=0, le=100, description="Social disruption score — bandh/curfew (0-100)")
    platform_score: float = Field(0.0, ge=0, le=100, description="Platform order drop score (0-100)")

    # Data source metadata — which layer/API provided each score
    rainfall_source: str = Field("none", description="API source used: tomorrow.io | open-meteo | redis_cache | imd_rss")
    aqi_source: str = Field("none", description="API source used: aqicn | cpcb | redis_cache")
    social_source: str = Field("none", description="Source: deccan_herald_rss | the_hindu_rss | ndma_rss")
    platform_source: str = Field("mock", description="always mock for hackathon — real in production")


class DCIEvent(BaseModel):
    """
    Represents one computed DCI cycle for a zone.
    Stored in the `dci_events` table (30-day retention).
    """
    id: Optional[str] = None
    pin_code: str = Field(..., description="6-digit Indian pin code for the zone")
    dci_score: float = Field(..., ge=0, le=100, description="Final composite DCI score 0-100")
    severity: DCISeverity
    components: DCIComponentScores
    computed_at: datetime = Field(default_factory=datetime.utcnow)

    # Special override flags
    ndma_override_active: bool = Field(
        False,
        description="True if NDMA has issued a disaster alert — overrides DCI to 90+ automatically"
    )
    individual_signal_trigger: bool = Field(
        False,
        description="True if any single component independently breached its own threshold"
        " (multi-parameter fallback trigger — bypasses composite DCI check)"
    )

    # 4-layer redundancy tracking
    data_layer_used: int = Field(
        1,
        ge=1, le=4,
        description="Which fallback layer was used: 1=primary API, 2=fallback API, 3=Redis cache, 4=IMD RSS"
    )
    sla_breach: bool = Field(
        False,
        description="True if all 4 layers failed >30 mins — auto-payout at probability-adjusted rate fires"
    )


class ZoneDCIStatus(BaseModel):
    """
    Returned by GET /dci/status/{pin_code}
    Used by the STATUS WhatsApp command and admin dashboard.
    """
    pin_code: str
    dci_score: float
    severity: DCISeverity
    is_trigger_active: bool   # True if DCI >= 65 right now
    last_updated: datetime
    next_poll_in_seconds: int  # Countdown to next DCI calculation
    components: DCIComponentScores
