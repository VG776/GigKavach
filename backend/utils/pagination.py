"""
utils/pagination.py — Standardized Pagination Utilities
────────────────────────────────────────────────────────
Provides reusable pagination helpers for list endpoints.

Usage:
    from utils.pagination import PaginationParams, paginate_query
    
    @router.get("/items")
    async def list_items(params: PaginationParams = Depends()):
        query = sb.table("items").select("*")
        paginated = paginate_query(query, params)
        result = paginated.execute()
        return {
            "items": result.data,
            "total": result.count,
            "page": params.page,
            "limit": params.limit
        }
"""

from pydantic import BaseModel, Field
from typing import Optional
import logging

logger = logging.getLogger("gigkavach.pagination")


class PaginationParams(BaseModel):
    """Standardized pagination parameters"""
    
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(20, ge=1, le=100, description="Items per page (1-100)")
    sort_by: Optional[str] = Field(None, description="Column to sort by")
    sort_order: str = Field("desc", regex="^(asc|desc)$", description="Sort order")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query"""
        return (self.page - 1) * self.limit
    
    @property
    def range_end(self) -> int:
        """Calculate end index for range query (Supabase uses inclusive ranges)"""
        return self.offset + self.limit - 1


def paginate_query(query, params: PaginationParams):
    """
    Apply pagination to a Supabase query.
    
    Args:
        query: Supabase query object
        params: PaginationParams instance
    
    Returns:
        Query object with pagination applied
    """
    # Apply sorting if specified
    if params.sort_by:
        query = query.order(
            params.sort_by,
            desc=(params.sort_order == "desc")
        )
    
    # Apply pagination range
    query = query.range(params.offset, params.range_end)
    
    return query


def format_paginated_response(
    items: list,
    total_count: int,
    params: PaginationParams,
    message: str = "Success"
) -> dict:
    """
    Format a consistent paginated response.
    
    Args:
        items: List of items
        total_count: Total count in database
        params: PaginationParams used in query
        message: Success message
    
    Returns:
        Standardized response dict
    """
    total_pages = (total_count + params.limit - 1) // params.limit  # Ceil division
    has_next = params.page < total_pages
    has_prev = params.page > 1
    
    return {
        "status": "success",
        "message": message,
        "data": items,
        "pagination": {
            "page": params.page,
            "limit": params.limit,
            "total": total_count,
            "pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
    }
