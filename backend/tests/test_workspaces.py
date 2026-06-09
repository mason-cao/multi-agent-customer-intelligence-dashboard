"""Smoke tests for workspace CRUD lifecycle."""

import pytest

from app.config import settings


ADMIN_HEADERS = {"X-Admin-Token": "test-admin-token"}


@pytest.mark.asyncio
async def test_workspace_list_requires_admin_token(client):
    resp = await client.get("/api/workspaces")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Admin token required"


@pytest.mark.asyncio
async def test_workspace_list_rejects_invalid_admin_token(client):
    resp = await client.get(
        "/api/workspaces",
        headers={"X-Admin-Token": "wrong-token"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Invalid admin token"


@pytest.mark.asyncio
async def test_create_workspace_returns_one_time_access_token(client):
    resp = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Token Test",
        "scenario": "velocity_saas",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["access_token"]) >= 43

    list_resp = await client.get("/api/workspaces", headers=ADMIN_HEADERS)
    assert list_resp.status_code == 200
    listed = list_resp.json()["workspaces"][0]
    assert "access_token" not in listed


@pytest.mark.asyncio
async def test_admin_can_rotate_workspace_access_token(client):
    create = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Rotate Token Test",
        "scenario": "velocity_saas",
    })
    ws_id = create.json()["id"]
    old_token = create.json()["access_token"]

    rotate = await client.post(
        f"/api/workspaces/{ws_id}/access-token",
        headers=ADMIN_HEADERS,
    )
    assert rotate.status_code == 200
    body = rotate.json()
    assert body["workspace_id"] == ws_id
    assert len(body["access_token"]) >= 43
    assert body["access_token"] != old_token


@pytest.mark.asyncio
async def test_dashboard_routes_require_workspace_access_token(client):
    create = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Dashboard Token Test",
        "scenario": "velocity_saas",
    })
    ws_id = create.json()["id"]
    token = create.json()["access_token"]

    missing = await client.get(
        "/api/overview/kpis",
        headers={"X-Workspace-ID": ws_id},
    )
    assert missing.status_code == 401
    assert missing.json()["detail"] == "Workspace token required"

    invalid = await client.get(
        "/api/overview/kpis",
        headers={"X-Workspace-ID": ws_id, "X-Workspace-Token": "wrong-token"},
    )
    assert invalid.status_code == 403
    assert invalid.json()["detail"] == "Invalid workspace token"

    authorized = await client.get(
        "/api/overview/kpis",
        headers={"X-Workspace-ID": ws_id, "X-Workspace-Token": token},
    )
    assert authorized.status_code == 404
    assert authorized.json()["detail"] == f"Workspace database not found: {ws_id}"


@pytest.mark.asyncio
async def test_list_workspaces_empty(client):
    resp = await client.get("/api/workspaces", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["workspaces"] == []


@pytest.mark.asyncio
async def test_create_workspace(client):
    resp = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
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
async def test_create_workspace_enforces_workspace_quota(client, monkeypatch):
    monkeypatch.setattr(settings, "max_workspaces", 1, raising=False)

    first = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Quota One",
        "scenario": "velocity_saas",
    })
    assert first.status_code == 201

    second = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Quota Two",
        "scenario": "velocity_saas",
    })
    assert second.status_code == 409
    assert second.json()["detail"] == "Workspace limit reached."


@pytest.mark.asyncio
async def test_get_workspace_by_id(client):
    create = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Fetch Test",
        "scenario": "atlas_enterprise",
    })
    ws_id = create.json()["id"]

    resp = await client.get(f"/api/workspaces/{ws_id}", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Fetch Test"
    assert resp.json()["company_name"] == "Atlas Enterprise"


@pytest.mark.asyncio
async def test_get_workspace_by_id_allows_workspace_token(client):
    create = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Workspace Token Fetch",
        "scenario": "atlas_enterprise",
    })
    body = create.json()

    resp = await client.get(
        f"/api/workspaces/{body['id']}",
        headers={
            "X-Workspace-ID": body["id"],
            "X-Workspace-Token": body["access_token"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Workspace Token Fetch"


@pytest.mark.asyncio
async def test_get_workspace_not_found(client):
    resp = await client.get("/api/workspaces/nonexistent123", headers=ADMIN_HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_workspace(client):
    create = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Delete Me",
        "scenario": "meridian_data",
    })
    ws_id = create.json()["id"]

    resp = await client.delete(f"/api/workspaces/{ws_id}", headers=ADMIN_HEADERS)
    assert resp.status_code == 204

    check = await client.get(f"/api/workspaces/{ws_id}", headers=ADMIN_HEADERS)
    assert check.status_code == 404


@pytest.mark.asyncio
async def test_create_workspace_random_scenario(client):
    resp = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Random Test",
        "scenario": "random",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["company_name"] != "Random Test"
    assert body["customer_count"] >= 100
    assert len(body["industry"]) > 0


@pytest.mark.asyncio
async def test_create_workspace_rejects_unknown_scenario(client):
    resp = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Typo Test",
        "scenario": "velocitty_saas",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_workspace_rejects_blank_name(client):
    resp = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "   ",
        "scenario": "velocity_saas",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_workspace_trims_name(client):
    resp = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "  Trimmed WS  ",
        "scenario": "velocity_saas",
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "Trimmed WS"


@pytest.mark.asyncio
async def test_regeneration_clears_stale_completion_state(client):
    create = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
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
async def test_datetime_fields_serialize_as_utc(client):
    """Naive UTC datetimes must serialize with an explicit UTC marker so the
    browser does not reinterpret them as local time (the '60m elapsed' bug)."""
    create = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Timezone Test",
        "scenario": "velocity_saas",
    })
    ws_id = create.json()["id"]

    from app.services.workspace_manager import update_workspace_status

    update_workspace_status(ws_id, "generating")

    resp = await client.get(f"/api/workspaces/{ws_id}", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["created_at"].endswith("Z"), body["created_at"]
    assert body["generation_started_at"].endswith("Z"), body["generation_started_at"]


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
    create = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Missing DB Test",
        "scenario": "velocity_saas",
    })
    ws_id = create.json()["id"]
    resp = await client.get(
        "/api/overview/kpis",
        headers={
            "X-Workspace-ID": ws_id,
            "X-Workspace-Token": create.json()["access_token"],
        },
    )
    assert resp.status_code == 404
