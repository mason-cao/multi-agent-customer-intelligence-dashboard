from sqlalchemy import Column, String, Text

from app.db.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    recommendation_id = Column(String, primary_key=True)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    action = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)
    priority = Column(String, nullable=False)
    expected_impact = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    run_id = Column(String, nullable=True)
