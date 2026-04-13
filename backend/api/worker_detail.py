from fastapi import APIRouter, HTTPException
from utils.db import get_supabase
import logging

logger = logging.getLogger("gigkavach.worker_detail")
router = APIRouter(prefix="/workers", tags=["Workers"])


@router.get("/{worker_id}")
def get_worker_detail(worker_id: str):
    try:
        sb = get_supabase()  # ✅ use your util function

        # 1️⃣ Worker profile
        worker_response = (
            sb.table("workers")
            .select(
                "id, name, phone, pin_codes, shift, shift_start, shift_end, language, plan, coverage_pct, last_seen_at, upi_id, is_active, gig_score, gig_platform, portfolio_score"
            )
            .eq("id", worker_id)
            .execute()
        )

        worker = worker_response.data[0] if worker_response.data else None

        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")

        # 2️⃣ Latest policy
        policy_response = (
            sb.table("policies")
            .select("*")
            .eq("worker_id", worker_id)
            .order("week_start", desc=True)
            .limit(1)
            .execute()
        )

        policy = policy_response.data[0] if policy_response.data else None

        # 3️⃣ Last 10 payouts
        payouts_response = (
            sb.table("payouts")
            .select("*")
            .eq("worker_id", worker_id)
            .order("triggered_at", desc=True)
            .limit(10)
            .execute()
        )

        payouts = [
            {
                "id": p.get("id"),
                "base_amount": p.get("base_amount"),
                "surge_multiplier": p.get("surge_multiplier"),
                "final_amount": p.get("final_amount"),
                "fraud_score": p.get("fraud_score"),
                "status": p.get("status"),
                "triggered_at": p.get("triggered_at"),
            }
            for p in payouts_response.data or []
        ]

        # 4️⃣ Last 20 activities
        activities_response = (
            sb.table("activities")
            .select("*")
            .eq("worker_id", worker_id)
            .order("date", desc=True)
            .limit(20)
            .execute()
        )

        activities = [
            {
                "id": a.get("id"),
                "description": a.get("description"),
                "date": a.get("date"),
            }
            for a in activities_response.data or []
        ]

        # 5️⃣ Last 20 activity logs
        activity_logs_response = (
            sb.table("activity_log")
            .select("*")
            .eq("worker_id", worker_id)
            .order("log_date", desc=True)
            .limit(20)
            .execute()
        )

        activity_logs = [
            {
                "id": al.get("id"),
                "log_date": al.get("log_date"),
                "first_login_at": al.get("first_login_at"),
                "last_login_at": al.get("last_login_at"),
                "active_hours": al.get("active_hours"),
                "orders_completed": al.get("orders_completed"),
                "estimated_earnings": al.get("estimated_earnings"),
                "zone_pin_codes": al.get("zone_pin_codes"),
                "platform_status": al.get("platform_status"),
            }
            for al in activity_logs_response.data or []
        ]

        # 6️⃣ Activity history
        activity_history_response = (
            sb.table("activity_history")
            .select("*")
            .eq("worker_id", worker_id)
            .limit(1)
            .execute()
        )

        activity_history = (
            activity_history_response.data[0]
            if activity_history_response.data
            else None
        )

        return {
            "worker": worker,
            "policy": policy,
            "payouts": payouts,
            "activities": activities,
            "activityLogs": activity_logs,
            "activityHistory": activity_history,
        }

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Worker Detail API Error: {err}")
        raise HTTPException(status_code=500, detail="Internal server error")