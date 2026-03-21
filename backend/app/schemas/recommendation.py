from typing import Optional

from pydantic import BaseModel


class RecommendationItem(BaseModel):
    recommendation_id: str
    target_type: str
    target_id: str
    action: str
    rationale: Optional[str] = None
    priority: str
    expected_impact: Optional[str] = None
    category: Optional[str] = None
