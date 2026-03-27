"""Compatibility layer for modules importing utils.db."""

from utils.supabase_client import get_supabase

__all__ = ["get_supabase"]
