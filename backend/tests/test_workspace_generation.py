"""Generation reliability: agent-outcome classification, degraded completion,
timeout scaling, and startup reconciliation of orphaned generations."""

import os
import sqlite3
import threading
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import OperationalError

from app.config import settings
from tests.conftest import ADMIN_HEADERS

from app.services.workspace_generator import (
    classify_agent_outcome,
    generation_timeout_seconds,
)


def test_completed_agent_is_ok():
    action, msg = classify_agent_outcome("BehaviorAgent", critical=True, status="completed")
    assert action == "ok"
    assert msg is None


def test_critical_failure_is_fatal():
    action, msg = classify_agent_outcome("ChurnAgent", critical=True, status="failed")
    assert action == "fatal"
    assert "ChurnAgent" in msg


def test_noncritical_failure_only_warns():
    action, msg = classify_agent_outcome("NarrativeAgent", critical=False, status="failed")
    assert action == "warn"
    assert "NarrativeAgent" in msg


def test_partial_warns_even_when_critical():
    action, msg = classify_agent_outcome("SegmentationAgent", critical=True, status="partial")
    assert action == "warn"
    assert "SegmentationAgent" in msg


def test_timeout_scales_with_customer_count_and_has_floor():
    # Larger workspaces (ML + SHAP) get a larger budget; small ones keep a floor.
    assert generation_timeout_seconds(500) >= 900
    assert generation_timeout_seconds(10000) > generation_timeout_seconds(1000)


def test_startup_prune_deletes_oldest_workspace_database_bundle(test_data_dir, monkeypatch):
    import app.services.workspace_manager as workspace_manager

    old_db = test_data_dir / "workspaces" / "111111111111.db"
    old_wal = test_data_dir / "workspaces" / "111111111111.db-wal"
    old_shm = test_data_dir / "workspaces" / "111111111111.db-shm"
    new_db = test_data_dir / "workspaces" / "222222222222.db"
    for path in [old_db, old_wal, old_shm, new_db]:
        path.write_bytes(b"x")

    old_time = 1_700_000_000
    new_time = old_time + 60
    for path in [old_db, old_wal, old_shm]:
        path.touch()
        path.chmod(0o600)
        os.utime(path, (old_time, old_time))
    os.utime(new_db, (new_time, new_time))

    free_space = iter([0, 128 * 1024 * 1024])
    monkeypatch.setattr(
        workspace_manager,
        "disk_usage",
        lambda _path: SimpleNamespace(free=next(free_space)),
    )

    deleted = workspace_manager.prune_workspace_data_for_free_space(
        min_free_bytes=64 * 1024 * 1024,
    )

    assert deleted == ["111111111111"]
    assert not old_db.exists()
    assert not old_wal.exists()
    assert not old_shm.exists()
    assert new_db.exists()


def test_pruned_workspace_records_are_marked_failed(client):
    from app.services.workspace_manager import (
        create_workspace,
        get_workspace,
        mark_pruned_workspaces_failed,
        update_workspace_status,
    )

    pruned = create_workspace("Pruned", "velocity_saas")
    retained = create_workspace("Retained", "velocity_saas")
    update_workspace_status(pruned.id, "ready")
    update_workspace_status(retained.id, "ready")

    count = mark_pruned_workspaces_failed([pruned.id, "missing000000"])

    pruned_after = get_workspace(pruned.id)
    retained_after = get_workspace(retained.id)
    assert count == 1
    assert pruned_after.status == "failed"
    assert "pruned" in pruned_after.error_message
    assert retained_after.status == "ready"


def test_reconcile_orphaned_workspaces_does_not_raise_when_disk_is_full(monkeypatch):
    import app.services.workspace_manager as workspace_manager

    workspace = SimpleNamespace(status="generating", error_message=None, completed_at=None)
    fake_session = SimpleNamespace(rolled_back=False, closed=False)

    class FakeQuery:
        def filter(self, *_args):
            return self

        def all(self):
            return [workspace]

    def fake_commit():
        raise OperationalError(
            "UPDATE workspaces",
            {},
            sqlite3.OperationalError("database or disk is full"),
        )

    fake_session.query = lambda _model: FakeQuery()
    fake_session.commit = fake_commit
    fake_session.rollback = lambda: setattr(fake_session, "rolled_back", True)
    fake_session.close = lambda: setattr(fake_session, "closed", True)

    monkeypatch.setattr(workspace_manager, "MetadataSession", lambda: fake_session)

    assert workspace_manager.reconcile_orphaned_workspaces() == 0
    assert fake_session.rolled_back is True
    assert fake_session.closed is True


@pytest.mark.asyncio
async def test_generate_endpoint_enforces_concurrency_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "max_concurrent_generations", 1, raising=False)

    started = threading.Event()
    release = threading.Event()

    def blocking_generation(_workspace_id: str):
        started.set()
        release.wait(timeout=5)

    import app.services.workspace_generator as generator

    monkeypatch.setattr(generator, "_run_generation", blocking_generation)

    first = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Concurrent One",
        "scenario": "velocity_saas",
    })
    second = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Concurrent Two",
        "scenario": "velocity_saas",
    })

    first_generate = await client.post(
        f"/api/workspaces/{first.json()['id']}/generate",
        headers=ADMIN_HEADERS,
    )
    assert first_generate.status_code == 202
    assert started.wait(timeout=2)

    second_generate = await client.post(
        f"/api/workspaces/{second.json()['id']}/generate",
        headers=ADMIN_HEADERS,
    )
    assert second_generate.status_code == 429
    assert second_generate.json()["detail"] == "Generation capacity reached. Try again later."

    release.set()


@pytest.mark.asyncio
async def test_generation_slot_is_released_after_worker_finishes(client, monkeypatch):
    monkeypatch.setattr(settings, "max_concurrent_generations", 1, raising=False)

    import app.services.workspace_generator as generator
    from app.services.workspace_manager import update_workspace_status

    def finishing_generation(workspace_id: str):
        update_workspace_status(workspace_id, "failed", error_message="stopped by test")

    monkeypatch.setattr(generator, "_run_generation", finishing_generation)

    first = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Release One",
        "scenario": "velocity_saas",
    })
    second = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Release Two",
        "scenario": "velocity_saas",
    })

    first_generate = await client.post(
        f"/api/workspaces/{first.json()['id']}/generate",
        headers=ADMIN_HEADERS,
    )
    assert first_generate.status_code == 202

    second_generate = await client.post(
        f"/api/workspaces/{second.json()['id']}/generate",
        headers=ADMIN_HEADERS,
    )
    assert second_generate.status_code == 202


@pytest.mark.asyncio
async def test_reconcile_orphaned_workspaces_fails_stuck_generations(client):
    create = await client.post("/api/workspaces", headers=ADMIN_HEADERS, json={
        "name": "Orphan Test",
        "scenario": "velocity_saas",
    })
    ws_id = create.json()["id"]

    from app.services.workspace_manager import (
        delete_workspace,
        get_workspace,
        reconcile_orphaned_workspaces,
        update_workspace_status,
    )

    update_workspace_status(ws_id, "generating")
    assert get_workspace(ws_id).status == "generating"

    count = reconcile_orphaned_workspaces()
    assert count >= 1

    ws = get_workspace(ws_id)
    assert ws.status == "failed"
    assert ws.error_message

    # Clean up so the shared session-scoped metadata DB stays empty for other tests.
    delete_workspace(ws_id)
