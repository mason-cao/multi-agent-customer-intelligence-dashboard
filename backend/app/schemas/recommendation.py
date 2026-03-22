from typing import Optional

from pydantic import BaseModel


class RecommendationItem(BaseModel):
    recommendation_id: str
    customer_id: str
    action_code: str
    action_label: str
    action_category: str
    action_priority: int
    urgency_score: float
    confidence: str
    primary_driver: str
    secondary_driver: Optional[str] = None
    reasoning: str
    recommended_channel: str
    recommended_owner: str
    target_timeframe: str
    recommendation_version: str
    computed_at: str


class RecommendationSummary(BaseModel):
    total_recommendations: int
    action_distribution: dict
    category_distribution: dict
    priority_distribution: dict
    confidence_distribution: dict
    avg_urgency: float
    timeframe_distribution: dict
