import json
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Question is required")
        return normalized


class QueryResultItem(BaseModel):
    query_id: str
    original_question: str
    matched_intent: str
    query_status: str
    answer_text: str
    structured_result: Optional[Any] = None
    source_tables: Optional[str] = None
    row_count: Optional[int] = None
    execution_ms: Optional[int] = None
    query_version: str
    executed_at: str

    @field_validator("structured_result", mode="before")
    @classmethod
    def parse_structured_result(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
