#!/usr/bin/env python3
"""
demo_claims_pipeline.py
─────────────────────────────────────────────────────────────────────
End-to-End Claims Processing Demo

Demonstrates the complete GigKavach claims processing pipeline:
  1. Sample disruption claims (real-world scenarios)
  2. Feature extraction from claim data
  3. Dynamic payout multiplier prediction (XGBoost v3)
  4. Payout calculation with breakdown
  5. Confidence scoring

This is the Phase 2 demo script for evaluating model performance
and claims processing integration.

Usage:
  python3 backend/demo_claims_pipeline.py

Requirements:
  - XGBoost v3 model trained (models/v3/xgboost_payout_v3.pkl)
  - All backend services imported and configured
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import logging

# Handle imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from ml.xgboost_loader import (
    extract_features,
    predict_with_confidence,
    load_metadata
)
from services.payout_service import calculate_payout

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo_claims_pipeline")


# ─────────────────────────────────────────────────────────────────
#  SAMPLE CLAIMS DATA
# ─────────────────────────────────────────────────────────────────

SAMPLE_CLAIMS = [
    {
        "claim_id": "CLM-20260328-001",
        "worker_id": "WKR-12547",
        "name": "Rajesh Kumar",
        "city": "Mumbai",
        "zone_density": "Mid",
        "shift": "Evening",
        "baseline_earnings": 1200.0,  # ₹
        "disruption_type": "Flood",
        "disruption_trigger_time": "2026-03-28 14:15",
        "impact_duration_minutes": 245,  # 4h 5m
        "dci_score": 78.5,
        "description": "Heavy flooding in suburban areas due to monsoon rain"
    },
    {
        "claim_id": "CLM-20260328-002",
        "worker_id": "WKR-89234",
        "name": "Priya Sharma",
        "city": "Delhi",
        "zone_density": "High",
        "shift": "Morning",
        "baseline_earnings": 950.0,  # ₹
        "disruption_type": "Traffic_Gridlock",
        "disruption_trigger_time": "2026-03-28 08:30",
        "impact_duration_minutes": 120,  # 2h
        "dci_score": 62.3,
        "description": "Major traffic gridlock on Ring Road due to accident"
    },
    {
        "claim_id": "CLM-20260328-003",
        "worker_id": "WKR-45612",
        "name": "Ahmed Hassan",
        "city": "Mumbai",
        "zone_density": "Low",
        "shift": "Night",
        "baseline_earnings": 1850.0,  # ₹
        "disruption_type": "Heatwave",
        "disruption_trigger_time": "2026-03-28 18:45",
        "impact_duration_minutes": 180,  # 3h
        "dci_score": 45.2,
        "description": "Extreme heat wave with temperatures >42°C in Mahim"
    },
    {
        "claim_id": "CLM-20260328-004",
        "worker_id": "WKR-67890",
        "name": "Sarita Gupta",
        "city": "Chennai",
        "zone_density": "Mid",
        "shift": "Morning",
        "baseline_earnings": 1100.0,  # ₹
        "disruption_type": "Rain",
        "disruption_trigger_time": "2026-03-28 07:00",
        "impact_duration_minutes": 90,  # 1.5h
        "dci_score": 55.8,
        "description": "Moderate rainfall affecting ride requests in CBD"
    },
    {
        "claim_id": "CLM-20260328-005",
        "worker_id": "WKR-11223",
        "name": "Vikram Singh",
        "city": "Delhi",
        "zone_density": "Low",
        "shift": "Morning",
        "baseline_earnings": 1500.0,  # ₹
        "disruption_type": "Flood",
        "disruption_trigger_time": "2026-03-28 17:20",
        "impact_duration_minutes": 210,  # 3.5h
        "dci_score": 72.1,
        "description": "Flash flooding in Dwarka after heavy downpour"
    },
]


# ─────────────────────────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def get_hour_and_day(timestamp_str: str) -> tuple:
    """Extract hour and day of week from timestamp."""
    dt = datetime.fromisoformat(timestamp_str)
    hour = dt.hour
    day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
    return hour, day_of_week


def process_single_claim(claim: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single claim through the complete pipeline.
    
    Returns:
        dict with all results and metrics
    """
    claim_id = claim["claim_id"]
    
    # Extract temporal features
    hour_of_day, day_of_week = get_hour_and_day(claim["disruption_trigger_time"])
    
    # Extract and predict
    features = extract_features(
        dci_score=claim["dci_score"],
        baseline_earnings=claim["baseline_earnings"],
        hour_of_day=hour_of_day,
        day_of_week=day_of_week,
        city=claim["city"],
        zone_density=claim["zone_density"],
        shift=claim["shift"],
        disruption_type=claim["disruption_type"]
    )
    
    # Get prediction with confidence
    prediction_result = predict_with_confidence(features)
    multiplier = prediction_result['multiplier']
    confidence = prediction_result['confidence']
    # Simple bounds estimation (±0.2x based on confidence)
    bounds = (
        max(1.0, multiplier - (0.3 * (1 - confidence))),
        min(5.0, multiplier + (0.3 * (1 - confidence)))
    )
    
    # Calculate payout
    payout_result = calculate_payout(
        baseline_earnings=claim["baseline_earnings"],
        disruption_duration=claim["impact_duration_minutes"],
        dci_score=claim["dci_score"],
        worker_id=claim["worker_id"],
        city=claim["city"],
        zone_density=claim["zone_density"],
        shift=claim["shift"],
        disruption_type=claim["disruption_type"],
        hour_of_day=hour_of_day,
        day_of_week=day_of_week,
        include_confidence=True
    )
    
    return {
        "claim": claim,
        "temporal_features": {
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
        },
        "model_prediction": {
            "multiplier": multiplier,
            "confidence": confidence,
            "bounds": bounds,
            "recommendation": prediction_result.get('recommendation', 'Review')
        },
        "payout_calculation": payout_result,
    }


def format_time_of_day(hour: int) -> str:
    """Convert hour to readable time period."""
    if 6 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    elif 17 <= hour < 21:
        return "Evening"
    else:
        return "Night"


def format_day_of_week(day: int) -> str:
    """Convert day index to day name."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days[day % 7]


def print_section_header(title: str, char: str = "─"):
    """Print a formatted section header."""
    width = 70
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def print_result(result: Dict[str, Any], index: int = 0):
    """Pretty-print the processing result for a single claim."""
    claim = result["claim"]
    temporal = result["temporal_features"]
    prediction = result["model_prediction"]
    payout = result["payout_calculation"]
    
    # Header with claim info
    print(f"\n{'='*70}")
    print(f"CLAIM #{index + 1}: {claim['claim_id']} | {claim['worker_id']}")
    print(f"{'='*70}")
    
    # Claim summary
    print(f"\n📋 WORKER & CLAIM DETAILS:")
    print(f"   Name:              {claim['name']}")
    print(f"   City:              {claim['city']} ({claim['zone_density']} density)")
    print(f"   Shift:             {claim['shift']}")
    print(f"   Baseline Earnings: ₹{claim['baseline_earnings']:.2f}")
    print(f"   Disruption Type:   {claim['disruption_type']}")
    print(f"   Impact Duration:   {claim['impact_duration_minutes']} minutes")
    print(f"   Description:       {claim['description']}")
    
    # Temporal & DCI
    print(f"\n⏰ TEMPORAL & DISRUPTION CONTEXT:")
    print(f"   Trigger Time:      {claim['disruption_trigger_time']}")
    print(f"   Hour of Day:       {temporal['hour_of_day']:02d}:00 ({format_time_of_day(temporal['hour_of_day'])})")
    print(f"   Day of Week:       {format_day_of_week(temporal['day_of_week'])}")
    print(f"   DCI Score:         {claim['dci_score']:.1f}/100")
    
    # Model prediction
    print(f"\n🤖 MODEL PREDICTION (XGBoost v3):")
    print(f"   Multiplier:        {prediction['multiplier']:.2f}x")
    print(f"   Confidence:        {prediction['confidence']:.1%}")
    print(f"   Range (95%):       {prediction['bounds'][0]:.2f}x – {prediction['bounds'][1]:.2f}x")
    
    # Payout breakdown
    print(f"\n💰 PAYOUT CALCULATION:")
    if "error" not in payout:
        breakdown = payout.get("breakdown", {})
        print(f"   Base Amount:       ₹{breakdown.get('baseline_earnings', 0):.2f}")
        print(f"   Duration Factor:   {breakdown.get('duration_factor', 0):.3f}")
        print(f"   Multiplier:        {breakdown.get('dci_score', 0) if 'dci_score' in breakdown else payout.get('multiplier', 0):.2f}x")
        print(f"   ────────────────────────────────")
        print(f"   FINAL PAYOUT:      ₹{payout.get('payout', 0):.2f}")
        
        # Confidence indicator
        if payout.get('confidence'):
            print(f"   Confidence:        {payout.get('confidence'):.1%}")
    else:
        print(f"   ❌ Error: {payout['error']}")
    
    # Recommendation
    print(f"\n✅ APPROVAL RECOMMENDATION:")
    recommended_amount = payout.get("payout", 0)
    if recommended_amount > 0:
        print(f"   Amount: ₹{recommended_amount:.2f}")
        if payout.get('confidence'):
            print(f"   Confidence: {payout.get('confidence'):.1%}")
            if payout['confidence'] > 0.70:
                print(f"   Status: ✅ Approve (High confidence)")
            elif payout['confidence'] > 0.60:
                print(f"   Status: ⚠️ Review (Moderate confidence)")
            else:
                print(f"   Status: ❌ Escalate (Low confidence)")
    else:
        print(f"   Cannot process claim due to missing data")
    
    print(f"\n{'─'*70}")


# ─────────────────────────────────────────────────────────────────
#  MAIN DEMO
# ─────────────────────────────────────────────────────────────────

def run_demo():
    """Execute the end-to-end demo pipeline."""
    print("\n" + "="*70)
    print("🎯 GIGKAVACH CLAIMS PROCESSING DEMO - PHASE 2 EVALUATION")
    print("="*70)
    
    # Load model info
    print("\n📦 Loading XGBoost v3 Model...")
    try:
        metadata = load_metadata()
        print(f"   ✅ Model: {metadata.get('model_name', 'XGBoost v3')}")
        
        training_samples = metadata.get('training', {}).get('train_samples', 'N/A')
        num_features = metadata.get('training', {}).get('num_features', 'N/A')
        print(f"   ✅ Training Samples: {training_samples}")
        print(f"   ✅ Features: {num_features} dimensions")
        
        test_r2 = metadata.get('performance', {}).get('test', {}).get('r2', 'N/A')
        if test_r2 != 'N/A':
            print(f"   ✅ Test R²: {test_r2:.4f}")
    except Exception as e:
        print(f"   ❌ Error loading model: {e}")
        return
    
    print_section_header("PROCESSING 5 SAMPLE CLAIMS")
    
    # Process all claims
    results = []
    for i, claim in enumerate(SAMPLE_CLAIMS):
        try:
            result = process_single_claim(claim)
            results.append(result)
            print_result(result, i)
        except Exception as e:
            print(f"\n❌ Error processing claim {claim['claim_id']}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary statistics
    print_section_header("PIPELINE SUMMARY", "═")
    
    if results:
        total_payout = sum(
            r["payout_calculation"].get("payout", 0)
            for r in results
            if "payout" in r["payout_calculation"]
        )
        avg_multiplier = sum(
            r["model_prediction"]["multiplier"]
            for r in results
        ) / len(results)
        avg_confidence = sum(
            r["model_prediction"]["confidence"]
            for r in results
        ) / len(results)
        
        print(f"\n📊 PROCESSING RESULTS:")
        print(f"   Claims Processed:  {len(results)} / {len(SAMPLE_CLAIMS)}")
        print(f"   Total Payout:      ₹{total_payout:.2f}")
        print(f"   Avg Multiplier:    {avg_multiplier:.2f}x")
        print(f"   Avg Confidence:    {avg_confidence:.1%}")
    
    print(f"\n✨ DEMO COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_demo()
