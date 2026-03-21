from pydantic import BaseModel


class SegmentSummary(BaseModel):
    segment_id: int
    segment_name: str
    customer_count: int
    avg_revenue: float
    avg_engagement: float
    avg_churn_risk: float


class SegmentRadarData(BaseModel):
    segment_name: str
    revenue: float
    engagement: float
    sentiment: float
    retention: float
    feature_adoption: float
    growth_rate: float
