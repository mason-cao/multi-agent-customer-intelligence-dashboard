"""Recommendation configuration shared by computation and validation."""


RECOMMENDATION_VERSION = "rules-v1"

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
