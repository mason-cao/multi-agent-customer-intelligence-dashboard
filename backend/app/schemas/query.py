from typing import Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class QueryResultItem(BaseModel):
    query_id: str
    original_question: str
    matched_intent: str
    query_status: str
    answer_text: str
    structured_result: Optional[dict] = None
    source_tables: Optional[str] = None
    row_count: Optional[int] = None
    execution_ms: Optional[int] = None
    query_version: str
    executed_at: str
