from sqlalchemy import Column, String, Integer, Float

from app.db.database import Base


class CustomerFeature(Base):
    __tablename__ = "customer_features"

    customer_id = Column(String, primary_key=True)
    login_frequency_7d = Column(Integer, nullable=True)
    login_frequency_30d = Column(Integer, nullable=True)
    feature_usage_breadth = Column(Integer, nullable=True)
    session_duration_avg = Column(Float, nullable=True)
    trend_direction = Column(String, nullable=True)
    engagement_score = Column(Float, nullable=True)
    total_revenue = Column(Float, nullable=True)
    order_count = Column(Integer, nullable=True)
    days_since_last_order = Column(Integer, nullable=True)
    avg_order_value = Column(Float, nullable=True)
    support_ticket_count_30d = Column(Integer, nullable=True)
    total_event_count = Column(Integer, nullable=True)
    last_active_at = Column(String, nullable=True)
    tenure_days = Column(Integer, nullable=True)
    avg_resolution_hours = Column(Float, nullable=True)
    avg_sentiment = Column(Float, nullable=True)
    nps_score = Column(Float, nullable=True)
    computed_at = Column(String, nullable=True)
