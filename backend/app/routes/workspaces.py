"""Workspace management API routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import get_admin_api_token
from app.config import settings
from app.security.auth import (
    ADMIN_TOKEN_HEADER,
    WORKSPACE_ID_HEADER,
    WORKSPACE_TOKEN_HEADER,
    require_admin_token,
)
from app.utils.error_handling import handle_errors

from app.schemas.workspace import (
    OwnerAccessCreate,
    OwnerAccessStatusResponse,
    ScenarioResponse,
    WorkspaceAccessTokenResponse,
    WorkspaceCreate,
    WorkspaceCreateResponse,
    WorkspaceListResponse,
    WorkspaceResponse,
)
from app.services.owner_access import (
    create_owner_passcode,
    owner_passcode_configured,
)
from app.services.workspace_manager import (
    DEMO_WORKSPACE_SOURCE,
    SCENARIOS,
    create_workspace,
    delete_workspace,
    get_workspace,
    list_all_workspace_records,
    list_workspaces,
    mark_pruned_workspaces_failed,
    prune_workspace_data_for_free_space,
    rotate_workspace_access_token,
    update_workspace_status,
    validate_workspace_access_token,
)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


def recover_data_volume_space() -> None:
    """Prune old workspace data if the persistent volume is below reserve."""
    pruned_workspace_ids = prune_workspace_data_for_free_space()
    mark_pruned_workspaces_failed(pruned_workspace_ids)


def get_owner_access_status_response() -> OwnerAccessStatusResponse:
    """Describe how owner workspace-management access is currently configured."""
    if get_admin_api_token():
        return OwnerAccessStatusResponse(
            mode="deployment_token",
            setup_required=False,
            owner_access_enabled=True,
        )
    if owner_passcode_configured():
        return OwnerAccessStatusResponse(
            mode="owner_passcode",
            setup_required=False,
            owner_access_enabled=True,
        )
    return OwnerAccessStatusResponse(
        mode="setup_required",
        setup_required=True,
        owner_access_enabled=False,
    )


def require_workspace_detail_access(workspace_id: str, request: Request) -> None:
    """Allow admins or the matching workspace token to read workspace metadata."""
    if request.headers.get(ADMIN_TOKEN_HEADER):
        require_admin_token(request)
        return

    supplied_workspace_id = request.headers.get(WORKSPACE_ID_HEADER)
    supplied_token = request.headers.get(WORKSPACE_TOKEN_HEADER)
    if not supplied_token:
        raise HTTPException(status_code=401, detail="Workspace token required")
    if supplied_workspace_id and supplied_workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Invalid workspace token")
    if not validate_workspace_access_token(workspace_id, supplied_token):
        raise HTTPException(status_code=403, detail="Invalid workspace token")


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
def list_all_workspaces(_: None = Depends(require_admin_token)):
    """List owner-created workspaces ordered by creation date."""
    workspaces = list_workspaces()
    return WorkspaceListResponse(
        workspaces=[WorkspaceResponse.model_validate(w) for w in workspaces],
        total=len(workspaces),
    )


@router.post("", response_model=WorkspaceCreateResponse, status_code=201)
@handle_errors("create_new_workspace")
def create_new_workspace(
    body: WorkspaceCreate,
    _: None = Depends(require_admin_token),
):
    """Create a new workspace with the given scenario configuration."""
    recover_data_volume_space()
    if len(list_workspaces()) >= settings.max_workspaces:
        raise HTTPException(status_code=409, detail="Workspace limit reached.")

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
    return WorkspaceCreateResponse.model_validate(ws)


@router.post("/synthetic", response_model=WorkspaceCreateResponse, status_code=201)
@handle_errors("create_public_synthetic_workspace")
def create_public_synthetic_workspace():
    """Create and start a bounded demo workspace without owner access."""
    if not settings.public_synthetic_access:
        raise HTTPException(
            status_code=403,
            detail="Synthetic workspace access is disabled.",
        )
    recover_data_volume_space()
    if len(list_all_workspace_records()) >= settings.max_workspaces:
        raise HTTPException(status_code=409, detail="Workspace limit reached.")

    ws = create_workspace(
        name="Synthetic Workspace",
        scenario="random",
        source=DEMO_WORKSPACE_SOURCE,
    )

    from app.services.workspace_generator import (
        GenerationStartStatus,
        start_generation,
    )

    result = start_generation(ws.id)
    if result.status != GenerationStartStatus.STARTED:
        delete_workspace(ws.id)
    if result.status == GenerationStartStatus.CAPACITY_REACHED:
        raise HTTPException(status_code=429, detail=result.detail)
    if result.status != GenerationStartStatus.STARTED:
        raise HTTPException(
            status_code=500,
            detail="We couldn't start the demo workspace. Try again.",
        )

    started_ws = get_workspace(ws.id)
    if not started_ws:
        raise HTTPException(
            status_code=500,
            detail="We couldn't load the demo workspace. Try again.",
        )
    started_ws.access_token = ws.access_token
    return WorkspaceCreateResponse.model_validate(started_ws)


@router.get("/owner-access", response_model=OwnerAccessStatusResponse)
@handle_errors("get_owner_access_status")
def get_owner_access_status():
    """Return owner-access setup status for the Workspaces screen."""
    return get_owner_access_status_response()


@router.post("/owner-access", response_model=OwnerAccessStatusResponse, status_code=201)
@handle_errors("create_owner_access")
def create_owner_access(body: OwnerAccessCreate):
    """Create first-run owner access when no deployment token is configured."""
    if get_admin_api_token():
        raise HTTPException(
            status_code=409,
            detail="Owner access is already controlled by the deployment settings.",
        )
    if owner_passcode_configured():
        raise HTTPException(
            status_code=409,
            detail="Owner access is already set up.",
        )

    create_owner_passcode(body.passcode)
    return get_owner_access_status_response()


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
@handle_errors("get_workspace_detail")
def get_workspace_detail(
    workspace_id: str,
    request: Request,
):
    """Get workspace details including generation progress."""
    require_workspace_detail_access(workspace_id, request)
    ws = get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="This workspace doesn't exist.")

    # Detect timed-out generation on poll
    if ws.status == "generating":
        from app.services.workspace_generator import generation_timeout_seconds
        limit = generation_timeout_seconds(ws.customer_count)
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
            if elapsed > limit:
                update_workspace_status(
                    workspace_id, "failed",
                    error_message=f"Timeout: generation exceeded {limit}s limit after {int(elapsed)}s",
                )
                ws = get_workspace(workspace_id)

    return WorkspaceResponse.model_validate(ws)


@router.post("/{workspace_id}/generate", response_model=WorkspaceResponse, status_code=202)
@handle_errors("trigger_generation")
def trigger_generation(
    workspace_id: str,
    _: None = Depends(require_admin_token),
):
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
    recover_data_volume_space()

    from app.services.workspace_generator import (
        GenerationStartStatus,
        start_generation,
    )

    result = start_generation(workspace_id)
    if result.status == GenerationStartStatus.NOT_FOUND:
        raise HTTPException(status_code=404, detail=result.detail)
    if result.status == GenerationStartStatus.INVALID_STATUS:
        raise HTTPException(status_code=409, detail=result.detail)
    if result.status == GenerationStartStatus.CAPACITY_REACHED:
        raise HTTPException(status_code=429, detail=result.detail)
    if result.status != GenerationStartStatus.STARTED:
        raise HTTPException(status_code=500, detail="We couldn't start the setup process. Try again.")

    ws = get_workspace(workspace_id)
    return WorkspaceResponse.model_validate(ws)


@router.post("/{workspace_id}/access-token", response_model=WorkspaceAccessTokenResponse)
@handle_errors("rotate_workspace_token")
def rotate_workspace_token(
    workspace_id: str,
    _: None = Depends(require_admin_token),
):
    """Rotate and return a workspace access token for authorized admins."""
    token = rotate_workspace_access_token(workspace_id)
    if not token:
        raise HTTPException(status_code=404, detail="This workspace doesn't exist.")
    return WorkspaceAccessTokenResponse(workspace_id=workspace_id, access_token=token)


@router.delete("/{workspace_id}", status_code=204)
@handle_errors("remove_workspace")
def remove_workspace(
    workspace_id: str,
    _: None = Depends(require_admin_token),
):
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
