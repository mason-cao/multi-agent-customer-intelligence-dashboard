"""Owner access setup and passcode authentication tests."""

import pytest


@pytest.fixture
def no_deployment_admin_token(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "admin_api_token", "", raising=False)
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)


@pytest.mark.asyncio
async def test_owner_access_status_requires_setup_without_deployment_token(
    client,
    no_deployment_admin_token,
):
    resp = await client.get("/api/workspaces/owner-access")

    assert resp.status_code == 200
    assert resp.json() == {
        "mode": "setup_required",
        "setup_required": True,
        "owner_access_enabled": False,
    }


@pytest.mark.asyncio
async def test_first_run_owner_passcode_can_manage_workspaces(
    client,
    no_deployment_admin_token,
):
    setup = await client.post(
        "/api/workspaces/owner-access",
        json={"passcode": "correct horse battery staple"},
    )

    assert setup.status_code == 201
    assert setup.json() == {
        "mode": "owner_passcode",
        "setup_required": False,
        "owner_access_enabled": True,
    }

    missing = await client.get("/api/workspaces")
    assert missing.status_code == 401
    assert missing.json()["detail"] == "Owner passcode required"

    invalid = await client.get(
        "/api/workspaces",
        headers={"X-Admin-Token": "wrong passcode"},
    )
    assert invalid.status_code == 403
    assert invalid.json()["detail"] == "Invalid owner passcode"

    authorized = await client.get(
        "/api/workspaces",
        headers={"X-Admin-Token": "correct horse battery staple"},
    )
    assert authorized.status_code == 200
    assert authorized.json() == {"workspaces": [], "total": 0}


@pytest.mark.asyncio
async def test_owner_passcode_setup_rejects_blank_passcode(
    client,
    no_deployment_admin_token,
):
    resp = await client.post(
        "/api/workspaces/owner-access",
        json={"passcode": "   "},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_deployment_admin_token_overrides_first_run_owner_setup(
    client,
    monkeypatch,
):
    from app.config import settings

    monkeypatch.setattr(settings, "admin_api_token", "configured-admin", raising=False)

    status = await client.get("/api/workspaces/owner-access")
    assert status.status_code == 200
    assert status.json() == {
        "mode": "deployment_token",
        "setup_required": False,
        "owner_access_enabled": True,
    }

    setup = await client.post(
        "/api/workspaces/owner-access",
        json={"passcode": "correct horse battery staple"},
    )
    assert setup.status_code == 409
    assert setup.json()["detail"] == (
        "Owner access is already controlled by the deployment settings."
    )

    invalid = await client.get(
        "/api/workspaces",
        headers={"X-Admin-Token": "correct horse battery staple"},
    )
    assert invalid.status_code == 403
    assert invalid.json()["detail"] == "Invalid admin token"

    authorized = await client.get(
        "/api/workspaces",
        headers={"X-Admin-Token": "configured-admin"},
    )
    assert authorized.status_code == 200
