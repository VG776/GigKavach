"""
services/gigscore_service.py
─────────────────────────────────────────────────────────────
Handles all updates to a worker's GigScore based on behavioral
and fraud events, maintaining the parametric trust metrics.
"""

import logging
from enum import Enum
from typing import Dict, Any

from utils.db import get_supabase

logger = logging.getLogger("gigkavach.gigscore_service")

class GigScoreEvent(Enum):
    # Fraud Detection Penalties (Negative)
    FRAUD_TIER_1 = "fraud_tier_1_soft"      # 2-3 suspicious signals
    FRAUD_TIER_2 = "fraud_tier_2_hard"      # 5+ signals
    FRAUD_TIER_3 = "fraud_tier_3_blacklist" # Confirmed spoofing syndicate
    ZONE_HOPPING = "zone_hopping"           # Claiming outside registered zones
    THRESHOLD_GAMING = "threshold_gaming"   # Barely triggering DCI repeatedly

    # Positive Reinforcement & Loyalty (Positive)
    CLEAN_RENEWAL = "clean_week_renewal"    # Completed week without fraud flags
    VALID_SEVERE_CLAIM = "valid_severe_claim" # Clean claim during catastrophic DCI > 85
    SUCCESSFUL_APPEAL = "successful_appeal" # Overturned a Tier 2 flag via WhatsApp

def get_event_impact(event_type: GigScoreEvent) -> float:
    """Returns the point adjustment for a given event type."""
    impacts = {
        GigScoreEvent.FRAUD_TIER_1: -7.5,    # Soft flag (-5 to -10)
        GigScoreEvent.FRAUD_TIER_2: -25.0,   # Hard flag (-25 to -30)
        GigScoreEvent.FRAUD_TIER_3: -100.0,  # Blacklist (Drops to 0)
        GigScoreEvent.ZONE_HOPPING: -2.0,    # Minor behavioral inconsistency
        GigScoreEvent.THRESHOLD_GAMING: -3.0,# Minor gaming penalty
        GigScoreEvent.CLEAN_RENEWAL: 2.0,    # Slow trust rebuild
        GigScoreEvent.VALID_SEVERE_CLAIM: 5.0, # Validates reliability
        GigScoreEvent.SUCCESSFUL_APPEAL: 15.0, # Complete restoration + bonus (context dependent)
    }
    return impacts.get(event_type, 0.0)

def update_gig_score(worker_id: str, event_type: GigScoreEvent, metadata: Dict[str, Any] = None) -> float:
    """
    Core function to update a worker's GigScore deterministically.
    Fetches the current score, applies the delta, enforces [0, 100] bounds,
    and writes back to Supabase.
    """
    sb = get_supabase()
    
    # 1. Fetch current score
    try:
        result = sb.table("workers").select("gig_score, account_status").eq("id", worker_id).execute()
        if not result.data:
            logger.error(f"Cannot update GigScore: Worker {worker_id} not found.")
            return -1.0 # Or raise Exception
            
        worker = result.data[0]
        current_score = float(worker.get("gig_score", 100.0))
        account_status = worker.get("account_status", "active")
        
    except Exception as e:
        logger.error(f"Failed to fetch worker {worker_id} from Supabase: {str(e)}")
        return -1.0
        
    # 2. Event Matcher & Delta application
    delta = get_event_impact(event_type)
    
    # Special case: Successful appeal should ideally restore the specific penalty
    if event_type == GigScoreEvent.SUCCESSFUL_APPEAL:
        # If we know the penalty they are appealing, we could restore it perfectly.
        # But for now, we give a fiat +15 to help them bounce back from a false positive.
        if metadata and "penalty_amount" in metadata:
            delta = abs(metadata["penalty_amount"]) + 5.0 # Restore + 5 bonus
            
    new_score = current_score + delta
    
    # 3. Bounds Enforcement [0.0, 100.0]
    new_score = max(0.0, min(100.0, float(new_score)))
    
    # Check if this drops them below 30 (Account suspension threshold)
    new_status = account_status
    if new_score < 30.0 and account_status == "active":
        new_status = "suspended"
        logger.warning(f"Worker {worker_id} GigScore dropped to {new_score}. Account suspended.")
    elif new_score >= 30.0 and account_status == "suspended":
        # Maybe they successfully appealed, bringing score back up over 30
        new_status = "active"
        logger.info(f"Worker {worker_id} GigScore restored to {new_score}. Account reactivated.")
        
    # 4. Database Write
    update_payload = {
        "gig_score": new_score,
        "account_status": new_status
    }
    
    try:
        # Perform update
        sb.table("workers").update(update_payload).eq("id", worker_id).execute()
        
        # Log to application insights (this acts as our audit log since we don't have gigscore_history table modeled)
        logger.info(
            f"GIGSCORE UPDATE | Worker: {worker_id} | Event: {event_type.value} | "
            f"Delta: {delta:+.1f} | New Score: {new_score:.1f}"
        )
        
        return new_score
        
    except Exception as e:
        logger.error(f"Failed to write updated GigScore for {worker_id}: {str(e)}")
        return current_score
