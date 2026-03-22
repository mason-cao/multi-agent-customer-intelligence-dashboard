"""Pydantic schemas for workspace API requests and responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str
    scenario: str  # "velocity_saas" | "atlas_enterprise" | "beacon_analytics" | "meridian_data" | "custom"
    industry: Optional[str] = None
    customer_count: Optional[int] = None
    seed: Optional[int] = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    company_name: str
    scenario: str
    industry: str
    customer_count: int
    status: str
    current_stage: Optional[str] = None
    stage_index: Optional[int] = None
    total_stages: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]
    total: int


class ScenarioResponse(BaseModel):
    key: str
    company_name: str
    industry: str
    customer_count: int
    description: str
    churn_rate: float
    profile: str
