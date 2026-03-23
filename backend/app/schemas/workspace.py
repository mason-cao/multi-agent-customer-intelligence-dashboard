"""Pydantic schemas for workspace API requests and responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str
    scenario: str  # "velocity_saas" | "atlas_enterprise" | "beacon_analytics" | "meridian_data" | "custom"
    industry: Optional[str] = None
    customer_count: Optional[int] = Field(default=None, ge=100, le=10000)
    seed: Optional[int] = None
    churn_rate: Optional[float] = Field(default=None, ge=0.05, le=0.30)
    include_outage: Optional[bool] = None
    scenario_description: Optional[str] = Field(default=None, max_length=500)


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
