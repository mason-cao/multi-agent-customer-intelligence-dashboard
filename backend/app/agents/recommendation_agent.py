"""
RecommendationAgent -- next-best-action engine for customer-level interventions.

Approach: Priority-ordered rule cascade with urgency scoring.
Each customer is evaluated against business rules derived from churn risk,
segment, sentiment, engagement, value, and support signals. The first
matching rule determines the recommended action.

Explainability: Every recommendation traces to named rules with explicit
conditions. Primary and secondary drivers are human-readable. Urgency
scores are computed from a weighted combination of five customer signals.

Inputs:  customer_features (5K), customer_segments (5K),
         churn_predictions (5K), subscriptions (5K),
         sentiment_results (~18K, aggregated to customer level)
Outputs: recommendations (5K rows)
Phase:   3 (depends on Behavior, Segmentation, Sentiment, Churn agents)
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import text

from app.agents.base import BaseAgent


# ── Version ───────────────────────────────────────────────────────
RECOMMENDATION_VERSION = "rules-v1"


# ── Action catalog ────────────────────────────────────────────────
# Each action has fixed metadata. The rule engine selects which action
# applies to each customer; these fields are copied into the output row.

ACTION_CATALOG = {
    "escalate_to_cs": {
        "label": "Escalate to Customer Success",
        "category": "retention",
        "priority": 1,
        "timeframe": "immediate",
        "channel": "phone",
        "owner": "customer_success",
    },
    "payment_recovery": {
        "label": "Payment Recovery",
        "category": "retention",
        "priority": 1,
        "timeframe": "immediate",
        "channel": "email",
        "owner": "support",
    },
    "retention_outreach": {
        "label": "Retention Outreach",
        "category": "retention",
        "priority": 2,
        "timeframe": "this_week",
        "channel": "email",
        "owner": "customer_success",
    },
    "proactive_support": {
        "label": "Proactive Support Follow-up",
        "category": "support",
        "priority": 2,
        "timeframe": "this_week",
        "channel": "email",
        "owner": "support",
    },
    "sentiment_recovery": {
        "label": "Sentiment Recovery",
        "category": "retention",
        "priority": 2,
        "timeframe": "this_week",
        "channel": "email",
        "owner": "customer_success",
    },
    "reengagement_campaign": {
        "label": "Re-engagement Campaign",
        "category": "retention",
        "priority": 3,
        "timeframe": "this_week",
        "channel": "email",
        "owner": "marketing",
    },
    "nurture_onboarding": {
        "label": "New Customer Nurture",
        "category": "growth",
        "priority": 3,
        "timeframe": "this_week",
        "channel": "in-app",
        "owner": "marketing",
    },
    "upsell_premium": {
        "label": "Upsell Premium Plan",
        "category": "growth",
        "priority": 4,
        "timeframe": "this_month",
        "channel": "email",
        "owner": "sales",
    },
    "loyalty_reward": {
        "label": "Loyalty Reward",
        "category": "growth",
        "priority": 4,
        "timeframe": "this_month",
        "channel": "email",
        "owner": "marketing",
    },
    "monitor_only": {
        "label": "Monitor Only",
        "category": "monitoring",
        "priority": 5,
        "timeframe": "monitor",
        "channel": "n/a",
        "owner": "none",
    },
}

RETENTION_ACTIONS = frozenset({
    "escalate_to_cs", "payment_recovery", "retention_outreach",
    "proactive_support", "sentiment_recovery", "reengagement_campaign",
})
GROWTH_ACTIONS = frozenset({
    "nurture_onboarding", "upsell_premium", "loyalty_reward",
})


class RecommendationAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "recommendation"

    # ──────────────────────────────────────────────────────────────
    # Main entry
    # ──────────────────────────────────────────────────────────────

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()

        # Step 1 -- Load and merge all input signals into one row per customer
        df = self._load_and_merge(engine)
        self._logger.info("merged_signals", customers=len(df))

        # Step 2 -- Compute derived tiers and thresholds from the data
        thresholds = _compute_thresholds(df)
        df = _add_derived_columns(df, thresholds)
        self._logger.info(
            "derived_columns_added",
            thresholds={k: round(v, 4) for k, v in thresholds.items()},
        )

        # Step 3 -- Find the top plan tier (for upsell logic)
        top_plan = df.loc[df["mrr"].idxmax(), "plan_tier"] if len(df) > 0 else "enterprise"

        # Step 4 -- Evaluate rule cascade for every customer
        recommendations = _evaluate_all(df, thresholds, top_plan)
        self._logger.info("rules_evaluated", recommendations=len(recommendations))

        # Step 5 -- Write to database
        self._write_recommendations(recommendations, db, engine)

        # Step 6 -- Build output summary
        action_dist = recommendations["action_code"].value_counts().to_dict()
        category_dist = recommendations["action_category"].value_counts().to_dict()
        priority_dist = recommendations["action_priority"].value_counts().to_dict()
        confidence_dist = recommendations["confidence"].value_counts().to_dict()
        timeframe_dist = recommendations["target_timeframe"].value_counts().to_dict()
        avg_urgency = round(float(recommendations["urgency_score"].mean()), 2)

        self._logger.info(
            "recommendation_complete",
            rows=len(recommendations),
            action_distribution=action_dist,
            avg_urgency=avg_urgency,
        )

        return {
            "status": "completed",
            "rows_affected": len(recommendations),
            "tokens_used": 0,
            "model_used": None,
            "recommendation_summary": {
                "recommendation_version": RECOMMENDATION_VERSION,
                "total_recommendations": len(recommendations),
                "action_distribution": action_dist,
                "category_distribution": category_dist,
                "priority_distribution": {str(k): v for k, v in priority_dist.items()},
                "confidence_distribution": confidence_dist,
                "avg_urgency": avg_urgency,
                "timeframe_distribution": timeframe_dist,
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
        if rows == 0:
            errors.append("No rows written to recommendations")
        elif rows < 4500:
            errors.append(f"Expected ~5000 rows, got {rows}")

        summary = output.get("recommendation_summary", {})
        action_dist = summary.get("action_distribution", {})

        # Must have at least 3 distinct actions (not all monitor_only)
        if len(action_dist) < 3:
            errors.append(
                f"Only {len(action_dist)} distinct actions, expected 3+"
            )

        # monitor_only should not exceed 60% (most customers should get an action)
        total = sum(action_dist.values()) if action_dist else 0
        if total > 0:
            monitor_frac = action_dist.get("monitor_only", 0) / total
            if monitor_frac > 0.60:
                errors.append(
                    f"monitor_only at {monitor_frac:.1%} (>60%), rules too narrow"
                )

        # No single action should exceed 40%
        if total > 0:
            for action, count in action_dist.items():
                if action == "monitor_only":
                    continue
                frac = count / total
                if frac > 0.40:
                    errors.append(
                        f"Action '{action}' dominates at {frac:.1%} (>40%)"
                    )

        # Average urgency should be in a reasonable range
        avg_urg = summary.get("avg_urgency", -1)
        if not (10 <= avg_urg <= 80):
            errors.append(
                f"avg_urgency {avg_urg} outside expected range [10, 80]"
            )

        # Confidence distribution should include high and medium
        conf_dist = summary.get("confidence_distribution", {})
        if "high" not in conf_dist and "medium" not in conf_dist:
            errors.append("No high or medium confidence recommendations")

        return (len(errors) == 0, errors)

    # ──────────────────────────────────────────────────────────────
    # Data loading
    # ──────────────────────────────────────────────────────────────

    def _load_and_merge(self, engine) -> pd.DataFrame:
        """Load all signal tables and merge into one row per customer."""
        features = pd.read_sql(
            text(
                "SELECT customer_id, total_revenue, order_count, "
                "days_since_last_order, engagement_score, "
                "support_ticket_count_30d, tenure_days "
                "FROM customer_features"
            ),
            engine,
        )

        segments = pd.read_sql(
            text(
                "SELECT customer_id, segment_code, segment_name "
                "FROM customer_segments"
            ),
            engine,
        )

        churn = pd.read_sql(
            text(
                "SELECT customer_id, churn_probability, risk_tier "
                "FROM churn_predictions"
            ),
            engine,
        )

        # Aggregate sentiment from sentiment_results (more reliable than
        # customer_features.avg_sentiment which may be NULL after re-runs)
        sentiment = pd.read_sql(
            text(
                "SELECT customer_id, AVG(sentiment_score) as avg_sentiment "
                "FROM sentiment_results GROUP BY customer_id"
            ),
            engine,
        )

        # Subscription-level aggregation (per customer)
        subs = pd.read_sql(
            text(
                "SELECT customer_id, plan_tier, mrr, "
                "payment_failures_90d, auto_renew "
                "FROM subscriptions"
            ),
            engine,
        )
        # Keep the plan tier with the highest MRR per customer
        subs_sorted = subs.sort_values("mrr", ascending=False)
        subs_plan = subs_sorted.groupby("customer_id")["plan_tier"].first().reset_index()
        subs_agg = (
            subs.groupby("customer_id")
            .agg({
                "mrr": "sum",
                "payment_failures_90d": "sum",
                "auto_renew": "min",
            })
            .reset_index()
        )
        subs_merged = subs_agg.merge(subs_plan, on="customer_id", how="left")

        # Merge everything onto features
        df = features.copy()
        df = df.merge(segments, on="customer_id", how="left")
        df = df.merge(churn, on="customer_id", how="left")
        df = df.merge(sentiment, on="customer_id", how="left")
        df = df.merge(subs_merged, on="customer_id", how="left")

        # Fill defaults for missing data
        df["segment_code"] = df["segment_code"].fillna("dormant")
        df["segment_name"] = df["segment_name"].fillna("Dormant")
        df["churn_probability"] = df["churn_probability"].fillna(0.15)
        df["risk_tier"] = df["risk_tier"].fillna("Medium")
        df["avg_sentiment"] = df["avg_sentiment"].fillna(0.0)
        df["mrr"] = df["mrr"].fillna(0.0)
        df["payment_failures_90d"] = df["payment_failures_90d"].fillna(0)
        df["auto_renew"] = df["auto_renew"].fillna(1)
        df["plan_tier"] = df["plan_tier"].fillna("starter")
        df["tenure_days"] = df["tenure_days"].fillna(365)
        df["support_ticket_count_30d"] = df["support_ticket_count_30d"].fillna(0)
        df["days_since_last_order"] = df["days_since_last_order"].fillna(90)

        self._logger.info(
            "loaded_inputs",
            features=len(features),
            segments=len(segments),
            churn=len(churn),
            sentiment=len(sentiment),
            subscriptions=len(subs),
        )
        return df

    # ──────────────────────────────────────────────────────────────
    # Database persistence
    # ──────────────────────────────────────────────────────────────

    def _write_recommendations(self, recommendations, db, engine):
        """Write recommendations via DELETE + INSERT to preserve ORM constraints."""
        self._logger.info("writing_recommendations", rows=len(recommendations))
        db.execute(text("DELETE FROM recommendations"))
        db.commit()
        recommendations.to_sql(
            "recommendations", engine, if_exists="append", index=False
        )


# ── Threshold computation ─────────────────────────────────────────


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


# ── Derived columns ──────────────────────────────────────────────


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


# ── Rule engine ───────────────────────────────────────────────────


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

    # ── Rule 1: Critical churn + high value → Escalate ────────────
    if r["risk_tier"] == "Critical" and r["value_tier"] == "high":
        return (
            "escalate_to_cs",
            f"Critical churn risk ({churn_pct}) on high-value account ({revenue_str} total revenue)",
            f"Sentiment at {sentiment_str}, {r['segment_name']} segment",
        )

    # ── Rule 2: Payment failures → Recovery ───────────────────────
    if r["payment_failures_90d"] > 0:
        failures = int(r["payment_failures_90d"])
        return (
            "payment_recovery",
            f"{failures} payment failure(s) in last 90 days",
            f"${r['mrr']:,.0f}/mo MRR at risk, auto-renew {'on' if r['auto_renew'] else 'off'}",
        )

    # ── Rule 3: Critical churn (non-high value) → Retention ──────
    if r["risk_tier"] == "Critical":
        return (
            "retention_outreach",
            f"Critical churn risk ({churn_pct}) with {r['value_tier']} value",
            f"{r['segment_name']} segment, engagement at {r['engagement_score']:.2f}",
        )

    # ── Rule 4: High churn + negative sentiment → Retention ──────
    if r["risk_tier"] == "High" and r["sentiment_category"] == "negative":
        return (
            "retention_outreach",
            f"High churn risk tier combined with negative sentiment ({sentiment_str})",
            f"{r['segment_name']} segment, {revenue_str} total revenue",
        )

    # ── Rule 5: High support burden + negative sentiment → Support
    if r["support_burden"] == "high" and r["sentiment_category"] == "negative":
        tickets = int(r["support_ticket_count_30d"])
        burden_word = "Heavy" if tickets >= 3 else "Elevated"
        return (
            "proactive_support",
            f"{burden_word} support load ({tickets} tickets/30d) with negative sentiment ({sentiment_str})",
            f"{r['segment_name']} segment, {r['risk_tier']} churn risk",
        )

    # ── Rule 6: Negative sentiment + medium/high value → Sentiment recovery
    if r["sentiment_category"] == "negative" and r["value_tier"] in ("high", "medium"):
        return (
            "sentiment_recovery",
            f"Negative sentiment ({sentiment_str}) on {r['value_tier']}-value account ({revenue_str})",
            f"{r['risk_tier']} churn risk, {r['segment_name']} segment",
        )

    # ── Rule 7: High churn + at-risk/dormant → Re-engagement ─────
    if r["risk_tier"] == "High" and r["segment_code"] in ("at_risk", "dormant"):
        recency = int(r["days_since_last_order"])
        return (
            "reengagement_campaign",
            f"High churn risk tier in {r['segment_name']} segment",
            f"Last purchase {recency}d ago, {revenue_str} total revenue",
        )

    # ── Rule 8: Growth segment + short tenure → Nurture ──────────
    if r["segment_code"] == "growth" and r["tenure_days"] < 120:
        return (
            "nurture_onboarding",
            f"New customer ({int(r['tenure_days'])}d tenure) in Growth Potential segment",
            f"Engagement at {r['engagement_score']:.2f}, {r['risk_tier']} churn risk",
        )

    # ── Rule 9: High engagement + not top plan + value → Upsell ──
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

    # ── Rule 10: Champions + positive sentiment → Loyalty reward ──
    if r["segment_code"] == "champions" and r["sentiment_category"] == "positive":
        return (
            "loyalty_reward",
            f"Champion customer with positive sentiment ({sentiment_str})",
            f"{revenue_str} total revenue, engagement at {r['engagement_score']:.2f}",
        )

    # ── Rule 11: At-risk or dormant (remaining) → Re-engagement ──
    if r["segment_code"] in ("at_risk", "dormant"):
        recency = int(r["days_since_last_order"])
        return (
            "reengagement_campaign",
            f"{r['segment_name']} segment with declining activity",
            f"Last purchase {recency}d ago, engagement at {r['engagement_score']:.2f}",
        )

    # ── Rule 12: Default → Monitor ───────────────────────────────
    return (
        "monitor_only",
        f"Stable {r['segment_name']} customer with {r['risk_tier']} churn risk",
        f"Sentiment at {sentiment_str}, engagement at {r['engagement_score']:.2f}",
    )


# ── Urgency scoring ──────────────────────────────────────────────


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


# ── Confidence scoring ────────────────────────────────────────────


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


# ── Reasoning text ────────────────────────────────────────────────


def _build_reasoning(
    action_label: str, primary: str, secondary: Optional[str]
) -> str:
    """Build a one-sentence human-readable reasoning string."""
    if secondary:
        return f"{action_label} recommended: {primary}. Additional context: {secondary}."
    return f"{action_label} recommended: {primary}."
