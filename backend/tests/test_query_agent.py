"""Tests for deterministic query agent handlers."""

from sqlalchemy import create_engine, text

from app.agents.query_agent import _handle_top_risk_customers


def test_top_risk_customers_answer_uses_customer_names():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE customers (customer_id TEXT, name TEXT, company TEXT)"))
        conn.execute(
            text(
                "CREATE TABLE churn_predictions ("
                "customer_id TEXT, churn_probability REAL, risk_tier TEXT, top_risk_factors TEXT"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE recommendations ("
                "customer_id TEXT, action_label TEXT, urgency_score REAL, primary_driver TEXT"
                ")"
            )
        )
        conn.execute(text("CREATE TABLE customer_segments (customer_id TEXT, segment_name TEXT)"))
        conn.execute(
            text(
                "INSERT INTO customers VALUES "
                "('CUST-001', 'Jordan Lee', 'Northstar Labs'), "
                "('CUST-002', 'Avery Chen', 'HelioWorks')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO churn_predictions VALUES "
                "('CUST-001', 0.91, 'Critical', '[]'), "
                "('CUST-002', 0.84, 'High', '[]')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO recommendations VALUES "
                "('CUST-001', 'Schedule executive save call', 94.0, 'low engagement'), "
                "('CUST-002', 'Resolve support escalation', 88.0, 'negative sentiment')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO customer_segments VALUES "
                "('CUST-001', 'At Risk'), "
                "('CUST-002', 'Loyal')"
            )
        )

    result = _handle_top_risk_customers(engine)

    assert "Jordan Lee at Northstar Labs" in result["answer_text"]
    assert "Avery Chen at HelioWorks" in result["answer_text"]
    assert "CUST-001:" not in result["answer_text"]
    assert result["source_tables"].startswith("customers,")
    assert result["structured_result"][0]["name"] == "Jordan Lee"
