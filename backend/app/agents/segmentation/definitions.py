"""Segmentation configuration shared by computation and validation."""


SEGMENTATION_VERSION = "rules-v1"

SEGMENTS = [
    {
        "id": 0,
        "code": "champions",
        "name": "Champions",
        "description": (
            "Top-tier customers with high revenue, strong engagement, "
            "and recent purchase activity. Priority for retention and upsell."
        ),
    },
    {
        "id": 1,
        "code": "loyal",
        "name": "Loyal Customers",
        "description": (
            "Consistent buyers with solid revenue contribution and "
            "regular purchase patterns. Priority for deepening relationship."
        ),
    },
    {
        "id": 2,
        "code": "growth",
        "name": "Growth Potential",
        "description": (
            "Recently active customers with moderate engagement showing "
            "room for expansion. Priority for activation campaigns."
        ),
    },
    {
        "id": 3,
        "code": "at_risk",
        "name": "At Risk",
        "description": (
            "Previously valuable customers showing signs of declining "
            "engagement or purchase frequency. Priority for re-engagement."
        ),
    },
    {
        "id": 4,
        "code": "dormant",
        "name": "Dormant",
        "description": (
            "Customers with low recent activity and minimal engagement. "
            "Priority for win-back campaigns or graceful sunset."
        ),
    },
]

SEGMENT_BY_CODE = {s["code"]: s for s in SEGMENTS}

VALID_CODES = {s["code"] for s in SEGMENTS}

FEATURE_COLS = [
    "customer_id",
    "total_revenue",
    "order_count",
    "days_since_last_order",
    "engagement_score",
    "avg_order_value",
    "support_ticket_count_30d",
]
