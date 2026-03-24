"""
utils/db.py — Supabase Database Client
──────────────────────────────────────
Provides a singleton Supabase client used across all API routes.

Usage:
    from utils.db import get_supabase
    sb = get_supabase()
    result = await sb.table("workers").select("*").execute()

The client uses the SERVICE_ROLE_KEY for backend operations
(bypasses row-level-security for server-side writes).
"""

from supabase import create_client, Client
from config.settings import settings
import logging

logger = logging.getLogger("gigkavach.db")

# Module-level singleton — initialised once at startup
_supabase_client: Client | None = None


def get_supabase() -> Client:
    """
    Returns the singleton Supabase client.
    Uses the service role key so backend operations can bypass RLS.
    NOTE: Never expose the service role key to the frontend.
    """
    global _supabase_client

    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            logger.warning(
                "Supabase credentials not set in .env — "
                "DB operations will fail. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
            )
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY  # Service role for server-side ops
        )
        logger.info("Supabase client initialised")

    return _supabase_client
