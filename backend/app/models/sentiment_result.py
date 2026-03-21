from sqlalchemy import Column, String, Float, Text

from app.db.database import Base


class SentimentResult(Base):
    __tablename__ = "sentiment_results"

    document_id = Column(String, primary_key=True)
    document_type = Column(String, nullable=False)
    customer_id = Column(String, nullable=False, index=True)
    sentiment_score = Column(Float, nullable=False)
    sentiment_label = Column(String, nullable=False)
    emotions = Column(Text, nullable=True)  # JSON list
    topics = Column(Text, nullable=True)  # JSON list
    summary = Column(Text, nullable=True)
    computed_at = Column(String, nullable=True)
