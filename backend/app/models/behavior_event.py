from sqlalchemy import Column, String, Integer, Text

from app.db.database import Base


class BehaviorEvent(Base):
    __tablename__ = "behavior_events"

    event_id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False, index=True)
    timestamp = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    feature_name = Column(String, nullable=True)
    session_duration_sec = Column(Integer, nullable=True)
    event_metadata = Column("metadata", Text, nullable=True)
