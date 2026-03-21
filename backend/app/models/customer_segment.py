from sqlalchemy import Column, String, Integer, Float

from app.db.database import Base


class CustomerSegment(Base):
    __tablename__ = "customer_segments"

    customer_id = Column(String, primary_key=True)
    segment_id = Column(Integer, nullable=False)
    segment_name = Column(String, nullable=False)
    cluster_distance = Column(Float, nullable=True)
    computed_at = Column(String, nullable=True)
