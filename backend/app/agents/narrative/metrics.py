"""Aggregate workspace data for deterministic executive summaries."""

import json
from typing import Any, Dict
import pandas as pd
from sqlalchemy import text
from app.utils.formatting import format_currency as _fmt_currency


def _aggregate_metrics(engine) -> Dict[str, Any]:
    """Aggregate all upstream tables into a single stats dictionary."""
    s: Dict[str, Any] = {}

    try:
        ctx = pd.read_sql(text("SELECT key, value FROM workspace_context"), engine)
        ws_ctx = dict(zip(ctx["key"], ctx["value"]))
    except Exception:
        ws_ctx = {}
    s["company_name"] = ws_ctx.get("company_name", "the platform")
    s["scenario_description"] = ws_ctx.get("scenario_description", "")

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

    s["total_revenue_fmt"] = _fmt_currency(s["total_revenue"])
    s["avg_revenue_fmt"] = _fmt_currency(s["avg_revenue"])

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

    orders = pd.read_sql(
        text("SELECT order_date, amount FROM orders WHERE status = 'completed'"),
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
