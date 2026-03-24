"""
models/worker.py — GigKavach Worker & Policy Pydantic Models
─────────────────────────────────────────────────────────────
These models define the data shapes for:
  - Worker onboarding via WhatsApp (WorkerCreate)
  - API registration endpoint (RegistrationResponse)
  - Policy creation and management (PolicyCreate, PolicyResponse, PolicyUpdate)
  - Worker status queries (WorkerResponse)

Pydantic validates all incoming data automatically —
FastAPI will return a 422 error if any field is missing or wrong type.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, date
from enum import Enum


# ─── Enums ───────────────────────────────────────────────────────────────────

class PlatformType(str, Enum):
    """Delivery platforms GigKavach currently supports"""
    ZOMATO = "zomato"
    SWIGGY = "swiggy"


class ShiftType(str, Enum):
    """Worker's typical working shift — used for DCI trigger eligibility"""
    MORNING = "morning"      # 6AM – 2PM
    DAY = "day"              # 9AM – 9PM (most common)
    NIGHT = "night"          # 6PM – 2AM
    FLEXIBLE = "flexible"    # No fixed window — eligible during any active DCI event


class PlanType(str, Enum):
    """
    Three fixed weekly premium tiers.
    Premium is fixed per tier. ML (XGBoost) only adjusts the PAYOUT amount,
    not what the worker pays.
    """
    BASIC = "basic"   # ₹69/week → 40% daily earnings covered
    PLUS = "plus"     # ₹89/week → 50% daily earnings covered
    PRO = "pro"       # ₹99/week → 70% daily earnings covered


class Language(str, Enum):
    """Supported languages — selected at onboarding Step 0"""
    ENGLISH = "en"
    KANNADA = "kn"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"


class FraudTier(str, Enum):
    """Three-tier penalization system for fraud detection"""
    CLEAN = "clean"           # 0–2 signals: full payout, no flag
    SOFT_FLAG = "soft_flag"   # 3–4 signals: 50% now, 48hr re-verification
    HARD_BLOCK = "hard_block" # 5–6 signals: payout withheld, Tier 2 action


# ─── Worker Models ────────────────────────────────────────────────────────────

class WorkerCreate(BaseModel):
    """
    Data required to onboard a new worker via WhatsApp.
    Collected across the 5-step onboarding flow.
    """
    phone_number: str = Field(
        ...,
        description="Worker's WhatsApp number in E.164 format e.g. +919876543210",
        example="+919876543210"
    )
    platform: PlatformType = Field(..., description="Zomato or Swiggy")
    shift: ShiftType = Field(..., description="Worker's regular shift window")
    upi_id: str = Field(..., description="UPI ID for payouts e.g. ravi@upi", example="ravi@upi")
    pin_codes: list[str] = Field(
        ...,
        description="List of pin codes the worker delivers in (1–5 zones)",
        example=["560047", "560034"]
    )
    plan: PlanType = Field(..., description="Selected weekly coverage plan")
    language: Language = Field(default=Language.HINDI, description="Preferred language")

    @field_validator("pin_codes")
    @classmethod
    def validate_pin_codes(cls, v: list[str]) -> list[str]:
        """Ensure pin codes are 6-digit Indian format"""
        if not v or len(v) > 5:
            raise ValueError("Provide 1–5 delivery zone pin codes")
        for pin in v:
            if not pin.isdigit() or len(pin) != 6:
                raise ValueError(f"Invalid pin code: {pin}. Must be a 6-digit number.")
        return v

    @field_validator("upi_id")
    @classmethod
    def validate_upi_id(cls, v: str) -> str:
        """Basic UPI ID format check — must contain @"""
        if "@" not in v:
            raise ValueError("Invalid UPI ID — must be in the format name@bank")
        return v.lower().strip()


class WorkerUpdate(BaseModel):
    """Used for mid-week updates a worker can trigger via WhatsApp commands"""
    shift: Optional[ShiftType] = None       # SHIFT command
    upi_id: Optional[str] = None            # UPI update after payment failure
    language: Optional[Language] = None     # LANG command
    pin_codes: Optional[list[str]] = None   # Zone update


class WorkerResponse(BaseModel):
    """What the API returns when querying a worker's profile"""
    id: str
    phone_number: str
    platform: PlatformType
    shift: ShiftType
    upi_id: str
    pin_codes: list[str]
    plan: PlanType
    language: Language
    gig_score: float = Field(default=100.0, description="Trust score (0-100), starts at 100")
    is_active: bool = True
    created_at: datetime
    coverage_active_from: Optional[datetime] = Field(
        None,
        description="Coverage starts 24hrs after first premium payment — moral hazard prevention"
    )


# ─── Policy Models ────────────────────────────────────────────────────────────

class PolicyCreate(BaseModel):
    """Created when a worker pays their weekly premium"""
    worker_id: str
    plan: PlanType
    week_start: datetime   # Monday 00:00 of coverage week
    week_end: datetime     # Sunday 23:59 of coverage week
    premium_paid: float    # 69 | 89 | 99 (INR)


class PolicyResponse(BaseModel):
    """Policy details returned by the API — used by GET and PATCH /api/v1/policy/{id}"""
    id: str
    worker_id: str
    plan: PlanType
    shift: ShiftType
    pin_codes: list[str]
    week_start: datetime
    week_end: datetime
    premium_paid: float
    is_active: bool
    created_at: datetime
    # Only populated when a tier change was requested via PATCH
    # The new tier takes effect from the next Monday cycle, not mid-week
    tier_change_effective: Optional[date] = Field(
        None,
        description="Date the tier change takes effect (always a Monday). None if no tier change."
    )


class PolicyUpdate(BaseModel):
    """
    Request body for PATCH /api/v1/policy/{id}.
    All fields are optional — only send what you want to change.

    Business rules enforced in the route handler:
      - plan: change queued for next Monday cycle (current week unaffected)
      - shift: effective immediately
      - pin_codes: effective immediately (new zones added to DCI eligibility)
    """
    plan: Optional[PlanType] = Field(
        None,
        description="New coverage tier. Takes effect NEXT Monday — current week coverage unchanged."
    )
    shift: Optional[ShiftType] = Field(
        None,
        description="New shift window. Takes effect immediately."
    )
    pin_codes: Optional[list[str]] = Field(
        None,
        description="Updated delivery zones. Takes effect immediately."
    )

    @field_validator("pin_codes")
    @classmethod
    def validate_pin_codes(cls, v: list[str]) -> list[str]:
        """Same validation as WorkerCreate — 1 to 5 valid 6-digit Indian pin codes"""
        if v is None:
            return v
        if not v or len(v) > 5:
            raise ValueError("Provide 1–5 delivery zone pin codes")
        for pin in v:
            if not pin.isdigit() or len(pin) != 6:
                raise ValueError(f"Invalid pin code: {pin}. Must be a 6-digit number.")
        return v


class RegistrationResponse(BaseModel):
    """
    Response returned by POST /api/v1/register.
    Contains IDs and the coverage start time so the worker knows
    when they can make their first claim.
    """
    worker_id: str
    policy_id: str
    phone_number: str
    plan: PlanType
    coverage_active_from: datetime = Field(
        description="Payouts only fire after this timestamp (24hr delay from registration)"
    )
    week_start: datetime
    week_end: datetime
    message: str = "Worker registered successfully"
