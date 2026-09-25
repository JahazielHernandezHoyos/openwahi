import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class ServerTimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds Server-Timing headers to the response.
    This helps in debugging performance issues by exposing timings to the browser's DevTools.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        
        # Attach start time to request state for granularity if needed later
        request.state.start_time = start_time
        
        response = await call_next(request)
        
        process_time = time.perf_counter() - start_time
        ms = process_time * 1000
        
        # Format: metric_name;dur=duration_in_ms
        timing_header = f"app;dur={ms:.2f}"
        
        # Existing headers might have other timings (though unlikely in this setup currently)
        if "Server-Timing" in response.headers:
            response.headers["Server-Timing"] += f", {timing_header}"
        else:
            response.headers["Server-Timing"] = timing_header
            
        # Log slow requests
        if ms > 500:
            logger.warning(
                f"Slow Request Detected: {request.method} {request.url.path} "
                f"took {ms:.2f}ms"
            )
            
        return response
