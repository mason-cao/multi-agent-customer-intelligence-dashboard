"""Recommendation scoring and explanations."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from app.agents.recommendation.definitions import RECOMMENDATION_VERSION, ACTION_CATALOG, RETENTION_ACTIONS, GROWTH_ACTIONS


def _compute_thresholds(df: pd.DataFrame) -> Dict[str, float]:
    """Derive percentile-based thresholds from the feature distribution."""
    return {
        "revenue_p75": float(df["total_revenue"].quantile(0.75)),
        "revenue_p50": float(df["total_revenue"].quantile(0.50)),
        "revenue_p25": float(df["total_revenue"].quantile(0.25)),
        "engagement_p60": float(df["engagement_score"].quantile(0.60)),
        "engagement_p40": float(df["engagement_score"].quantile(0.40)),
        "engagement_p30": float(df["engagement_score"].quantile(0.30)),
        "support_p80": float(df["support_ticket_count_30d"].quantile(0.80)),
        "support_p50": float(df["support_ticket_count_30d"].quantile(0.50)),
        "sentiment_pos": 0.15,
        "sentiment_neg": -0.15,
    }

def _add_derived_columns(
    df: pd.DataFrame, t: Dict[str, float]
) -> pd.DataFrame:
    """Add business-tier columns used by the rule engine."""
    # Value tier: percentile-based on total_revenue
    df["value_tier"] = np.select(
        [
            df["total_revenue"] >= t["revenue_p75"],
            df["total_revenue"] >= t["revenue_p25"],
        ],
        ["high", "medium"],
        default="low",
    )

    # Sentiment category
    df["sentiment_category"] = np.select(
        [
            df["avg_sentiment"] > t["sentiment_pos"],
            df["avg_sentiment"] < t["sentiment_neg"],
        ],
        ["positive", "negative"],
        default="neutral",
    )

    # Support burden
    # Handle the case where support_p80 might equal support_p50 (sparse data)
    support_high = max(t["support_p80"], 1)
    support_mod = max(t["support_p50"], 0.5)
    df["support_burden"] = np.select(
        [
            df["support_ticket_count_30d"] >= support_high,
            df["support_ticket_count_30d"] >= support_mod,
        ],
        ["high", "moderate"],
        default="low",
    )

    # Engagement level
    df["engagement_level"] = np.select(
        [
            df["engagement_score"] >= t["engagement_p60"],
            df["engagement_score"] >= t["engagement_p30"],
        ],
        ["high", "medium"],
        default="low",
    )

    # Revenue percentile rank (for urgency calculation)
    df["revenue_pct"] = df["total_revenue"].rank(pct=True)

    # Support percentile rank (for urgency calculation)
    df["support_pct"] = df["support_ticket_count_30d"].rank(pct=True)

    return df

def _evaluate_all(
    df: pd.DataFrame, thresholds: Dict[str, float], top_plan: str
) -> pd.DataFrame:
    """Evaluate the rule cascade for every customer. Returns recommendations DF."""
    now = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, Any]] = []

    for _, r in df.iterrows():
        action_code, primary, secondary = _evaluate_rules(r, top_plan)
        action = ACTION_CATALOG[action_code]
        urgency = _compute_urgency(r, action_code)
        confidence = _compute_confidence(r, action_code, thresholds)
        reasoning = _build_reasoning(action["label"], primary, secondary)

        rows.append({
            "recommendation_id": str(uuid.uuid4()),
            "customer_id": r["customer_id"],
            "action_code": action_code,
            "action_label": action["label"],
            "action_category": action["category"],
            "action_priority": action["priority"],
            "urgency_score": urgency,
            "confidence": confidence,
            "primary_driver": primary,
            "secondary_driver": secondary,
            "reasoning": reasoning,
            "recommended_channel": action["channel"],
            "recommended_owner": action["owner"],
            "target_timeframe": action["timeframe"],
            "recommendation_version": RECOMMENDATION_VERSION,
            "computed_at": now,
        })

    return pd.DataFrame(rows)

def _evaluate_rules(
    r: pd.Series, top_plan: str
) -> Tuple[str, str, Optional[str]]:
    """Evaluate the priority-ordered rule cascade for one customer.

    Returns (action_code, primary_driver, secondary_driver).
    The first matching rule wins.
    """
    churn_pct = f"{r['churn_probability']:.0%}"
    revenue_str = f"${r['total_revenue']:,.0f}"
    sentiment_str = f"{r['avg_sentiment']:.2f}"

    if r["risk_tier"] == "Critical" and r["value_tier"] == "high":
        return (
            "escalate_to_cs",
            f"Critical churn risk ({churn_pct}) on high-value account ({revenue_str} total revenue)",
            f"Sentiment at {sentiment_str}, {r['segment_name']} segment",
        )

    if r["payment_failures_90d"] > 0:
        failures = int(r["payment_failures_90d"])
        return (
            "payment_recovery",
            f"{failures} payment failure(s) in last 90 days",
            f"${r['mrr']:,.0f}/mo MRR at risk, auto-renew {'on' if r['auto_renew'] else 'off'}",
        )

    if r["risk_tier"] == "Critical":
        return (
            "retention_outreach",
            f"Critical churn risk ({churn_pct}) with {r['value_tier']} value",
            f"{r['segment_name']} segment, engagement at {r['engagement_score']:.2f}",
        )

    if r["risk_tier"] == "High" and r["sentiment_category"] == "negative":
        return (
            "retention_outreach",
            f"High churn risk tier combined with negative sentiment ({sentiment_str})",
            f"{r['segment_name']} segment, {revenue_str} total revenue",
        )

    if r["support_burden"] == "high" and r["sentiment_category"] == "negative":
        tickets = int(r["support_ticket_count_30d"])
        burden_word = "Heavy" if tickets >= 3 else "Elevated"
        return (
            "proactive_support",
            f"{burden_word} support load ({tickets} tickets/30d) with negative sentiment ({sentiment_str})",
            f"{r['segment_name']} segment, {r['risk_tier']} churn risk",
        )

    if r["sentiment_category"] == "negative" and r["value_tier"] in ("high", "medium"):
        return (
            "sentiment_recovery",
            f"Negative sentiment ({sentiment_str}) on {r['value_tier']}-value account ({revenue_str})",
            f"{r['risk_tier']} churn risk, {r['segment_name']} segment",
        )

    if r["risk_tier"] == "High" and r["segment_code"] in ("at_risk", "dormant"):
        recency = int(r["days_since_last_order"])
        return (
            "reengagement_campaign",
            f"High churn risk tier in {r['segment_name']} segment",
            f"Last purchase {recency}d ago, {revenue_str} total revenue",
        )

    if r["segment_code"] == "growth" and r["tenure_days"] < 120:
        return (
            "nurture_onboarding",
            f"New customer ({int(r['tenure_days'])}d tenure) in Growth Potential segment",
            f"Engagement at {r['engagement_score']:.2f}, {r['risk_tier']} churn risk",
        )

    if (
        r["engagement_level"] == "high"
        and r["plan_tier"] != top_plan
        and r["value_tier"] in ("high", "medium")
    ):
        return (
            "upsell_premium",
            f"High engagement ({r['engagement_score']:.2f}) on {r['plan_tier']} plan with room to upgrade",
            f"{revenue_str} total revenue, {r['segment_name']} segment",
        )

    if r["segment_code"] == "champions" and r["sentiment_category"] == "positive":
        return (
            "loyalty_reward",
            f"Champion customer with positive sentiment ({sentiment_str})",
            f"{revenue_str} total revenue, engagement at {r['engagement_score']:.2f}",
        )

    if r["segment_code"] in ("at_risk", "dormant"):
        recency = int(r["days_since_last_order"])
        return (
            "reengagement_campaign",
            f"{r['segment_name']} segment with declining activity",
            f"Last purchase {recency}d ago, engagement at {r['engagement_score']:.2f}",
        )

    return (
        "monitor_only",
        f"Stable {r['segment_name']} customer with {r['risk_tier']} churn risk",
        f"Sentiment at {sentiment_str}, engagement at {r['engagement_score']:.2f}",
    )

def _compute_urgency(r: pd.Series, action_code: str) -> float:
    """Compute a 0-100 urgency score from weighted customer signals.

    Components:
      - Churn probability: 0-40 points (primary driver)
      - Sentiment penalty: 0-20 points (negative sentiment adds urgency)
      - Value weight:      0-20 points (higher value = more urgent to act)
      - Support burden:    0-10 points
      - Recency penalty:   0-10 points (longer inactivity = more urgent)

    monitor_only actions are scaled to 40% to keep them below real action
    items in any urgency-sorted view.
    """
    churn_component = float(r["churn_probability"]) * 40

    # Map sentiment [-1, +1] → urgency [20, 0]
    # Negative sentiment = high urgency, positive = low
    sentiment_component = (1 - float(r["avg_sentiment"])) / 2 * 20

    value_component = float(r["revenue_pct"]) * 20

    support_component = min(1.0, float(r["support_pct"])) * 10

    recency_component = min(1.0, float(r["days_since_last_order"]) / 180) * 10

    total = (
        churn_component
        + sentiment_component
        + value_component
        + support_component
        + recency_component
    )
    raw = round(max(0, min(100, total)), 1)

    # Discount monitor_only so it sorts below real action items
    if action_code == "monitor_only":
        return round(raw * 0.4, 1)

    return raw

def _compute_confidence(
    r: pd.Series, action_code: str, t: Dict[str, float]
) -> str:
    """Assess confidence by counting how many signals support the action.

    Retention actions are supported by: high churn, negative sentiment,
    at-risk/dormant segment, low engagement, high support burden.

    Growth actions are supported by: low churn, positive sentiment,
    strong segment, high engagement.

    Returns 'high', 'medium', or 'low'.
    """
    if action_code in RETENTION_ACTIONS:
        signals = sum([
            r["churn_probability"] > 0.2,
            r["avg_sentiment"] < t["sentiment_neg"],
            r["segment_code"] in ("at_risk", "dormant"),
            r["engagement_score"] < t["engagement_p40"],
            r["support_ticket_count_30d"] > max(t["support_p80"], 1),
        ])
        if signals >= 4:
            return "high"
        if signals >= 2:
            return "medium"
        return "low"

    if action_code in GROWTH_ACTIONS:
        signals = sum([
            r["churn_probability"] < 0.15,
            r["avg_sentiment"] > t["sentiment_pos"],
            r["segment_code"] in ("champions", "loyal", "growth"),
            r["engagement_score"] > t["engagement_p60"],
        ])
        if signals >= 3:
            return "high"
        if signals >= 2:
            return "medium"
        return "low"

    # monitor_only
    return "medium"

def _build_reasoning(
    action_label: str, primary: str, secondary: Optional[str]
) -> str:
    """Build a one-sentence human-readable reasoning string."""
    if secondary:
        return f"{action_label} recommended: {primary}. Additional context: {secondary}."
    return f"{action_label} recommended: {primary}."
