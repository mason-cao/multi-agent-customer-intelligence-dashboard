from typing import List, Optional

from pydantic import BaseModel


class SentimentTrendPoint(BaseModel):
    date: str
    avg_score: float
    positive_count: int
    neutral_count: int
    negative_count: int


class TopicSummary(BaseModel):
    topic: str
    count: int
    avg_sentiment: float


class TicketRow(BaseModel):
    ticket_id: str
    customer_id: str
    customer_name: str
    created_at: str
    category: str
    priority: str
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
    topics: List[str] = []
    summary: Optional[str] = None


class SentimentSummaryResponse(BaseModel):
    distribution: dict[str, int]
    avg_score: float
    total: int
    topics: List[TopicSummary]
