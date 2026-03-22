from typing import Optional

from pydantic import BaseModel


class AuditResultItem(BaseModel):
    audit_id: str
    audit_scope: str
    entity_type: str
    entity_id: Optional[str] = None
    check_category: str
    check_name: str
    severity: str
    passed: bool
    audit_message: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    affected_rows: Optional[int] = None
    audit_version: str
    computed_at: str


class AuditSummary(BaseModel):
    total_checks: int
    passed: int
    failed: int
    critical_failures: int
    warnings: int
    check_categories: dict
    severity_distribution: dict
