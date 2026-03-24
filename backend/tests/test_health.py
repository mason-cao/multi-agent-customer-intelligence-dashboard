"""Smoke test for the health endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_returns_healthy(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["version"] == "0.1.0"
