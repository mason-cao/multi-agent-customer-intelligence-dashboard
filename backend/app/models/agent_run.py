from sqlalchemy import Column, String, Integer, Text

from app.db.database import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True)
    agent_name = Column(String, nullable=False)
    run_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)
    started_at = Column(String, nullable=False)
    completed_at = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    input_summary = Column(Text, nullable=True)  # JSON
    output_data = Column(Text, nullable=True)  # JSON
    output_summary = Column(Text, nullable=True)  # JSON
    error_message = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    model_used = Column(String, nullable=True)
