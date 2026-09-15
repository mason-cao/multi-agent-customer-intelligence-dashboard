"""Read-only customers query handlers with bound parameters."""

from typing import Any, Dict, Optional
import pandas as pd
from sqlalchemy import text


def _handle_top_risk_customers(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Highest-risk customers with their recommended actions. `params['limit']`
    (1-50, default 10) controls how many are returned, bound as a SQL param."""
    limit = int((params or {}).get("limit") or 10)
    limit = max(1, min(limit, 50))
    df = pd.read_sql(
        text(
            "SELECT cp.customer_id, c.name, c.company, cp.churn_probability, cp.risk_tier, "
            "cp.top_risk_factors, "
            "r.action_label, r.urgency_score, r.primary_driver, "
            "cs.segment_name "
            "FROM churn_predictions cp "
            "JOIN customers c ON cp.customer_id = c.customer_id "
            "JOIN recommendations r ON cp.customer_id = r.customer_id "
            "JOIN customer_segments cs ON cp.customer_id = cs.customer_id "
            "ORDER BY cp.churn_probability DESC "
            "LIMIT :limit"
        ),
        engine,
        params={"limit": limit},
    )
    rows = df.to_dict("records")
    if not rows:
        return {
            "answer_text": "No high-risk customers are available in this workspace yet.",
            "structured_result": [],
            "source_tables": "customers,churn_predictions,recommendations,customer_segments",
            "row_count": 0,
        }

    answer = f"Top {len(rows)} highest-risk customers by churn probability:\n"
    for i, r in enumerate(rows, 1):
        answer += (
            f"  {i}. {r['name']} at {r['company']}: "
            f"{r['churn_probability']:.1%} churn risk ({r['risk_tier']}). "
            f"Recommended action: {r['action_label']}. "
            f"Segment: {r['segment_name']}.\n"
        )
    return {
        "answer_text": answer.strip(),
        "structured_result": rows,
        "source_tables": "customers,churn_predictions,recommendations,customer_segments",
        "row_count": len(rows),
    }

def _handle_high_risk_negative(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Actions for high-risk + negative-sentiment customers."""
    df = pd.read_sql(
        text(
            "SELECT r.customer_id, r.action_label, r.urgency_score, "
            "r.primary_driver, cp.churn_probability, cp.risk_tier, "
            "cs.segment_name, "
            "ROUND(AVG(sr.sentiment_score), 3) as avg_sentiment "
            "FROM recommendations r "
            "JOIN churn_predictions cp ON r.customer_id = cp.customer_id "
            "JOIN customer_segments cs ON r.customer_id = cs.customer_id "
            "LEFT JOIN sentiment_results sr ON r.customer_id = sr.customer_id "
            "WHERE cp.risk_tier IN ('Critical', 'High') "
            "GROUP BY r.customer_id, r.action_label, r.urgency_score, "
            "r.primary_driver, cp.churn_probability, cp.risk_tier, cs.segment_name "
            "HAVING avg_sentiment < -0.15 "
            "ORDER BY cp.churn_probability DESC "
            "LIMIT 15"
        ),
        engine,
    )
    rows = df.to_dict("records")
    # Also get action distribution for this group (one row per customer)
    dist = pd.read_sql(
        text(
            "SELECT r.customer_id, r.action_label "
            "FROM recommendations r "
            "JOIN churn_predictions cp ON r.customer_id = cp.customer_id "
            "LEFT JOIN sentiment_results sr ON r.customer_id = sr.customer_id "
            "WHERE cp.risk_tier IN ('Critical', 'High') "
            "GROUP BY r.customer_id, r.action_label "
            "HAVING AVG(sr.sentiment_score) < -0.15"
        ),
        engine,
    )

    action_counts = dist.groupby("action_label").size().sort_values(ascending=False)
    total_affected = len(dist)

    answer = f"{total_affected} high-risk customers with negative sentiment:\n"
    answer += "Action breakdown:\n"
    for action, cnt in action_counts.items():
        answer += f"  {action}: {int(cnt)} customers\n"
    if rows:
        answer += f"\nTop {len(rows)} by churn probability:\n"
        for i, r in enumerate(rows[:5], 1):
            answer += (
                f"  {i}. {r['customer_id']}: {r['churn_probability']:.1%} churn, "
                f"sentiment {r['avg_sentiment']:.3f}, "
                f"action: {r['action_label']}\n"
            )
    return {
        "answer_text": answer.strip(),
        "structured_result": {"top_customers": rows, "action_distribution": action_counts.to_dict()},
        "source_tables": "recommendations,churn_predictions,sentiment_results,customer_segments",
        "row_count": total_affected,
    }

def _handle_customer_lookup(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Look up specific customers by name/company/id. The search term is always
    passed as a bound parameter (never interpolated into SQL)."""
    src = "customers,customer_features,churn_predictions,customer_segments"
    term = ((params or {}).get("query") or "").strip()
    if not term:
        return {
            "answer_text": "Tell me a customer name, company, or ID to look up.",
            "structured_result": [],
            "source_tables": src,
            "row_count": 0,
        }
    df = pd.read_sql(
        text(
            "SELECT c.customer_id, c.name, c.company, c.industry, c.plan_tier, "
            "cf.total_revenue, cf.engagement_score, "
            "cp.churn_probability, cp.risk_tier, cs.segment_name "
            "FROM customers c "
            "LEFT JOIN customer_features cf ON c.customer_id = cf.customer_id "
            "LEFT JOIN churn_predictions cp ON c.customer_id = cp.customer_id "
            "LEFT JOIN customer_segments cs ON c.customer_id = cs.customer_id "
            "WHERE c.name LIKE :like OR c.company LIKE :like OR c.customer_id = :exact "
            "ORDER BY cp.churn_probability DESC "
            "LIMIT 10"
        ),
        engine,
        params={"like": f"%{term}%", "exact": term},
    )
    rows = df.to_dict("records")
    if not rows:
        return {
            "answer_text": f"No customer matched '{term}'.",
            "structured_result": [],
            "source_tables": src,
            "row_count": 0,
        }
    answer = f"{len(rows)} match(es) for '{term}':\n"
    for r in rows:
        churn = r.get("churn_probability")
        churn_txt = (
            f"{churn:.1%} churn ({r.get('risk_tier')})"
            if churn is not None
            else "no churn score"
        )
        answer += (
            f"  {r['name']} at {r['company']} — "
            f"{r.get('segment_name') or 'unsegmented'}, {churn_txt}\n"
        )
    return {
        "answer_text": answer.strip(),
        "structured_result": rows,
        "source_tables": src,
        "row_count": len(rows),
    }

def _handle_industry_breakdown(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Customer count, average revenue, and average churn per industry."""
    df = pd.read_sql(
        text(
            "SELECT c.industry, COUNT(*) as customer_count, "
            "ROUND(AVG(cf.total_revenue), 2) as avg_revenue, "
            "ROUND(AVG(cp.churn_probability), 4) as avg_churn "
            "FROM customers c "
            "LEFT JOIN customer_features cf ON c.customer_id = cf.customer_id "
            "LEFT JOIN churn_predictions cp ON c.customer_id = cp.customer_id "
            "GROUP BY c.industry "
            "ORDER BY customer_count DESC"
        ),
        engine,
    )
    rows = df.to_dict("records")
    answer = "Customers by industry:\n"
    for r in rows:
        answer += (
            f"  {r['industry']}: {r['customer_count']:,} customers, "
            f"${(r['avg_revenue'] or 0):,.0f} avg revenue, "
            f"{(r['avg_churn'] or 0):.1%} avg churn\n"
        )
    return {
        "answer_text": answer.strip(),
        "structured_result": rows,
        "source_tables": "customers,customer_features,churn_predictions",
        "row_count": len(rows),
    }
