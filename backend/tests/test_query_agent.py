"""Tests for deterministic query agent handlers."""

from sqlalchemy import create_engine, text

from app.agents.query_agent import (
    QueryAgent,
    _handle_customer_lookup,
    _handle_industry_breakdown,
    _handle_revenue_by_segment,
    _handle_ticket_topics,
    _handle_top_risk_customers,
    classify_intent,
    extract_params,
)
from app.services.llm_client import LLMClient


def _top_risk_engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text("CREATE TABLE customers (customer_id TEXT, name TEXT, company TEXT, industry TEXT, plan_tier TEXT)")
        )
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
                "('CUST-001', 'Jordan Lee', 'Northstar Labs', 'Technology', 'enterprise'), "
                "('CUST-002', 'Avery Chen', 'HelioWorks', 'Finance', 'growth')"
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
    return engine


def test_top_risk_customers_answer_uses_customer_names():
    engine = _top_risk_engine()
    result = _handle_top_risk_customers(engine)

    assert "Jordan Lee at Northstar Labs" in result["answer_text"]
    assert "Avery Chen at HelioWorks" in result["answer_text"]
    assert "CUST-001:" not in result["answer_text"]
    assert result["source_tables"].startswith("customers,")
    assert result["structured_result"][0]["name"] == "Jordan Lee"


def test_top_risk_customers_respects_limit_param():
    engine = _top_risk_engine()
    result = _handle_top_risk_customers(engine, {"limit": 1})
    assert result["row_count"] == 1
    assert len(result["structured_result"]) == 1
    # Highest churn probability first
    assert result["structured_result"][0]["name"] == "Jordan Lee"


# ── Parameter extraction ──────────────────────────────────────────


def test_extract_params_reads_top_n():
    assert extract_params("show the top 5 riskiest customers", "top_risk_customers") == {"limit": 5}


def test_extract_params_no_number_returns_empty():
    assert extract_params("show the riskiest customers", "top_risk_customers") == {}


def test_extract_params_customer_lookup_term():
    params = extract_params("look up customer Jordan Lee", "customer_lookup")
    assert "Jordan Lee" in params.get("query", "")


# ── Scored intent matching (rewordings) ───────────────────────────


def test_classify_revenue_by_segment_from_reworded():
    intent, _ = classify_intent("break down revenue across customer segments")
    assert intent == "revenue_by_segment"


def test_classify_industry_breakdown():
    intent, _ = classify_intent("how does churn vary by industry?")
    assert intent == "industry_breakdown"


def test_classify_customer_lookup():
    intent, _ = classify_intent("look up customer Jordan Lee")
    assert intent == "customer_lookup"


def test_classify_ticket_topics():
    intent, _ = classify_intent("what are the most common support ticket topics?")
    assert intent == "ticket_topics"


def test_classify_unsupported_stays_unsupported():
    intent, _ = classify_intent("what is the meaning of life")
    assert intent == "unsupported"


# ── New handlers ──────────────────────────────────────────────────


def test_revenue_by_segment_handler():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE customer_segments (customer_id TEXT, segment_name TEXT)"))
        conn.execute(text("CREATE TABLE customer_features (customer_id TEXT, total_revenue REAL)"))
        conn.execute(
            text(
                "INSERT INTO customer_segments VALUES "
                "('c1','Champions'),('c2','Champions'),('c3','At Risk')"
            )
        )
        conn.execute(
            text("INSERT INTO customer_features VALUES ('c1',1000),('c2',3000),('c3',500)")
        )
    result = _handle_revenue_by_segment(engine)
    rows = {r["segment_name"]: r for r in result["structured_result"]}
    assert rows["Champions"]["total_revenue"] == 4000
    assert rows["At Risk"]["total_revenue"] == 500
    # Ordered by total revenue descending
    assert result["structured_result"][0]["segment_name"] == "Champions"


def test_industry_breakdown_handler():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE customers (customer_id TEXT, industry TEXT)"))
        conn.execute(text("CREATE TABLE customer_features (customer_id TEXT, total_revenue REAL)"))
        conn.execute(text("CREATE TABLE churn_predictions (customer_id TEXT, churn_probability REAL)"))
        conn.execute(
            text(
                "INSERT INTO customers VALUES "
                "('c1','Technology'),('c2','Technology'),('c3','Finance')"
            )
        )
        conn.execute(
            text("INSERT INTO customer_features VALUES ('c1',1000),('c2',2000),('c3',500)")
        )
        conn.execute(
            text("INSERT INTO churn_predictions VALUES ('c1',0.1),('c2',0.3),('c3',0.5)")
        )
    result = _handle_industry_breakdown(engine)
    rows = {r["industry"]: r for r in result["structured_result"]}
    assert rows["Technology"]["customer_count"] == 2
    assert rows["Finance"]["customer_count"] == 1


def test_customer_lookup_handler_finds_by_name():
    engine = _top_risk_engine()
    # Add the tables customer_lookup also reads
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE customer_features (customer_id TEXT, total_revenue REAL, engagement_score REAL)"))
        conn.execute(text("INSERT INTO customer_features VALUES ('CUST-001', 1200.0, 0.4), ('CUST-002', 800.0, 0.7)"))
    result = _handle_customer_lookup(engine, {"query": "Jordan"})
    assert result["row_count"] >= 1
    assert any(r["name"] == "Jordan Lee" for r in result["structured_result"])


def test_customer_lookup_uses_bound_param_safe_against_injection():
    engine = _top_risk_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE customer_features (customer_id TEXT, total_revenue REAL, engagement_score REAL)"))
        conn.execute(text("INSERT INTO customer_features VALUES ('CUST-001', 1200.0, 0.4)"))
    # An injection-style term must not error or drop tables; it simply matches nothing.
    result = _handle_customer_lookup(engine, {"query": "'; DROP TABLE customers;--"})
    assert result["row_count"] == 0
    # Table still exists
    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar()
    assert count == 2


def test_ticket_topics_handler():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE support_tickets ("
                "ticket_id TEXT, category TEXT, resolution_status TEXT"
                ")"
            )
        )
        conn.execute(
            text(
                "INSERT INTO support_tickets VALUES "
                "('t1','billing','resolved'),('t2','billing','open'),('t3','performance','resolved')"
            )
        )
    result = _handle_ticket_topics(engine)
    rows = {r["category"]: r for r in result["structured_result"]}
    assert rows["billing"]["count"] == 2
    assert result["structured_result"][0]["category"] == "billing"  # most common first


# ── Response envelope: result_kind + suggested_followups ──────────


def test_answer_question_includes_result_kind_and_followups():
    engine = create_engine("sqlite:///:memory:")
    agent = QueryAgent()
    out = agent.answer_question("what is the meaning of life", engine)
    assert out["query_status"] == "unsupported"
    assert "result_kind" in out
    assert "suggested_followups" in out
    assert isinstance(out["suggested_followups"], list)


def test_answer_question_supported_has_result_kind():
    engine = _top_risk_engine()
    agent = QueryAgent()
    out = agent.answer_question("show the top 2 riskiest customers", engine)
    assert out["query_status"] == "success"
    assert out["matched_intent"] == "top_risk_customers"
    assert out["result_kind"] in {"metric", "list", "table", "distribution", "text"}


# ── Optional LLM routing falls back cleanly with no key ───────────


def test_llm_route_query_mock_returns_none():
    client = LLMClient(mock=True)
    # Mock mode performs no routing — deterministic engine stays authoritative.
    assert client.route_query("anything at all", ["top_risk_customers"]) is None
