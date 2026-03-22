"""
Workspace database management.

Two database layers:
1. Metadata DB (`data/workspaces.db`) — stores workspace records
2. Per-workspace DBs (`data/workspaces/{id}.db`) — store agent pipeline data

The metadata DB uses a separate DeclarativeBase (WorkspaceBase) so its models
stay independent of the per-workspace agent models (which use Base from database.py).
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ── Paths ───────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
WORKSPACES_DIR = DATA_DIR / "workspaces"
METADATA_DB_PATH = DATA_DIR / "workspaces.db"

# ── Metadata database (workspace records) ──────────────────────
metadata_engine = create_engine(f"sqlite:///{METADATA_DB_PATH}", echo=False)
MetadataSession = sessionmaker(bind=metadata_engine)


class WorkspaceBase(DeclarativeBase):
    """Separate Base for workspace metadata models."""
    pass


# ── Helpers ─────────────────────────────────────────────────────

def ensure_workspace_dirs():
    """Create workspace data directories if they don't exist."""
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)


def get_workspace_db_path(workspace_id: str) -> Path:
    """Get the SQLite database path for a specific workspace."""
    return WORKSPACES_DIR / f"{workspace_id}.db"


def get_workspace_engine(workspace_id: str):
    """Create a SQLAlchemy engine for a specific workspace database."""
    db_path = get_workspace_db_path(workspace_id)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_workspace_session(workspace_id: str):
    """Create a new database session for a specific workspace."""
    engine = get_workspace_engine(workspace_id)
    Session = sessionmaker(bind=engine)
    return Session()
