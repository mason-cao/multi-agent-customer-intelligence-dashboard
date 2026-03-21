from sqlalchemy import Column, String, Integer, Text

from app.db.database import Base


class CustomerSegment(Base):
    __tablename__ = "customer_segments"

    customer_id = Column(String, primary_key=True)
    segment_id = Column(Integer, nullable=False)
    segment_code = Column(String, nullable=False)
    segment_name = Column(String, nullable=False)
    segment_description = Column(Text, nullable=True)
    primary_reason = Column(String, nullable=True)
    segmentation_version = Column(String, nullable=True)
    computed_at = Column(String, nullable=True)
