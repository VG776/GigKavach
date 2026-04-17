"""
models/telemetry.py
━━━━━━━━━━━━━━━━━━━
Pydantic schemas for telemetry data transfer.
"""

from pydantic import BaseModel, Field
from typing import List

class TelemetrySubmission(BaseModel):
    worker_id: str = Field(..., example="f47ac10b-58cc-4372-a567-0e02b2c3d479")
    coordinates: List[float] = Field(..., min_items=2, max_items=2, example=[12.9352, 77.6245])
    speed: float = Field(0.0, description="Speed in meters per second")
    accuracy: float = Field(10.0, description="GPS accuracy in meters")

class TelemetryResponse(BaseModel):
    status: str
    is_suspicious: bool
    teleportation_detected: bool
