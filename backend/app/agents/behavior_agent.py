"""
BehaviorAgent — computes per-customer behavioral feature vectors.

This is a deterministic agent (pure Python/Pandas, no LLM calls).
It reads raw events, orders, tickets, and customer records, computes
engagement metrics, and populates the customer_features table.

Inputs:  behavior_events, orders, support_tickets, customers
Outputs: customer_features (5,000 rows)
Phase:   1 (no agent dependencies)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import pandas as pd
from sqlalchemy import text

from app.agents.base import BaseAgent
from app.services.feature_engine import (
    compute_activity_features,
    compute_engagement_features,
    compute_login_features,
    compute_revenue_features,
    compute_support_features,
    compute_tenure_features,
)


# ── Version ───────────────────────────────────────────────────────
# Bump when features, weights, or computation logic changes.
BEHAVIOR_VERSION = "features-v2"


class BehaviorAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "behavior"

    # ──────────────────────────────────────────────────────────────
    # Main entry
    # ──────────────────────────────────────────────────────────────

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()
        self._logger.info("computing_features")

        # Step 1 — Load customer base
        customers = pd.read_sql(
            text("SELECT customer_id FROM customers"), engine
        )
        self._logger.info("customer_count", count=len(customers))

        # Step 2 — Compute each feature group
        self._logger.info("computing_login_features")
        logins = compute_login_features(engine)

        self._logger.info("computing_engagement_features")
        engagement = compute_engagement_features(engine)

        self._logger.info("computing_revenue_features")
        revenue = compute_revenue_features(engine)

        self._logger.info("computing_support_features")
        support = compute_support_features(engine)

        self._logger.info("computing_activity_features")
        activity = compute_activity_features(engine)

        self._logger.info("computing_tenure_features")
        tenure = compute_tenure_features(engine)

        # Step 3 — Merge all features onto the customer base
        features = customers.copy()
        for df in [logins, engagement, revenue, support, activity, tenure]:
            if not df.empty:
                features = features.merge(df, on="customer_id", how="left")

        # Step 4 — Fill missing values for customers with no activity
        fill_defaults = {
            "login_frequency_7d": 0,
            "login_frequency_30d": 0,
            "feature_usage_breadth": 0,
            "session_duration_avg": 0.0,
            "trend_direction": "stable",
            "total_revenue": 0.0,
            "order_count": 0,
            "days_since_last_order": 999,
            "avg_order_value": 0.0,
            "support_ticket_count_30d": 0,
            "avg_resolution_hours": 0.0,
            "total_event_count": 0,
            "last_active_at": None,
            "tenure_days": 0,
        }
        for col, default in fill_defaults.items():
            if col in features.columns:
                if default is not None:
                    features[col] = features[col].fillna(default)
            else:
                features[col] = default

        # Cast integer columns
        int_cols = [
            "login_frequency_7d", "login_frequency_30d",
            "feature_usage_breadth", "order_count",
            "days_since_last_order", "support_ticket_count_30d",
            "total_event_count", "tenure_days",
        ]
        for col in int_cols:
            features[col] = features[col].astype(int)

        # Step 5 — Compute composite engagement_score (0 to 1)
        features["engagement_score"] = self._compute_engagement_score(features)

        # Placeholder columns for sentiment (populated by SentimentAgent later)
        features["avg_sentiment"] = None
        features["nps_score"] = None

        # Timestamp
        features["computed_at"] = datetime.now(timezone.utc).isoformat()

        # Step 6 — Write to database (DELETE + INSERT preserves ORM constraints)
        # NOTE: This wipes avg_sentiment and nps_score set by SentimentAgent.
        # The orchestrator must re-run Sentiment after Behavior whenever
        # Behavior is re-executed.
        self._logger.info("writing_features", rows=len(features))
        db.execute(text("DELETE FROM customer_features"))
        db.commit()
        features.to_sql(
            "customer_features", engine, if_exists="append", index=False
        )

        # Step 7 — Build summary statistics
        summary = {
            "avg_engagement_score": round(
                features["engagement_score"].mean(), 4
            ),
            "trend_distribution": features["trend_direction"]
            .value_counts()
            .to_dict(),
            "avg_login_30d": round(
                features["login_frequency_30d"].mean(), 2
            ),
            "avg_revenue": round(features["total_revenue"].mean(), 2),
            "avg_tenure_days": round(features["tenure_days"].mean(), 1),
            "avg_total_events": round(
                features["total_event_count"].mean(), 1
            ),
            "avg_resolution_hours": round(
                features["avg_resolution_hours"].mean(), 2
            ),
        }

        self._logger.info("behavior_complete", summary=summary)

        return {
            "status": "completed",
            "rows_affected": len(features),
            "input_count": len(customers),
            "tokens_used": 0,
            "model_used": None,
            "feature_summary": summary,
        }

    # ──────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────

    def validate_output(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        rows = output.get("rows_affected", 0)
        input_count = output.get("input_count", 0)
        if rows == 0:
            errors.append("No rows written to customer_features")
        elif input_count > 0 and rows < input_count * 0.9:
            errors.append(f"Expected ~{input_count} rows, got {rows}")

        summary = output.get("feature_summary", {})

        avg_eng = summary.get("avg_engagement_score", -1)
        if not (0.0 <= avg_eng <= 1.0):
            errors.append(
                f"avg_engagement_score out of range [0,1]: {avg_eng}"
            )

        trend_dist = summary.get("trend_distribution", {})
        valid_trends = {"increasing", "stable", "declining"}
        invalid = set(trend_dist.keys()) - valid_trends
        if invalid:
            errors.append(f"Invalid trend_direction values: {invalid}")

        avg_tenure = summary.get("avg_tenure_days", 0)
        if avg_tenure <= 0:
            errors.append(f"avg_tenure_days should be positive: {avg_tenure}")

        return (len(errors) == 0, errors)

    # ──────────────────────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_engagement_score(df: pd.DataFrame) -> pd.Series:
        """
        Composite engagement score in [0, 1].

        Weights:
            0.3 * normalized_login_frequency_30d
            0.3 * normalized_feature_usage_breadth
            0.2 * normalized_session_duration_avg
            0.2 * normalized_trend_score

        Each component is min-max normalized to [0, 1].
        """

        def _normalize(series: pd.Series) -> pd.Series:
            mn, mx = series.min(), series.max()
            if mx == mn:
                return pd.Series(0.5, index=series.index)
            return (series - mn) / (mx - mn)

        n_login = _normalize(df["login_frequency_30d"].astype(float))
        n_breadth = _normalize(df["feature_usage_breadth"].astype(float))
        n_duration = _normalize(df["session_duration_avg"].astype(float))

        # Encode trend as numeric: increasing=1, stable=0.5, declining=0
        trend_map = {"increasing": 1.0, "stable": 0.5, "declining": 0.0}
        n_trend = df["trend_direction"].map(trend_map).fillna(0.5)

        score = (
            0.3 * n_login
            + 0.3 * n_breadth
            + 0.2 * n_duration
            + 0.2 * n_trend
        )

        # Clamp to [0, 1]
        return score.clip(0.0, 1.0).round(4)
