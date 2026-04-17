"""
models/worker.py — GigKavach Worker & Policy Pydantic Models
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


# ─── Enums ───────────────────────────────────────────────────────────────────

class PlatformType(str, Enum):
    ZOMATO = "zomato"
    SWIGGY = "swiggy"


class ShiftType(str, Enum):
    MORNING = "morning"
    DAY = "day"
    NIGHT = "night"
    FLEXIBLE = "flexible"


class PlanType(str, Enum):
    BASIC = "basic"
    PLUS = "plus"
    PRO = "pro"


class Language(str, Enum):
    ENGLISH = "en"
    KANNADA = "kn"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"


class FraudTier(str, Enum):
    CLEAN = "clean"
    SOFT_FLAG = "soft_flag"
    HARD_BLOCK = "hard_block"


# ─── Worker Models ────────────────────────────────────────────────────────────

class WorkerCreate(BaseModel):
    phone_number: str = Field(..., description="E.164 format")
    name: str = Field(..., description="Full Name")
    platform: PlatformType
    shift: ShiftType
    upi_id: str
    pin_codes: List[str]
    plan: PlanType = Field(default=PlanType.BASIC)
    language: Language = Field(default=Language.HINDI)

    @field_validator("pin_codes")
    @classmethod
    def validate_pin_codes(cls, v: List[str]) -> List[str]:
        if not v or len(v) > 5:
            raise ValueError("Provide 1–5 delivery zone pin codes")
        for pin in v:
            if not pin.isdigit() or len(pin) != 6:
                raise ValueError(f"Invalid pin code: {pin}. Must be a 6-digit number.")
        return v

    @field_validator("upi_id")
    @classmethod
    def validate_upi(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid UPI ID. Must contain '@' (e.g., worker@upi)")
        return v


class WorkerUpdate(BaseModel):
    name: Optional[str] = None
    shift: Optional[ShiftType] = None
    upi_id: Optional[str] = None
    language: Optional[Language] = None
    pin_codes: Optional[List[str]] = None
    gig_score: Optional[float] = None


class WorkerResponse(BaseModel):
    id: str
    phone_number: str
    platform: PlatformType
    shift: ShiftType
    upi_id: str
    pin_codes: List[str]
    plan: PlanType
    language: Language
    gig_score: float = 100.0
    is_active: bool = True
    is_on_shift: bool = False
    created_at: datetime
    coverage_active_from: Optional[datetime] = None


class WorkerProfile(BaseModel):
    id: str
    name: str
    phone: str
    gig_platform: str
    shift: str
    gig_score: float
    is_active: bool
    pin_codes: List[str]
    policies: Optional[List[dict]] = None


# ─── Policy Models ────────────────────────────────────────────────────────────

class PolicyCreate(BaseModel):
    worker_id: str
    plan: PlanType
    week_start: datetime
    week_end: datetime
    premium_paid: float


class PolicyResponse(BaseModel):
    id: str
    worker_id: str
    plan: PlanType
    shift: ShiftType
    pin_codes: List[str]
    week_start: datetime
    week_end: datetime
    premium_paid: float
    is_active: bool
    created_at: datetime
    tier_change_effective: Optional[date] = None


class PolicyUpdate(BaseModel):
    plan: Optional[PlanType] = None
    shift: Optional[ShiftType] = None
    pin_codes: Optional[List[str]] = None


class RegistrationResponse(BaseModel):
    message: str
    worker_id: str
    share_token: str
    share_url: str
    phone_number: str
    plan: PlanType
    coverage_active_from: datetime
    policy_id: str
    week_start: Optional[datetime] = None
    week_end: Optional[datetime] = None
