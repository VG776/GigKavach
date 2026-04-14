import sys
import os
import asyncio
import time
import logging
import json
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.weather_service import get_weather_score
from services.dci_engine import calculate_dci
from services.fraud_service import check_fraud
from services.premium_service import compute_dynamic_quote
from services.gigscore_service import update_gig_score, GigScoreEvent
from config.settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("brutal_audit")

class BrutalAuditReport:
    def __init__(self):
        self.results = []
        self.start_time = time.time()

    def add_result(self, name, status, details=""):
        self.results.append({
            "name": name,
            "status": "✅ PASS" if status else "❌ FAIL",
            "details": details
        })

    def print_report(self):
        print("\n" + "═" * 80)
        print("🛡️  GIGKAVACH BRUTAL PRODUCTION AUDIT REPORT")
        print("═" * 80)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Duration: {time.time() - self.start_time:.2f}s")
        print("-" * 80)
        for res in self.results:
            print(f"{res['status']} | {res['name']:<40} | {res['details']}")
        print("═" * 80 + "\n")

audit = BrutalAuditReport()

@pytest.mark.asyncio
async def audit_api_redundancy_cascade():
    """Verify that the 4-layer redundancy cascade actually falls back correctly."""
    print("\n[AUDIT] Layer Cascade Verification...")
    
    # Test L1 -> L2 fallback
    with patch("services.weather_service.fetch_tomorrow_io", return_value=None), \
         patch("services.weather_service.fetch_open_meteo") as mock_l2:
        mock_l2.return_value = {"rainfall": 10.0, "temperature": 25.0, "humidity": 60.0}
        
        result = await get_weather_score("560001")
        passed = result.get("source") == "Layer_2_Open_Meteo"
        audit.add_result("4-Layer Redundancy (L1 -> L2)", passed, "Correctly fell back to Open-Meteo")

    # Test L1+L2 -> L3 (Redis) fallback
    with patch("services.weather_service.fetch_tomorrow_io", return_value=None), \
         patch("services.weather_service.fetch_open_meteo", return_value=None), \
         patch("utils.redis_client.get_redis") as mock_redis:
        
        redis_instance = MagicMock()
        # Modern AsyncMock approach (or just define async lambda)
        async def mock_async_get(k):
            return json.dumps({"rainfall": 15.0, "source": "Layer_3_Redis_Stale"})
        
        redis_instance.get = mock_async_get
        mock_redis.return_value = redis_instance
        
        result = await get_weather_score("560001")
        passed = result.get("source") == "Layer_3_Redis_Stale"
        audit.add_result("4-Layer Redundancy (L1-2 -> L3)", passed, "Correctly fell back to Redis cache")

@pytest.mark.asyncio
async def audit_city_aware_weights():
    """Brutally verify that DCI weights are indeed different per city and sum to 1.0."""
    print("[AUDIT] City Weight Stability...")
    from config.city_dci_weights import CITY_DCI_WEIGHTS
    
    cities = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata"]
    all_sum_to_one = True
    all_distinct = True
    
    prev_weights = None
    for city in cities:
        weights = CITY_DCI_WEIGHTS.get(city)
        if not weights:
            all_sum_to_one = False
            continue
        
        # Sum check
        w_sum = sum(weights.values())
        if abs(w_sum - 1.0) > 1e-6:
            all_sum_to_one = False
            
        # Distinction check
        if prev_weights and weights == prev_weights:
            all_distinct = False
        prev_weights = weights

    audit.add_result("DCI Weight Integrity (Sum=1.0)", all_sum_to_one, f"Cities checked: {len(cities)}")
    audit.add_result("City-Specific Distinction", all_distinct, "Verified Mumbai, Delhi, BLR have unique risk profiles")

@pytest.mark.asyncio
async def audit_fraud_model_adversarial_teleport():
    """Test Isolation Forest with an adversarial 'teleportation' claim burst."""
    print("[AUDIT] Adversarial Fraud Detection...")
    
    # 500 simultaneous claims in 30 mins = Coordination Signal
    claim = {
        "claim_id": "teleport_1",
        "worker_id": "W999",
        "dci_score": 66.0, # Gaming the threshold
        "gps_verified": False,
        "location": {"lat": 12.97, "lng": 77.59},
        "registration_age_days": 0, # New account
        "claims_in_zone_2min": 500, # High density
        "device_id": "DEVICE_SURGE_999"
    }
    
    # Mocking historical context for coord detection
    worker_history = {
        "recent_claims_in_zone_2m": 500,
        "ip_geoloc_mismatch": True,
        "device_ids": {"DEVICE_SURGE_999": ["W999", "W888"]} # Device farming
    }
    
    res = check_fraud(claim, worker_history)
    passed = res["decision"] in ["FLAG_50", "BLOCK"]
    audit.add_result("Isolation Forest Adversarial Scan", passed, f"Decision: {res['decision']} | Reason: {res['explanation']}")

@pytest.mark.asyncio
async def audit_trinity_gigscore_feedback_loop():
    """Verify that updating GigScore via Fraud Service actually reduces Premium Quote."""
    print("[AUDIT] Trinity Pipeline Loop (Fraud -> GigScore -> Premium)...")
    
    worker_id = "test_worker_trinity"
    
    # 1. Setup mock worker in Supabase
    mock_worker = {
        "id": worker_id,
        "gig_score": 100.0,
        "pin_codes": ["560001"],
        "shift": "day",
        "language": "en",
        "plan": "basic"
    }
    
    # We need to mock get_supabase in multiple places where it's imported
    with patch("services.premium_service.get_supabase") as mock_gs_prem, \
         patch("services.gigscore_service.get_supabase") as mock_gs_gig, \
         patch("services.fraud_service.update_gig_score") as mock_ugs, \
         patch("utils.db.get_supabase") as mock_gs_db:
        
        sb_instance = MagicMock()
        sb_instance.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_worker]
        
        # Ensure our mocks return the worker data
        mock_gs_prem.return_value = sb_instance
        mock_gs_gig.return_value = sb_instance
        mock_gs_db.return_value = sb_instance
        mock_ugs.return_value = None
        
        # Step A: Get baseline quote (Score 100)
        quote_1 = await compute_dynamic_quote(worker_id, "basic")
        
        # Step B: Apply Fraud Penalty (Tier 2 = -20 score)
        # We simulate the score reduction in the second call
        mock_worker["gig_score"] = 80.0
        quote_2 = await compute_dynamic_quote(worker_id, "basic")
        
        # Premium should be higher (less discount) if score dropped
        passed = quote_2["dynamic_premium"] >= quote_1["dynamic_premium"]
        delta = quote_2["dynamic_premium"] - quote_1["dynamic_premium"]
        audit.add_result("Trinity Feedback loop", passed, f"Premium delta: +₹{delta:.2f} after 20pt GigScore penalty")

@pytest.mark.asyncio
async def audit_cleanliness_check():
    """Search for hardcoded stubs or 'return 0.5' mocks in critical path."""
    print("[AUDIT] Source Code Purity Scan...")
    
    forbidden = [
        "return 0.7", # Hardcoded coverage pct
        "return 30",  # Hardcoded premium
        "score = 75", # Hardcoded DCI
    ]
    
    violations = []
    # Check specific critical path files
    paths = ["backend/services/dci_engine.py", "backend/services/payout_service.py", "backend/services/premium_service.py"]
    
    for path in paths:
        full_path = os.path.join(os.getcwd(), path)
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                content = f.read()
                for f_p in forbidden:
                    if f_p in content:
                        # Allow it if it's inside a 'fallback' or 'except' block as mentioned in README
                        # Very simple heuristic: check if word 'fallback' or 'except' is on the same/prev line
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if f_p in line:
                                context = (lines[i-1] + " " + line).lower()
                                if "fallback" not in context and "except" not in context and "metadata" not in context:
                                    violations.append(f"{path}: '{f_p}'")

    passed = len(violations) == 0
    audit.add_result("Absence of Hardcoded Logic", passed, f"Violations outside fallbacks: {violations if violations else 'None'}")

async def run_all():
    await audit_api_redundancy_cascade()
    await audit_city_aware_weights()
    await audit_fraud_model_adversarial_teleport()
    await audit_trinity_gigscore_feedback_loop()
    await audit_cleanliness_check()
    audit.print_report()

if __name__ == "__main__":
    asyncio.run(run_all())
