"""Audit checks must expose invalid and unavailable data."""

import pytest
from sqlalchemy import create_engine, text

from app.agents.auditing.completeness import _check_completeness
from app.agents.auditing.consistency import _check_consistency
from app.agents.auditing.schema_sanity import SCHEMA_CHECKS, _check_schema_sanity


def test_missing_schema_tables_produce_failures_for_every_check():
    engine = create_engine("sqlite:///:memory:")
    findings = _check_schema_sanity(engine, "now")
    assert len(findings) == len(SCHEMA_CHECKS)
    assert all(finding["passed"] == 0 for finding in findings)
    engine.dispose()


@pytest.mark.parametrize("probability", [None, -0.1, 1.1])
def test_null_and_out_of_range_probabilities_are_reported(probability):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE churn_predictions (customer_id TEXT, risk_tier TEXT, churn_probability REAL)"))
        connection.execute(text("INSERT INTO churn_predictions VALUES ('c1', 'High', :probability)"), {"probability": probability})
    findings = {row["check_name"]: row for row in _check_schema_sanity(engine, "now")}
    assert findings["churn_probability_range"]["passed"] == 0
    assert findings["churn_probability_range"]["affected_rows"] == 1
    engine.dispose()


def test_duplicate_and_orphan_ids_do_not_count_as_customer_coverage():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE customers (customer_id TEXT)"))
        connection.execute(text("CREATE TABLE customer_features (customer_id TEXT)"))
        connection.execute(text("INSERT INTO customers VALUES ('c1'), ('c2')"))
        connection.execute(text("INSERT INTO customer_features VALUES ('c1'), ('c1'), ('orphan')"))
    findings = {row["check_name"]: row for row in _check_completeness(engine, "now")}
    assert findings["customer_features_cover_customers"]["passed"] == 0
    assert findings["customer_features_cover_customers"]["actual_value"] == "1"
    engine.dispose()


def test_missing_consistency_inputs_are_not_silently_skipped():
    engine = create_engine("sqlite:///:memory:")
    findings = _check_consistency(engine, "now")
    assert len(findings) == 7
    assert all(finding["passed"] == 0 for finding in findings)
    engine.dispose()
