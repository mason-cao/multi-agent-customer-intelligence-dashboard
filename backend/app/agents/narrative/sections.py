"""Assemble narrative sections and attach their supporting metrics."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from sqlalchemy import text
from app.agents.narrative.definitions import NARRATIVE_VERSION
from app.utils.formatting import format_currency as _fmt_currency


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
