"""
CSRF/Origin Protection Middleware for API endpoints.

Since this API uses JWT tokens in Authorization headers (not cookies),
traditional CSRF tokens are not necessary. However, we implement Origin
validation to protect against unauthorized cross-origin requests for
state-changing operations.
"""

import logging
from typing import List

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class OriginValidationMiddleware(BaseHTTPMiddleware):
    """
    Validates Origin/Referer headers for state-changing requests.

    This protects against:
    - Unauthorized cross-origin requests
    - Potential CSRF-like attacks if cookies are ever used
    - Malicious requests from untrusted origins
    """

    def __init__(self, app, allowed_origins: List[str], strict_mode: bool = True):
        super().__init__(app)
        self.allowed_origins = set(allowed_origins)
        self.strict_mode = strict_mode

        # Methods that modify state and need origin validation
        self.protected_methods = {"POST", "PUT", "DELETE", "PATCH"}

        # Paths that should skip origin validation (e.g., webhooks from external services)
        self.exempt_paths = {
            "/webhook",
            "/api/v1/whatsapp/webhook",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/widget/",  # Public widget endpoints called from third-party websites
        }

    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is in allowed list."""
        if not origin:
            return False

        # Remove trailing slash for comparison
        origin = origin.rstrip("/")

        return origin in self.allowed_origins

    def _extract_origin(self, request: Request) -> str:
        """Extract origin from Origin or Referer header."""
        # Try Origin header first (more reliable)
        origin = request.headers.get("origin")
        if origin:
            return origin.rstrip("/")

        # Fallback to Referer header
        referer = request.headers.get("referer")
        if referer:
            # Extract origin from referer URL
            from urllib.parse import urlparse

            parsed = urlparse(referer)
            return f"{parsed.scheme}://{parsed.netloc}"

        return ""

    async def dispatch(self, request: Request, call_next):
        """Validate origin for state-changing requests."""

        # Skip validation for safe methods (GET, HEAD, OPTIONS)
        if request.method not in self.protected_methods:
            return await call_next(request)

        # Skip validation for exempt paths (e.g., webhooks)
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            logger.debug(f"Skipping origin validation for exempt path: {path}")
            return await call_next(request)

        # Extract origin from request
        origin = self._extract_origin(request)

        # In strict mode, reject requests without Origin/Referer
        if not origin:
            if self.strict_mode:
                logger.warning(
                    f"Blocked {request.method} request to {path} - No Origin or Referer header"
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Origin header required for this operation"},
                )
            else:
                # In non-strict mode, log and allow
                logger.warning(
                    f"Allowed {request.method} request to {path} without origin (strict_mode=False)"
                )
                return await call_next(request)

        # Validate origin is in allowed list
        if not self._is_origin_allowed(origin):
            logger.warning(
                f"Blocked {request.method} request to {path} from unauthorized origin: {origin}"
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": f"Origin not allowed: {origin}"},
            )

        # Origin is valid, proceed with request
        logger.debug(f"Origin validated: {origin} for {request.method} {path}")
        return await call_next(request)
