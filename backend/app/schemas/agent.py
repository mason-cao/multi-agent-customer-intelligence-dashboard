from typing import List, Optional

from pydantic import BaseModel


class AgentRunSummary(BaseModel):
    id: str
    agent_name: str
    run_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None


class AgentDetail(BaseModel):
    agent_name: str
    description: str
    latest_run: Optional[AgentRunSummary] = None
    input_summary: Optional[dict] = None
    output_summary: Optional[dict] = None
    validation_results: List[str] = []


class AuditCheckResponse(BaseModel):
    audit_id: str
    check_category: str
    check_name: str
    severity: str
    passed: bool
    audit_message: str


class AuditOverviewResponse(BaseModel):
    total_checks: int
    passed: int
    failed: int
    critical_failures: int
    warnings: int
    check_categories: dict


class AgentsSummaryResponse(BaseModel):
    audit: AuditOverviewResponse
    runs: List[AgentRunSummary]
    checks: List[AuditCheckResponse]
