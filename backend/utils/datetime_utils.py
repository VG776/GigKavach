"""
utils/datetime_utils.py — Unified Shift & Time Management
────────────────────────────────────────────────────────
Provides mapping between string shift names (onboarding) and 
time-based windows (payouts/eligibility).
"""
from datetime import datetime, time, timezone

SHIFTS = {
    "Morning": (6, 14),   # 6 AM - 2 PM
    "Day": (10, 18),      # 10 AM - 6 PM
    "Night": (18, 2),     # 6 PM - 2 AM (crosses midnight)
    "Late Night": (22, 6) # 10 PM - 6 AM (crosses midnight)
}

def get_current_shift_name(dt: datetime = None) -> str:
    """Returns the most active shift name for the current hour."""
    if dt is None:
        dt = datetime.now()
    hour = dt.hour
    
    # Simple strategy: Find first shift that covers this hour
    for name, (start, end) in SHIFTS.items():
        if start < end:
            if start <= hour < end:
                return name
        else: # Crosses midnight
            if hour >= start or hour < end:
                return name
    return "Flexible"

def is_within_shift(shift_name: str, dt: datetime = None) -> bool:
    """Checks if a given time falls within a named shift window."""
    if dt is None:
        dt = datetime.now()
    if shift_name == "Flexible":
        return True
    
    window = SHIFTS.get(shift_name)
    if not window:
        return False
        
    start, end = window
    hour = dt.hour
    
    if start < end:
        return start <= hour < end
    else: # Crosses midnight
        return hour >= start or hour < end
