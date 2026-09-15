"""Churn configuration shared by computation and validation."""

from datetime import datetime


SCORING_VERSION = "gb-v1"

MODEL_FEATURES = [
    "login_frequency_7d",
    "login_frequency_30d",
    "feature_usage_breadth",
    "session_duration_avg",
    "engagement_score",
    "total_revenue",
    "order_count",
    "days_since_last_order",
    "avg_order_value",
    "support_ticket_count_30d",
    "avg_sentiment",
    "nps_score",
    "mrr",
    "payment_failures_90d",
    "auto_renew",
    "days_until_renewal",
    "segment_id",
]

FEATURE_DISPLAY_NAMES = {
    "login_frequency_7d": "recent login activity",
    "login_frequency_30d": "login frequency",
    "feature_usage_breadth": "feature adoption breadth",
    "session_duration_avg": "session duration",
    "engagement_score": "engagement score",
    "total_revenue": "total revenue",
    "order_count": "purchase frequency",
    "days_since_last_order": "purchase recency",
    "avg_order_value": "average order value",
    "support_ticket_count_30d": "support ticket volume",
    "avg_sentiment": "customer sentiment",
    "nps_score": "NPS score",
    "mrr": "monthly recurring revenue",
    "payment_failures_90d": "payment failures",
    "auto_renew": "auto-renewal status",
    "days_until_renewal": "time until renewal",
    "segment_id": "customer segment",
}

RISK_DESCRIPTORS = {
    "login_frequency_7d": ("low recent login activity", "active recent logins"),
    "login_frequency_30d": ("declining login frequency", "consistent login activity"),
    "feature_usage_breadth": ("narrow feature adoption", "broad feature usage"),
    "session_duration_avg": ("short session durations", "healthy session engagement"),
    "engagement_score": ("low engagement", "strong engagement"),
    "total_revenue": ("low revenue contribution", "significant revenue history"),
    "order_count": ("low purchase frequency", "active purchasing"),
    "days_since_last_order": ("long time since last purchase", "recent purchase activity"),
    "avg_order_value": ("low order values", "healthy order values"),
    "support_ticket_count_30d": ("high support ticket volume", "low support needs"),
    "avg_sentiment": ("negative sentiment", "positive sentiment"),
    "nps_score": ("low NPS rating", "high NPS rating"),
    "mrr": ("low monthly revenue", "healthy monthly revenue"),
    "payment_failures_90d": ("recent payment failures", "clean payment history"),
    "auto_renew": ("auto-renewal disabled", "auto-renewal active"),
    "days_until_renewal": ("imminent renewal deadline", "distant renewal date"),
    "segment_id": ("at-risk customer segment", "healthy customer segment"),
}

TIER_PERCENTILE_BREAKS = [
    (85, "Critical"),   # top 15%
    (65, "High"),       # next 20%
    (35, "Medium"),     # next 30%
    (0, "Low"),         # bottom 35%
]

MODEL_PARAMS = {
    "n_estimators": 100,
    "max_depth": 4,
    "learning_rate": 0.1,
    "min_samples_leaf": 20,
    "subsample": 0.8,
    "random_state": 42,
}

REFERENCE_DATE = datetime(2025, 12, 31)
