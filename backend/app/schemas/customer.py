from typing import Optional

from pydantic import BaseModel


class CustomerBase(BaseModel):
    customer_id: str
    name: str
    email: str
    company: str
    industry: str
    company_size: str
    plan_tier: str
    signup_date: str
    region: str
    acquisition_channel: str
    is_churned: bool
    churned_date: Optional[str] = None


class CustomerDetail(CustomerBase):
    engagement_score: Optional[float] = None
    churn_probability: Optional[float] = None
    risk_tier: Optional[str] = None
    segment_name: Optional[str] = None
    total_revenue: Optional[float] = None
    avg_sentiment: Optional[float] = None


class CustomerSearchResult(BaseModel):
    customer_id: str
    name: str
    company: str
    plan_tier: str


class CustomerListItem(BaseModel):
    customer_id: str
    name: str
    email: str
    company: str
    industry: str
    plan_tier: str
    signup_date: str
    region: str
    is_churned: bool
    engagement_score: Optional[float] = None
    total_revenue: Optional[float] = None
    segment_name: Optional[str] = None
    churn_probability: Optional[float] = None
    risk_tier: Optional[str] = None
    avg_sentiment: Optional[float] = None


class CustomerListResponse(BaseModel):
    customers: list[CustomerListItem]
    total: int
