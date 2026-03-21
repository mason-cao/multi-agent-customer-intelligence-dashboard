from sqlalchemy import Column, String, Integer, Text

from app.db.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False, index=True)
    submitted_at = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    rating = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
