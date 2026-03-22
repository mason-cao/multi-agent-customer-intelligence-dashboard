from sqlalchemy import Column, Float, Integer, String, Text

from app.db.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    recommendation_id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False, index=True)
    action_code = Column(String, nullable=False)
    action_label = Column(String, nullable=False)
    action_category = Column(String, nullable=False)
    action_priority = Column(Integer, nullable=False)
    urgency_score = Column(Float, nullable=False)
    confidence = Column(String, nullable=False)
    primary_driver = Column(String, nullable=False)
    secondary_driver = Column(String, nullable=True)
    reasoning = Column(Text, nullable=False)
    recommended_channel = Column(String, nullable=False)
    recommended_owner = Column(String, nullable=False)
    target_timeframe = Column(String, nullable=False)
    recommendation_version = Column(String, nullable=False)
    computed_at = Column(String, nullable=False)
