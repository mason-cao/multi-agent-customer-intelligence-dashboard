"""Standardized error handling for API route endpoints."""

import functools

import structlog
from fastapi import HTTPException

logger = structlog.get_logger(__name__)


def handle_errors(endpoint_name: str):
    """Wrap a route handler with standardized error logging and 500 responses.

    HTTPExceptions pass through unchanged. All other exceptions are logged
    with structlog and converted to a 500 with a generic detail message.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception:
                logger.exception(f"{endpoint_name}_failed")
                raise HTTPException(
                    status_code=500, detail="Internal server error"
                )

        return wrapper

    return decorator
