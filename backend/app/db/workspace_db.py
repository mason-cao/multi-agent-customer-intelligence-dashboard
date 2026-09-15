"""
Workspace database management.

Two database layers:
1. Metadata DB (`data/workspaces.db`) — stores workspace records
2. Per-workspace DBs (`data/workspaces/{id}.db`) — store agent pipeline data

The metadata DB uses a separate DeclarativeBase (WorkspaceBase) so its models
stay independent of the per-workspace agent models (which use Base from database.py).
"""

import re
import threading
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ── Paths ───────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
WORKSPACES_DIR = DATA_DIR / "workspaces"
METADATA_DB_PATH = DATA_DIR / "workspaces.db"
WORKSPACE_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")

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


def is_valid_workspace_id(workspace_id: str) -> bool:
    """Return whether a workspace ID matches generated workspace IDs."""
    return bool(WORKSPACE_ID_PATTERN.fullmatch(workspace_id))


def get_workspace_db_path(workspace_id: str) -> Path:
    """Get the SQLite database path for a specific workspace."""
    if not is_valid_workspace_id(workspace_id):
        raise ValueError("Invalid workspace ID")
    return WORKSPACES_DIR / f"{workspace_id}.db"


# ── Workspace engine cache ──────────────────────────────────────
# A fresh engine per request discards SQLite's page cache and pays
# connection setup on every dashboard call. Engines are cached per
# workspace instead; anything that deletes the underlying DB file
# (delete, regeneration, pruning) must call dispose_workspace_engine()
# so no pooled connection keeps the stale file's inode alive.
_ENGINE_LOCK = threading.Lock()
_ENGINE_CACHE: dict[str, tuple] = {}


def _get_workspace_database(workspace_id: str):
    """Resolve the engine and sessionmaker together under the cache lock."""
    db_path = get_workspace_db_path(workspace_id)
    with _ENGINE_LOCK:
        cached = _ENGINE_CACHE.get(workspace_id)
        if cached is None:
            engine = create_engine(f"sqlite:///{db_path}", echo=False)
            cached = (engine, sessionmaker(bind=engine))
            _ENGINE_CACHE[workspace_id] = cached
    return cached


def get_workspace_engine(workspace_id: str):
    return _get_workspace_database(workspace_id)[0]


def get_workspace_sessionmaker(workspace_id: str):
    """Return the cached sessionmaker bound to a workspace engine."""
    return _get_workspace_database(workspace_id)[1]


def get_workspace_session(workspace_id: str):
    """Create a new database session for a specific workspace."""
    return get_workspace_sessionmaker(workspace_id)()


def dispose_workspace_engine(workspace_id: str):
    """Evict a workspace engine and close its pooled connections."""
    with _ENGINE_LOCK:
        cached = _ENGINE_CACHE.pop(workspace_id, None)
    if cached:
        cached[0].dispose()
