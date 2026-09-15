"""Declarative schema checks; missing tables and NULL values produce findings."""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.agents.auditing.definitions import (
    VALID_ACTION_CODES, VALID_RISK_TIERS, VALID_SEGMENT_CODES, VALID_SENTIMENT_LABELS,
)
from app.agents.auditing.results import _make_result, unavailable_result


@dataclass(frozen=True)
class ValueCheck:
    name: str
    table: str
    invalid_condition: str
    expected: str
    severity: str = "critical"
    params: dict[str, Any] = field(default_factory=dict)


def domain_check(name, table, column, values, severity="critical"):
    params = {f"v{i}": value for i, value in enumerate(sorted(values))}
    placeholders = ", ".join(f":{key}" for key in params)
    return ValueCheck(
        name, table, f"{column} IS NULL OR {column} NOT IN ({placeholders})",
        str(sorted(values)), severity, params,
    )


def range_check(name, table, column, low, high, severity="critical"):
    return ValueCheck(
        name, table, f"{column} IS NULL OR {column} < :low OR {column} > :high",
        f"[{low}, {high}]", severity, {"low": low, "high": high},
    )


SCHEMA_CHECKS = (
    domain_check("churn_risk_tier_domain", "churn_predictions", "risk_tier", VALID_RISK_TIERS),
    range_check("churn_probability_range", "churn_predictions", "churn_probability", 0.0, 1.0),
    domain_check("segment_code_domain", "customer_segments", "segment_code", VALID_SEGMENT_CODES),
    range_check("sentiment_score_range", "sentiment_results", "sentiment_score", -1.0, 1.0),
    domain_check("sentiment_label_domain", "sentiment_results", "sentiment_label", VALID_SENTIMENT_LABELS, "warning"),
    domain_check("recommendation_action_code_domain", "recommendations", "action_code", VALID_ACTION_CODES),
    range_check("urgency_score_range", "recommendations", "urgency_score", 0.0, 100.0, "warning"),
    *(ValueCheck(f"{table}_no_null_customer_id", table, "customer_id IS NULL", "no NULL customer IDs")
      for table in ("customer_segments", "churn_predictions", "recommendations")),
    ValueCheck("narrative_no_empty_text", "executive_summaries",
               "summary_text IS NULL OR trim(summary_text) = ''", "non-empty summary text"),
)


def _check_schema_sanity(engine, now: str) -> list[dict[str, Any]]:
    results = []
    with engine.connect() as connection:
        for check in SCHEMA_CHECKS:
            try:
                # Identifiers and predicates come only from the definitions above.
                stats = connection.execute(text(
                    f"SELECT COUNT(*) AS total, "
                    f"SUM(CASE WHEN {check.invalid_condition} THEN 1 ELSE 0 END) AS invalid "
                    f"FROM {check.table}"
                ), check.params).mappings().one()
                total, invalid = stats["total"], stats["invalid"] or 0
                passed = total > 0 and invalid == 0
                results.append(_make_result(
                    check_category="schema", check_name=check.name,
                    severity="info" if passed else check.severity, passed=passed,
                    audit_message=f"{check.table}: {invalid}/{total} rows violate {check.expected}"
                                  if total else f"{check.table} is empty; values could not be checked",
                    now=now, entity_id=check.table, expected_value=check.expected,
                    actual_value=f"{invalid}/{total} invalid", affected_rows=invalid,
                ))
            except SQLAlchemyError:
                results.append(unavailable_result("schema", check.name, now))
    return results
