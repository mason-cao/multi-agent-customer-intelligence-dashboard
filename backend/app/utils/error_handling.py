"""Standardized error handling for API route endpoints."""

import functools
import inspect

import structlog
from fastapi import HTTPException

logger = structlog.get_logger(__name__)

DATA_VOLUME_FULL_DETAIL = (
    "The data volume is full. Free storage or increase the Railway "
    "volume size, then try again."
)


def is_storage_full_error(exc: BaseException) -> bool:
    """Return whether an exception chain indicates exhausted storage."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current and id(current) not in seen:
        seen.add(id(current))
        message = str(current).lower()
        if (
            "database or disk is full" in message
            or "no space left on device" in message
        ):
            return True
        current = (
            getattr(current, "orig", None)
            or getattr(current, "__cause__", None)
            or getattr(current, "__context__", None)
        )
    return False


def handle_errors(endpoint_name: str):
    """Wrap a route handler with standardized error logging and 500 responses.

    HTTPExceptions pass through unchanged. All other exceptions are logged
    with structlog and converted to a 500 with a generic detail message.
    """

    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except HTTPException:
                    raise
                except Exception as exc:
                    logger.exception(f"{endpoint_name}_failed")
                    if is_storage_full_error(exc):
                        raise HTTPException(
                            status_code=507,
                            detail=DATA_VOLUME_FULL_DETAIL,
                        )
                    raise HTTPException(
                        status_code=500, detail="Internal server error"
                    )

            return async_wrapper

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as exc:
                logger.exception(f"{endpoint_name}_failed")
                if is_storage_full_error(exc):
                    raise HTTPException(
                        status_code=507,
                        detail=DATA_VOLUME_FULL_DETAIL,
                    )
                raise HTTPException(
                    status_code=500, detail="Internal server error"
                )

        return wrapper

    return decorator
