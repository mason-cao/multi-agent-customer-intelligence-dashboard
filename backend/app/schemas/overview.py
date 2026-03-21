from typing import List, Union

from pydantic import BaseModel


class KpiCard(BaseModel):
    label: str
    value: Union[str, float, int]
    trend: float
    trend_label: str


class OverviewKpis(BaseModel):
    total_customers: KpiCard
    monthly_revenue: KpiCard
    churn_rate: KpiCard
    avg_sentiment: KpiCard
    active_anomalies: KpiCard


class NarrativeResponse(BaseModel):
    executive_summary: str
    key_metrics: List[dict]
    highlights: List[str]
    concerns: List[str]
    generated_at: str


class RevenueTrendPoint(BaseModel):
    date: str
    revenue: float
    is_anomaly: bool = False
