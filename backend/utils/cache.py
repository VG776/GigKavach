"""Simple in-memory TTL cache used by health checks."""

from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock

_store: dict[str, tuple[datetime, object]] = {}
_lock = Lock()


def _set(key: str, value: object, ttl_seconds: int = 60) -> None:
    expires_at = datetime.utcnow() + timedelta(seconds=max(1, ttl_seconds))
    with _lock:
        _store[key] = (expires_at, value)


def _get(key: str) -> object | None:
    with _lock:
        entry = _store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if datetime.utcnow() >= expires_at:
            _store.pop(key, None)
            return None
        return value
