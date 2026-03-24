"""Smoke tests for scenario resolution."""

import pytest

EXPECTED_KEYS = {"velocity_saas", "atlas_enterprise", "beacon_analytics", "meridian_data"}
REQUIRED_FIELDS = {"key", "company_name", "industry", "customer_count", "description", "churn_rate", "profile"}


@pytest.mark.asyncio
async def test_scenarios_returns_list(client):
    resp = await client.get("/api/workspaces/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 4


@pytest.mark.asyncio
async def test_scenario_keys_match(client):
    resp = await client.get("/api/workspaces/scenarios")
    keys = {s["key"] for s in resp.json()}
    assert keys == EXPECTED_KEYS


@pytest.mark.asyncio
async def test_scenario_fields_present(client):
    resp = await client.get("/api/workspaces/scenarios")
    for scenario in resp.json():
        assert REQUIRED_FIELDS.issubset(scenario.keys()), f"Missing fields in {scenario['key']}"
