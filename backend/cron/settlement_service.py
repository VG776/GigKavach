"""
cron/settlement_service.py — Daily Payout Settlement
────────────────────────────────────────────────────
Runs at 11:55 PM Daily.
Aggregates all disruption data for the day, calculates total hours per worker, 
and triggers the final payout settlement via api/payouts.py.
"""
import logging
import asyncio
from datetime import datetime, time, timedelta, timezone
from api.payouts import calculate_payout, PayoutRequest
from services.eligibility_service import check_eligibility, WORKER_POLICIES_DB

logger = logging.getLogger("gigkavach.settlement")

async def run_daily_settlement():
    """Main settlement loop to be triggered by APScheduler at 11:55 PM."""
    logger.info("🌓 SYSTEM SETTLEMENT INITIATED (11:55 PM)...")
    
    # 1. Determine the 'Day Boundary'
    now = datetime.now(timezone.utc)
    day_start = datetime.combine(now.date(), time.min).replace(tzinfo=timezone.utc)
    
    # 2. Aggregation Logic — Reconciles all DCI windows today (Image #5 Requirement)
    # In a full Supabase implementation, we'd query rows where dci_score >= 65
    # For the hackathon demo, we check if any disruption occurred in the last 24h.
    # (Mocking a 2-hour disruption window for simulation)
    mock_disruption_windows = [
        (now - timedelta(hours=5), now - timedelta(hours=3), 72), # 2 hour gap
    ]

    # 3. Iterate through all workers with active policies
    for worker_id, policy in WORKER_POLICIES_DB.items():
        if policy["status"] != "active": continue
        
        for d_start, d_end, d_score in mock_disruption_windows:
            # 4. Eligibility Check (Firewall) — Re-enforces coverage delays and activity (Image #5)
            eligible, reason = check_eligibility(worker_id, dci_event={
                "disruption_start": d_start.isoformat(),
                "shift_affected": policy["shift"],
                "dci_score": d_score
            })
            
            if eligible:
                # 5. Execute Final Payout Calculation
                # This naturally handles Midnight Splits via internal logic (Image #4)
                payout_req = PayoutRequest(
                    worker_id=worker_id,
                    disruption_start=d_start,
                    disruption_end=d_end,
                    dci_score=d_score
                )
                
                payout_res = await calculate_payout(payout_req)
                logger.info(f"✅ SETTLED: Worker {worker_id} | Amount: ₹{payout_res.payout_amount}")
                
                # TRIGGER SETTLEMENT ALERT (Requirement §11 / Image #5)
                from api.whatsapp import send_whatsapp_alert
                send_whatsapp_alert(worker_id, "payout_sent", {
                    "amount": payout_res.payout_amount,
                    "upi": policy.get("upi_id", "your UPI"),
                    "ref": f"RZP_SETTLE_{worker_id[:4].upper()}"
                })
            else:
                logger.warning(f"❌ REJECTED: Worker {worker_id} ineligible. Reason: {reason}")

    logger.info("🏁 DAILY SETTLEMENT CYCLE COMPLETED.")

if __name__ == "__main__":
    asyncio.run(run_daily_settlement())
