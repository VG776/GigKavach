"""
utils/cache.py — In-Memory Cache (No Redis)
────────────────────────────────────────────
Replaces Upstash Redis with a simple Python dict for the hackathon.
Stores DCI scores and payout dedup locks in process memory.

⚠️  This is intentionally simple — good enough for a single-server hackathon demo.
    In production we'd swap this back to Redis for multi-instance deployments.

Usage:
    from utils.cache import set_dci_cache, get_dci_cache, acquire_payout_lock
"""

import time
import json
import logging
from typing import Optional

logger = logging.getLogger("gigkavach.cache")

# ─── In-Memory Store ─────────────────────────────────────────────────────────
# Structure: { key: {"value": ..., "expires_at": float | None} }
_store: dict[str, dict] = {}

# DCI cache TTL (seconds) — same as the Redis TTL we had before
DCI_CACHE_TTL_SECONDS = 1800   # 30 minutes


# ─── Core Get / Set / Delete ─────────────────────────────────────────────────

def _set(key: str, value: str, ttl_seconds: int | None = None) -> None:
    """Internal: store a value with optional expiry"""
    expires_at = time.time() + ttl_seconds if ttl_seconds else None
    _store[key] = {"value": value, "expires_at": expires_at}


def _get(key: str) -> str | None:
    """Internal: retrieve a value, returning None if missing or expired"""
    entry = _store.get(key)
    if entry is None:
        return None
    if entry["expires_at"] and time.time() > entry["expires_at"]:
        del _store[key]   # lazy expiry — clean up on access
        return None
    return entry["value"]


def _delete(key: str) -> None:
    """Internal: remove a key"""
    _store.pop(key, None)


def _set_nx(key: str, value: str, ttl_seconds: int | None = None) -> bool:
    """Internal: SET if Not eXists — atomic in single-threaded Python. Returns True if set."""
    if _get(key) is not None:
        return False
    _set(key, value, ttl_seconds)
    return True


# ─── DCI Score Cache ──────────────────────────────────────────────────────────

def _dci_key(pin_code: str) -> str:
    return f"dci:score:{pin_code}"


def set_dci_cache(pin_code: str, dci_data: dict, ttl_seconds: int = DCI_CACHE_TTL_SECONDS) -> None:
    """
    Stores a DCI result for a zone. TTL = 30 min.
    After TTL expires, DCI engine must recompute or trigger SLA breach.
    """
    _set(_dci_key(pin_code), json.dumps(dci_data), ttl_seconds)
    logger.debug(f"DCI cached for pin {pin_code} | TTL {ttl_seconds}s")


def get_dci_cache(pin_code: str) -> Optional[dict]:
    """
    Returns cached DCI data for a zone, or None if expired / not set.
    None signals the DCI engine to fall back to Layer 3 → Layer 4.
    """
    raw = _get(_dci_key(pin_code))
    if raw is None:
        logger.debug(f"DCI cache miss for pin {pin_code}")
        return None
    return json.loads(raw)


# ─── Payout Deduplication Lock ───────────────────────────────────────────────

def _lock_key(worker_id: str, dci_event_id: str) -> str:
    return f"payout:lock:{worker_id}:{dci_event_id}"


def acquire_payout_lock(worker_id: str, dci_event_id: str, ttl_seconds: int = 86400) -> bool:
    """
    Tries to acquire a payout lock for this worker + DCI event.
    Returns True if acquired (first call), False if already locked.
    Prevents double payouts if the pipeline fires twice for one event.
    TTL = 24 hours (auto-expires after the day ends).
    """
    acquired = _set_nx(_lock_key(worker_id, dci_event_id), "locked", ttl_seconds)
    if acquired:
        logger.info(f"Payout lock acquired: worker={worker_id} event={dci_event_id}")
    else:
        logger.warning(f"Payout lock exists — preventing duplicate: worker={worker_id} event={dci_event_id}")
    return acquired


def release_payout_lock(worker_id: str, dci_event_id: str) -> None:
    """Release a payout lock (used when a payout fails and must be retried)."""
    _delete(_lock_key(worker_id, dci_event_id))
    logger.info(f"Payout lock released: worker={worker_id} event={dci_event_id}")


# ─── API Health Tracking ──────────────────────────────────────────────────────

def record_api_failure(api_name: str) -> None:
    """Mark when an API first went down. Used for SLA breach detection."""
    key = f"api:failure_start:{api_name}"
    _set_nx(key, str(time.time()), DCI_CACHE_TTL_SECONDS * 2)


def record_api_success(api_name: str) -> None:
    """Clear failure record when an API recovers."""
    _delete(f"api:failure_start:{api_name}")
