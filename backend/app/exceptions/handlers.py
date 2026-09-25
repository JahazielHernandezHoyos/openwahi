import logging

import sentry_sdk
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    # Capture 5xx errors to Sentry
    if exc.status_code >= 500:
        sentry_sdk.capture_exception(exc)

    # Optionally capture 4xx client errors (useful for tracking bad requests patterns)
    elif exc.status_code >= 400:
        with sentry_sdk.push_scope() as scope:
            scope.set_level("warning")
            scope.set_tag("http.status_code", exc.status_code)
            scope.set_context(
                "request",
                {
                    "url": str(request.url),
                    "method": request.method,
                    "headers": dict(request.headers),
                },
            )
            sentry_sdk.capture_message(
                f"HTTP {exc.status_code}: {exc.detail}", level="warning"
            )

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    # Track validation errors as warnings in Sentry
    with sentry_sdk.push_scope() as scope:
        scope.set_level("warning")
        scope.set_tag("error.type", "validation")
        scope.set_context(
            "validation_errors",
            {"errors": exc.errors(), "body": str(exc.body)[:1000]},  # Truncate body
        )
        scope.set_context(
            "request",
            {
                "url": str(request.url),
                "method": request.method,
            },
        )
        sentry_sdk.capture_message("Request validation failed", level="warning")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions (500 errors)."""
    # Always capture unhandled exceptions to Sentry
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    sentry_sdk.capture_exception(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
