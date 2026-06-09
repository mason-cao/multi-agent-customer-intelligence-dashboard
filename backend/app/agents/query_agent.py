"""
QueryAgent -- controlled natural-language analytics query layer.

Approach: Scored keyword intent classification, routed to whitelisted query
handlers. Every question maps to exactly one named handler with a pre-built
read-only SQL query. User text never composes SQL; the only values that reach
SQL are bound parameters (e.g. top-N limits, a customer search term).

14 intents are supported (see INTENT_REGISTRY), including per-segment churn /
sentiment / revenue, segment + industry breakdowns, top-risk customers,
priority actions, recommendation distribution, executive insights, audit
findings, high-risk-negative actions, a full summary, customer lookup, and
support-ticket topics. Each carries a result_kind (rendering hint) and
suggested follow-ups.

Resolution is deterministic and zero-key by default. When a real LLM provider
is configured, it may OPTIONALLY route an otherwise-unmatched question to one
of these whitelisted intents and extract bound params — it never emits SQL.
The mock / no-key path is unchanged and always available.

Unsupported questions fail safely with an honest explanation of what IS
supported. No arbitrary SQL, no mutations, no unbounded execution.

Inputs:  A question string + all upstream agent output tables (read-only)
Outputs: query_results (one row per query invocation)
Phase:   5 (runs on-demand, after pipeline agents)
"""

import inspect
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import text

from app.agents.base import BaseAgent
from app.utils.privacy import text_log_metadata


# ── Version ───────────────────────────────────────────────────────
QUERY_VERSION = "intent-v2"


# ── Intent definitions ────────────────────────────────────────────
# Each intent declares weighted keyword phrases. classify_intent() scores
# every intent by the weights of the phrases present in the (normalized)
# question and picks the best-scoring one — so rewordings still resolve.
# Registry order is the tie-breaker (earlier wins on equal scores), so more
# specific intents are listed first.
#
# `kw` entries are (phrase, weight). Phrases are matched as substrings of the
# normalized question (lowercased, punctuation -> spaces). `result_kind` tells
# the frontend how to render, `followups` seeds guided next questions, and
# `label`/`example` drive the /suggestions endpoint.

INTENT_REGISTRY: List[Dict[str, Any]] = [
    {
        "intent": "high_risk_negative",
        "kw": [("negative sentiment", 3), ("high risk", 2), ("at risk", 1),
               ("unhappy", 2), ("frustrated", 2), ("negative", 1)],
        "description": "Actions for high-risk negative-sentiment customers",
        "result_kind": "table",
        "label": "High-risk + unhappy",
        "example": "What should we do for high-risk customers with negative sentiment?",
        "followups": ["Show the top 10 highest-risk customers",
                      "How does sentiment vary by segment?"],
    },
    {
        "intent": "customer_lookup",
        "kw": [("look up", 3), ("lookup", 3), ("who is", 3), ("customer named", 3),
               ("show me customer", 3), ("find", 2), ("search", 2), ("profile", 2),
               ("details for", 2), ("customer", 1)],
        "description": "Look up a specific customer by name, company, or ID",
        "result_kind": "table",
        "label": "Find a customer",
        "example": "Look up customer Jordan Lee",
        "followups": ["Show the top 10 highest-risk customers",
                      "Give me an overall customer intelligence summary"],
    },
    {
        "intent": "ticket_topics",
        "kw": [("ticket", 3), ("support topic", 3), ("topics", 2), ("complaint", 2),
               ("support", 1)],
        "description": "Most common support ticket topics",
        "result_kind": "distribution",
        "label": "Support topics",
        "example": "What are the most common support ticket topics?",
        "followups": ["How does sentiment vary by segment?",
                      "What should we prioritize this week?"],
    },
    {
        "intent": "industry_breakdown",
        "kw": [("industry", 3), ("industries", 3), ("vertical", 2), ("sector", 2)],
        "description": "Customer count, revenue, and churn broken down by industry",
        "result_kind": "table",
        "label": "By industry",
        "example": "How does churn vary by industry?",
        "followups": ["Break down revenue by segment",
                      "Which segment has the highest churn risk?"],
    },
    {
        "intent": "audit_findings",
        "kw": [("audit", 3), ("validation", 2), ("data quality", 2),
               ("trust", 1), ("warning", 1)],
        "description": "Current audit warnings and failures",
        "result_kind": "table",
        "label": "Audit findings",
        "example": "Are there any audit warnings?",
        "followups": ["Give me an overall customer intelligence summary",
                      "What are the most important executive insights?"],
    },
    {
        "intent": "executive_insights",
        "kw": [("executive", 3), ("narrative", 2), ("key insight", 2),
               ("what matters", 2), ("headline", 2), ("insight", 1)],
        "description": "Current executive narrative summaries",
        "result_kind": "list",
        "label": "Executive insights",
        "example": "What are the most important executive insights right now?",
        "followups": ["Give me an overall customer intelligence summary",
                      "What should we prioritize this week?"],
    },
    {
        "intent": "priority_actions",
        "kw": [("prioritize", 3), ("this week", 3), ("what should we do", 3),
               ("priority", 2), ("urgent", 2), ("immediate", 2),
               ("focus on", 2), ("act now", 2)],
        "description": "Highest-priority retention actions for this week",
        "result_kind": "table",
        "label": "This week's priorities",
        "example": "What should we prioritize this week?",
        "followups": ["Show the top 10 highest-risk customers",
                      "What actions are most common?"],
    },
    {
        "intent": "recommendation_dist",
        "kw": [("next best action", 3), ("recommend", 2), ("recommendation", 2),
               ("distribution", 2), ("action", 1), ("common", 1), ("frequent", 1)],
        "description": "Recommendation action distribution",
        "result_kind": "distribution",
        "label": "Recommended actions",
        "example": "What actions are most common?",
        "followups": ["What should we prioritize this week?",
                      "Break down revenue by segment"],
    },
    {
        "intent": "segment_overview",
        "kw": [("segment", 2), ("overview", 2), ("how many", 2),
               ("size", 1), ("breakdown", 1)],
        "description": "Segment sizes and key metrics",
        "result_kind": "table",
        "label": "Segment overview",
        "example": "Give me a segment overview",
        "followups": ["Break down revenue by segment",
                      "Which segment has the highest churn risk?"],
    },
    {
        "intent": "revenue_by_segment",
        "kw": [("revenue", 2), ("segment", 2), ("mrr", 1), ("spend", 1)],
        "description": "Total and average revenue per customer segment",
        "result_kind": "distribution",
        "label": "Revenue by segment",
        "example": "Break down revenue by segment",
        "followups": ["Give me a segment overview",
                      "Which segment has the highest churn risk?"],
    },
    {
        "intent": "sentiment_by_segment",
        "kw": [("sentiment", 2), ("segment", 2), ("feel", 1), ("mood", 1), ("happy", 1)],
        "description": "Average sentiment per customer segment",
        "result_kind": "distribution",
        "label": "Sentiment by segment",
        "example": "How does sentiment vary by segment?",
        "followups": ["What are the most common support ticket topics?",
                      "Which segment has the highest churn risk?"],
    },
    {
        "intent": "churn_by_segment",
        "kw": [("segment", 2), ("churn", 1), ("risk", 1), ("retention", 1)],
        "description": "Average churn risk per customer segment",
        "result_kind": "distribution",
        "label": "Churn by segment",
        "example": "Which segment has the highest churn risk?",
        "followups": ["Show the top 10 highest-risk customers",
                      "Break down revenue by segment"],
    },
    {
        "intent": "top_risk_customers",
        "kw": [("riskiest", 3), ("most likely to leave", 3), ("highest risk", 2),
               ("who will churn", 2), ("high risk", 1), ("at risk", 1),
               ("top", 1), ("customer", 1)],
        "description": "Highest-risk customers with recommended actions",
        "result_kind": "table",
        "label": "Highest-risk customers",
        "example": "Show the top 10 highest-risk customers",
        "followups": ["What should we do for high-risk customers with negative sentiment?",
                      "What should we prioritize this week?"],
    },
    {
        "intent": "customer_summary",
        "kw": [("overall", 2), ("summary", 2), ("intelligence", 2), ("dashboard", 2),
               ("everything", 2), ("snapshot", 2), ("at a glance", 2),
               ("how are we doing", 3)],
        "description": "Aggregated intelligence summary across all outputs",
        "result_kind": "metric",
        "label": "Full summary",
        "example": "Give me an overall customer intelligence summary",
        "followups": ["Which segment has the highest churn risk?",
                      "What are the most important executive insights?"],
    },
]

# Per-intent rendering + guidance metadata, keyed by intent for O(1) lookup.
INTENT_META: Dict[str, Dict[str, Any]] = {
    e["intent"]: {
        "result_kind": e["result_kind"],
        "followups": e["followups"],
        "label": e["label"],
        "example": e["example"],
        "description": e["description"],
    }
    for e in INTENT_REGISTRY
}

# Default follow-ups offered when a question is not understood.
UNSUPPORTED_FOLLOWUPS = [
    "Which segment has the highest churn risk?",
    "Show the top 10 highest-risk customers",
    "What should we prioritize this week?",
]

MIN_INTENT_SCORE = 1


def _normalize(question: str) -> str:
    """Lowercase and replace non-alphanumeric runs with single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()


def build_suggestions() -> List[Dict[str, str]]:
    """Guided prompt suggestions derived from the intent registry."""
    return [
        {"intent": e["intent"], "label": e["label"], "example": e["example"]}
        for e in INTENT_REGISTRY
    ]


# ══════════════════════════════════════════════════════════════════
# QUERY HANDLERS — one per intent
# ══════════════════════════════════════════════════════════════════


def _handle_churn_by_segment(engine) -> Dict[str, Any]:
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


def _handle_recommendation_dist(engine) -> Dict[str, Any]:
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


def _handle_sentiment_by_segment(engine) -> Dict[str, Any]:
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


def _handle_segment_overview(engine) -> Dict[str, Any]:
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


def _handle_priority_actions(engine) -> Dict[str, Any]:
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


def _handle_executive_insights(engine) -> Dict[str, Any]:
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


def _handle_audit_findings(engine) -> Dict[str, Any]:
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


def _handle_high_risk_negative(engine) -> Dict[str, Any]:
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
    # Count customers per action
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


def _format_segments(segments: List[Dict]) -> str:
    """Format segment list for answer text."""
    parts = []
    for s in segments:
        parts.append(f"{s['segment_name']} ({s['cnt']})")
    return ", ".join(parts)


def _handle_customer_summary(engine) -> Dict[str, Any]:
    """Aggregated intelligence summary across all outputs."""
    stats = {}

    # Customer count
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


def _extract_lookup_term(question: str) -> str:
    """Pull a likely customer name / company / id out of a lookup question."""
    m = re.search(
        r"(?:customer named|show me customer|look up|lookup|who is|profile of|"
        r"details for|about|for|customer)\s+([A-Za-z0-9'.\- ]{2,60})",
        question,
        re.I,
    )
    if m:
        term = m.group(1).strip()
    else:
        caps = re.findall(r"\b[A-Z][\w'.\-]*(?:\s+[A-Z][\w'.\-]*)*\b", question)
        term = caps[0] if caps else ""
    term = re.sub(r"^(customer|client|account)\s+", "", term, flags=re.I).strip()
    term = re.sub(r"\s+(please|now|today|thanks|thank you).*$", "", term, flags=re.I).strip()
    return term


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


# ── Parameter extraction ──────────────────────────────────────────


def extract_params(question: str, intent: str) -> Dict[str, Any]:
    """Extract safe, bound parameters from a question for the matched intent.

    Returns only scalar values. Callers pass these to handlers as bound SQL
    params — they are never string-interpolated into SQL.
    """
    params: Dict[str, Any] = {}
    if intent == "top_risk_customers":
        m = re.search(r"\b(?:top|first|highest|show me)\s+(\d{1,3})\b", question, re.I)
        if not m:
            m = re.search(r"\b(\d{1,3})\s+(?:customers?|riskiest|accounts?)\b", question, re.I)
        if m:
            params["limit"] = max(1, min(int(m.group(1)), 50))
    elif intent == "customer_lookup":
        term = _extract_lookup_term(question)
        if term:
            params["query"] = term
    return params


def _sanitize_params(raw: Any) -> Dict[str, Any]:
    """Whitelist params returned by LLM routing down to safe scalar types,
    so a model can never smuggle anything into a handler beyond limit/query."""
    params: Dict[str, Any] = {}
    if not isinstance(raw, dict):
        return params
    limit = raw.get("limit")
    if isinstance(limit, bool):
        limit = None
    if isinstance(limit, int) or (isinstance(limit, str) and limit.isdigit()):
        params["limit"] = max(1, min(int(limit), 50))
    query = raw.get("query")
    if isinstance(query, str) and query.strip():
        params["query"] = query.strip()[:80]
    return params


# ── Handler dispatch map ──────────────────────────────────────────
INTENT_HANDLERS = {
    "churn_by_segment": _handle_churn_by_segment,
    "top_risk_customers": _handle_top_risk_customers,
    "recommendation_dist": _handle_recommendation_dist,
    "sentiment_by_segment": _handle_sentiment_by_segment,
    "segment_overview": _handle_segment_overview,
    "priority_actions": _handle_priority_actions,
    "executive_insights": _handle_executive_insights,
    "audit_findings": _handle_audit_findings,
    "high_risk_negative": _handle_high_risk_negative,
    "customer_summary": _handle_customer_summary,
    "revenue_by_segment": _handle_revenue_by_segment,
    "industry_breakdown": _handle_industry_breakdown,
    "customer_lookup": _handle_customer_lookup,
    "ticket_topics": _handle_ticket_topics,
}

# Columns persisted to the query_results table (response-only fields like
# result_kind / suggested_followups are intentionally excluded).
QUERY_RESULT_COLUMNS = [
    "query_id", "original_question", "matched_intent", "query_status",
    "answer_text", "structured_result", "source_tables", "row_count",
    "execution_ms", "query_version", "executed_at",
]


def _call_handler(handler, engine, params: Optional[Dict[str, Any]]):
    """Invoke a handler, passing params only to handlers that accept them.
    Keeps older single-arg handlers working without signature churn."""
    if len(inspect.signature(handler).parameters) >= 2:
        return handler(engine, params)
    return handler(engine)

# ── Supported intents list (for unsupported message) ──────────────
SUPPORTED_DESCRIPTIONS = [entry["description"] for entry in INTENT_REGISTRY]


# ══════════════════════════════════════════════════════════════════
# INTENT CLASSIFIER
# ══════════════════════════════════════════════════════════════════


def classify_intent(question: str) -> Tuple[str, str]:
    """
    Classify a question into a supported intent via keyword scoring.

    Each intent's score is the sum of the weights of its keyword phrases that
    appear in the normalized question; the highest-scoring intent wins, with
    registry order breaking ties (earlier entries win). This makes rewordings
    resolve to the best match rather than the first regex hit.

    Returns (intent_name, intent_description), or ("unsupported", ...) when no
    intent clears MIN_INTENT_SCORE.
    """
    q = _normalize(question)

    best_intent: Optional[str] = None
    best_score = 0
    best_desc = ""
    for entry in INTENT_REGISTRY:
        score = sum(weight for phrase, weight in entry["kw"] if phrase in q)
        if score > best_score:
            best_score = score
            best_intent = entry["intent"]
            best_desc = entry["description"]

    if best_intent is None or best_score < MIN_INTENT_SCORE:
        return "unsupported", "Question does not match any supported query type"
    return best_intent, best_desc


# ══════════════════════════════════════════════════════════════════
# AGENT CLASS
# ══════════════════════════════════════════════════════════════════


class QueryAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "query"

    # ──────────────────────────────────────────────────────────────
    # Main entry — batch mode for BaseAgent compatibility
    # ──────────────────────────────────────────────────────────────

    def run(self, db) -> Dict[str, Any]:
        """
        Run a batch of demo questions to populate query_results.

        This satisfies the BaseAgent interface. For single-question use,
        call answer_question() directly.
        """
        engine = db.get_bind()

        demo_questions = [
            "Which segment has the highest churn risk?",
            "Show the top 10 highest-risk customers.",
            "What actions are most common?",
            "How does sentiment vary by segment?",
            "Give me a segment overview.",
            "What should we prioritize this week?",
            "What are the most important executive insights right now?",
            "Are there any audit warnings?",
            "What actions are recommended for high-risk negative-sentiment customers?",
            "Give me an overall customer intelligence summary.",
            "What is the meaning of life?",
        ]

        results = []
        for q in demo_questions:
            result = self.answer_question(q, engine)
            results.append(result)

        # Write all results to query_results table (DELETE + INSERT preserves ORM
        # constraints). Only persisted columns are written — response-only fields
        # (result_kind, suggested_followups) are dropped here.
        df = pd.DataFrame(results)[QUERY_RESULT_COLUMNS]
        db.execute(text("DELETE FROM query_results"))
        db.commit()
        df.to_sql("query_results", engine, if_exists="append", index=False)
        self._logger.info("query_results_written", rows=len(df))

        success = sum(1 for r in results if r["query_status"] == "success")
        unsupported = sum(1 for r in results if r["query_status"] == "unsupported")

        return {
            "status": "completed",
            "rows_affected": len(results),
            "tokens_used": 0,
            "model_used": None,
            "query_summary": {
                "query_version": QUERY_VERSION,
                "total_queries": len(results),
                "successful": success,
                "unsupported": unsupported,
                "supported_intents": len(INTENT_HANDLERS),
            },
        }

    # ──────────────────────────────────────────────────────────────
    # Single-question interface
    # ──────────────────────────────────────────────────────────────

    def answer_question(
        self, question: str, engine, llm_client=None
    ) -> Dict[str, Any]:
        """
        Answer a single natural-language question.

        Resolution order:
          1. Deterministic keyword classifier (always runs — mock-first).
          2. Optional LLM routing — only when a *real* provider is supplied and
             the deterministic classifier matched nothing. The model may only
             choose an intent from the whitelist and extract simple params; it
             never emits SQL. With no key (mock), this step is skipped.

        Returns a dict for the API response; the persisted-column subset is what
        run() writes to query_results.
        """
        now = datetime.now(timezone.utc).isoformat()
        start = time.time()

        intent, description = classify_intent(question)
        params = extract_params(question, intent) if intent != "unsupported" else {}

        if (
            intent == "unsupported"
            and llm_client is not None
            and not getattr(llm_client, "is_mock", True)
        ):
            routed = llm_client.route_query(question, list(INTENT_HANDLERS.keys()))
            if routed and routed.get("intent") in INTENT_HANDLERS:
                intent = routed["intent"]
                params = _sanitize_params(routed.get("params"))

        if intent == "unsupported":
            elapsed_ms = int((time.time() - start) * 1000)
            supported_list = "\n".join(f"  - {d}" for d in SUPPORTED_DESCRIPTIONS)
            return {
                "query_id": str(uuid.uuid4()),
                "original_question": question,
                "matched_intent": "unsupported",
                "query_status": "unsupported",
                "answer_text": (
                    f"I can't answer that one yet. I currently understand these question types:\n"
                    f"{supported_list}\n\n"
                    f"Try one of the suggested questions below."
                ),
                "structured_result": json.dumps({"supported_intents": SUPPORTED_DESCRIPTIONS}),
                "source_tables": None,
                "row_count": None,
                "execution_ms": elapsed_ms,
                "query_version": QUERY_VERSION,
                "executed_at": now,
                "result_kind": "text",
                "suggested_followups": list(UNSUPPORTED_FOLLOWUPS),
            }

        meta = INTENT_META.get(intent, {})
        handler = INTENT_HANDLERS[intent]
        try:
            result = _call_handler(handler, engine, params)
            elapsed_ms = int((time.time() - start) * 1000)

            self._logger.info(
                "query_answered",
                intent=intent,
                **text_log_metadata(question),
                row_count=result.get("row_count"),
                elapsed_ms=elapsed_ms,
            )

            return {
                "query_id": str(uuid.uuid4()),
                "original_question": question,
                "matched_intent": intent,
                "query_status": "success",
                "answer_text": result["answer_text"],
                "structured_result": json.dumps(
                    result["structured_result"], default=str
                ),
                "source_tables": result["source_tables"],
                "row_count": result.get("row_count"),
                "execution_ms": elapsed_ms,
                "query_version": QUERY_VERSION,
                "executed_at": now,
                "result_kind": result.get("result_kind", meta.get("result_kind", "table")),
                "suggested_followups": list(meta.get("followups", UNSUPPORTED_FOLLOWUPS)),
            }
        except Exception as exc:
            elapsed_ms = int((time.time() - start) * 1000)
            self._logger.error(
                "query_failed",
                intent=intent,
                error_type=type(exc).__name__,
            )
            return {
                "query_id": str(uuid.uuid4()),
                "original_question": question,
                "matched_intent": intent,
                "query_status": "error",
                "answer_text": (
                    "We couldn't complete that query safely. "
                    "Try a suggested question or refresh the workspace."
                ),
                "structured_result": None,
                "source_tables": None,
                "row_count": None,
                "execution_ms": elapsed_ms,
                "query_version": QUERY_VERSION,
                "executed_at": now,
                "result_kind": "text",
                "suggested_followups": list(meta.get("followups", UNSUPPORTED_FOLLOWUPS)),
            }

    # ──────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────

    def validate_output(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        rows = output.get("rows_affected", 0)
        if rows == 0:
            errors.append("No query results were produced")

        summary = output.get("query_summary", {})
        successful = summary.get("successful", 0)
        if successful == 0:
            errors.append("No queries resolved successfully")

        total = summary.get("total_queries", 0)
        if total > 0 and successful / total < 0.5:
            errors.append(
                f"Only {successful}/{total} queries successful, expected >50%"
            )

        return (len(errors) == 0, errors)
