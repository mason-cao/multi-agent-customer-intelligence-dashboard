"""
NarrativeAgent -- synthesizes existing agent outputs into executive summaries.

Approach: Template-driven narrative generation from aggregated metrics with
deterministic insight ranking. Every sentence traces to a real aggregate
metric computed from existing agent output tables.

Three phases:
  1. Aggregate metrics from all upstream tables into a stats dictionary
  2. Generate ranked insights by evaluating conditions against those stats
  3. Assemble section-level narrative summaries from templates with real numbers

No LLM calls. Fully deterministic. Zero API keys required.

Inputs:  customer_features (5K), customer_segments (5K),
         churn_predictions (5K), sentiment_results (~18K),
         recommendations (5K), orders (~36K)
Outputs: executive_summaries (7 rows, one per section)
Phase:   4 (depends on all prior agents)
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import pandas as pd
from sqlalchemy import text

from app.agents.base import BaseAgent


# ── Version ───────────────────────────────────────────────────────
NARRATIVE_VERSION = "template-v1"

# ── Section definitions (display order) ──────────────────────────
SECTIONS = [
    "executive_overview",
    "key_findings",
    "churn_analysis",
    "sentiment_analysis",
    "segment_highlights",
    "action_priorities",
    "revenue_snapshot",
]


class NarrativeAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "narrative"

    # ──────────────────────────────────────────────────────────────
    # Main entry
    # ──────────────────────────────────────────────────────────────

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()

        # Step 1 -- Aggregate all metrics
        stats = _aggregate_metrics(engine)

        if stats["total_customers"] == 0:
            return {
                "status": "failed",
                "rows_affected": 0,
                "tokens_used": 0,
                "model_used": None,
                "error": "No customer data available — upstream agents may have failed",
            }

        self._logger.info(
            "metrics_aggregated",
            total_customers=stats["total_customers"],
            segments=len(stats["segment_dist"]),
        )

        # Step 2 -- Generate ranked insights
        insights = _generate_insights(stats)
        self._logger.info("insights_generated", count=len(insights))

        # Step 3 -- Assemble section narratives
        summaries = _assemble_sections(stats, insights)
        self._logger.info("sections_assembled", count=len(summaries))

        # Step 4 -- Write to database (DELETE + INSERT preserves ORM constraints)
        self._write_summaries(summaries, db, engine)

        # Step 5 -- Build output summary
        section_types = [s["summary_type"] for s in summaries]
        total_text_len = sum(len(s["summary_text"]) for s in summaries)

        self._logger.info(
            "narrative_complete",
            sections=len(summaries),
            total_text_chars=total_text_len,
        )

        return {
            "status": "completed",
            "rows_affected": len(summaries),
            "tokens_used": 0,
            "model_used": None,
            "narrative_summary": {
                "narrative_version": NARRATIVE_VERSION,
                "sections_generated": section_types,
                "total_sections": len(summaries),
                "total_text_chars": total_text_len,
                "insights_ranked": len(insights),
            },
        }

    # ──────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────

    def validate_output(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        rows = output.get("rows_affected", 0)
        if rows < len(SECTIONS):
            errors.append(
                f"Expected {len(SECTIONS)} sections, got {rows}"
            )

        summary = output.get("narrative_summary", {})
        sections = summary.get("sections_generated", [])

        # All section types must be present
        missing = set(SECTIONS) - set(sections)
        if missing:
            errors.append(f"Missing sections: {missing}")

        # Total text should be substantive (at least 200 chars per section)
        total_chars = summary.get("total_text_chars", 0)
        if total_chars < len(SECTIONS) * 200:
            errors.append(
                f"Total text too short at {total_chars} chars "
                f"(expected {len(SECTIONS) * 200}+)"
            )

        # Should have generated insights
        insights_count = summary.get("insights_ranked", 0)
        if insights_count < 5:
            errors.append(
                f"Only {insights_count} insights generated, expected 5+"
            )

        return (len(errors) == 0, errors)

    # ──────────────────────────────────────────────────────────────
    # Database persistence
    # ──────────────────────────────────────────────────────────────

    def _write_summaries(self, summaries: List[Dict], db, engine):
        """Write summaries via DELETE + INSERT to preserve ORM constraints."""
        self._logger.info("writing_summaries", rows=len(summaries))
        db.execute(text("DELETE FROM executive_summaries"))
        db.commit()
        df = pd.DataFrame(summaries)
        df.to_sql(
            "executive_summaries", engine, if_exists="append", index=False
        )


# ══════════════════════════════════════════════════════════════════
# PHASE 1: Metric aggregation
# ══════════════════════════════════════════════════════════════════


def _aggregate_metrics(engine) -> Dict[str, Any]:
    """Aggregate all upstream tables into a single stats dictionary."""
    s: Dict[str, Any] = {}

    # ── Workspace context (scenario description, company name) ────
    try:
        ctx = pd.read_sql(text("SELECT key, value FROM workspace_context"), engine)
        ws_ctx = dict(zip(ctx["key"], ctx["value"]))
    except Exception:
        ws_ctx = {}
    s["company_name"] = ws_ctx.get("company_name", "the platform")
    s["scenario_description"] = ws_ctx.get("scenario_description", "")

    # ── Customer base ─────────────────────────────────────────────
    cf = pd.read_sql(
        text(
            "SELECT customer_id, total_revenue, engagement_score, "
            "order_count, days_since_last_order, "
            "support_ticket_count_30d, tenure_days "
            "FROM customer_features"
        ),
        engine,
    )
    s["total_customers"] = len(cf)
    s["total_revenue"] = float(cf["total_revenue"].sum())
    s["avg_revenue"] = float(cf["total_revenue"].mean())
    s["avg_engagement"] = float(cf["engagement_score"].mean())
    s["avg_tenure_days"] = float(cf["tenure_days"].mean())
    s["median_recency"] = float(cf["days_since_last_order"].median())

    # Revenue formatting
    s["total_revenue_fmt"] = _fmt_currency(s["total_revenue"])
    s["avg_revenue_fmt"] = _fmt_currency(s["avg_revenue"])

    # ── Segments ──────────────────────────────────────────────────
    seg = pd.read_sql(
        text("SELECT customer_id, segment_code, segment_name FROM customer_segments"),
        engine,
    )
    seg_with_features = seg.merge(
        cf[["customer_id", "total_revenue", "engagement_score"]], on="customer_id"
    )

    seg_dist = seg["segment_name"].value_counts().to_dict()
    s["segment_dist"] = seg_dist
    s["segment_pct"] = {
        k: round(v / s["total_customers"] * 100, 1)
        for k, v in seg_dist.items()
    }

    seg_rev = (
        seg_with_features.groupby("segment_name")["total_revenue"]
        .agg(["sum", "mean"])
        .to_dict()
    )
    s["segment_total_rev"] = {k: round(v) for k, v in seg_rev["sum"].items()}
    s["segment_avg_rev"] = {k: round(v) for k, v in seg_rev["mean"].items()}
    s["segment_rev_share"] = {
        k: round(v / s["total_revenue"] * 100, 1)
        for k, v in seg_rev["sum"].items()
    }

    seg_eng = (
        seg_with_features.groupby("segment_name")["engagement_score"]
        .mean()
        .round(3)
        .to_dict()
    )
    s["segment_avg_eng"] = seg_eng

    largest_seg = max(seg_dist, key=seg_dist.get)
    s["largest_segment"] = largest_seg
    s["largest_segment_count"] = seg_dist[largest_seg]

    # ── Churn predictions ─────────────────────────────────────────
    churn = pd.read_sql(
        text("SELECT customer_id, churn_probability, risk_tier FROM churn_predictions"),
        engine,
    )
    s["avg_churn_prob"] = float(churn["churn_probability"].mean())
    s["risk_tier_dist"] = churn["risk_tier"].value_counts().to_dict()
    s["critical_count"] = int(s["risk_tier_dist"].get("Critical", 0))
    s["high_risk_count"] = (
        s["critical_count"] + int(s["risk_tier_dist"].get("High", 0))
    )
    s["high_risk_pct"] = round(
        s["high_risk_count"] / s["total_customers"] * 100, 1
    )

    # Churn by segment
    churn_seg = churn.merge(seg[["customer_id", "segment_name"]], on="customer_id")
    s["churn_by_segment"] = {}
    for seg_name in seg_dist:
        mask = churn_seg["segment_name"] == seg_name
        tier_counts = churn_seg.loc[mask, "risk_tier"].value_counts().to_dict()
        s["churn_by_segment"][seg_name] = tier_counts

    # High-value at-risk (top 25% revenue + Critical/High churn)
    rev_p75 = cf["total_revenue"].quantile(0.75)
    high_value_ids = set(cf.loc[cf["total_revenue"] >= rev_p75, "customer_id"])
    high_risk_ids = set(
        churn.loc[churn["risk_tier"].isin(["Critical", "High"]), "customer_id"]
    )
    hv_hr_ids = high_value_ids & high_risk_ids
    s["high_value_at_risk_count"] = len(hv_hr_ids)
    s["high_value_at_risk_revenue"] = float(
        cf.loc[cf["customer_id"].isin(hv_hr_ids), "total_revenue"].sum()
    )
    s["high_value_at_risk_revenue_fmt"] = _fmt_currency(
        s["high_value_at_risk_revenue"]
    )

    # ── Sentiment ─────────────────────────────────────────────────
    sent_agg = pd.read_sql(
        text(
            "SELECT customer_id, AVG(sentiment_score) as avg_s "
            "FROM sentiment_results GROUP BY customer_id"
        ),
        engine,
    )
    s["avg_sentiment"] = float(sent_agg["avg_s"].mean())
    s["sentiment_label"] = (
        "positive" if s["avg_sentiment"] > 0.15
        else "negative" if s["avg_sentiment"] < -0.15
        else "neutral"
    )
    s["negative_sentiment_count"] = int((sent_agg["avg_s"] < -0.15).sum())
    s["negative_sentiment_pct"] = round(
        s["negative_sentiment_count"] / len(sent_agg) * 100, 1
    )

    # Sentiment by segment
    sent_seg = sent_agg.merge(seg[["customer_id", "segment_name"]], on="customer_id")
    s["sentiment_by_segment"] = (
        sent_seg.groupby("segment_name")["avg_s"]
        .mean()
        .round(3)
        .to_dict()
    )

    # Top sentiment topics
    topics_df = pd.read_sql(
        text("SELECT topics FROM sentiment_results WHERE topics IS NOT NULL"),
        engine,
    )
    topic_counts: Dict[str, int] = {}
    for row in topics_df["topics"]:
        try:
            for t in json.loads(row):
                topic_counts[t] = topic_counts.get(t, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass
    s["top_topics"] = sorted(topic_counts.items(), key=lambda x: -x[1])[:7]

    # ── Recommendations ───────────────────────────────────────────
    recs = pd.read_sql(
        text(
            "SELECT action_code, action_label, action_category, "
            "action_priority, urgency_score FROM recommendations"
        ),
        engine,
    )
    s["rec_action_dist"] = recs["action_code"].value_counts().to_dict()
    s["rec_action_labels"] = (
        recs.drop_duplicates("action_code")
        .set_index("action_code")["action_label"]
        .to_dict()
    )
    s["rec_category_dist"] = recs["action_category"].value_counts().to_dict()
    s["retention_count"] = int(s["rec_category_dist"].get("retention", 0))
    s["growth_count"] = int(s["rec_category_dist"].get("growth", 0))
    s["immediate_count"] = int((recs["action_priority"] == 1).sum())
    s["urgent_count"] = int((recs["action_priority"] <= 2).sum())
    s["avg_urgency"] = float(recs["urgency_score"].mean())

    top_action_code = recs["action_code"].value_counts().idxmax()
    s["top_action_code"] = top_action_code
    s["top_action_label"] = recs.loc[
        recs["action_code"] == top_action_code, "action_label"
    ].iloc[0]
    s["top_action_count"] = int(s["rec_action_dist"][top_action_code])

    # ── Orders (revenue trend) ────────────────────────────────────
    orders = pd.read_sql(
        text("SELECT order_date, amount FROM orders"),
        engine,
    )
    latest_date = orders["order_date"].max()
    if latest_date:
        cutoff_30 = pd.to_datetime(latest_date) - pd.Timedelta(days=30)
        cutoff_60 = pd.to_datetime(latest_date) - pd.Timedelta(days=60)
        orders["order_date_dt"] = pd.to_datetime(orders["order_date"])
        recent = orders.loc[orders["order_date_dt"] >= cutoff_30, "amount"].sum()
        prior = orders.loc[
            (orders["order_date_dt"] >= cutoff_60)
            & (orders["order_date_dt"] < cutoff_30),
            "amount",
        ].sum()
        s["monthly_revenue"] = float(recent)
        s["monthly_revenue_fmt"] = _fmt_currency(float(recent))
        s["prior_monthly_revenue"] = float(prior)
        s["revenue_trend_pct"] = (
            round((recent - prior) / prior * 100, 1) if prior > 0 else 0.0
        )
    else:
        s["monthly_revenue"] = 0.0
        s["monthly_revenue_fmt"] = "$0"
        s["prior_monthly_revenue"] = 0.0
        s["revenue_trend_pct"] = 0.0

    return s


# ══════════════════════════════════════════════════════════════════
# PHASE 2: Insight generation and ranking
# ══════════════════════════════════════════════════════════════════


def _generate_insights(s: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate ranked business insights from aggregated metrics.

    Each insight has:
      - text: the human-readable finding
      - importance: 0-100 score for ranking
      - category: churn / sentiment / segment / revenue / action
      - scope: global / segment-specific
    """
    insights: List[Dict[str, Any]] = []

    # ── Churn concentration ───────────────────────────────────────
    insights.append({
        "text": (
            f"{s['high_risk_pct']:.1f}% of customers "
            f"({s['high_risk_count']:,}) are at high or critical churn risk."
        ),
        "importance": min(100, s["high_risk_pct"] * 2.5),
        "category": "churn",
        "scope": "global",
    })

    # ── High-value at-risk ────────────────────────────────────────
    if s["high_value_at_risk_count"] > 0:
        insights.append({
            "text": (
                f"{s['high_value_at_risk_count']:,} high-value customers "
                f"are at elevated churn risk, representing "
                f"{s['high_value_at_risk_revenue_fmt']} in revenue."
            ),
            "importance": min(100, 50 + s["high_value_at_risk_count"] * 0.1),
            "category": "churn",
            "scope": "global",
        })

    # ── Sentiment direction ───────────────────────────────────────
    sent_importance = abs(s["avg_sentiment"]) * 200
    if s["avg_sentiment"] < -0.05:
        insights.append({
            "text": (
                f"Overall customer sentiment is trending negative "
                f"(avg score: {s['avg_sentiment']:.2f}), with "
                f"{s['negative_sentiment_pct']:.1f}% of customers "
                f"showing negative sentiment."
            ),
            "importance": min(100, 40 + sent_importance),
            "category": "sentiment",
            "scope": "global",
        })
    elif s["avg_sentiment"] > 0.15:
        insights.append({
            "text": (
                f"Customer sentiment is positive overall "
                f"(avg score: {s['avg_sentiment']:.2f}), a healthy signal "
                f"for retention and expansion."
            ),
            "importance": 25,
            "category": "sentiment",
            "scope": "global",
        })

    # ── Top concern topic ─────────────────────────────────────────
    if s["top_topics"]:
        top_topic, top_count = s["top_topics"][0]
        topic_label = top_topic.replace("_", " ").title()
        insights.append({
            "text": (
                f'"{topic_label}" is the most frequent customer concern, '
                f"appearing in {top_count:,} feedback and support documents."
            ),
            "importance": min(60, 30 + top_count / 200),
            "category": "sentiment",
            "scope": "global",
        })

    # ── Immediate interventions needed ────────────────────────────
    if s["immediate_count"] > 0:
        insights.append({
            "text": (
                f"{s['immediate_count']:,} customers require immediate "
                f"intervention (P1 priority), including "
                f"{s['critical_count']:,} critical churn escalations."
            ),
            "importance": min(95, 55 + s["immediate_count"] * 0.05),
            "category": "action",
            "scope": "global",
        })

    # ── Retention dominance ───────────────────────────────────────
    if s["retention_count"] > 0:
        ret_pct = s["retention_count"] / s["total_customers"] * 100
        if ret_pct > 40:
            insights.append({
                "text": (
                    f"Retention actions dominate recommendations at "
                    f"{ret_pct:.1f}% of the customer base, indicating "
                    f"systemic retention pressure."
                ),
                "importance": min(80, 40 + ret_pct * 0.5),
                "category": "action",
                "scope": "global",
            })

    # ── Revenue concentration ─────────────────────────────────────
    champ_share = s["segment_rev_share"].get("Champions", 0)
    loyal_share = s["segment_rev_share"].get("Loyal Customers", 0)
    top_two_share = champ_share + loyal_share
    if top_two_share > 60:
        insights.append({
            "text": (
                f"Champions and Loyal Customers generate "
                f"{top_two_share:.1f}% of total revenue, creating high "
                f"concentration risk in these segments."
            ),
            "importance": min(70, 35 + top_two_share * 0.4),
            "category": "revenue",
            "scope": "global",
        })

    # ── Segment-specific: At Risk ─────────────────────────────────
    at_risk_count = s["segment_dist"].get("At Risk", 0)
    at_risk_pct = s["segment_pct"].get("At Risk", 0)
    if at_risk_pct > 15:
        at_risk_churn = s["churn_by_segment"].get("At Risk", {})
        at_risk_critical = at_risk_churn.get("Critical", 0) + at_risk_churn.get("High", 0)
        insights.append({
            "text": (
                f"The At Risk segment contains {at_risk_count:,} customers "
                f"({at_risk_pct:.1f}% of the base), with {at_risk_critical:,} "
                f"at high or critical churn risk."
            ),
            "importance": min(75, 35 + at_risk_pct),
            "category": "segment",
            "scope": "segment",
        })

    # ── Segment-specific: Dormant ─────────────────────────────────
    dormant_count = s["segment_dist"].get("Dormant", 0)
    dormant_pct = s["segment_pct"].get("Dormant", 0)
    dormant_rev = s["segment_avg_rev"].get("Dormant", 0)
    if dormant_count > 0:
        insights.append({
            "text": (
                f"{dormant_count:,} Dormant customers ({dormant_pct:.1f}% "
                f"of the base) have low engagement and average revenue of "
                f"{_fmt_currency(dormant_rev)}, representing win-back or "
                f"sunset candidates."
            ),
            "importance": min(45, 20 + dormant_pct),
            "category": "segment",
            "scope": "segment",
        })

    # ── Growth opportunity ────────────────────────────────────────
    if s["growth_count"] > 0:
        growth_pct = s["growth_count"] / s["total_customers"] * 100
        insights.append({
            "text": (
                f"{s['growth_count']:,} customers ({growth_pct:.1f}%) are "
                f"recommended for growth actions (upsell, loyalty, nurture), "
                f"representing expansion opportunity."
            ),
            "importance": min(50, 25 + growth_pct),
            "category": "action",
            "scope": "global",
        })

    # ── Revenue trend ─────────────────────────────────────────────
    trend = s["revenue_trend_pct"]
    if abs(trend) > 5:
        direction = "up" if trend > 0 else "down"
        insights.append({
            "text": (
                f"Monthly revenue is {direction} {abs(trend):.1f}% vs. the "
                f"prior period ({s['monthly_revenue_fmt']} vs. "
                f"{_fmt_currency(s['prior_monthly_revenue'])})."
            ),
            "importance": min(55, 25 + abs(trend) * 0.5),
            "category": "revenue",
            "scope": "global",
        })

    # ── Payment issues ────────────────────────────────────────────
    payment_count = s["rec_action_dist"].get("payment_recovery", 0)
    if payment_count > 0:
        insights.append({
            "text": (
                f"{payment_count:,} customers have outstanding payment "
                f"failures requiring recovery."
            ),
            "importance": min(65, 35 + payment_count * 0.05),
            "category": "action",
            "scope": "global",
        })

    # Sort by importance descending
    insights.sort(key=lambda x: -x["importance"])
    return insights


# ══════════════════════════════════════════════════════════════════
# PHASE 3: Section assembly
# ══════════════════════════════════════════════════════════════════


def _assemble_sections(
    s: Dict[str, Any], insights: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Assemble all narrative sections from stats and insights."""
    now = datetime.now(timezone.utc).isoformat()
    sections: List[Dict[str, Any]] = []

    builders = [
        (1, "executive_overview", "global", _build_executive_overview),
        (2, "key_findings", "global", _build_key_findings),
        (3, "churn_analysis", "churn", _build_churn_analysis),
        (4, "sentiment_analysis", "sentiment", _build_sentiment_analysis),
        (5, "segment_highlights", "segment", _build_segment_highlights),
        (6, "action_priorities", "recommendation", _build_action_priorities),
        (7, "revenue_snapshot", "revenue", _build_revenue_snapshot),
    ]

    for order, summary_type, scope, builder_fn in builders:
        title, text = builder_fn(s, insights)
        # Collect supporting metrics relevant to this section
        metrics = _section_metrics(s, summary_type)

        sections.append({
            "summary_id": str(uuid.uuid4()),
            "summary_type": summary_type,
            "title": title,
            "summary_text": text,
            "supporting_metrics": json.dumps(metrics),
            "priority": order,
            "section_order": order,
            "source_scope": scope,
            "narrative_version": NARRATIVE_VERSION,
            "computed_at": now,
        })

    return sections


# ── Section builders ──────────────────────────────────────────────


def _build_executive_overview(
    s: Dict, _insights: List[Dict]
) -> Tuple[str, str]:
    title = "Executive Overview"

    company = s.get("company_name", "the platform")
    scenario_desc = s.get("scenario_description", "")
    intro = f"{scenario_desc} " if scenario_desc else ""

    para1 = (
        f"{intro}Across {s['total_customers']:,} active customers generating "
        f"{s['total_revenue_fmt']} in cumulative revenue, {company} "
        f"identifies {s['high_risk_count']:,} customers "
        f"({s['high_risk_pct']:.1f}%) at high or critical churn risk. "
        f"Average customer sentiment is {s['sentiment_label']} "
        f"({s['avg_sentiment']:.2f}), and "
        f"{s['immediate_count']:,} customers require immediate intervention."
    )

    para2 = (
        f"The most common recommended action is "
        f'"{s["top_action_label"]}" ({s["top_action_count"]:,} customers), '
        f"with retention-focused actions accounting for "
        f"{s['retention_count']:,} of all recommendations. "
        f"Monthly revenue stands at {s['monthly_revenue_fmt']}"
    )
    if s["revenue_trend_pct"] != 0:
        direction = "up" if s["revenue_trend_pct"] > 0 else "down"
        para2 += f", {direction} {abs(s['revenue_trend_pct']):.1f}% vs. the prior 30 days."
    else:
        para2 += "."

    return title, f"{para1}\n\n{para2}"


def _build_key_findings(
    _s: Dict, insights: List[Dict]
) -> Tuple[str, str]:
    title = "Key Findings"

    # Take top 6 insights
    top = insights[:6]
    lines = []
    for i, ins in enumerate(top, 1):
        lines.append(f"{i}. {ins['text']}")

    return title, "\n".join(lines)


def _build_churn_analysis(
    s: Dict, _insights: List[Dict]
) -> Tuple[str, str]:
    title = "Churn Risk Analysis"

    # Tier breakdown
    tier_lines = []
    for tier in ["Critical", "High", "Medium", "Low"]:
        count = s["risk_tier_dist"].get(tier, 0)
        pct = round(count / s["total_customers"] * 100, 1)
        tier_lines.append(f"{tier}: {count:,} ({pct}%)")
    tier_str = ", ".join(tier_lines)

    para1 = (
        f"Churn risk is distributed as: {tier_str}. "
        f"The average predicted churn probability is "
        f"{s['avg_churn_prob']:.1%} across the customer base."
    )

    # Where risk concentrates
    worst_segment = max(
        s["churn_by_segment"],
        key=lambda seg: (
            s["churn_by_segment"][seg].get("Critical", 0)
            + s["churn_by_segment"][seg].get("High", 0)
        ),
    )
    worst_high = (
        s["churn_by_segment"][worst_segment].get("Critical", 0)
        + s["churn_by_segment"][worst_segment].get("High", 0)
    )
    para2 = (
        f"Churn risk is most concentrated in the {worst_segment} segment, "
        f"where {worst_high:,} customers are at high or critical risk."
    )

    # High-value at-risk
    para3 = ""
    if s["high_value_at_risk_count"] > 0:
        para3 = (
            f" {s['high_value_at_risk_count']:,} of these high-risk "
            f"customers are also high-value accounts, representing "
            f"{s['high_value_at_risk_revenue_fmt']} in revenue at risk."
        )

    return title, f"{para1}\n\n{para2}{para3}"


def _build_sentiment_analysis(
    s: Dict, _insights: List[Dict]
) -> Tuple[str, str]:
    title = "Sentiment & Support Analysis"

    para1 = (
        f"Customer sentiment averages {s['avg_sentiment']:.2f} "
        f"({s['sentiment_label']}). "
        f"{s['negative_sentiment_count']:,} customers "
        f"({s['negative_sentiment_pct']:.1f}%) show negative sentiment, "
        f"signaling dissatisfaction that may precede churn."
    )

    # Sentiment by segment
    seg_sent_sorted = sorted(
        s["sentiment_by_segment"].items(), key=lambda x: x[1]
    )
    worst_seg, worst_val = seg_sent_sorted[0]
    best_seg, best_val = seg_sent_sorted[-1]
    para2 = (
        f"Sentiment is weakest in the {worst_seg} segment "
        f"(avg: {worst_val:.3f}) and strongest in {best_seg} "
        f"(avg: {best_val:.3f})."
    )

    # Top topics
    if s["top_topics"]:
        topic_strs = [
            f'{t.replace("_", " ").title()} ({c:,})'
            for t, c in s["top_topics"][:5]
        ]
        para3 = (
            f"The most frequently mentioned customer concerns are: "
            f"{', '.join(topic_strs)}."
        )
    else:
        para3 = ""

    parts = [para1, para2]
    if para3:
        parts.append(para3)
    return title, "\n\n".join(parts)


def _build_segment_highlights(
    s: Dict, _insights: List[Dict]
) -> Tuple[str, str]:
    title = "Segment Highlights"

    lines = []
    # Order segments by revenue share descending
    for seg_name in sorted(
        s["segment_dist"], key=lambda x: s["segment_total_rev"].get(x, 0), reverse=True
    ):
        count = s["segment_dist"][seg_name]
        pct = s["segment_pct"][seg_name]
        rev_share = s["segment_rev_share"].get(seg_name, 0)
        avg_eng = s["segment_avg_eng"].get(seg_name, 0)
        avg_sent = s["sentiment_by_segment"].get(seg_name, 0)

        churn_data = s["churn_by_segment"].get(seg_name, {})
        high_risk = churn_data.get("Critical", 0) + churn_data.get("High", 0)

        lines.append(
            f"{seg_name} ({count:,}, {pct}%): "
            f"{rev_share:.1f}% of revenue, "
            f"avg engagement {avg_eng:.3f}, "
            f"sentiment {avg_sent:+.3f}, "
            f"{high_risk:,} high/critical churn risk."
        )

    return title, "\n".join(lines)


def _build_action_priorities(
    s: Dict, _insights: List[Dict]
) -> Tuple[str, str]:
    title = "Recommended Action Priorities"

    para1 = (
        f"The recommendation engine has assigned actions to all "
        f"{s['total_customers']:,} customers. "
        f"{s['immediate_count']:,} require immediate intervention (P1), "
        f"and {s['urgent_count']:,} are urgent (P1-P2). "
        f"Average urgency across all recommendations is "
        f"{s['avg_urgency']:.1f}/100."
    )

    # Category breakdown
    cat_lines = []
    for cat in ["retention", "support", "growth", "monitoring"]:
        count = s["rec_category_dist"].get(cat, 0)
        pct = round(count / s["total_customers"] * 100, 1)
        cat_lines.append(f"{cat.title()}: {count:,} ({pct}%)")
    para2 = "Action categories: " + ", ".join(cat_lines) + "."

    # Top 3 specific actions
    top_actions = sorted(
        s["rec_action_dist"].items(), key=lambda x: -x[1]
    )[:3]
    action_strs = []
    for code, count in top_actions:
        label = s["rec_action_labels"].get(code, code.replace("_", " ").title())
        action_strs.append(f"{label} ({count:,})")
    para3 = f"Top recommended actions: {', '.join(action_strs)}."

    return title, f"{para1}\n\n{para2}\n\n{para3}"


def _build_revenue_snapshot(
    s: Dict, _insights: List[Dict]
) -> Tuple[str, str]:
    title = "Revenue Snapshot"

    para1 = (
        f"Total cumulative revenue across the customer base is "
        f"{s['total_revenue_fmt']}, with an average of "
        f"{s['avg_revenue_fmt']} per customer. "
        f"Monthly revenue is {s['monthly_revenue_fmt']}"
    )
    if s["revenue_trend_pct"] != 0:
        direction = "up" if s["revenue_trend_pct"] > 0 else "down"
        para1 += f", {direction} {abs(s['revenue_trend_pct']):.1f}% vs. the prior 30 days."
    else:
        para1 += "."

    # Revenue concentration by segment
    rev_lines = []
    for seg_name in sorted(
        s["segment_rev_share"], key=lambda x: s["segment_rev_share"][x], reverse=True
    ):
        share = s["segment_rev_share"][seg_name]
        total = s["segment_total_rev"][seg_name]
        rev_lines.append(f"{seg_name}: {_fmt_currency(total)} ({share:.1f}%)")
    para2 = "Revenue by segment: " + ", ".join(rev_lines) + "."

    return title, f"{para1}\n\n{para2}"


# ── Supporting metrics per section ────────────────────────────────


def _section_metrics(s: Dict, summary_type: str) -> Dict[str, Any]:
    """Extract supporting metrics relevant to each section type."""
    if summary_type == "executive_overview":
        return {
            "total_customers": s["total_customers"],
            "total_revenue": s["total_revenue"],
            "high_risk_count": s["high_risk_count"],
            "high_risk_pct": s["high_risk_pct"],
            "avg_sentiment": round(s["avg_sentiment"], 3),
            "immediate_count": s["immediate_count"],
            "monthly_revenue": s["monthly_revenue"],
            "revenue_trend_pct": s["revenue_trend_pct"],
        }
    if summary_type == "key_findings":
        return {
            "high_risk_count": s["high_risk_count"],
            "immediate_count": s["immediate_count"],
            "retention_count": s["retention_count"],
            "avg_sentiment": round(s["avg_sentiment"], 3),
        }
    if summary_type == "churn_analysis":
        return {
            "risk_tier_dist": s["risk_tier_dist"],
            "avg_churn_prob": round(s["avg_churn_prob"], 4),
            "high_value_at_risk_count": s["high_value_at_risk_count"],
            "high_value_at_risk_revenue": s["high_value_at_risk_revenue"],
        }
    if summary_type == "sentiment_analysis":
        return {
            "avg_sentiment": round(s["avg_sentiment"], 3),
            "negative_sentiment_pct": s["negative_sentiment_pct"],
            "sentiment_by_segment": s["sentiment_by_segment"],
            "top_topics": s["top_topics"][:5],
        }
    if summary_type == "segment_highlights":
        return {
            "segment_dist": s["segment_dist"],
            "segment_rev_share": s["segment_rev_share"],
        }
    if summary_type == "action_priorities":
        return {
            "rec_category_dist": s["rec_category_dist"],
            "immediate_count": s["immediate_count"],
            "urgent_count": s["urgent_count"],
            "avg_urgency": round(s["avg_urgency"], 1),
        }
    if summary_type == "revenue_snapshot":
        return {
            "total_revenue": s["total_revenue"],
            "monthly_revenue": s["monthly_revenue"],
            "revenue_trend_pct": s["revenue_trend_pct"],
            "segment_rev_share": s["segment_rev_share"],
        }
    return {}


# ── Formatting helpers ────────────────────────────────────────────


def _fmt_currency(amount: float) -> str:
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.1f}K"
    return f"${amount:,.0f}"
