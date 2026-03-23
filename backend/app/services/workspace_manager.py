"""
Workspace lifecycle management.

Handles workspace CRUD and scenario resolution. Data generation and
pipeline execution are handled separately by workspace_generator.py.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.db.workspace_db import (
    MetadataSession,
    WorkspaceBase,
    ensure_workspace_dirs,
    get_workspace_db_path,
    metadata_engine,
)
from app.models.workspace import Workspace

# ── Predefined company archetypes ───────────────────────────────

SCENARIOS = {
    "velocity_saas": {
        "company_name": "Velocity SaaS",
        "industry": "Technology",
        "customer_count": 1000,
        "description": "Fast-growing startup with high engagement and low churn",
        "churn_rate": 0.08,
        "profile": "healthy_growth",
    },
    "atlas_enterprise": {
        "company_name": "Atlas Enterprise",
        "industry": "Finance",
        "customer_count": 5000,
        "description": "Mature B2B platform with mixed customer health",
        "churn_rate": 0.14,
        "profile": "mixed_health",
    },
    "beacon_analytics": {
        "company_name": "Beacon Analytics",
        "industry": "Technology",
        "customer_count": 2500,
        "description": "Mid-market analytics company experiencing a churn crisis",
        "churn_rate": 0.25,
        "profile": "churn_crisis",
    },
    "meridian_data": {
        "company_name": "Meridian Data",
        "industry": "Healthcare",
        "customer_count": 500,
        "description": "Small data company with heavy support load",
        "churn_rate": 0.12,
        "profile": "support_heavy",
    },
}


def init_metadata_db():
    """Create the workspace metadata tables."""
    WorkspaceBase.metadata.create_all(bind=metadata_engine)


def list_workspaces() -> list[Workspace]:
    """Return all workspaces ordered by creation date (newest first)."""
    db = MetadataSession()
    try:
        return db.query(Workspace).order_by(Workspace.created_at.desc()).all()
    finally:
        db.close()


def get_workspace(workspace_id: str) -> Optional[Workspace]:
    """Return a single workspace by ID, or None."""
    db = MetadataSession()
    try:
        return db.query(Workspace).filter(Workspace.id == workspace_id).first()
    finally:
        db.close()


def create_workspace(
    name: str,
    scenario: str,
    industry: Optional[str] = None,
    customer_count: Optional[int] = None,
    seed: Optional[int] = None,
    churn_rate: Optional[float] = None,
    include_outage: Optional[bool] = None,
    scenario_description: Optional[str] = None,
) -> Workspace:
    """Create a new workspace record in the metadata database."""
    ensure_workspace_dirs()

    # Resolve scenario defaults
    if scenario in SCENARIOS:
        defaults = SCENARIOS[scenario]
        company_name = defaults["company_name"]
        resolved_industry = industry or defaults["industry"]
        resolved_count = customer_count or defaults["customer_count"]
        resolved_churn = churn_rate if churn_rate is not None else defaults["churn_rate"]
        resolved_profile = defaults["profile"]
        resolved_outage = include_outage if include_outage is not None else True
    else:
        # Custom scenario
        company_name = name
        resolved_industry = industry or "Technology"
        resolved_count = customer_count or 2000
        resolved_churn = churn_rate if churn_rate is not None else 0.14
        resolved_profile = "custom"
        resolved_outage = include_outage if include_outage is not None else True

    workspace = Workspace(
        id=uuid.uuid4().hex[:12],
        name=name,
        company_name=company_name,
        scenario=scenario,
        industry=resolved_industry,
        customer_count=resolved_count,
        status="created",
        created_at=datetime.now(timezone.utc),
        seed=seed,
        config_json=json.dumps({
            "scenario": scenario,
            "company_name": company_name,
            "industry": resolved_industry,
            "customer_count": resolved_count,
            "churn_rate": resolved_churn,
            "profile": resolved_profile,
            "seed": seed,
            "include_outage": resolved_outage,
            "scenario_description": scenario_description or "",
        }),
    )

    db = MetadataSession()
    try:
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        return workspace
    finally:
        db.close()


def prepare_for_regeneration(workspace_id: str) -> bool:
    """Reset a workspace for regeneration by deleting its stale database.

    Returns False if the workspace doesn't exist.
    """
    ws = get_workspace(workspace_id)
    if not ws:
        return False

    # Delete the old workspace database file
    db_path = get_workspace_db_path(workspace_id)
    if db_path.exists():
        db_path.unlink()

    # Reset progress fields
    update_workspace_status(
        workspace_id,
        status="generating",
        current_stage="Initializing workspace",
        stage_index=0,
        total_stages=14,
        error_message="",
    )
    return True


def update_workspace_status(
    workspace_id: str,
    status: str,
    current_stage: Optional[str] = None,
    stage_index: Optional[int] = None,
    total_stages: Optional[int] = None,
    error_message: Optional[str] = None,
) -> Optional[Workspace]:
    """Update workspace status and progress fields."""
    db = MetadataSession()
    try:
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not ws:
            return None
        ws.status = status
        if current_stage is not None:
            ws.current_stage = current_stage
        if stage_index is not None:
            ws.stage_index = stage_index
        if total_stages is not None:
            ws.total_stages = total_stages
        if error_message is not None:
            ws.error_message = error_message
        if status == "ready":
            ws.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(ws)
        return ws
    finally:
        db.close()


def delete_workspace(workspace_id: str) -> bool:
    """Delete a workspace record and its database file."""
    db = MetadataSession()
    try:
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not ws:
            return False
        db.delete(ws)
        db.commit()
    finally:
        db.close()

    # Remove the workspace database file if it exists
    db_path = get_workspace_db_path(workspace_id)
    if db_path.exists():
        db_path.unlink()

    return True
