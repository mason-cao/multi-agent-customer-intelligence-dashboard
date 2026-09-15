"""Read-only segments query handlers with bound parameters."""

from typing import Any, Dict, Optional
import pandas as pd
from sqlalchemy import text


def _handle_churn_by_segment(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Avg churn risk per segment, ordered by risk descending."""
    df = pd.read_sql(
        text(
            "SELECT cs.segment_name, "
            "COUNT(*) as customer_count, "
            "ROUND(AVG(cp.churn_probability), 4) as avg_churn_prob, "
            "SUM(CASE WHEN cp.risk_tier = 'Critical' THEN 1 ELSE 0 END) as critical_count, "
            "SUM(CASE WHEN cp.risk_tier = 'High' THEN 1 ELSE 0 END) as high_count "
            "FROM customer_segments cs "
            "JOIN churn_predictions cp ON cs.customer_id = cp.customer_id "
            "GROUP BY cs.segment_name "
            "ORDER BY avg_churn_prob DESC"
        ),
        engine,
    )
    rows = df.to_dict("records")
    top = rows[0] if rows else {}
    answer = (
        f"Highest churn risk segment: {top.get('segment_name', 'N/A')} "
        f"(avg churn probability {top.get('avg_churn_prob', 0):.1%}, "
        f"{top.get('critical_count', 0)} Critical + {top.get('high_count', 0)} High). "
    )
    if len(rows) > 1:
        bottom = rows[-1]
        answer += (
            f"Lowest risk: {bottom['segment_name']} "
            f"(avg {bottom['avg_churn_prob']:.1%})."
        )
    return {
        "answer_text": answer,
        "structured_result": rows,
        "source_tables": "customer_segments,churn_predictions",
        "row_count": len(rows),
    }

def _handle_sentiment_by_segment(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Avg sentiment per segment."""
    df = pd.read_sql(
        text(
            "SELECT cs.segment_name, "
            "COUNT(DISTINCT cs.customer_id) as customer_count, "
            "ROUND(AVG(sr.sentiment_score), 4) as avg_sentiment, "
            "SUM(CASE WHEN sr.sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count, "
            "SUM(CASE WHEN sr.sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count "
            "FROM customer_segments cs "
            "LEFT JOIN sentiment_results sr ON cs.customer_id = sr.customer_id "
            "GROUP BY cs.segment_name "
            "ORDER BY avg_sentiment ASC"
        ),
        engine,
    )
    rows = df.to_dict("records")
    answer = "Sentiment by segment (lowest to highest):\n"
    for r in rows:
        answer += (
            f"  {r['segment_name']}: avg sentiment {r['avg_sentiment']:.3f} "
            f"({r['negative_count']} negative, {r['positive_count']} positive documents)\n"
        )
    return {
        "answer_text": answer.strip(),
        "structured_result": rows,
        "source_tables": "customer_segments,sentiment_results",
        "row_count": len(rows),
    }

def _handle_segment_overview(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Segment sizes with key metrics."""
    df = pd.read_sql(
        text(
            "SELECT cs.segment_name, cs.segment_code, "
            "COUNT(*) as customer_count, "
            "ROUND(AVG(cf.total_revenue), 2) as avg_revenue, "
            "ROUND(AVG(cf.engagement_score), 3) as avg_engagement, "
            "ROUND(AVG(cp.churn_probability), 4) as avg_churn "
            "FROM customer_segments cs "
            "JOIN customer_features cf ON cs.customer_id = cf.customer_id "
            "JOIN churn_predictions cp ON cs.customer_id = cp.customer_id "
            "GROUP BY cs.segment_name, cs.segment_code "
            "ORDER BY customer_count DESC"
        ),
        engine,
    )
    rows = df.to_dict("records")
    total = sum(r["customer_count"] for r in rows)
    answer = f"Customer segments ({total:,} total customers):\n"
    for r in rows:
        pct = r["customer_count"] / total * 100 if total > 0 else 0
        answer += (
            f"  {r['segment_name']}: {r['customer_count']:,} customers ({pct:.1f}%), "
            f"avg revenue ${r['avg_revenue']:,.0f}, "
            f"engagement {r['avg_engagement']:.2f}, "
            f"churn risk {r['avg_churn']:.1%}\n"
        )
    return {
        "answer_text": answer.strip(),
        "structured_result": rows,
        "source_tables": "customer_segments,customer_features,churn_predictions",
        "row_count": len(rows),
    }

def _handle_revenue_by_segment(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Total and average revenue per customer segment, highest total first."""
    df = pd.read_sql(
        text(
            "SELECT cs.segment_name, COUNT(*) as customer_count, "
            "ROUND(SUM(cf.total_revenue), 2) as total_revenue, "
            "ROUND(AVG(cf.total_revenue), 2) as avg_revenue "
            "FROM customer_segments cs "
            "JOIN customer_features cf ON cs.customer_id = cf.customer_id "
            "GROUP BY cs.segment_name "
            "ORDER BY total_revenue DESC"
        ),
        engine,
    )
    rows = df.to_dict("records")
    grand_total = sum((r["total_revenue"] or 0) for r in rows)
    answer = f"Revenue by segment (${grand_total:,.0f} total):\n"
    for r in rows:
        pct = (r["total_revenue"] or 0) / grand_total * 100 if grand_total else 0
        answer += (
            f"  {r['segment_name']}: ${r['total_revenue']:,.0f} ({pct:.1f}%), "
            f"${r['avg_revenue']:,.0f} avg across {r['customer_count']:,} customers\n"
        )
    return {
        "answer_text": answer.strip(),
        "structured_result": rows,
        "source_tables": "customer_segments,customer_features",
        "row_count": len(rows),
    }
