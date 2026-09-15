"""Audit domains derived from the producing stages' configuration."""

from app.agents.churn.definitions import TIER_PERCENTILE_BREAKS
from app.agents.segmentation.definitions import VALID_CODES
from app.agents.recommendation.definitions import ACTION_CATALOG
from app.agents.narrative.definitions import SECTIONS

AUDIT_VERSION = "rules-v1"
PER_CUSTOMER_TABLES = (
    "customer_features", "customer_segments", "churn_predictions", "recommendations",
)
SENTIMENT_SOURCE_TABLES = ("feedback", "support_tickets")
STATIC_TABLE_MINIMUMS = {"executive_summaries": len(SECTIONS), "agent_runs": 1}
VALID_RISK_TIERS = {tier for _, tier in TIER_PERCENTILE_BREAKS}
VALID_SEGMENT_CODES = VALID_CODES
VALID_SENTIMENT_LABELS = {"positive", "neutral", "negative"}
VALID_ACTION_CODES = set(ACTION_CATALOG)
VALID_SUMMARY_TYPES = set(SECTIONS)
