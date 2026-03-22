"""Workspace management API routes."""

from fastapi import APIRouter, HTTPException

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
)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("/scenarios", response_model=list[ScenarioResponse])
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
def list_all_workspaces():
    """List all workspaces ordered by creation date."""
    workspaces = list_workspaces()
    return WorkspaceListResponse(
        workspaces=[WorkspaceResponse.model_validate(w) for w in workspaces],
        total=len(workspaces),
    )


@router.post("", response_model=WorkspaceResponse, status_code=201)
def create_new_workspace(body: WorkspaceCreate):
    """Create a new workspace with the given scenario configuration."""
    ws = create_workspace(
        name=body.name,
        scenario=body.scenario,
        industry=body.industry,
        customer_count=body.customer_count,
        seed=body.seed,
    )
    return WorkspaceResponse.model_validate(ws)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace_detail(workspace_id: str):
    """Get workspace details including generation progress."""
    ws = get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceResponse.model_validate(ws)


@router.post("/{workspace_id}/generate", status_code=202)
def trigger_generation(workspace_id: str):
    """Start workspace data generation and agent pipeline.

    Returns 202 Accepted immediately. The frontend should poll
    GET /api/workspaces/{id} to track progress via status,
    current_stage, stage_index, and total_stages fields.
    """
    ws = get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws.status not in ("created", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Workspace is '{ws.status}' — generation can only start from 'created' or 'failed' state",
        )

    from app.services.workspace_generator import start_generation

    started = start_generation(workspace_id)
    if not started:
        raise HTTPException(status_code=500, detail="Failed to start generation")

    return {"status": "generating", "workspace_id": workspace_id}


@router.delete("/{workspace_id}", status_code=204)
def remove_workspace(workspace_id: str):
    """Delete a workspace and its database file."""
    if not delete_workspace(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
