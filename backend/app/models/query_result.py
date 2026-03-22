from sqlalchemy import Column, String, Integer, Text

from app.db.database import Base


class QueryResult(Base):
    __tablename__ = "query_results"

    query_id = Column(String, primary_key=True)
    original_question = Column(Text, nullable=False)
    matched_intent = Column(String, nullable=False, index=True)  # e.g. "churn_by_segment"
    query_status = Column(String, nullable=False, index=True)  # success, unsupported, partial
    answer_text = Column(Text, nullable=False)
    structured_result = Column(Text, nullable=True)  # JSON
    source_tables = Column(String, nullable=True)  # comma-separated table names
    row_count = Column(Integer, nullable=True)
    execution_ms = Column(Integer, nullable=True)
    query_version = Column(String, nullable=False)
    executed_at = Column(String, nullable=False)
