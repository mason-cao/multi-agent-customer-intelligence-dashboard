"""Public demos stay available without consuming owner capacity or growing forever."""

import asyncio
import threading

import pytest

from app.config import settings
from app.db.workspace_db import get_workspace_db_path, get_workspace_engine
from app.services import workspace_generator as generator
from app.services.workspace_manager import (
    create_workspace,
    get_workspace,
    list_all_workspace_records,
    update_workspace_status,
)


@pytest.fixture(autouse=True)
def demo_settings(monkeypatch):
    monkeypatch.setattr(settings, "public_synthetic_access", True)
    monkeypatch.setattr(settings, "max_demo_workspaces", 25)
    monkeypatch.setattr(generator, "_run_generation", lambda _workspace_id: None)


def saved_workspace(name, *, source="demo", status="ready"):
    workspace = create_workspace(name, "velocity_saas", source=source)
    update_workspace_status(workspace.id, status)
    return workspace


@pytest.mark.asyncio
async def test_demo_starts_when_old_records_fill_the_former_global_quota(client):
    # Production had 11 legacy failures, 12 failed demos, and two ready demos.
    for index in range(11):
        saved_workspace(f"Legacy {index}", source="legacy", status="failed")
    for index in range(12):
        saved_workspace(f"Failed demo {index}", status="failed")
    for index in range(2):
        saved_workspace(f"Ready demo {index}")
    assert len(list_all_workspace_records()) == settings.max_workspaces

    response = await client.post("/api/workspaces/synthetic")

    assert response.status_code == 201
    workspace = response.json()
    assert workspace["status"] == "generating"
    detail = await client.get(
        f"/api/workspaces/{workspace['id']}",
        headers={"X-Workspace-Token": workspace["access_token"]},
    )
    assert detail.status_code == 200
    assert get_workspace(workspace["id"]).source == "demo"


@pytest.mark.asyncio
async def test_full_demo_pool_reclaims_failed_data_and_preserves_other_workspaces(
    client, monkeypatch,
):
    monkeypatch.setattr(settings, "max_demo_workspaces", 2)
    owner = saved_workspace("Owner", source="owner")
    legacy = saved_workspace("Legacy", source="legacy", status="failed")
    ready = saved_workspace("Ready demo")
    failed = saved_workspace("Failed demo", status="failed")
    # A newer failed demo should be reclaimed before an older working demo.
    old_engine = get_workspace_engine(failed.id)
    with old_engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE demo_data (value INTEGER)")
    db_path = get_workspace_db_path(failed.id)
    bundle = [db_path, *(db_path.with_name(f"{db_path.name}{suffix}")
                        for suffix in ("-wal", "-shm", "-journal"))]
    for sidecar in bundle[1:]:
        sidecar.write_bytes(b"stale")

    response = await client.post("/api/workspaces/synthetic")

    assert response.status_code == 201
    assert get_workspace(failed.id) is None
    assert all(not path.exists() for path in bundle)
    assert get_workspace_engine(failed.id) is not old_engine
    assert {ws.id for ws in list_all_workspace_records()} == {
        owner.id, legacy.id, ready.id, response.json()["id"],
    }


@pytest.mark.asyncio
async def test_full_demo_pool_reclaims_the_oldest_completed_demo(client, monkeypatch):
    monkeypatch.setattr(settings, "max_demo_workspaces", 2)
    oldest = saved_workspace("Oldest demo")
    newest = saved_workspace("Newest demo")

    response = await client.post("/api/workspaces/synthetic")

    assert response.status_code == 201
    assert get_workspace(oldest.id) is None
    assert {ws.id for ws in list_all_workspace_records()} == {
        newest.id, response.json()["id"],
    }


@pytest.mark.asyncio
async def test_demo_capacity_recovers_after_the_limit_is_lowered(client, monkeypatch):
    monkeypatch.setattr(settings, "max_demo_workspaces", 1)
    for index in range(3):
        saved_workspace(f"Old demo {index}", status="failed")

    response = await client.post("/api/workspaces/synthetic")

    assert response.status_code == 201
    assert [ws.id for ws in list_all_workspace_records()] == [response.json()["id"]]


@pytest.mark.asyncio
async def test_demo_capacity_preserves_workspaces_still_being_generated(client, monkeypatch):
    monkeypatch.setattr(settings, "max_demo_workspaces", 1)
    generating = saved_workspace("Generating demo", status="generating")

    response = await client.post("/api/workspaces/synthetic")

    assert response.status_code == 429
    assert [ws.id for ws in list_all_workspace_records()] == [generating.id]
    assert get_workspace(generating.id).status == "generating"


@pytest.mark.asyncio
async def test_busy_generation_does_not_evict_a_saved_demo(client, monkeypatch):
    monkeypatch.setattr(settings, "max_demo_workspaces", 1)
    monkeypatch.setattr(settings, "max_concurrent_generations", 0)
    saved = saved_workspace("Saved demo")

    response = await client.post("/api/workspaces/synthetic")

    assert response.status_code == 429
    assert [ws.id for ws in list_all_workspace_records()] == [saved.id]


@pytest.mark.asyncio
async def test_demo_does_not_consume_owner_quota(client, monkeypatch):
    monkeypatch.setattr(settings, "max_workspaces", 1)
    saved_workspace("Saved demo")
    owner_request = {"name": "Owner workspace", "scenario": "velocity_saas"}
    headers = {"X-Admin-Token": "test-admin-token"}

    owner = await client.post("/api/workspaces", headers=headers, json=owner_request)
    assert owner.status_code == 201
    overflow = await client.post("/api/workspaces", headers=headers, json=owner_request)
    assert overflow.status_code == 409
    demo = await client.post("/api/workspaces/synthetic")
    assert demo.status_code == 201


@pytest.mark.asyncio
async def test_timed_out_demo_with_a_live_worker_is_not_reclaimed(client, monkeypatch):
    monkeypatch.setattr(settings, "max_demo_workspaces", 1)
    monkeypatch.setattr(settings, "max_concurrent_generations", 2)
    release = threading.Event()
    monkeypatch.setattr(generator, "_run_generation", lambda _workspace_id: release.wait(5))
    workspace = saved_workspace("Slow demo", status="created")
    assert generator.start_generation(workspace.id).status == generator.GenerationStartStatus.STARTED
    update_workspace_status(workspace.id, "failed", error_message="Timeout detected by polling")

    try:
        response = await client.post("/api/workspaces/synthetic")
        assert response.status_code == 429
        assert [ws.id for ws in list_all_workspace_records()] == [workspace.id]
        assert generator.active_generation_count() == 1
    finally:
        release.set()
        for _ in range(100):
            if generator.active_generation_count() == 0:
                break
            await asyncio.sleep(0.01)
    assert generator.active_generation_count() == 0


@pytest.mark.asyncio
async def test_concurrent_demo_starts_keep_one_generation_and_one_record(client, monkeypatch):
    monkeypatch.setattr(settings, "max_demo_workspaces", 1)
    monkeypatch.setattr(settings, "max_concurrent_generations", 1)
    release = threading.Event()
    monkeypatch.setattr(generator, "_run_generation", lambda _workspace_id: release.wait(5))

    try:
        responses = await asyncio.gather(*(
            client.post("/api/workspaces/synthetic") for _ in range(4)
        ))
        assert sorted(response.status_code for response in responses) == [201, 429, 429, 429]
        assert len(list_all_workspace_records()) == 1
        assert generator.active_generation_count() == 1
    finally:
        release.set()
        for _ in range(100):
            if generator.active_generation_count() == 0:
                break
            await asyncio.sleep(0.01)
    assert generator.active_generation_count() == 0


@pytest.mark.asyncio
async def test_demo_start_failure_does_not_leave_a_record(client, monkeypatch):
    def fail_start(_workspace_id):
        return generator.GenerationStartResult(generator.GenerationStartStatus.START_FAILED, "Failed")

    monkeypatch.setattr(generator, "start_generation", fail_start)

    response = await client.post("/api/workspaces/synthetic")

    assert response.status_code == 500
    assert list_all_workspace_records() == []
