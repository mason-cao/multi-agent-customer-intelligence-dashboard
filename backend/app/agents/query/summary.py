"""Read-only summary query handlers with bound parameters."""

from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import text


def _format_segments(segments: List[Dict]) -> str:
    """Format segment list for answer text."""
    parts = []
    for s in segments:
        parts.append(f"{s['segment_name']} ({s['cnt']})")
    return ", ".join(parts)

def _handle_customer_summary(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Aggregated intelligence summary across all outputs."""
    stats = {}

    stats["total_customers"] = int(pd.read_sql(
        text("SELECT COUNT(*) as cnt FROM customer_features"), engine
    )["cnt"].iloc[0])

    # Revenue
    rev = pd.read_sql(
        text("SELECT SUM(total_revenue) as total, AVG(total_revenue) as avg FROM customer_features"),
        engine,
    )
    stats["total_revenue"] = round(float(rev["total"].iloc[0]), 2)
    stats["avg_revenue"] = round(float(rev["avg"].iloc[0]), 2)

    # Churn
    churn = pd.read_sql(
        text(
            "SELECT ROUND(AVG(churn_probability), 4) as avg_churn, "
            "SUM(CASE WHEN risk_tier = 'Critical' THEN 1 ELSE 0 END) as critical, "
            "SUM(CASE WHEN risk_tier = 'High' THEN 1 ELSE 0 END) as high "
            "FROM churn_predictions"
        ),
        engine,
    )
    stats["avg_churn"] = float(churn["avg_churn"].iloc[0])
    stats["critical_churn"] = int(churn["critical"].iloc[0])
    stats["high_churn"] = int(churn["high"].iloc[0])

    # Sentiment
    sent = pd.read_sql(
        text("SELECT ROUND(AVG(sentiment_score), 4) as avg FROM sentiment_results"),
        engine,
    )
    stats["avg_sentiment"] = float(sent["avg"].iloc[0])

    # Recommendations
    rec = pd.read_sql(
        text(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN target_timeframe = 'immediate' THEN 1 ELSE 0 END) as immediate, "
            "ROUND(AVG(urgency_score), 1) as avg_urgency "
            "FROM recommendations"
        ),
        engine,
    )
    stats["total_recommendations"] = int(rec["total"].iloc[0])
    stats["immediate_actions"] = int(rec["immediate"].iloc[0])
    stats["avg_urgency"] = float(rec["avg_urgency"].iloc[0])

    # Segments
    segs = pd.read_sql(
        text("SELECT segment_name, COUNT(*) as cnt FROM customer_segments GROUP BY segment_name ORDER BY cnt DESC"),
        engine,
    )
    stats["segments"] = segs.to_dict("records")

    # Audit
    audit = pd.read_sql(
        text("SELECT COUNT(*) as total, SUM(CASE WHEN passed = 0 THEN 1 ELSE 0 END) as failures FROM audit_results"),
        engine,
    )
    stats["audit_checks"] = int(audit["total"].iloc[0])
    stats["audit_failures"] = int(audit["failures"].iloc[0])

    answer = (
        f"Customer Intelligence Summary ({stats['total_customers']:,} customers):\n"
        f"  Revenue: ${stats['total_revenue']:,.0f} total, ${stats['avg_revenue']:,.0f} avg per customer\n"
        f"  Churn: {stats['avg_churn']:.1%} avg probability, "
        f"{stats['critical_churn']} Critical + {stats['high_churn']} High risk\n"
        f"  Sentiment: {stats['avg_sentiment']:.3f} avg score\n"
        f"  Actions: {stats['immediate_actions']} immediate, "
        f"{stats['avg_urgency']} avg urgency across {stats['total_recommendations']:,} recommendations\n"
        f"  Audit: {stats['audit_checks']} checks, {stats['audit_failures']} failures\n"
        f"  Segments: {_format_segments(stats['segments'])}"
    )
    return {
        "answer_text": answer,
        "structured_result": stats,
        "source_tables": "customer_features,churn_predictions,sentiment_results,recommendations,customer_segments,audit_results",
        "row_count": stats["total_customers"],
    }
