"""Pydantic schemas for workspace API requests and responses."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, computed_field, field_validator


WorkspaceScenario = Literal[
    "velocity_saas",
    "atlas_enterprise",
    "beacon_analytics",
    "meridian_data",
    "custom",
    "random",
]


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    scenario: WorkspaceScenario
    industry: Optional[str] = None
    customer_count: Optional[int] = Field(default=None, ge=100, le=10000)
    seed: Optional[int] = None
    churn_rate: Optional[float] = Field(default=None, ge=0.05, le=0.30)
    include_outage: Optional[bool] = None
    scenario_description: Optional[str] = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Strip incidental whitespace and reject blank workspace names."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Workspace name is required")
        return normalized


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
    generation_started_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def user_message(self) -> Optional[str]:
        """Human-readable lifecycle message for the frontend."""
        if self.status != "failed" or not self.error_message:
            return None
        msg = self.error_message
        if msg.startswith("Timeout"):
            return "This workspace took too long to set up. You can try again."
        if "generate_data" in msg or "generate_dataset" in msg:
            return "Something went wrong while generating company data. You can try again."
        return "Something went wrong while setting up this workspace. You can try again."


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
