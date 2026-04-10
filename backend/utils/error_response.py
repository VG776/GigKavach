"""
utils/error_response.py — Standardized Error Response Format
────────────────────────────────────────────────────────────
Ensures all API endpoints return consistent error responses.

Standard format:
{
    "status": "error",
    "code": "VALIDATION_ERROR" or HTTP status code,
    "message": "User-friendly error message",
    "details": {...}  # Optional: extra context
}

Usage:
    from utils.error_response import APIError, ValidationError, DatabaseError
    
    raise ValidationError("Invalid phone number", {"phone": "+91123"})
    raise DatabaseError("Worker not found")
"""

from fastapi import HTTPException, status
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger("gigkavach.errors")


class APIErrorResponse(HTTPException):
    """
    Base error class for GigKavach API.
    Automatically formats response to match standard error schema.
    """
    
    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
        log_level: str = "warning"
    ):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}
        
        # Log the error
        log_func = getattr(logger, log_level.lower(), logger.warning)
        log_func(f"[{code}] {message}", extra=self.details)
        
        # Format response
        detail = {
            "status": "error",
            "code": code,
            "message": message,
            "details": self.details if self.details else None
        }
        
        # Remove None details for cleaner JSON
        if detail["details"] is None:
            del detail["details"]
        
        super().__init__(
            status_code=http_status,
            detail=detail
        )


# ─── Specialized Error Types ──────────────────────────────────────────────────

class ValidationError(APIErrorResponse):
    """Client sent invalid data (422 Unprocessable Entity)"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            log_level="warning"
        )


class NotFoundError(APIErrorResponse):
    """Resource not found (404)"""
    def __init__(self, message: str, resource_type: str = "Resource", resource_id: str = ""):
        super().__init__(
            code="NOT_FOUND",
            message=message,
            http_status=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id} if resource_id else None,
            log_level="info"
        )


class ConflictError(APIErrorResponse):
    """Resource already exists (409 Conflict)"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            code="CONFLICT",
            message=message,
            http_status=status.HTTP_409_CONFLICT,
            details=details,
            log_level="warning"
        )


class UnauthorizedError(APIErrorResponse):
    """Authentication failed (401)"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            http_status=status.HTTP_401_UNAUTHORIZED,
            log_level="info"
        )


class ForbiddenError(APIErrorResponse):
    """Authorized but forbidden (403)"""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            http_status=status.HTTP_403_FORBIDDEN,
            log_level="info"
        )


class DatabaseError(APIErrorResponse):
    """Database operation failed (500)"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            code="DATABASE_ERROR",
            message=message,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            log_level="error"
        )


class ServiceUnavailableError(APIErrorResponse):
    """External service unavailable (503)"""
    def __init__(self, service_name: str, message: str = "Service temporarily unavailable"):
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=message,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service_name},
            log_level="error"
        )


class ConfigurationError(APIErrorResponse):
    """Configuration/environment issue (500)"""
    def __init__(self, message: str, missing_vars: Optional[list] = None):
        super().__init__(
            code="CONFIGURATION_ERROR",
            message=message,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"missing_env_vars": missing_vars} if missing_vars else None,
            log_level="error"
        )


class RateLimitError(APIErrorResponse):
    """Too many requests (429)"""
    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            log_level="info"
        )


# ─── Success Response Helper ──────────────────────────────────────────────────

class SuccessResponse:
    """Standardized success response format"""
    
    @staticmethod
    def format(data: Any = None, message: str = "Success", count: Optional[int] = None) -> Dict:
        """
        Format a successful response.
        
        Args:
            data: Response payload
            message: Success message
            count: Total count (for paginated responses)
        
        Returns:
            Formatted response dict
        """
        response = {
            "status": "success",
            "message": message,
            "data": data
        }
        
        if count is not None:
            response["count"] = count
        
        return response
