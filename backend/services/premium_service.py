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

logger = logging.getLogger("gigkavach.premium_service")

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

def _derive_mock_zone_metrics(pincode: str) -> tuple[float, float]:
    """
    For demo purposes: derived deterministic values for 
    'historical avg DCI' and 'predicted max DCI' based on the pincode string hash.
    In real production, this queries from a time-series datastore using Tomorrow.io.
    """
    # Deterministic pseudo-randomness based on pincode
    pin_val = sum(ord(c) for c in pincode)
    
    # 30d avg DCI (usually between 10 and 50)
    avg_dci = 10 + (pin_val % 40)
    
    # Predicted 7d max DCI (usually between 20 and 80)
    # If standard avg is high, forecast is generally higher
    pred_dci = avg_dci * 0.8 + (pin_val % 30)
    
    return float(avg_dci), float(pred_dci)

def compute_dynamic_quote(worker_id: str, plan: str) -> dict:
    """
    Given a worker_id and requested plan, computes the personalized
    dynamic premium quote integrating 'Discount-Only' psychology.
    """
    model, _ = load_ai_model()
    
    # 1. Fetch Worker Base Profile
    sb = get_supabase()
    result = sb.table("workers").select("id, shift, pin_codes, gig_score, plan").eq("id", worker_id).execute()
    
    if not result.data:
        raise ValueError(f"Worker {worker_id} not found.")
    
    worker = result.data[0]
    gig_score = float(worker.get("gig_score", 100.0))
    shift = worker.get("shift", "day")
    pincodes = worker.get("pin_codes", [])
    primary_pincode = pincodes[0] if pincodes else "560001"
    
    # Validation: Enforce base rules (new prices)
    try:
        requested_plan = PlanType(plan.lower())
    except ValueError:
        requested_plan = PlanType.BASIC
        
    base_price = PLAN_PREMIUMS[requested_plan][0]  # Should be 30, 37, or 44
    
    # Fallback to simple deterministic discount if Model is missing
    if model == "FAILED" or model is None:
        logger.warning(f"Using fallback deterministic discount for {worker_id}.")
        raw_discount_mult = 0.05 if gig_score > 80 else 0.0
    else:
        # 2. Extract Geospacial Features
        avg_dci, pred_dci = _derive_mock_zone_metrics(primary_pincode)
        
        features = pd.DataFrame([{
            'worker_gig_score': gig_score,
            'pincode_30d_avg_dci': avg_dci,
            'predicted_7d_max_dci': pred_dci,
            'shift_morning': int(shift == 'morning'),
            'shift_day': int(shift == 'day'),
            'shift_night': int(shift == 'night'),
            'shift_flexible': int(shift == 'flexible')
        }])
        
        # 3. Model Inference
        prediction = model.predict(features)[0]
        raw_discount_mult = np.clip(prediction, 0.0, 0.30)
        
        # Explainability feature mapping for UI Insights
        reason_msg = _generate_nlp_reason(raw_discount_mult, gig_score, pred_dci, shift)

    # 4. Premium Math
    # Discount is strictly proportional to base price, capped mathematically
    discount_amount = round(base_price * raw_discount_mult, 1)
    
    # Ensure Discount isn't mathematically bizarre
    discount_amount = max(0.0, discount_amount)
    
    final_premium = base_price - discount_amount
    
    # Check if we should offer 'Bonus Coverage' instead of pure discount
    # E.g. If DCI is super high, we don't hike prices (Psychology rule!), 
    # but we might give the worker +1 guaranteed active hour extension!
    bonus_coverage_hours = 0
    if locals().get('pred_dci', 0) > 70:
        bonus_coverage_hours = 2
        
    return {
        "worker_id": worker_id,
        "base_premium": float(base_price),
        "dynamic_premium": float(final_premium),
        "discount_applied": float(discount_amount),
        "bonus_coverage_hours": bonus_coverage_hours,
        "plan_type": requested_plan.value,
        "insights": {
            "reason": locals().get('reason_msg', "Thank you for being a reliable GigKavach partner."),
            "gig_score": gig_score,
            "primary_zone": primary_pincode,
            "forecasted_zone_risk": "High" if locals().get('pred_dci', 0) > 65 else "Normal"
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
