"""
QueryAgent -- controlled natural-language analytics query layer.

Approach: Intent classification via keyword matching, routed to whitelisted
query handlers. Every question maps to exactly one named handler with a
pre-built read-only SQL query. No user text ever composes SQL.

Supported intents (10):
  1. churn_by_segment       — Avg churn risk per segment
  2. top_risk_customers     — Highest-risk customers with their actions
  3. recommendation_dist    — Recommendation action distribution
  4. sentiment_by_segment   — Avg sentiment per segment
  5. segment_overview       — Segment sizes and key metrics
  6. priority_actions       — Highest-priority retention actions this week
  7. executive_insights     — Current executive narrative summaries
  8. audit_findings         — Current audit warnings and failures
  9. high_risk_negative     — High-risk + negative-sentiment customer actions
  10. customer_summary      — Aggregated intelligence summary across all outputs

Unsupported questions fail safely with an honest explanation of what IS
supported. No arbitrary SQL, no mutations, no unbounded execution.

No LLM calls for core resolution. Fully deterministic. Zero API keys required.

Inputs:  A question string + all upstream agent output tables (read-only)
Outputs: query_results (one row per query invocation)
Phase:   5 (runs on-demand, after pipeline agents)
"""

import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import text

from app.agents.base import BaseAgent


# ── Version ───────────────────────────────────────────────────────
QUERY_VERSION = "intent-v1"


# ── Intent definitions ────────────────────────────────────────────
# Each intent has keyword patterns (any match triggers) and a description
# for traceability. Patterns are evaluated in order; first match wins.

INTENT_REGISTRY: List[Dict[str, Any]] = [
    {
        "intent": "audit_findings",
        "patterns": [
            r"\baudit\b",
            r"\bvalidation\b.*\b(result|finding|warning|fail)",
            r"\btrust\b.*\b(check|score|result)",
        ],
        "description": "Retrieve current audit warnings and failures",
    },
    {
        "intent": "executive_insights",
        "patterns": [
            r"\bexecutive\b",
            r"\bnarrative\b",
            r"\binsight[s]?\b.*\b(important|key|main|top|now|current)",
            r"\b(important|key|main)\b.*\binsight",
            r"\bsummar(y|ize)\b.*\b(executive|overall|business)",
            r"\bfinding[s]?\b.*\b(matter|important|key)",
        ],
        "description": "Current executive narrative summaries",
    },
    {
        "intent": "high_risk_negative",
        "patterns": [
            r"\bhigh.risk\b.*\bnegative\b",
            r"\bnegative.sentiment\b.*\b(risk|churn|action)",
            r"\b(risk|churn)\b.*\bnegative.sentiment\b",
            r"\bnegative\b.*\b(customer|action|recommend)",
        ],
        "description": "Actions for high-risk negative-sentiment customers",
    },
    {
        "intent": "top_risk_customers",
        "patterns": [
            r"\btop\b.*\b(risk|churn)",
            r"\bhighest.risk\b.*\bcustomer",
            r"\briskiest\b",
            r"\bcritical\b.*\bcustomer",
            r"\bmost\b.*\b(risk|danger|churn)",
        ],
        "description": "Highest-risk customers with recommended actions",
    },
    {
        "intent": "priority_actions",
        "patterns": [
            r"\bprioritiz",
            r"\bpriority\b.*\b(action|retention|this week|immediate)",
            r"\bthis week\b",
            r"\bimmediate\b.*\baction",
            r"\burgent\b",
            r"\bwhat\b.*\bshould\b.*\b(do|act|focus)",
        ],
        "description": "Highest-priority retention actions for this week",
    },
    {
        "intent": "churn_by_segment",
        "patterns": [
            r"\bchurn\b.*\bsegment",
            r"\bsegment\b.*\bchurn",
            r"\brisk\b.*\bsegment",
            r"\bsegment\b.*\brisk",
            r"\bwhich\b.*\bsegment\b.*\b(high|churn|risk)",
        ],
        "description": "Average churn risk per customer segment",
    },
    {
        "intent": "sentiment_by_segment",
        "patterns": [
            r"\bsentiment\b.*\bsegment",
            r"\bsegment\b.*\bsentiment",
            r"\bsentiment\b.*\btrend",
            r"\bhow\b.*\b(feel|sentiment)\b.*\bsegment",
        ],
        "description": "Average sentiment per customer segment",
    },
    {
        "intent": "recommendation_dist",
        "patterns": [
            r"\brecommendation\b.*\b(distribution|common|frequent|breakdown)",
            r"\baction[s]?\b.*\b(common|frequent|distribution|most)",
            r"\bmost\b.*\brecommend",
            r"\bwhat\b.*\brecommend",
        ],
        "description": "Recommendation action distribution",
    },
    {
        "intent": "segment_overview",
        "patterns": [
            r"\bsegment\b.*\b(overview|size|count|breakdown|summary)",
            r"\bhow\b.*\bmany\b.*\bsegment",
            r"\bsegment\b.*\b(look|like|distribution)",
            r"\bcustomer\b.*\bsegment\b",
        ],
        "description": "Segment sizes and key metrics",
    },
    {
        "intent": "customer_summary",
        "patterns": [
            r"\b(overall|general|full|complete)\b.*\bsummar",
            r"\bsummar\b.*\b(customer|intelligence|all|everything)",
            r"\boverview\b",
            r"\bdashboard\b",
            r"\bhow\b.*\b(doing|perform|look)\b.*\b(overall|general)",
        ],
        "description": "Aggregated intelligence summary across all outputs",
    },
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


def _handle_top_risk_customers(engine) -> Dict[str, Any]:
    """Top 10 highest-risk customers with their recommended actions."""
    df = pd.read_sql(
        text(
            "SELECT cp.customer_id, cp.churn_probability, cp.risk_tier, "
            "cp.top_risk_factors, "
            "r.action_label, r.urgency_score, r.primary_driver, "
            "cs.segment_name "
            "FROM churn_predictions cp "
            "JOIN recommendations r ON cp.customer_id = r.customer_id "
            "JOIN customer_segments cs ON cp.customer_id = cs.customer_id "
            "ORDER BY cp.churn_probability DESC "
            "LIMIT 10"
        ),
        engine,
    )
    rows = df.to_dict("records")
    answer = f"Top 10 highest-risk customers (by churn probability):\n"
    for i, r in enumerate(rows, 1):
        answer += (
            f"  {i}. {r['customer_id']}: {r['churn_probability']:.1%} churn risk "
            f"({r['risk_tier']}), action: {r['action_label']}, "
            f"segment: {r['segment_name']}\n"
        )
    return {
        "answer_text": answer.strip(),
        "structured_result": rows,
        "source_tables": "churn_predictions,recommendations,customer_segments",
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
    # Also get action distribution for this group
    dist = pd.read_sql(
        text(
            "SELECT r.action_label, COUNT(*) as cnt "
            "FROM recommendations r "
            "JOIN churn_predictions cp ON r.customer_id = cp.customer_id "
            "LEFT JOIN sentiment_results sr ON r.customer_id = sr.customer_id "
            "WHERE cp.risk_tier IN ('Critical', 'High') "
            "GROUP BY r.customer_id, r.action_label "
            "HAVING AVG(sr.sentiment_score) < -0.15"
        ),
        engine,
    )
    # Aggregate action counts from the per-customer rows
    action_counts = dist.groupby("action_label")["cnt"].sum().sort_values(ascending=False)
    total_affected = int(action_counts.sum())

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
}

# ── Supported intents list (for unsupported message) ──────────────
SUPPORTED_DESCRIPTIONS = [entry["description"] for entry in INTENT_REGISTRY]


# ══════════════════════════════════════════════════════════════════
# INTENT CLASSIFIER
# ══════════════════════════════════════════════════════════════════


def classify_intent(question: str) -> Tuple[str, str]:
    """
    Classify a question into a supported intent.

    Returns (intent_name, intent_description).
    Returns ("unsupported", description) if no intent matches.
    """
    q = question.lower().strip()

    for entry in INTENT_REGISTRY:
        for pattern in entry["patterns"]:
            if re.search(pattern, q):
                return entry["intent"], entry["description"]

    return "unsupported", "Question does not match any supported query type"


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

        # Write all results to query_results table
        df = pd.DataFrame(results)
        df.to_sql("query_results", engine, if_exists="replace", index=False)
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
        self, question: str, engine
    ) -> Dict[str, Any]:
        """
        Answer a single natural-language question.

        Returns a dict suitable for insertion into query_results.
        """
        now = datetime.now(timezone.utc).isoformat()
        start = time.time()

        intent, description = classify_intent(question)

        if intent == "unsupported":
            elapsed_ms = int((time.time() - start) * 1000)
            supported_list = "\n".join(f"  - {d}" for d in SUPPORTED_DESCRIPTIONS)
            return {
                "query_id": str(uuid.uuid4()),
                "original_question": question,
                "matched_intent": "unsupported",
                "query_status": "unsupported",
                "answer_text": (
                    f"Unsupported query. This system currently supports these question types:\n"
                    f"{supported_list}\n\n"
                    f"Try rephrasing your question to match one of these categories."
                ),
                "structured_result": json.dumps({"supported_intents": SUPPORTED_DESCRIPTIONS}),
                "source_tables": None,
                "row_count": None,
                "execution_ms": elapsed_ms,
                "query_version": QUERY_VERSION,
                "executed_at": now,
            }

        handler = INTENT_HANDLERS[intent]
        try:
            result = handler(engine)
            elapsed_ms = int((time.time() - start) * 1000)

            self._logger.info(
                "query_answered",
                intent=intent,
                question=question[:80],
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
            }
        except Exception as exc:
            elapsed_ms = int((time.time() - start) * 1000)
            self._logger.error(
                "query_failed",
                intent=intent,
                error=str(exc),
            )
            return {
                "query_id": str(uuid.uuid4()),
                "original_question": question,
                "matched_intent": intent,
                "query_status": "error",
                "answer_text": f"Query matched intent '{intent}' but execution failed: {exc}",
                "structured_result": None,
                "source_tables": None,
                "row_count": None,
                "execution_ms": elapsed_ms,
                "query_version": QUERY_VERSION,
                "executed_at": now,
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
