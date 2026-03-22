from sqlalchemy import Column, Integer, String, Text

from app.db.database import Base


class ExecutiveSummary(Base):
    __tablename__ = "executive_summaries"

    summary_id = Column(String, primary_key=True)
    summary_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    summary_text = Column(Text, nullable=False)
    supporting_metrics = Column(Text, nullable=True)  # JSON
    priority = Column(Integer, nullable=False)
    section_order = Column(Integer, nullable=False)
    source_scope = Column(String, nullable=False)
    narrative_version = Column(String, nullable=False)
    computed_at = Column(String, nullable=False)
