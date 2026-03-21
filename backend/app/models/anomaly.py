from sqlalchemy import Column, String, Float, Text

from app.db.database import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    anomaly_id = Column(String, primary_key=True)
    anomaly_type = Column(String, nullable=False)
    metric = Column(String, nullable=False)
    expected_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    deviation_sigma = Column(Float, nullable=False)
    affected_segment = Column(String, nullable=True)
    timestamp = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    explanation = Column(Text, nullable=True)
    run_id = Column(String, nullable=True)
