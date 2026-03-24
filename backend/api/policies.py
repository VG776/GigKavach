"""
api/routes/policies.py — Policy Management Endpoints
──────────────────────────────────────────────────────
Sumukh's endpoints:
  GET  /api/v1/policy/{policy_id}  — Fetch policy details
  PATCH /api/v1/policy/{policy_id} — Update tier, shift, pin_codes

Business Rules:
  ─────────────
  Plan (tier) changes:
    Worker upgrades Basic → Pro mid-week.
    Current week: still covered at Basic rate (40%)
    Next Monday onwards: covered at Pro rate (70%)
    → We set `next_plan` on the policy row; a weekly cron job (Varshit's DCI
      scheduler) activates it on Monday by swapping `plan ← next_plan`.

  Shift changes:
    Effective immediately — DCI eligibility window updates right away.
    A night-shift worker who switches to day shift mid-week is covered
    only during their new shift from that moment forward.

  Pin code changes:
    Effective immediately — new zones are added to the worker's DCI trigger
    eligibility. Old zones continue to be tracked (no mid-week gaps).

Error handling:
  404 — policy_id not found in `policies` table
  422 — invalid field values (Pydantic catches these before the handler)
  503 — Supabase unavailable
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime, date, timedelta
import logging

from models.worker import PolicyResponse, PolicyUpdate, ShiftType, PlanType
from utils.db import get_supabase

logger = logging.getLogger("gigkavach.policies")

router = APIRouter(prefix="/api/v1", tags=["Policies"])


# ─── Helper: Next Monday ──────────────────────────────────────────────────────

def next_monday_date() -> date:
    """
    Returns the date of the next Monday.
    Tier changes always take effect on the Monday following the request.
    If today IS Monday, the change still applies to the NEXT Monday
    (current week coverage is protected).
    """
    today = datetime.utcnow().date()
    days_until_monday = (7 - today.weekday()) % 7
    # If today is Monday (weekday=0), days_until_monday=0 → we want next Monday (+7)
    if days_until_monday == 0:
        days_until_monday = 7
    return today + timedelta(days=days_until_monday)


# ─── Helper: Fetch policy or 404 ─────────────────────────────────────────────

def _get_policy_or_404(policy_id: str) -> dict:
    """
    Fetches a policy from Supabase by ID.
    Raises 404 if not found, 503 if DB is unreachable.
    """
    sb = get_supabase()
    try:
        result = (
            sb.table("policies")
            .select("*")
            .eq("id", policy_id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.error(f"Supabase error fetching policy {policy_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please try again shortly."
        )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": f"Policy '{policy_id}' not found.",
                "hint": "Check the policy_id from the registration response, or list policies via GET /api/v1/workers/{worker_id}/policies",
            }
        )

    return result.data[0]


# ─── Helper: Map DB row → PolicyResponse ─────────────────────────────────────

def _policy_row_to_response(row: dict, tier_change_effective: date | None = None) -> PolicyResponse:
    """
    Converts a raw Supabase row dict to a typed PolicyResponse.
    pin_codes may be stored as a Postgres array or a comma-separated string
    depending on Supabase client version — we handle both.
    """
    # pin_codes may come back as a list or a string like '{560047,560034}'
    pin_codes = row.get("pin_codes", [])
    if isinstance(pin_codes, str):
        pin_codes = pin_codes.strip("{}").split(",")

    return PolicyResponse(
        id=row["id"],
        worker_id=row["worker_id"],
        plan=PlanType(row["plan"]),
        shift=ShiftType(row["shift"]),
        pin_codes=pin_codes,
        week_start=datetime.fromisoformat(row["week_start"]),
        week_end=datetime.fromisoformat(row["week_end"]),
        premium_paid=float(row.get("premium_paid", 0.0)),
        is_active=bool(row.get("is_active", True)),
        created_at=datetime.fromisoformat(row["created_at"]),
        tier_change_effective=tier_change_effective,
    )


# ─── GET /api/v1/policy/{policy_id} ──────────────────────────────────────────

@router.get(
    "/policy/{policy_id}",
    response_model=PolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch policy details by ID",
    responses={
        200: {"description": "Policy found"},
        404: {"description": "Policy ID not found"},
        503: {"description": "Database unavailable"},
    },
)
async def get_policy(policy_id: str) -> PolicyResponse:
    """
    Retrieves full policy details for a given policy_id.

    Used by:
      - Frontend dashboard (V Saatwik) to display active coverage details
      - WhatsApp STATUS command handler (Sumukh) to show worker their plan
      - Payout engine (Varshit) to confirm coverage before processing payout
    """
    row = _get_policy_or_404(policy_id)
    logger.info(f"Policy fetch: id={policy_id} worker={row.get('worker_id')}")
    return _policy_row_to_response(row)


# ─── PATCH /api/v1/policy/{policy_id} ────────────────────────────────────────

@router.patch(
    "/policy/{policy_id}",
    response_model=PolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update policy tier, shift, or delivery zones",
    responses={
        200: {"description": "Policy updated — see tier_change_effective if plan was changed"},
        400: {"description": "Nothing to update — no fields provided"},
        404: {"description": "Policy ID not found"},
        422: {"description": "Invalid field values"},
        503: {"description": "Database unavailable"},
    },
)
async def update_policy(policy_id: str, update_data: PolicyUpdate) -> PolicyResponse:
    """
    Updates allowed policy fields with business-rule enforcement.

    Business rules applied here:
      - plan change  → queued for next Monday (tier_change_effective set in response)
      - shift change → effective immediately (DB updated now)
      - pin_codes    → effective immediately (DB updated now)

    The response always returns the CURRENT state of the policy.
    If a tier change was queued, `tier_change_effective` tells the caller
    the date from which the new plan applies.

    How tier-change queuing works:
      We write `next_plan` to the policy row.
      Varshit's DCI cron scheduler calls `activate_pending_tier_changes()` every
      Monday at 00:01 UTC, which swaps `plan ← next_plan` for all policies
      where `next_plan IS NOT NULL`.
    """
    sb = get_supabase()

    # ── Guard: ensure at least one field is being updated ────────────────────
    if update_data.plan is None and update_data.shift is None and update_data.pin_codes is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided. Send at least one of: plan, shift, pin_codes."
        )

    # ── Fetch current policy (raises 404/503 automatically) ──────────────────
    row = _get_policy_or_404(policy_id)

    # ── Build the Supabase update payload ────────────────────────────────────
    updates: dict = {}
    tier_change_effective: date | None = None

    # ── Tier change: queue for next Monday, don't apply now ──────────────────
    if update_data.plan is not None:
        if update_data.plan.value == row["plan"]:
            # Requesting the same tier they already have — no-op for plan
            logger.info(f"Policy {policy_id}: plan unchanged ({row['plan']}) — no tier update queued")
        else:
            effective = next_monday_date()
            updates["next_plan"] = update_data.plan.value
            tier_change_effective = effective
            logger.info(
                f"Policy {policy_id}: tier change queued "
                f"{row['plan']} → {update_data.plan.value} effective {effective}"
            )

    # ── Shift change: immediate ───────────────────────────────────────────────
    if update_data.shift is not None:
        updates["shift"] = update_data.shift.value
        logger.info(f"Policy {policy_id}: shift updated to {update_data.shift.value}")

    # ── Pin codes change: immediate ───────────────────────────────────────────
    if update_data.pin_codes is not None:
        updates["pin_codes"] = update_data.pin_codes
        logger.info(f"Policy {policy_id}: pin codes updated to {update_data.pin_codes}")

    # ── If nothing actually changed (e.g. same plan), skip DB write ──────────
    if not updates:
        logger.info(f"Policy {policy_id}: no effective changes to apply")
        return _policy_row_to_response(row)

    # ── Apply updates to Supabase ─────────────────────────────────────────────
    try:
        updated = (
            sb.table("policies")
            .update(updates)
            .eq("id", policy_id)
            .execute()
        )
        if not updated.data:
            # Supabase update returned empty — shouldn't happen after the fetch above
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Policy update failed — no rows were modified."
            )
        updated_row = updated.data[0]
        logger.info(f"Policy {policy_id} updated successfully: {list(updates.keys())}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Supabase update failed for policy {policy_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to update policy. Please try again."
        )

    return _policy_row_to_response(updated_row, tier_change_effective=tier_change_effective)
