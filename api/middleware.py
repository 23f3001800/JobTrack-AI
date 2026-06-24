"""API Middleware — request logging, error handling, and timing.

WHY middleware instead of try/except in every route?
1. DRY — catches ALL errors in one place, not per-route
2. Request logging gives us observability without LangSmith
3. Timing data helps identify slow endpoints
4. Structured error responses are consistent across the API

This follows the FastAPI middleware pattern:
request → logging middleware → error middleware → route handler → response
"""
import time
import logging
import traceback
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Configure structured logging
# WHY structured logging? JSON logs are parseable by log aggregators
# (Datadog, CloudWatch, etc.) for production monitoring.
logger = logging.getLogger("autoapply")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and duration.

    WHY log every request?
    In production, this is how you debug issues:
    "User X hit /run at 14:32 and got a 500" — without this,
    you're debugging blind.

    Example log output:
    2024-01-15 14:32:01 | INFO | req_abc123 POST /run → 200 (1.23s)
    """

    async def dispatch(self, request: Request, call_next):
        # Generate a unique request ID for tracing
        request_id = str(uuid4())[:8]
        request.state.request_id = request_id

        method = request.method
        path = request.url.path
        start = time.time()

        # Log the incoming request
        logger.info(f"{request_id} → {method} {path}")

        response = await call_next(request)

        # Log the completed request with timing
        duration = round(time.time() - start, 3)
        status = response.status_code
        level = "WARNING" if status >= 400 else "INFO"
        getattr(logger, level.lower())(
            f"{request_id} ← {method} {path} → {status} ({duration}s)"
        )

        # Add request ID header for client-side debugging
        response.headers["X-Request-ID"] = request_id
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return structured JSON errors.

    WHY structured error responses?
    Without this, FastAPI returns HTML error pages for 500s,
    which the frontend can't parse. The dashboard needs JSON
    responses to show user-friendly error messages.

    Response format:
    {
        "error": "Internal server error",
        "detail": "Division by zero in tools/scraper.py:42",
        "request_id": "abc12345"
    }
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            # Get request ID if available
            request_id = getattr(request.state, "request_id", "unknown")

            # Log the full traceback for debugging
            logger.error(
                f"{request_id} UNHANDLED ERROR: {type(exc).__name__}: {exc}\n"
                f"{traceback.format_exc()}"
            )

            # Return a structured JSON error (no stack traces to clients!)
            # WHY hide the stack trace? Security — stack traces can
            # reveal file paths, dependency versions, and internal logic.
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": str(exc),
                    "request_id": request_id,
                },
            )
