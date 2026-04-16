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


@pytest.mark.asyncio
async def test_regeneration_clears_stale_completion_state(client):
    create = await client.post("/api/workspaces", json={
        "name": "Regenerate Test",
        "scenario": "velocity_saas",
    })
    ws_id = create.json()["id"]

    from app.services.workspace_manager import get_workspace, update_workspace_status

    update_workspace_status(ws_id, "ready", error_message="old failure")
    ready = get_workspace(ws_id)
    assert ready.completed_at is not None
    assert ready.error_message is None

    update_workspace_status(ws_id, "generating", error_message="")
    generating = get_workspace(ws_id)
    assert generating.completed_at is None
    assert generating.error_message == ""
    assert generating.generation_started_at is not None


@pytest.mark.asyncio
async def test_dashboard_routes_reject_invalid_workspace_header(client):
    resp = await client.get(
        "/api/overview/kpis",
        headers={"X-Workspace-ID": "../../nexus"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid workspace ID"


@pytest.mark.asyncio
async def test_dashboard_routes_404_for_missing_workspace_database(client):
    resp = await client.get(
        "/api/overview/kpis",
        headers={"X-Workspace-ID": "abcdef123456"},
    )
    assert resp.status_code == 404
