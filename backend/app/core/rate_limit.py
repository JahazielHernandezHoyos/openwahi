"""
Rate limiting configuration for API endpoints.

Protects against:
- DDoS attacks
- Brute force attacks on authentication
- API abuse
- Excessive webhook calls
"""

import logging

from fastapi import HTTPException, Request, status
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def get_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting.

    Uses multiple strategies:
    1. User ID from JWT token (if authenticated)
    2. API key (if provided)
    3. IP address (fallback)
    """
    # Try to get user ID from request state (set by auth middleware)
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"

    # Try to get API key
    api_key = request.headers.get("x-api-key")
    if api_key:
        # Use first 16 chars of API key for identification
        return f"apikey:{api_key[:16]}"

    # Fallback to IP address
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Get first IP in chain (client IP)
        return f"ip:{forwarded.split(',')[0].strip()}"

    # Direct connection IP
    client = request.client
    if client:
        return f"ip:{client.host}"

    return "unknown"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    """
    logger.warning(
        f"Rate limit exceeded for {get_identifier(request)} "
        f"on {request.method} {request.url.path}"
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded. Please try again later.",
        headers={
            "Retry-After": str(exc.detail.split("Retry after ")[1] if "Retry after" in exc.detail else "60")
        }
    )


# Initialize limiter with custom identifier function
limiter = Limiter(
    key_func=get_identifier,
    default_limits=["1000/hour"],  # Default limit for all endpoints
    storage_uri="memory://",  # Use in-memory storage (consider Redis for production)
    strategy="fixed-window",  # fixed-window, moving-window, or fixed-window-elastic-expiry
)


# Common rate limit configurations
class RateLimits:
    """Predefined rate limit configurations for different endpoint types."""

    # Authentication endpoints - protect against brute force
    AUTH = "10/minute"  # 10 requests per minute
    AUTH_STRICT = "5/minute"  # For login/password reset

    # Public endpoints - moderate limits
    PUBLIC = "100/minute"  # General public endpoints

    # Webhook endpoints - higher limits but still protected
    WEBHOOK = "1000/minute"  # Webhooks from external services

    # Authenticated API endpoints - higher limits
    AUTHENTICATED = "500/minute"  # For authenticated users

    # Heavy operations - strict limits
    FILE_UPLOAD = "20/minute"  # File upload operations
    AI_OPERATIONS = "50/minute"  # AI/LLM operations (expensive)

    # Developer API - moderate limits
    DEVELOPER_API = "100/minute"  # API key based access
