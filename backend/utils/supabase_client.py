"""
utils/supabase_client.py — Supabase Database Client
──────────────────────────────────────
Provides a singleton Supabase client used across all API routes.

Usage:
    from utils.supabase_client import get_supabase
    sb = get_supabase()
    result = await sb.table("workers").select("*").execute()

The client uses the SERVICE_ROLE_KEY for backend operations
(bypasses row-level-security for server-side writes).

IMPORTANT: This module validates credentials on initialization.
If credentials are missing, it raises an exception immediately
rather than silently creating a broken client.
"""

from supabase import create_client, Client
from config.settings import settings
from utils.error_response import ConfigurationError
import logging

logger = logging.getLogger("gigkavach.supabase_client")

# Module-level singleton — initialised once at startup
_supabase_client: Client | None = None
_initialization_error: Exception | None = None


def _validate_credentials() -> tuple[str, str]:
    """
    Validate that Supabase credentials are present and non-empty.
    Raises ConfigurationError if validation fails.
    
    Returns:
        Tuple of (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    """
    missing_vars = []
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_URL.strip():
        missing_vars.append("SUPABASE_URL")
    
    if not settings.SUPABASE_SERVICE_ROLE_KEY or not settings.SUPABASE_SERVICE_ROLE_KEY.strip():
        missing_vars.append("SUPABASE_SERVICE_ROLE_KEY")
    
    if missing_vars:
        raise ConfigurationError(
            message="Cannot initialize Supabase client: missing required credentials",
            missing_vars=missing_vars
        )
    
    return settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY


def get_supabase() -> Client:
    """
    Returns the singleton Supabase client.
    Uses the service role key so backend operations can bypass RLS.
    
    NOTE: This function validates credentials on first call.
    If validation fails, it raises ConfigurationError (500) immediately.
    
    Raises:
        ConfigurationError: If credentials are missing or invalid
    
    Returns:
        Initialized Supabase client
    """
    global _supabase_client, _initialization_error

    # If we already tried and failed, raise the cached error
    if _initialization_error:
        raise _initialization_error

    # If we already succeeded, return cached client
    if _supabase_client is not None:
        return _supabase_client

    try:
        # Validate credentials before creating client
        url, key = _validate_credentials()
        
        # Create the client
        _supabase_client = create_client(url, key)
        
        logger.info("✅ Supabase client initialized successfully")
        logger.debug(f"   URL: {url[:30]}...")
        
        return _supabase_client
        
    except ConfigurationError as e:
        _initialization_error = e
        logger.error(f"❌ Failed to initialize Supabase client: {e.message}")
        raise
    except Exception as e:
        error = ConfigurationError(
            message=f"Unexpected error initializing Supabase: {str(e)}"
        )
        _initialization_error = error
        logger.error(f"❌ {error.message}")
        raise error
