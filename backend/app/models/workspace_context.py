"""
Per-workspace key-value context table.

Stored in the per-workspace database (data/workspaces/{id}.db) alongside
agent tables. Uses Base (not WorkspaceBase) so it is created by
Base.metadata.create_all during generation.

Allows agents and routes to read scenario metadata (e.g. scenario_description,
company_name) without changing the BaseAgent execute() signature.
"""

from sqlalchemy import Column, String, Text

from app.db.database import Base


class WorkspaceContext(Base):
    __tablename__ = "workspace_context"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
