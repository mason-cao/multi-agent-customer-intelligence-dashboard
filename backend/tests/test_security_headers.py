"""Tests for HTTP security headers."""

import pytest


@pytest.mark.asyncio
async def test_security_headers_are_applied_to_api_responses(client):
    resp = await client.get("/api/health")

    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert resp.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
    assert resp.headers["strict-transport-security"].startswith("max-age=31536000")
