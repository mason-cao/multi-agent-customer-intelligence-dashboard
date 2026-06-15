"""
Workspace metadata model.

Stored in the metadata database (data/workspaces.db), NOT in per-workspace
databases. Uses WorkspaceBase instead of Base.
"""

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.workspace_db import WorkspaceBase


class Workspace(WorkspaceBase):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    scenario = Column(String, nullable=False)
    source = Column(String, nullable=False, default="owner")
    industry = Column(String, nullable=False)
    customer_count = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="created")
    current_stage = Column(String, nullable=True)
    stage_index = Column(Integer, nullable=True)
    total_stages = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    generation_started_at = Column(DateTime, nullable=True)
    seed = Column(Integer, nullable=True)
    config_json = Column(Text, nullable=True)
    access_token_hash = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    pipeline_warnings = Column(Text, nullable=True)


class OwnerAccess(WorkspaceBase):
    """Single-row owner passcode metadata for first-run setup."""

    __tablename__ = "owner_access"

    id = Column(String, primary_key=True)
    passcode_hash = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
