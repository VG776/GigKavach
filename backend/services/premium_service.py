"""
services/premium_service.py
─────────────────────────────────────────────────────────────
Handles logic to compute dynamic premium discounts by leveraging the 
AI model (hgb_premium_v1.pkl) based on worker behavior + zone risk.
"""

import os
import json
import pickle
import logging
import pandas as pd
import numpy as np
from datetime import datetime

from utils.db import get_supabase
from models.worker import PlanType
from api.workers import PLAN_PREMIUMS
from config.settings import settings

logger = logging.getLogger("gigkavach.premium_service")

# Bonus coverage limits per plan (max hours during high-DCI)
BONUS_COVERAGE_LIMITS = {
    PlanType.BASIC: 1,   # Basic: max 1 bonus hour
    PlanType.PLUS: 2,    # Plus: max 2 bonus hours
    PlanType.PRO: 3,     # Pro: max 3 bonus hours
}

# Model Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "v1", "hgb_premium_v1.pkl")
METADATA_PATH = os.path.join(PROJECT_ROOT, "models", "v1", "hgb_premium_metadata_v1.json")

_MODEL = None
_METADATA = None

def load_ai_model():
    """Load the trained HistGradientBoosting model & metadata into memory."""
    global _MODEL, _METADATA
    if _MODEL is None:
        try:
            with open(MODEL_PATH, 'rb') as f:
                _MODEL = pickle.load(f)
            with open(METADATA_PATH, 'r') as f:
                _METADATA = json.load(f)
            logger.info("Premium Pricing AI Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load AI model: {e}")
            _MODEL = "FAILED"
    return _MODEL, _METADATA

async def _derive_zone_metrics(pincode: str) -> tuple[float, float]:
    """
    Fetch real zone metrics using the DCI engine data.
    
    Steps:
      1. Try to fetch current DCI from Redis cache (updated every 5 min)
      2. Query DB for 30-day historical DCI average
      3. Predict 7-day max using current + historical trend
      4. Fall back to deterministic values if all APIs fail
    """
    try:
        from utils.redis_client import get_dci_cache
        
        # 1. Try to get current DCI from Redis cache
        dci_cache = await get_dci_cache(pincode)
        if dci_cache and "dci_score" in dci_cache:
            current_dci = float(dci_cache["dci_score"])
        else:
            current_dci = None
            
        # 2. Query 30-day historical average from Supabase
        sb = get_supabase()
        from datetime import datetime, timedelta
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
        result = sb.table("dci_logs").select("dci_score").eq("pincode", pincode)\
            .gte("updated_at", thirty_days_ago).execute()
        
        if result.data and len(result.data) > 0:
            dci_scores = [float(row.get("dci_score", 0)) for row in result.data]
            avg_dci = sum(dci_scores) / len(dci_scores)
        else:
            # Fallback: use current DCI or safe default
            avg_dci = current_dci if current_dci is not None else 30.0
        
        # 3. Predict 7d max: current + trend adjustment
        if current_dci is not None:
            # If current is trending high, predict higher for next 7 days
            pred_dci = min(100, current_dci * 1.1 + 10)  # Add 10% buffer + 10 points
        else:
            # Use historical average + safety margin
            pred_dci = min(100, avg_dci * 1.2)
            
        logger.info(f"Zone metrics for {pincode}: avg_30d={avg_dci:.1f}, pred_7d={pred_dci:.1f}")
        return float(avg_dci), float(pred_dci)
        
    except Exception as e:
        logger.warning(f"Failed to derive real zone metrics for {pincode}: {e}. Using safe fallback.")
        # Fallback: deterministic but conservative
        pin_val = sum(ord(c) for c in pincode)
        avg_dci = 25 + (pin_val % 30)  # 25-55 range (conservative)
        pred_dci = avg_dci + 15  # Slightly higher prediction
        return float(avg_dci), float(pred_dci)

async def compute_dynamic_quote(worker_id: str, plan: str) -> dict:
    """
    Given a worker_id and requested plan, computes the personalized
    dynamic premium quote integrating 'Discount-Only' psychology.
    Uses real DCI data from weather APIs and historical trends.
    
    Returns:
        dict with keys: worker_id, base_premium, dynamic_premium, 
                        discount_applied, bonus_coverage_hours, plan_type, insights
    """
    model, _ = load_ai_model()
    
    # 1. Fetch Worker Base Profile from DB
    sb = get_supabase()
    result = sb.table("workers").select("id, shift, pin_codes, gig_score, plan").eq("id", worker_id).execute()
    
    if not result.data:
        raise ValueError(f"Worker {worker_id} not found.")
    
    worker = result.data[0]
    gig_score = float(worker.get("gig_score", 100.0))
    shift = worker.get("shift", "day")
    pincodes = worker.get("pin_codes", [])
    primary_pincode = pincodes[0] if pincodes else "560001"
    
    # Normalize gig_score to [0, 100]
    gig_score = max(0, min(100, gig_score))
    
    # Validation: Enforce base rules (new prices)
    try:
        requested_plan = PlanType(plan.lower())
    except ValueError:
        requested_plan = PlanType.BASIC
        
    base_price = PLAN_PREMIUMS[requested_plan][0]  # Should be 30, 37, or 44
    
    # Initialize zone metrics (computed once, reused throughout)
    avg_dci = None
    pred_dci = None
    
    # Fallback to simple deterministic discount if Model is missing
    if model == "FAILED" or model is None:
        logger.warning(f"Using fallback deterministic discount for {worker_id}.")
        raw_discount_mult = 0.05 if gig_score > 80 else 0.0
        reason_msg = "Unable to compute personalized discount at this time. Standard rates apply."
    else:
        # 2. Extract Geospacial Features using real DCI data (COMPUTED ONCE, REUSED)
        try:
            avg_dci, pred_dci = await _derive_zone_metrics(primary_pincode)
        except Exception as e:
            logger.warning(f"Failed to derive zone metrics for pincode {primary_pincode}: {e}")
            avg_dci, pred_dci = 30.0, 50.0  # Fallback safe defaults
        
        # 3. Build feature vector with proper validation
        features = pd.DataFrame([{
            'worker_gig_score': gig_score,
            'pincode_30d_avg_dci': avg_dci,
            'predicted_7d_max_dci': pred_dci,
            'shift_morning': int(shift == 'morning'),
            'shift_day': int(shift == 'day'),
            'shift_night': int(shift == 'night'),
            'shift_flexible': int(shift == 'flexible')
        }])
        
        # 4. Model Inference with clipping
        try:
            prediction = model.predict(features)[0]
            raw_discount_mult = np.clip(prediction, 0.0, 0.30)
        except Exception as e:
            logger.error(f"Model inference failed for {worker_id}: {e}")
            raw_discount_mult = 0.05 if gig_score > 80 else 0.0
        
        # Explainability: generate human-readable reason (computed once)
        reason_msg = _generate_nlp_reason(raw_discount_mult, gig_score, pred_dci, shift)

    # 5. Premium Math with validation
    discount_amount = round(base_price * raw_discount_mult, 1)
    discount_amount = max(0.0, discount_amount)
    
    final_premium = base_price - discount_amount
    
    # Ensure premium stays within valid range (0.7x to 1.3x of base after discount)
    # For BASIC (₹30): range is ₹21-₹39
    # For PLUS (₹37): range is ₹25.90-₹48.10
    # For PRO (₹44): range is ₹30.80-₹57.20
    min_premium = base_price * 0.7
    max_premium = base_price * 1.3
    final_premium = np.clip(final_premium, min_premium, max_premium)
    
    # Recalculate actual discount based on bounded premium
    discount_amount = base_price - final_premium
    
    # Check if we should offer 'Bonus Coverage' instead of pure discount
    # E.g. If DCI is super high, we don't hike prices (Psychology rule!), 
    # but we might give the worker +1 guaranteed active hour extension!
    # Validate against plan-specific maximum limits
    bonus_coverage_hours = 0
    if model != "FAILED" and model is not None and pred_dci is not None:
        # Reuse zone metrics computed above
        if pred_dci > 70:
            plan_bonus_limit = BONUS_COVERAGE_LIMITS.get(requested_plan, 2)
            # Clamp to plan-specific maximum (but never exceed 3 hours)
            bonus_coverage_hours = min(plan_bonus_limit, 3)
    
    # Determine zone risk level (reusing zone metrics computed above)
    forecasted_zone_risk = "Normal"
    if model != "FAILED" and model is not None and pred_dci is not None:
        forecasted_zone_risk = "High" if pred_dci > 65 else "Normal"
        
    return {
        "worker_id": worker_id,
        "base_premium": float(base_price),
        "dynamic_premium": float(final_premium),
        "discount_applied": float(discount_amount),
        "bonus_coverage_hours": bonus_coverage_hours,
        "plan_type": requested_plan.value,
        "insights": {
            "reason": reason_msg,
            "gig_score": gig_score,
            "primary_zone": primary_pincode,
            "forecasted_zone_risk": forecasted_zone_risk
        }
    }

def _generate_nlp_reason(discount: float, score: float, pred_dci: float, shift: str) -> str:
    """Generate a human-readable and encouraging reasoning for the discount."""
    if score < 70:
        return "Improve your GigScore (Trust rating) to unlock weekly premium discounts!"
    
    if discount > 0.20: # Over 20% discount
        if shift == 'night':
            return f"{int(discount*100)}% discount unlocked! Your exceptional GigScore over {int(score)} and safe Night-shift history gives you maximum savings."
        return f"{int(discount*100)}% discount unlocked! Your exceptional GigScore gives you maximum savings."
    
    elif discount > 0.05:
        if pred_dci > 65:
            return f"Upcoming week shows moderate risk, but your GigScore of {int(score)} still unlocks a {int(discount*100)}% premium discount."
        return f"{int(discount*100)}% discount unlocked based on your positive GigScore."
        
    else:
        return "No significant discount this week due to high forecasted disruption in your zone. Your coverage amount stays exactly the same — stay safe out there!"
