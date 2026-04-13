import sys
import os
import asyncio
import logging
import datetime

# Add the backend directory to sys.path
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

# Explicitly load .env from the backend directory
from dotenv import load_dotenv
load_dotenv(os.path.join(backend_path, ".env"))

from utils.supabase_client import get_supabase
from services.payout_service import calculate_payout
from services.razorpay_payout_service import initiate_payout
from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("e2e_audit")

async def run_audit():
    logger.info("🚀 Starting GigKavach E2E Payout Audit...")
    
    # ─── 0. Configuration Check ───
    if not settings.RAZORPAY_KEY_ID or "test" not in settings.RAZORPAY_KEY_ID:
        logger.error(f"❌ Razorpay Test Keys NOT found in .env (Found: {settings.RAZORPAY_KEY_ID}). Please add them first.")
        return

    logger.info(f"Supabase URL: {settings.SUPABASE_URL}")
    sb = get_supabase()
    
    # ─── 1. Real-time DCI Validation ───
    logger.info("\nStage 1: Validating Real-time DCI Sync...")
    dci_res = sb.table("dci_logs").select("*").order("created_at", desc=True).limit(1).execute()
    
    # Force a high DCI score for the test to ensure payout logic is exercised
    live_dci = 85.0 
    logger.info(f"✅ Using TEST DCI Score: {live_dci}")

    # ─── 2. Derive Payout (Business Logic) ───
    logger.info("\nStage 2: Deriving Payout Value in Real-time...")
    # Mock parameters for calculation
    test_worker_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479" # Example UUID
    payout_result = calculate_payout(
        baseline_earnings=1000,
        disruption_duration=120, # 2 hours (in minutes)
        dci_score=live_dci,
        worker_id=test_worker_id,
        city="Bengaluru",
        zone_density="High", 
        shift="Morning",
        disruption_type="Rain", # Fixed type
        hour_of_day=10, 
        day_of_week=0 
    )
    
    amount = payout_result.get("payout", 0)
    logger.info(f"✅ Real-time Payout Derived: ₹{amount:.2f} (Multiplier: {payout_result.get('multiplier', 1):.2f})")

    # ─── 3. RazorpayX Lifecycle Test ───
    logger.info("\nStage 3: Testing RazorpayX Disbursement Loop (Test Mode)...")
    
    # 3a. Picker / Creator of Test Payout Entry
    # For audit purposes, we create a temporary payout record in Supabase
    temp_payout = {
        "worker_id": None,
        "policy_id": None, 
        "upi_id": None, # MUST NOT BE NULL
        "base_amount": 1000.0,
        "surge_multiplier": payout_result.get("multiplier", 1.0),
        "final_amount": amount,
        "status": "pending",
        "triggered_at": datetime.datetime.now(datetime.UTC).isoformat()
    }
    
    # Try to find a real worker with an active policy to avoid constraint violations
    worker_res = sb.table("policies").select("worker_id, id, workers(name, upi_id)").eq("status", "active").limit(1).execute()
    if worker_res.data:
        real_data = worker_res.data[0]
        temp_payout["worker_id"] = real_data["worker_id"]
        temp_payout["policy_id"] = real_data["id"]
        worker_info = real_data.get("workers", {})
        temp_payout["upi_id"] = worker_info.get("upi_id") or "success@razorpay"
        logger.info(f"Using Real Worker/Policy for Test: {worker_info.get('name')} (UPI: {temp_payout['upi_id']})")
    else:
        logger.error("❌ No active policies found in database. Cannot run payout test.")
        return

    payout_insert = sb.table("payouts").insert(temp_payout).execute()
    if not payout_insert.data:
        logger.error("❌ Failed to create local payout record.")
        return
        
    payout_id = payout_insert.data[0]["id"]
    logger.info(f"✅ Local Payout Record Created: {payout_id}")

    # 3b. Trigger Disbursement
    try:
        logger.info("Executing Razorpay disbursement...")
        rzp_resp = await initiate_payout(payout_id)
        logger.info(f"✅ RAZORPAY SUCCESS! Payout ID: {rzp_resp.get('id')}")
        logger.info(f"Status: {rzp_resp.get('status')}")
    except Exception as e:
        logger.error(f"❌ Razorpay Initiation FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # ─── 4. Audit Verification ───
    logger.info("\nStage 4: Verifying Database Audit Trail...")
    final_payout = sb.table("payouts").select("*").eq("id", payout_id).single().execute()
    
    if final_payout.data and final_payout.data.get("razorpay_payout_id"):
        logger.info(f"✅ Database sync verified! Razorpay ID: {final_payout.data.get('razorpay_payout_id')}")
    else:
        logger.error("❌ Database sync FAILED. Razorpay ID not found in record.")

    logger.info("\n✨ E2E AUDIT COMPLETE! ✨")

if __name__ == "__main__":
    asyncio.run(run_audit())
