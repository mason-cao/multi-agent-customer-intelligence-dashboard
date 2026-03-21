from typing import Optional

from pydantic import BaseModel


class ChurnDistribution(BaseModel):
    risk_tier: str
    count: int
    mrr_at_risk: float


class ChurnScatterPoint(BaseModel):
    customer_id: str
    name: str
    engagement_score: float
    churn_probability: float
    segment_name: str
    mrr: float


class AtRiskCustomer(BaseModel):
    customer_id: str
    name: str
    company: str
    churn_probability: float
    risk_tier: str
    top_risk_factor: str
    mrr: float
    days_until_renewal: Optional[int] = None


class FeatureImportance(BaseModel):
    feature: str
    importance: float
