"""Tests for shared route error handling utilities."""

import pytest
from fastapi import HTTPException

from app.utils.error_handling import handle_errors


@pytest.mark.asyncio
async def test_handle_errors_converts_async_exceptions_to_500():
    @handle_errors("async_test")
    async def broken_handler():
        raise RuntimeError("boom")

    with pytest.raises(HTTPException) as exc_info:
        await broken_handler()

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal server error"


@pytest.mark.asyncio
async def test_handle_errors_preserves_async_http_exceptions():
    @handle_errors("async_test")
    async def not_found_handler():
        raise HTTPException(status_code=404, detail="missing")

    with pytest.raises(HTTPException) as exc_info:
        await not_found_handler()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "missing"


def test_handle_errors_converts_sync_exceptions_to_500():
    @handle_errors("sync_test")
    def broken_handler():
        raise RuntimeError("boom")

    with pytest.raises(HTTPException) as exc_info:
        broken_handler()

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal server error"
