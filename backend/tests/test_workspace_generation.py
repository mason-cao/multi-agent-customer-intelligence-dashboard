"""Generation reliability: agent-outcome classification, degraded completion,
timeout scaling, and startup reconciliation of orphaned generations."""

import threading

import pytest

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
