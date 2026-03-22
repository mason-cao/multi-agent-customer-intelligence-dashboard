from sqlalchemy import Column, String, Integer, Text

from app.db.database import Base


class AuditResult(Base):
    __tablename__ = "audit_results"

    audit_id = Column(String, primary_key=True)
    audit_scope = Column(String, nullable=False)  # "full_pipeline" or agent name
    entity_type = Column(String, nullable=False)  # "customer", "agent", "table"
    entity_id = Column(String, nullable=True)  # customer_id or agent name or null
    check_category = Column(String, nullable=False, index=True)  # completeness, schema, consistency, groundedness
    check_name = Column(String, nullable=False)  # specific check identifier
    severity = Column(String, nullable=False, index=True)  # critical, warning, info
    passed = Column(Integer, nullable=False)  # 1=pass, 0=fail
    audit_message = Column(Text, nullable=False)
    expected_value = Column(String, nullable=True)
    actual_value = Column(String, nullable=True)
    affected_rows = Column(Integer, nullable=True)
    audit_version = Column(String, nullable=False)
    computed_at = Column(String, nullable=False)
