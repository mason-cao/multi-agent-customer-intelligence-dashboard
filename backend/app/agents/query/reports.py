"""Read-only reports query handlers with bound parameters."""

from typing import Any, Dict, Optional
import pandas as pd
from sqlalchemy import text


def _handle_recommendation_dist(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Recommendation action distribution."""
    df = pd.read_sql(
        text(
            "SELECT action_label, action_category, COUNT(*) as count, "
            "ROUND(AVG(urgency_score), 1) as avg_urgency "
            "FROM recommendations "
            "GROUP BY action_label, action_category "
            "ORDER BY count DESC"
        ),
        engine,
    )
    rows = df.to_dict("records")
    total = sum(r["count"] for r in rows)
    lines = []
    for r in rows:
        pct = r["count"] / total * 100 if total > 0 else 0
        lines.append(
            f"  {r['action_label']}: {r['count']:,} ({pct:.1f}%), "
            f"avg urgency {r['avg_urgency']}"
        )
    answer = f"Recommendation distribution across {total:,} customers:\n" + "\n".join(lines)
    return {
        "answer_text": answer,
        "structured_result": rows,
        "source_tables": "recommendations",
        "row_count": len(rows),
    }

def _handle_priority_actions(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Highest-priority retention actions (immediate + this_week timeframe)."""
    df = pd.read_sql(
        text(
            "SELECT r.action_label, r.action_category, r.target_timeframe, "
            "COUNT(*) as customer_count, "
            "ROUND(AVG(r.urgency_score), 1) as avg_urgency "
            "FROM recommendations r "
            "WHERE r.target_timeframe IN ('immediate', 'this_week') "
            "AND r.action_code != 'monitor_only' "
            "GROUP BY r.action_label, r.action_category, r.target_timeframe "
            "ORDER BY r.target_timeframe ASC, avg_urgency DESC"
        ),
        engine,
    )
    rows = df.to_dict("records")
    total = sum(r["customer_count"] for r in rows)
    answer = f"{total:,} customers need action this week:\n"
    for r in rows:
        answer += (
            f"  {r['action_label']} ({r['target_timeframe']}): "
            f"{r['customer_count']:,} customers, avg urgency {r['avg_urgency']}\n"
        )
    return {
        "answer_text": answer.strip(),
        "structured_result": rows,
        "source_tables": "recommendations",
        "row_count": len(rows),
    }

def _handle_executive_insights(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Current executive narrative summaries."""
    df = pd.read_sql(
        text(
            "SELECT summary_type, title, summary_text, priority "
            "FROM executive_summaries "
            "ORDER BY section_order ASC"
        ),
        engine,
    )
    rows = df.to_dict("records")
    answer = "Executive insights:\n"
    for r in rows:
        # Truncate long summaries for the answer text
        text_preview = r["summary_text"][:200]
        if len(r["summary_text"]) > 200:
            text_preview += "..."
        answer += f"  [{r['summary_type']}] {r['title']}: {text_preview}\n\n"
    return {
        "answer_text": answer.strip(),
        "structured_result": rows,
        "source_tables": "executive_summaries",
        "row_count": len(rows),
    }

def _handle_audit_findings(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Current audit warnings and failures."""
    df = pd.read_sql(
        text(
            "SELECT check_category, check_name, severity, passed, "
            "audit_message, expected_value, actual_value "
            "FROM audit_results "
            "ORDER BY CASE severity "
            "  WHEN 'critical' THEN 1 "
            "  WHEN 'warning' THEN 2 "
            "  ELSE 3 END, "
            "passed ASC"
        ),
        engine,
    )
    total = len(df)
    failures = df[df["passed"] == 0]
    fail_count = len(failures)
    rows = df.to_dict("records")

    if fail_count == 0:
        answer = (
            f"All {total} audit checks passed. "
            f"No warnings or critical failures detected. "
            f"System health: clean."
        )
    else:
        answer = f"{fail_count} audit issue(s) found out of {total} checks:\n"
        for _, r in failures.iterrows():
            answer += f"  [{r['severity'].upper()}] {r['audit_message']}\n"
    return {
        "answer_text": answer.strip(),
        "structured_result": rows,
        "source_tables": "audit_results",
        "row_count": total,
    }

def _handle_ticket_topics(engine, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Most common support ticket topics (by category), with open counts."""
    df = pd.read_sql(
        text(
            "SELECT category, COUNT(*) as count, "
            "SUM(CASE WHEN resolution_status != 'resolved' THEN 1 ELSE 0 END) as open_count "
            "FROM support_tickets "
            "GROUP BY category "
            "ORDER BY count DESC"
        ),
        engine,
    )
    rows = df.to_dict("records")
    total = sum(r["count"] for r in rows)
    answer = f"Top support ticket topics ({total:,} tickets):\n"
    for r in rows:
        pct = r["count"] / total * 100 if total else 0
        answer += (
            f"  {r['category']}: {r['count']:,} ({pct:.1f}%), "
            f"{int(r['open_count'])} still open\n"
        )
    return {
        "answer_text": answer.strip(),
        "structured_result": rows,
        "source_tables": "support_tickets",
        "row_count": len(rows),
    }
