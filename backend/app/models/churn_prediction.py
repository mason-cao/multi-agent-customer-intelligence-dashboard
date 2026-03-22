from sqlalchemy import Column, String, Float, Text

from app.db.database import Base


class ChurnPrediction(Base):
    __tablename__ = "churn_predictions"

    customer_id = Column(String, primary_key=True)
    churn_probability = Column(Float, nullable=False)
    risk_tier = Column(String, nullable=False)
    top_risk_factors = Column(Text, nullable=True)  # JSON
    explanation = Column(Text, nullable=True)
    scoring_version = Column(String, nullable=True)
    computed_at = Column(String, nullable=True)
