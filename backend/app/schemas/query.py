from typing import List, Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class QuerySource(BaseModel):
    type: str
    id: str
    excerpt: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[QuerySource] = []
    confidence: str
    sql_generated: Optional[str] = None
    visualization_suggestion: Optional[str] = None
