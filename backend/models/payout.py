"""
models/payout.py — Payout & Fraud Detection Models
────────────────────────────────────────────────────
Data shapes for:
  - PayoutCalculation: XGBoost model output
  - FraudSignal: individual signal from the 6-signal fraud checker
  - FraudAssessment: composite fraud score and tier decision
  - PayoutRecord: stored in the `payouts` table (permanent, audit trail)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from models.worker import PlanType, FraudTier


class PayoutStatus(str, Enum):
    """Tracks where a payout is in its lifecycle"""
    PENDING = "pending"              # Eligibility check passed, fraud check running
    PROCESSING = "processing"        # Razorpay transfer initiated
    PARTIAL = "partial"              # Soft-flag: 50% sent, 48hr re-verification active
    COMPLETED = "completed"          # Full payout sent to UPI
    WITHHELD = "withheld"            # Hard block — Tier 2 or Tier 3 fraud
    ESCROWED = "escrowed"            # UPI transfer failed, held for 48hrs
    FAILED = "failed"                # All retries exhausted and escrow window lapsed
    SLA_AUTO = "sla_auto"            # Auto-payout fired because all 4 data layers failed


class PayoutCalculation(BaseModel):
    """
    Output from the XGBoost payout model.
    XGBoost determines city-specific disruption weights and uses them
    to compute the fair payout for the disrupted hours.
    """
    worker_id: str
    dci_score: float
    disrupted_hours: float = Field(..., description="Total hours DCI was ≥ 65 during worker's shift")
    working_hours: float = Field(..., description="Worker's total declared shift hours for the day")
    daily_baseline_earnings: float = Field(
        ...,
        description="Worker's expected daily earnings from 4-week rolling median. "
                    "Source: Earnings Fingerprint model."
    )
    disruption_ratio: float = Field(
        ...,
        ge=0.0, le=1.0,
        description="disrupted_hours / working_hours — capped at 1.0"
    )
    plan: PlanType
    coverage_pct: float = Field(..., description="0.40 | 0.50 | 0.70 depending on plan")

    # Payout calculation (edge case #17 from edge_cases doc):
    # payout = min(coverage_pct × baseline, disruption_ratio × baseline)
    # This prevents a full-day payout for a 1-hour disruption.
    tier_max_payout: float = Field(..., description="coverage_pct × baseline (plan's maximum)")
    disruption_ratio_payout: float = Field(..., description="disruption_ratio × baseline")
    final_payout: float = Field(..., description="min(tier_max, ratio_based) — actual amount sent")

    # Surge protection multiplier (special feature from README §13)
    surge_active: bool = Field(False, description="True if worker was in a surge zone during disruption")
    surge_multiplier: float = Field(1.0, description="e.g. 1.5x during 7PM-10PM surge window")

    # XGBoost model metadata
    xgboost_model_version: str = Field("v1.0", description="Model version for audit trail")
    city_disruption_weights: dict = Field(
        default_factory=dict,
        description="City-specific component weights used by XGBoost for this calculation"
    )


class FraudSignal(BaseModel):
    """One of the 6 anti-spoofing signals evaluated per payout"""
    signal_name: str         # e.g. "gps_ip_mismatch", "claim_burst", "zero_pre_disruption_earnings"
    triggered: bool          # True = suspicious
    severity: str = "low"   # low | medium | high
    detail: str = ""         # Human-readable explanation for audit log


class FraudAssessment(BaseModel):
    """
    Full fraud assessment for one worker's payout attempt.
    Scores each of the 6 signals independently — workers are NEVER
    batch-rejected based on zone-level patterns.
    """
    worker_id: str
    dci_event_id: str
    signals: list[FraudSignal]                    # All 6 signals evaluated
    triggered_signal_count: int                   # How many signals fired
    isolation_forest_score: Optional[float] = None  # Raw IF model output (-1=anomaly, 1=normal)
    fraud_tier: FraudTier                         # Clean | soft_flag | hard_block

    # Dynamic threshold adjustment based on DCI severity (README §11)
    # During catastrophic events (DCI ≥ 85), genuine signal degradation is expected.
    # The system requires MORE signals before hard-blocking to protect real workers.
    catastrophic_mode: bool = Field(
        False,
        description="If True, threshold for hard_block raises to 5-of-6 signals (vs 3-of-6)"
    )
    assessed_at: datetime = Field(default_factory=datetime.utcnow)


class PayoutRecord(BaseModel):
    """
    Stored in the `payouts` table — permanent audit trail, never deleted.
    This is the ground truth for all financial transactions.
    """
    id: Optional[str] = None
    worker_id: str
    policy_id: str
    dci_event_id: str

    # Amounts
    calculated_amount: float     # What XGBoost said to pay
    actual_amount_sent: float    # What was actually transferred (may be 50% if soft-flagged)
    remaining_held: float = 0.0  # Amount held pending 48hr re-verification

    # Status tracking
    status: PayoutStatus
    razorpay_payment_id: Optional[str] = None   # Razorpay transaction reference
    upi_id_used: str                            # The UPI ID money was sent to

    # Fraud context
    fraud_tier: FraudTier
    fraud_assessment_id: Optional[str] = None

    # Timestamps
    triggered_at: datetime       # When DCI breach was first detected
    payout_fired_at: Optional[datetime] = None   # When Razorpay transfer was initiated
    completed_at: Optional[datetime] = None      # When transfer confirmed

    # Failure handling (edge case #18: UPI failure → escrow)
    retry_count: int = 0
    escrow_until: Optional[datetime] = None      # 48hr window for worker to fix UPI
