"""
cron/settlement_service.py — Daily Payout Settlement (City-Aware)
──────────────────────────────────────────────────────────────────
Runs at 11:55 PM Daily.
Aggregates all disruption data for the day, calculates total hours per worker,
and triggers the final payout settlement via api/payouts.py.

Now city-aware: each worker's city is resolved from their pincode or DB record
so the payout calculation uses the correct city-specific DCI weight profile.
"""
import logging
import asyncio
from datetime import datetime, time, timedelta, timezone
from typing import List, Tuple
from api.payouts import calculate_payout, PayoutRequest
from services.eligibility_service import check_eligibility
from config.city_dci_weights import resolve_city_from_pincode, normalise_city_name
from config.settings import settings

logger = logging.getLogger("gigkavach.settlement")


# ─── Settlement Helper Functions ──────────────────────────────────────────────

def _get_todays_disruptions(day_start: datetime) -> List[Tuple[datetime, datetime, float]]:
    """
    Queries dci_logs for all disruption windows today where total_score >= 65
    (the payout trigger threshold). Merges consecutive high-DCI windows into
    contiguous disruption blocks per zone.

    Returns:
        List of (start_dt, end_dt, avg_dci_score) tuples — one per disruption window.
    """
    try:
        from utils.supabase_client import get_supabase
        sb = get_supabase()

        day_end = day_start + timedelta(hours=24)

        result = (
            sb.table("dci_logs")
            .select("pincode, total_score, severity_tier, created_at")
            .gte("created_at", day_start.isoformat())
            .lte("created_at", day_end.isoformat())
            .gte("total_score", 65)         # Only payout-triggering disruptions
            .order("created_at", desc=False)
            .execute()
        )

        rows = result.data if result.data else []
        if not rows:
            logger.info("[SETTLEMENT] No qualifying DCI events found today.")
            return []

        # Group rows into contiguous disruption blocks.
        # Two DCI readings are "the same disruption" if < 15 min apart.
        windows: List[Tuple[datetime, datetime, float]] = []
        MERGE_GAP_MINUTES = 15

        block_start = None
        block_end = None
        block_scores = []

        for row in rows:
            ts_raw = row.get("created_at", "")
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except Exception:
                continue

            score = float(row.get("total_score", 0))

            if block_start is None:
                # Start first block
                block_start = ts
                block_end = ts
                block_scores = [score]
            else:
                gap = (ts - block_end).total_seconds() / 60
                if gap <= MERGE_GAP_MINUTES:
                    # Extend current block
                    block_end = ts
                    block_scores.append(score)
                else:
                    # Close current block, start new one
                    avg_score = sum(block_scores) / len(block_scores)
                    windows.append((block_start, block_end, avg_score))
                    block_start = ts
                    block_end = ts
                    block_scores = [score]

        # Close the last open block
        if block_start is not None:
            avg_score = sum(block_scores) / len(block_scores)
            # Assume disruption lasted at least 30 min if only one reading
            effective_end = block_end if (block_end - block_start).total_seconds() > 0 else block_start + timedelta(minutes=30)
            windows.append((block_start, effective_end, avg_score))

        logger.info(f"[SETTLEMENT] Found {len(windows)} disruption window(s) today.")
        return windows

    except Exception as e:
        logger.error(f"[SETTLEMENT] Failed to fetch today's disruptions: {e}")
        return []


def _get_active_worker_policies() -> List[dict]:
    """
    Fetches all currently active workers along with their active policy.
    Joins workers → policies in a single Supabase query to avoid N+1 queries.

    Returns:
        List of worker dicts, each enriched with a 'policies' key containing
        the list of their active policy records.
    """
    try:
        from utils.supabase_client import get_supabase
        sb = get_supabase()

        # Fetch all workers who are active (using verified live-DB columns)
        workers_result = (
            sb.table("workers")
            .select("id, phone, shift, upi_id, plan, pin_codes, is_active")
            .eq("is_active", True)
            .execute()
        )
        workers = workers_result.data if workers_result.data else []
        if not workers:
            logger.info("[SETTLEMENT] No active workers found.")
            return []

        worker_ids = [w["id"] for w in workers]

        # Fetch all active policies (using verified live-DB columns only)
        policies_result = (
            sb.table("policies")
            .select("worker_id, plan, status, coverage_pct, weekly_premium, week_start")
            .in_("worker_id", worker_ids)
            .eq("status", "active")
            .execute()
        )
        policies = policies_result.data if policies_result.data else []

        # Build a dict of worker_id → [policies]
        policy_map: dict = {}
        for p in policies:
            wid = p["worker_id"]
            policy_map.setdefault(wid, [])
            # Treat any policy returned by status='active' filter as active
            p["is_active"] = True
            policy_map[wid].append(p)

        # Enrich workers with their policies + resolve primary pincode
        enriched = []
        for w in workers:
            wid = w["id"]
            w_policies = policy_map.get(wid, [])
            if not w_policies:
                continue  # Skip workers with no active policy this week

            # Resolve primary pincode (first in list)
            pin_codes = w.get("pin_codes") or []
            w["pincode"] = pin_codes[0] if pin_codes else ""
            w["policies"] = w_policies
            enriched.append(w)

        logger.info(f"[SETTLEMENT] {len(enriched)} workers with active policies ready for settlement.")
        return enriched

    except Exception as e:
        logger.error(f"[SETTLEMENT] Failed to fetch active worker policies: {e}")
        return []


def get_worker_baseline(worker_id: str, plan: str = "basic") -> float:
    """
    Proxy to the canonical baseline service.
    Keeps settlement_service free of direct DB logic while reusing
    the fully-featured 4-week rolling median implementation.
    """
    try:
        from services.baseline_service import get_worker_baseline as _get_baseline
        return _get_baseline(worker_id, plan=plan)
    except Exception as e:
        logger.error(f"[SETTLEMENT] Baseline lookup failed for {worker_id}: {e}")
        # Conservative plan-tier fallback
        defaults = {"basic": 800.0, "plus": 1100.0, "pro": 1500.0}
        return defaults.get(plan.lower(), 800.0)

async def run_daily_settlement():
    """Main settlement loop triggered by APScheduler at 11:55 PM."""
    logger.info("🌓 SYSTEM SETTLEMENT INITIATED (11:55 PM)...")

    from utils.supabase_client import get_supabase
    sb = get_supabase()

    # 1. Determine the day boundary
    now = datetime.now(timezone.utc)
    day_start = datetime.combine(now.date(), time.min).replace(tzinfo=timezone.utc)

    # 2. Fetch disruption windows from DCI logs (Task 7: DB-backed)
    disruption_windows = _get_todays_disruptions(day_start)
    if not disruption_windows:
        logger.info("[SETTLEMENT] No disruption events today. Exiting.")
        return

    # 3. Fetch active workers with their policies (Task 7: DB-backed)
    workers = _get_active_worker_policies()
    if not workers:
        logger.warning("[SETTLEMENT] No active workers found. Exiting.")
        return

    settled_count = 0
    rejected_count = 0

    # 4. Iterate through all workers with active policies
    for worker in workers:
        worker_id = worker["id"]
        active_policies = [
            p for p in (worker.get("policies") or []) if p.get("is_active")
        ]
        if not active_policies:
            continue

        policy = active_policies[0]  # Use most recent active policy
        # Shift: read from worker record (always present) → policy fallback
        worker_shift = worker.get("shift") or policy.get("shift", "day")

        for d_start, d_end, d_score in disruption_windows:
            # 5. Eligibility check firewall (24-hr coverage delay + shift alignment)
            eligible, reason = check_eligibility(worker_id, dci_event={
                "disruption_start": d_start.isoformat(),
                "shift_affected":   worker_shift,
                "dci_score":        d_score,
            })

            if not eligible:
                logger.debug(f"[SETTLEMENT] ❌ Ineligible: worker={worker_id} reason={reason}")
                rejected_count += 1
                continue

            # 5.5 CRITICAL FIX: Fraud verification before payout
            # Check if this worker has any fraud-flagged claims during this disruption window
            fraud_check_passed = True
            try:
                from utils.supabase_client import get_supabase as get_sb_fraud
                sb_fraud = get_sb_fraud()
                if sb_fraud and settings.SUPABASE_URL:
                    claims_result = (
                        sb_fraud.table("claims")
                        .select("id, is_fraud, fraud_decision")
                        .eq("worker_id", worker_id)
                        .gte("created_at", d_start.isoformat())
                        .lte("created_at", d_end.isoformat())
                        .execute()
                    )
                    disruption_claims = claims_result.data if claims_result.data else []
                    
                    # Check each claim for fraud status
                    for claim in disruption_claims:
                        if claim.get("is_fraud") or claim.get("fraud_decision") in ["FLAG_50", "BLOCK"]:
                            logger.warning(
                                f"[SETTLEMENT] ❌ FRAUD DETECTED: Worker {worker_id} claim {claim.get('id')} "
                                f"marked as fraud (decision: {claim.get('fraud_decision')}). Skipping payout."
                            )
                            fraud_check_passed = False
                            break
            except Exception as fraud_check_err:
                logger.error(f"[SETTLEMENT] Fraud check failed: {fraud_check_err}. Proceeding with caution.")
            
            if not fraud_check_passed:
                rejected_count += 1
                continue

            # 6. Task 6: Call SERVICE layer, not API endpoint function
            #    payout_service.calculate_payout handles midnight splits internally
            try:
                duration_hours = (d_end - d_start).total_seconds() / 3600
                duration_minutes = int(duration_hours * 60)
                baseline = get_worker_baseline(worker_id, plan=worker.get("plan", "basic"))

                # Import here to avoid circular dependency at module load time
                from services.payout_service import calculate_payout as svc_calculate_payout

                # ── City Resolution ──────────────────────────────────────────────
                # Priority:
                #   1. worker record's 'city' field (previously stored canonical name)
                #   2. resolve from worker's pincode
                #   3. safe regional fallback → "Bengaluru"
                worker_city_raw = worker.get("city") or ""
                worker_pincode  = worker.get("pincode") or ""

                worker_city = normalise_city_name(worker_city_raw)
                if not worker_city and worker_pincode:
                    worker_city = resolve_city_from_pincode(worker_pincode)
                if not worker_city or worker_city == "default":
                    worker_city = "Bengaluru"
                    logger.debug(
                        f"[SETTLEMENT] Worker {worker_id} city unresolvable — "
                        f"defaulting to Bengaluru"
                    )

                logger.debug(
                    f"[SETTLEMENT] worker={worker_id} | city={worker_city} | "
                    f"pincode={worker_pincode}"
                )

                # ── Payout calculation with city-specific weights ─────────────
                payout_result = svc_calculate_payout(
                    baseline_earnings=baseline,
                    disruption_duration=min(duration_minutes, 480),
                    dci_score=d_score,
                    worker_id=worker_id,
                    city=worker_city,
                    zone_density="Mid",
                    shift=policy.get("shift", "day").capitalize(),
                    disruption_type="Disruption",
                    hour_of_day=d_start.hour,
                    day_of_week=d_start.weekday(),
                    include_confidence=False,
                )

                payout_amount = payout_result.get("payout", 0.0)
                multiplier    = payout_result.get("multiplier", 1.0)

                # ── 8. PERSIST TO DB & DISBURSE ──
                # Create the payout record in 'payouts' table
                payout_insert_data = {
                    "worker_id": worker_id,
                    "base_amount": round(baseline, 2),
                    "surge_multiplier": round(multiplier, 2),
                    "final_amount": round(payout_amount, 2),
                    "status": "pending",
                    "triggered_at": datetime.now(timezone.utc).isoformat()
                }
                
                insert_result = sb.table("payouts").insert(payout_insert_data).execute()
                if not insert_result.data:
                    logger.error(f"[SETTLEMENT] Failed to create payout record for {worker_id}")
                    continue
                
                payout_id = insert_result.data[0]["id"]
                
                # Trigger Razorpay Disbursement
                try:
                    from services.razorpay_payout_service import initiate_payout
                    rzp_response = await initiate_payout(payout_id)
                    rzp_ref = rzp_response.get("id", "PENDING")
                    
                    logger.info(
                        f"✅ DISBURSED: Worker {worker_id} | Amount: ₹{payout_amount:.2f} | RZP: {rzp_ref}"
                    )
                except Exception as rzp_err:
                    logger.error(f"[SETTLEMENT] Razorpay disbursement trigger failed for {payout_id}: {rzp_err}")
                    rzp_ref = "ERROR"

                settled_count += 1
                
                # INTEGRATION: Reward valid severe claims
                if d_score > 85:
                    from services.gigscore_service import update_gig_score, GigScoreEvent
                    update_gig_score(worker_id, GigScoreEvent.VALID_SEVERE_CLAIM, {"dci": d_score})

                # 9. Trigger WhatsApp settlement alert
                try:
                    from services.whatsapp_service import send_settlement_alert
                    await send_settlement_alert(
                        worker_id=worker_id,
                        amount=payout_amount,
                        upi_id=worker.get("upi_id", "your UPI"),
                        hours=duration_hours,
                        ref=rzp_ref,
                    )
                except Exception as wa_err:
                    logger.warning(f"[SETTLEMENT] WhatsApp alert failed for {worker_id}: {wa_err}")

            except Exception as e:
                logger.error(f"[SETTLEMENT] Payout failed for worker {worker_id}: {e}")

    logger.info(
        f"🏁 DAILY SETTLEMENT COMPLETED | Settled: {settled_count} | Rejected: {rejected_count}"
    )

if __name__ == "__main__":
    asyncio.run(run_daily_settlement())
