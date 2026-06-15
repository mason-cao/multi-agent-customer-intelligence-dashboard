"""
Workspace lifecycle management.

Handles workspace CRUD and scenario resolution. Data generation and
pipeline execution are handled separately by workspace_generator.py.
"""

import json
import random
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from shutil import disk_usage
from typing import Optional

import structlog
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.db import workspace_db
from app.db.workspace_db import (
    MetadataSession,
    WorkspaceBase,
    ensure_workspace_dirs,
    get_workspace_db_path,
    metadata_engine,
)
from app.models.workspace import Workspace
from app.security.auth import (
    generate_workspace_token,
    hash_workspace_token,
    workspace_token_matches,
)

logger = structlog.get_logger(__name__)

OWNER_WORKSPACE_SOURCE = "owner"
DEMO_WORKSPACE_SOURCE = "demo"

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


_RANDOM_PREFIXES = [
    "Nova", "Apex", "Crest", "Pulse", "Summit",
    "Orbit", "Forge", "Helix", "Prism", "Vantage",
    "Nimbus", "Cipher", "Ember", "Lumen", "Zenith",
]
_RANDOM_SUFFIXES = [
    "Labs", "Systems", "Solutions", "Group", "Technologies",
    "Analytics", "Networks", "Digital", "Dynamics", "Platforms",
]
_RANDOM_INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Retail",
    "Manufacturing", "Education", "Media", "Logistics",
]


def generate_random_scenario() -> dict:
    """Generate a bounded random company scenario configuration."""
    rng = random.Random()
    company_name = f"{rng.choice(_RANDOM_PREFIXES)} {rng.choice(_RANDOM_SUFFIXES)}"
    industry = rng.choice(_RANDOM_INDUSTRIES)
    customer_count = rng.choice([300, 500, 800, 1000, 1500, 2000, 3000, 4000, 5000, 6000])
    churn_rate = round(rng.uniform(0.06, 0.25), 2)
    include_outage = rng.choice([True, False])
    seed = rng.randint(1, 99999)

    # Pick a profile label based on churn rate
    if churn_rate <= 0.10:
        profile = "healthy_growth"
    elif churn_rate <= 0.18:
        profile = "mixed_health"
    else:
        profile = "churn_crisis"

    return {
        "company_name": company_name,
        "industry": industry,
        "customer_count": customer_count,
        "churn_rate": churn_rate,
        "include_outage": include_outage,
        "profile": profile,
        "seed": seed,
    }


def init_metadata_db():
    """Create the workspace metadata tables (with column migrations)."""
    WorkspaceBase.metadata.create_all(bind=metadata_engine)
    # Lightweight column migrations for existing DBs
    from sqlalchemy import inspect, text
    columns = [c['name'] for c in inspect(metadata_engine).get_columns('workspaces')]
    migrations = {
        'source': 'ALTER TABLE workspaces ADD COLUMN source VARCHAR',
        'current_stage': 'ALTER TABLE workspaces ADD COLUMN current_stage VARCHAR',
        'stage_index': 'ALTER TABLE workspaces ADD COLUMN stage_index INTEGER',
        'total_stages': 'ALTER TABLE workspaces ADD COLUMN total_stages INTEGER',
        'completed_at': 'ALTER TABLE workspaces ADD COLUMN completed_at DATETIME',
        'generation_started_at': 'ALTER TABLE workspaces ADD COLUMN generation_started_at DATETIME',
        'seed': 'ALTER TABLE workspaces ADD COLUMN seed INTEGER',
        'config_json': 'ALTER TABLE workspaces ADD COLUMN config_json TEXT',
        'access_token_hash': 'ALTER TABLE workspaces ADD COLUMN access_token_hash VARCHAR',
        'error_message': 'ALTER TABLE workspaces ADD COLUMN error_message TEXT',
        'pipeline_warnings': 'ALTER TABLE workspaces ADD COLUMN pipeline_warnings TEXT',
    }
    for column, ddl in migrations.items():
        if column not in columns:
            with metadata_engine.begin() as conn:
                conn.execute(text(ddl))


def is_disk_full_error(exc: BaseException) -> bool:
    """Return whether an exception represents an exhausted data volume."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current and id(current) not in seen:
        seen.add(id(current))
        message = str(current).lower()
        if (
            "database or disk is full" in message
            or "no space left on device" in message
        ):
            return True
        if isinstance(current, sqlite3.OperationalError) and "disk" in message:
            return True
        current = (
            getattr(current, "orig", None)
            or getattr(current, "__cause__", None)
            or getattr(current, "__context__", None)
        )
    return False


def _workspace_database_bundle_paths(db_path: Path) -> list[Path]:
    """Return the SQLite database file and possible sidecar files."""
    return [
        db_path,
        db_path.with_name(f"{db_path.name}-wal"),
        db_path.with_name(f"{db_path.name}-shm"),
        db_path.with_name(f"{db_path.name}-journal"),
    ]


def prune_workspace_data_for_free_space(
    min_free_bytes: Optional[int] = None,
) -> list[str]:
    """Delete oldest workspace DB files until the data volume has free space.

    Startup can run before SQLite is writable. This routine only removes
    per-workspace data files, so it can recover space before metadata cleanup
    attempts its first write.
    """
    target_free_bytes = (
        settings.min_data_volume_free_bytes
        if min_free_bytes is None
        else min_free_bytes
    )
    if target_free_bytes <= 0:
        return []

    ensure_workspace_dirs()
    workspaces_dir = workspace_db.WORKSPACES_DIR
    if disk_usage(workspaces_dir).free >= target_free_bytes:
        return []

    db_files = sorted(
        workspaces_dir.glob("*.db"),
        key=lambda path: (path.stat().st_mtime, path.name),
    )
    deleted_workspace_ids: list[str] = []

    for db_path in db_files:
        removed_any = False
        for path in _workspace_database_bundle_paths(db_path):
            try:
                path.unlink()
                removed_any = True
            except FileNotFoundError:
                continue
        if removed_any:
            deleted_workspace_ids.append(db_path.stem)

        if disk_usage(workspaces_dir).free >= target_free_bytes:
            break

    return deleted_workspace_ids


def mark_pruned_workspaces_failed(workspace_ids: list[str]) -> int:
    """Mark workspaces whose database files were pruned as retryable failures."""
    if not workspace_ids:
        return 0

    db = MetadataSession()
    try:
        workspaces = (
            db.query(Workspace)
            .filter(Workspace.id.in_(workspace_ids))
            .all()
        )
        for ws in workspaces:
            ws.status = "failed"
            ws.error_message = (
                "Workspace data was pruned to recover storage. You can try again."
            )
            ws.completed_at = datetime.now(timezone.utc)
        if workspaces:
            try:
                db.commit()
            except OperationalError as exc:
                if is_disk_full_error(exc):
                    db.rollback()
                    logger.error(
                        "mark_pruned_workspaces_failed_skipped_disk_full",
                        workspace_ids=workspace_ids,
                        error=str(exc),
                    )
                    return 0
                raise
        return len(workspaces)
    finally:
        db.close()


def list_workspaces() -> list[Workspace]:
    """Return owner-created workspaces ordered by creation date (newest first)."""
    db = MetadataSession()
    try:
        return (
            db.query(Workspace)
            .filter(Workspace.source == OWNER_WORKSPACE_SOURCE)
            .order_by(Workspace.created_at.desc())
            .all()
        )
    finally:
        db.close()


def list_all_workspace_records() -> list[Workspace]:
    """Return all workspace records, including demo and legacy records."""
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
    source: str = OWNER_WORKSPACE_SOURCE,
) -> Workspace:
    """Create a new workspace record in the metadata database."""
    ensure_workspace_dirs()
    access_token = generate_workspace_token()

    # Resolve scenario defaults
    if scenario == "random":
        rand = generate_random_scenario()
        company_name = rand["company_name"]
        resolved_industry = rand["industry"]
        resolved_count = rand["customer_count"]
        resolved_churn = rand["churn_rate"]
        resolved_profile = rand["profile"]
        resolved_outage = rand["include_outage"]
        seed = seed or rand["seed"]
    elif scenario in SCENARIOS:
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
        source=source,
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
        access_token_hash=hash_workspace_token(access_token),
    )

    db = MetadataSession()
    try:
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        workspace.access_token = access_token
        return workspace
    finally:
        db.close()


def rotate_workspace_access_token(workspace_id: str) -> Optional[str]:
    """Replace a workspace access token and return the new plaintext token."""
    access_token = generate_workspace_token()
    db = MetadataSession()
    try:
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not ws:
            return None
        ws.access_token_hash = hash_workspace_token(access_token)
        db.commit()
        return access_token
    finally:
        db.close()


def validate_workspace_access_token(workspace_id: str, access_token: str) -> bool:
    """Return whether a workspace access token authorizes that workspace."""
    ws = get_workspace(workspace_id)
    if not ws:
        return False
    return workspace_token_matches(access_token, ws.access_token_hash)


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
    pipeline_warnings: Optional[str] = None,
) -> Optional[Workspace]:
    """Update workspace status and progress fields."""
    db = MetadataSession()
    try:
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not ws:
            return None
        old_status = ws.status
        ws.status = status
        if status == "generating" and old_status != "generating":
            ws.generation_started_at = datetime.now(timezone.utc)
            ws.completed_at = None
            ws.error_message = None
            ws.pipeline_warnings = None
        if current_stage is not None:
            ws.current_stage = current_stage
        if stage_index is not None:
            ws.stage_index = stage_index
        if total_stages is not None:
            ws.total_stages = total_stages
        if error_message is not None:
            ws.error_message = error_message
        if pipeline_warnings is not None:
            ws.pipeline_warnings = pipeline_warnings
        if status == "ready":
            ws.completed_at = datetime.now(timezone.utc)
            ws.error_message = None
        db.commit()
        db.refresh(ws)
        return ws
    finally:
        db.close()


def reconcile_orphaned_workspaces() -> int:
    """Fail workspaces stuck in 'generating' with no live worker.

    Generation runs in a daemon thread that does not survive a process
    restart (dev `--reload`, Railway redeploy). Any workspace still
    'generating' at startup has no worker producing progress, so mark it
    failed cleanly instead of leaving it stuck forever. Returns the count
    reconciled.
    """
    db = MetadataSession()
    try:
        stuck = db.query(Workspace).filter(Workspace.status == "generating").all()
        for ws in stuck:
            ws.status = "failed"
            ws.error_message = (
                "Setup was interrupted by a server restart. You can try again."
            )
            ws.completed_at = datetime.now(timezone.utc)
        if stuck:
            try:
                db.commit()
            except OperationalError as exc:
                if is_disk_full_error(exc):
                    db.rollback()
                    logger.error(
                        "reconcile_orphaned_workspaces_skipped_disk_full",
                        stuck_count=len(stuck),
                        error=str(exc),
                    )
                    return 0
                raise
        return len(stuck)
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
