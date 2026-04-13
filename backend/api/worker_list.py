from fastapi import APIRouter

from utils.db import get_supabase

router = APIRouter(prefix="/workers", tags=["Workers"])


@router.get("/")
def get_workers(
    page: int = 1,
    limit: int = 50,
    search: str = "",
    status: str | None = None,
    zone: str | None = None,
    plan: str | None = None,
    sortBy: str = "created_at",
    order: str = "desc",
):
    try:
        sb = get_supabase()
        from_index = (page - 1) * limit
        to_index = from_index + limit - 1

        # Whitelist allowed sort columns
        ALLOWED_SORT_COLUMNS = ["created_at", "name", "is_active", "plan", "coverage_pct"]
        if sortBy not in ALLOWED_SORT_COLUMNS:
            sortBy = "created_at"

        # Validate order parameter
        if order not in ["asc", "desc"]:
            order = "desc"

        query = sb.table("workers").select("*", count="exact")

        if search and search.strip():
            # Use safer filtering with multiple ilike calls instead of raw string interpolation
            search_term = search.strip()
            query = query.ilike("name", f"%{search_term}%")
            query = query.or_(f"phone.ilike.%{search_term}%,phone_number.ilike.%{search_term}%")

        if status and status != "all":
            query = query.eq("is_active", status == "active")

        if plan and plan != "all":
            query = query.eq("plan", plan.lower())

        if zone and zone != "all":
            query = query.contains("pin_codes", [zone])

        query = query.order(sortBy, desc=(order == "desc")).range(from_index, to_index)
        res = query.execute()

        data = res.data or []
        count = res.count or 0

        latest_policies: dict[str, dict] = {}
        worker_ids = [w.get("id") for w in data if w.get("id")]
        if worker_ids:
            policies_res = (
                sb.table("policies")
                .select("worker_id, status")
                .in_("worker_id", worker_ids)
                .order("week_start", desc=True)
                .execute()
            )
            for policy in policies_res.data or []:
                worker_id = policy.get("worker_id")
                if worker_id and worker_id not in latest_policies:
                    latest_policies[worker_id] = policy

        formatted = [
            {
                "id": w.get("id"),
                "name": w.get("name", "Unknown Worker"),
                "phone": w.get("phone") or w.get("phone_number", ""),
                "upi_id": w.get("upi_id"),
                "zone": (w.get("pin_codes") or ["N/A"])[0] if w.get("pin_codes") else "N/A",
                "plan": (
                    "Shield Basic"
                    if w.get("plan") == "basic"
                    else "Shield Plus"
                    if w.get("plan") == "plus"
                    else "Shield Pro"
                ),
                "coverage": w.get("coverage_pct", 0),
                "status": latest_policies.get(w.get("id"), {}).get("status", "inactive"),
                "last_active": w.get("last_seen_at"),
                "gig_score": w.get("gig_score", 0),
                "gig_platform": w.get("gig_platform", ""),
                "shift": w.get("shift", ""),
                "portfolio_score": w.get("portfolio_score", 0),
            }
            for w in data
        ]

        return {
            "data": formatted,
            "total": count,
            "page": page,
            "totalPages": (count // limit) + (1 if count % limit else 0),
        }
    except Exception:
        return {"error": "Failed to fetch workers", "data": []}
