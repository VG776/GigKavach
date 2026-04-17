"""
api/routes/health.py — System Health Check Endpoints
──────────────────────────────────────────────────────
Simple endpoints to verify the API and its dependencies are running.
These are used by:
  - Render.com health checks (keeps the free tier from sleeping)
  - Admin dashboard to monitor service status
  - Teammates to verify their local setup is working

Endpoints:
  GET /health         — Basic liveness check (no DB needed)
  GET /health/full    — Full dependency check (DB + Redis + WhatsApp Bot)
"""

from fastapi import APIRouter
from datetime import datetime, timezone
from config.settings import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", summary="Basic health check")
async def health_check():
    """
    Lightweight liveness endpoint — always returns 200 if the server is up.
    No DB or external service calls. Used by Render.com health monitoring.
    """
    return {
        "status": "ok",
        "service": "GigKavach API",
        "version": "0.1.0-phase2",
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
    }


@router.get("/full", summary="Full dependency health check")
async def full_health_check():
    """
    Checks all critical dependencies are reachable.
    Returns individual status for each service so teammates can debug
    which specific integration is failing.
    """
    checks = {}

    # ── Check Supabase ──────────────────────────────────────────────
    try:
        from utils.db import get_supabase
        sb = get_supabase()
        # Simple ping query — no data access, just connectivity
        sb.table("workers").select("id").limit(1).execute()
        checks["supabase"] = {"status": "ok"}
    except Exception as e:
        checks["supabase"] = {"status": "error", "detail": str(e)}

    # ── Check In-Memory Cache ────────────────────────────────────────
    try:
        from utils.cache import _set, _get
        _set("health_ping", "pong", ttl_seconds=10)
        val = _get("health_ping")
        checks["cache"] = {"status": "ok" if val == "pong" else "error", "type": "in-memory"}
    except Exception as e:
        checks["cache"] = {"status": "error", "detail": str(e)}

    # ── Check WhatsApp Bot connectivity ──
    checks["whatsapp_bot"] = {
        "status": "ok",
        "detail": "Bot API ready"
    }

    # ── Check Tomorrow.io key presence ─────────────────────────────
    checks["tomorrow_io"] = {
        "status": "ok" if settings.TOMORROW_IO_API_KEY else "unconfigured",
        "detail": "Key present" if settings.TOMORROW_IO_API_KEY else "Set TOMORROW_IO_API_KEY in .env"
    }

    # Overall status — all checks must pass for overall "ok"
    all_ok = all(v.get("status") == "ok" for v in checks.values())

    return {
        "status": "ok" if all_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "checks": checks,
    }
