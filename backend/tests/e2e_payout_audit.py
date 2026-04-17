import sys
import os
import asyncio
import logging
import datetime

# Add the backend directory to sys.path
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_path, ".env"))

from utils.supabase_client import get_supabase
from services.payout_service import calculate_payout
from services.razorpay_payout_service import initiate_payout
from config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("e2e_audit")

async def run_audit():
    logger.info("🚀 Starting GigKavach E2E Payout Audit...")
    sb = get_supabase()
    
    # Force a high DCI score for the test
    live_dci = 85.0 
    logger.info(f"✅ Using TEST DCI Score: {live_dci}")

    # Derive Payout
    worker_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    payout_result = calculate_payout(
        baseline_earnings=1000,
        disruption_duration=120,
        dci_score=live_dci,
        worker_id=worker_id,
        city="Bengaluru",
        zone_density="High", 
        shift="Morning",
        disruption_type="Rain",
        hour_of_day=10, 
        day_of_week=0 
    )
    
    amount = payout_result.get("payout", 0)
    logger.info(f"✅ Real-time Payout Derived: ₹{amount:.2f}")

    logger.info("\n✨ E2E AUDIT COMPLETE! ✨")

if __name__ == "__main__":
    asyncio.run(run_audit())
