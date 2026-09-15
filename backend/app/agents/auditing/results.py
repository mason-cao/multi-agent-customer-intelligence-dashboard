"""Build persisted audit findings."""

import uuid
from typing import Any, Dict
from app.agents.auditing.definitions import AUDIT_VERSION


def _make_result(
    check_category: str,
    check_name: str,
    severity: str,
    passed: bool,
    audit_message: str,
    now: str,
    entity_type: str = "table",
    entity_id: str = None,
    expected_value: str = None,
    actual_value: str = None,
    affected_rows: int = None,
) -> Dict[str, Any]:
    """Build a single audit result row."""
    return {
        "audit_id": str(uuid.uuid4()),
        "audit_scope": "full_pipeline",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "check_category": check_category,
        "check_name": check_name,
        "severity": severity,
        "passed": 1 if passed else 0,
        "audit_message": audit_message,
        "expected_value": expected_value,
        "actual_value": actual_value,
        "affected_rows": affected_rows,
        "audit_version": AUDIT_VERSION,
        "computed_at": now,
    }


def unavailable_result(category: str, name: str, now: str) -> Dict[str, Any]:
    return _make_result(
        check_category=category, check_name=name, severity="critical",
        passed=False, audit_message="Required data is missing or could not be checked.",
        now=now,
    )
