from typing import Optional

from pydantic import BaseModel


class ExecutiveSummaryItem(BaseModel):
    summary_id: str
    summary_type: str
    title: str
    summary_text: str
    supporting_metrics: Optional[dict] = None
    priority: int
    section_order: int
    source_scope: str
    narrative_version: str
    computed_at: str
