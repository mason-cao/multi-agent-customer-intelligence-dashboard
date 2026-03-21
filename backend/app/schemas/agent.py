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
