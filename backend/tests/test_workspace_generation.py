"""Generation reliability: agent-outcome classification, degraded completion,
timeout scaling, and startup reconciliation of orphaned generations."""

import pytest

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
