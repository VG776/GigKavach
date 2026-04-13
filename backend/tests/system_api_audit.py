"""
backend/tests/system_api_audit.py
─────────────────────────────────────────────────────────────
Comprehensive Audit Script to verify API stability and 
Real-time data flow for the GigKavach Backend Core.
"""

import os
import sys
import asyncio
import json
import logging
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from main import app
from services.weather_service import get_weather_score
from services.aqi_service import get_aqi_score
from services.premium_service import compute_dynamic_quote
from services.gigscore_service import update_gig_score, GigScoreEvent
from utils.db import get_supabase

# Configure logging to see the data cascade
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("api_audit")

client = TestClient(app)

async def audit_dci_realtime():
    """Verify that DCI engine consumes real-time values (Layer 1 or 2)."""
    print("\n--- [Audit] DCI Engine Real-time Flow ---")
    pincode = "560001"
    
    # Weather Audit
    weather = await get_weather_score(pincode)
    print(f"  [Weather] Source: {weather.get('source', 'Unknown')}")
    print(f"  [Weather] Score: {weather.get('score', 0)} | Rain: {weather.get('rainfall', 0)}mm")
    
    # AQI Audit
    aqi = await get_aqi_score(pincode)
    print(f"  [AQI] Source: {aqi.get('source', 'Unknown')}")
    print(f"  [AQI] Index: {aqi.get('aqi', 0)}")
    
    return weather, aqi

async def audit_premium_logic():
    """Verify that Premium Engine pulls live worker and zone data."""
    print("\n--- [Audit] AI Premium Engine ---")
    # Using a known test/demo worker if exists, or a random one for path testing
    sb = get_supabase()
    res = sb.table("workers").select("id").limit(1).execute()
    
    if not res.data:
        print("  [SKIP] No workers in DB to test premium quote.")
        return
    
    worker_id = res.data[0]["id"]
    print(f"  [Action] Requesting quote for worker: {worker_id}")
    
    quote = await compute_dynamic_quote(worker_id, "pro")
    print(f"  [Result] Dynamic Premium: ₹{quote['dynamic_premium']} (Base: ₹{quote['base_premium']})")
    print(f"  [Result] Reason: {quote['insights']['reason']}")
    print(f"  [Verified] DCI Risk Level: {quote['insights']['forecasted_zone_risk']}")

def audit_api_endpoints():
    """Thoroughly check endpoint reachability."""
    print("\n--- [Audit] API Endpoint Health ---")
    
    # 1. Health
    resp = client.get("/api/v1/health")
    print(f"  [GET /health] Status: {resp.status_code} | {resp.json().get('status', 'FAIL')}")
    
    # 2. Worker List
    resp = client.get("/api/v1/workers")
    print(f"  [GET /workers] Status: {resp.status_code} | Count: {len(resp.json()) if resp.is_success else 'ERR'}")
    
    # 3. Share Tokens (Security check)
    resp = client.get("/api/v1/share-tokens/non-existent-id")
    print(f"  [GET /share-tokens] Status: {resp.status_code} (Expected 404/Empty)")

async def main():
    print("🚀 Starting GigKavach System Audit...")
    
    # 1. Connectivity Check
    try:
        sb = get_supabase()
        sb.table("workers").select("count").limit(1).execute()
        print("✅ Supabase: Connected")
    except Exception as e:
        print(f"❌ Supabase: Connection Failed - {e}")

    # 2. API Endpoints
    audit_api_endpoints()
    
    # 3. Real-time DCI
    await audit_dci_realtime()
    
    # 4. Premium AI
    await audit_premium_logic()
    
    print("\n--- Audit Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
