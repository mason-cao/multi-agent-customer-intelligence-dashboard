"""Workspace management API routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.utils.error_handling import handle_errors

from app.schemas.workspace import (
    ScenarioResponse,
    WorkspaceCreate,
    WorkspaceListResponse,
    WorkspaceResponse,
)
from app.services.workspace_manager import (
    SCENARIOS,
    create_workspace,
    delete_workspace,
    get_workspace,
    list_workspaces,
    update_workspace_status,
)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("/scenarios", response_model=list[ScenarioResponse])
@handle_errors("get_scenarios")
def get_scenarios():
    """Return available company scenario archetypes."""
    return [
        ScenarioResponse(
            key=key,
            company_name=val["company_name"],
            industry=val["industry"],
            customer_count=val["customer_count"],
            description=val["description"],
            churn_rate=val["churn_rate"],
            profile=val["profile"],
        )
        for key, val in SCENARIOS.items()
    ]


@router.get("", response_model=WorkspaceListResponse)
@handle_errors("list_all_workspaces")
def list_all_workspaces():
    """List all workspaces ordered by creation date."""
    workspaces = list_workspaces()
    return WorkspaceListResponse(
        workspaces=[WorkspaceResponse.model_validate(w) for w in workspaces],
        total=len(workspaces),
    )


@router.post("", response_model=WorkspaceResponse, status_code=201)
@handle_errors("create_new_workspace")
def create_new_workspace(body: WorkspaceCreate):
    """Create a new workspace with the given scenario configuration."""
    ws = create_workspace(
        name=body.name,
        scenario=body.scenario,
        industry=body.industry,
        customer_count=body.customer_count,
        seed=body.seed,
        churn_rate=body.churn_rate,
        include_outage=body.include_outage,
        scenario_description=body.scenario_description,
    )
    return WorkspaceResponse.model_validate(ws)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
@handle_errors("get_workspace_detail")
def get_workspace_detail(workspace_id: str):
    """Get workspace details including generation progress."""
    ws = get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="This workspace doesn't exist.")

    # Detect timed-out generation on poll
    if ws.status == "generating":
        from app.services.workspace_generator import GENERATION_TIMEOUT_SECONDS
        if not ws.generation_started_at:
            update_workspace_status(
                workspace_id, "failed",
                error_message="Timeout: generation state is stale (missing start time)",
            )
            ws = get_workspace(workspace_id)
        else:
            # SQLite returns naive datetimes; make both sides aware for safe comparison
            started = ws.generation_started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            if elapsed > GENERATION_TIMEOUT_SECONDS:
                update_workspace_status(
                    workspace_id, "failed",
                    error_message=f"Timeout: generation exceeded {GENERATION_TIMEOUT_SECONDS}s limit after {int(elapsed)}s",
                )
                ws = get_workspace(workspace_id)

    return WorkspaceResponse.model_validate(ws)


@router.post("/{workspace_id}/generate", response_model=WorkspaceResponse, status_code=202)
@handle_errors("trigger_generation")
def trigger_generation(workspace_id: str):
    """Start workspace data generation and agent pipeline.

    Accepts 'created', 'failed', or 'ready' status. For 'ready' and
    'failed' workspaces, the old database is deleted before regeneration.
    """
    ws = get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="This workspace doesn't exist.")
    if ws.status not in ("created", "failed", "ready"):
        raise HTTPException(
            status_code=409,
            detail="This workspace is already being set up.",
        )

    from app.services.workspace_generator import start_generation

    started = start_generation(workspace_id)
    if not started:
        raise HTTPException(status_code=500, detail="We couldn't start the setup process. Try again.")

    ws = get_workspace(workspace_id)
    return WorkspaceResponse.model_validate(ws)


@router.delete("/{workspace_id}", status_code=204)
@handle_errors("remove_workspace")
def remove_workspace(workspace_id: str):
    """Delete a workspace and its database file."""
    ws = get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="This workspace doesn't exist.")
    if ws.status == "generating":
        raise HTTPException(
            status_code=409,
            detail="This workspace can't be deleted while it's being set up.",
        )
    if not delete_workspace(workspace_id):
        raise HTTPException(status_code=404, detail="This workspace doesn't exist.")
