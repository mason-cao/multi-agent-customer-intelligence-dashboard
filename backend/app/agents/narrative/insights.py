"""Rank insights from computed metrics."""

from typing import Any, Dict, List
from app.utils.formatting import format_currency as _fmt_currency


def _generate_insights(s: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate ranked business insights from aggregated metrics.

    Each insight has:
      - text: the human-readable finding
      - importance: 0-100 score for ranking
      - category: churn / sentiment / segment / revenue / action
      - scope: global / segment-specific
    """
    insights: List[Dict[str, Any]] = []

    insights.append({
        "text": (
            f"{s['high_risk_pct']:.1f}% of customers "
            f"({s['high_risk_count']:,}) are at high or critical churn risk."
        ),
        "importance": min(100, s["high_risk_pct"] * 2.5),
        "category": "churn",
        "scope": "global",
    })

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

    insights.sort(key=lambda x: -x["importance"])
    return insights
