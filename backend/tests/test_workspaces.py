"""Smoke tests for workspace CRUD lifecycle."""

import pytest


@pytest.mark.asyncio
async def test_list_workspaces_empty(client):
    resp = await client.get("/api/workspaces")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["workspaces"] == []


@pytest.mark.asyncio
async def test_create_workspace(client):
    resp = await client.post("/api/workspaces", json={
        "name": "Test WS",
        "scenario": "velocity_saas",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Test WS"
    assert body["company_name"] == "Velocity SaaS"
    assert body["status"] == "created"
    assert body["industry"] == "Technology"
    assert body["customer_count"] == 1000
    assert "id" in body


@pytest.mark.asyncio
async def test_get_workspace_by_id(client):
    create = await client.post("/api/workspaces", json={
        "name": "Fetch Test",
        "scenario": "atlas_enterprise",
    })
    ws_id = create.json()["id"]

    resp = await client.get(f"/api/workspaces/{ws_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Fetch Test"
    assert resp.json()["company_name"] == "Atlas Enterprise"


@pytest.mark.asyncio
async def test_get_workspace_not_found(client):
    resp = await client.get("/api/workspaces/nonexistent123")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_workspace(client):
    create = await client.post("/api/workspaces", json={
        "name": "Delete Me",
        "scenario": "meridian_data",
    })
    ws_id = create.json()["id"]

    resp = await client.delete(f"/api/workspaces/{ws_id}")
    assert resp.status_code == 204

    check = await client.get(f"/api/workspaces/{ws_id}")
    assert check.status_code == 404


@pytest.mark.asyncio
async def test_create_workspace_random_scenario(client):
    resp = await client.post("/api/workspaces", json={
        "name": "Random Test",
        "scenario": "random",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["company_name"] != "Random Test"
    assert body["customer_count"] >= 100
    assert len(body["industry"]) > 0
