from sqlalchemy import Column, String, Integer, Float

from app.db.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    target_segment = Column(String, nullable=False)
    customers_targeted = Column(Integer, nullable=False)
    customers_engaged = Column(Integer, nullable=False)
    conversion_rate = Column(Float, nullable=False)
