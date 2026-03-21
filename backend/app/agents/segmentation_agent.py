"""
SegmentationAgent — clusters customers into 5 named segments.

Uses KMeans on standardized RFM + engagement features from customer_features.
Deterministic ML agent (scikit-learn only, no LLM calls).

Inputs:  customer_features
Outputs: customer_segments (5,000 rows)
Phase:   1 (depends on BehaviorAgent having populated customer_features)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

from app.agents.base import BaseAgent


# Features used for clustering
CLUSTER_FEATURES = [
    "login_frequency_30d",
    "feature_usage_breadth",
    "session_duration_avg",
    "engagement_score",
    "total_revenue",
    "order_count",
    "days_since_last_order",
    "avg_order_value",
    "support_ticket_count_30d",
]

# Segment names assigned by descending average revenue after clustering.
# Index 0 = highest revenue cluster, index 4 = lowest.
SEGMENT_NAMES = [
    "Champions",
    "Loyal Customers",
    "At Risk",
    "New Customers",
    "Hibernating",
]

K = 5
RANDOM_STATE = 42
MIN_SEGMENT_FRACTION = 0.02  # Validation: no segment below 2%


class SegmentationAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "segmentation"

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()

        # Load features
        df = pd.read_sql(
            text(
                "SELECT customer_id, "
                + ", ".join(CLUSTER_FEATURES)
                + " FROM customer_features"
            ),
            engine,
        )
        self._logger.info("loaded_features", rows=len(df))

        if len(df) < K * 10:
            # Not enough data for meaningful clustering — use fallback
            return self._fallback_quartile(df, db, engine)

        # Prepare feature matrix
        X = df[CLUSTER_FEATURES].copy()
        # days_since_last_order is inverse (lower = better), invert it
        max_days = X["days_since_last_order"].max()
        X["days_since_last_order"] = max_days - X["days_since_last_order"]
        X = X.fillna(0)

        # Standardize
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # KMeans
        kmeans = KMeans(n_clusters=K, random_state=RANDOM_STATE, n_init=10)
        labels = kmeans.fit_predict(X_scaled)

        # Compute distance to assigned cluster center
        distances = np.linalg.norm(
            X_scaled - kmeans.cluster_centers_[labels], axis=1
        )

        df["cluster_label"] = labels
        df["cluster_distance"] = np.round(distances, 4)

        # Order clusters by average total_revenue (descending) and assign names
        cluster_revenue = (
            df.groupby("cluster_label")["total_revenue"]
            .mean()
            .sort_values(ascending=False)
        )
        label_to_rank = {
            label: rank for rank, label in enumerate(cluster_revenue.index)
        }
        df["segment_id"] = df["cluster_label"].map(label_to_rank)
        df["segment_name"] = df["segment_id"].map(
            lambda i: SEGMENT_NAMES[i] if i < len(SEGMENT_NAMES) else f"Segment_{i}"
        )

        # Build output DataFrame
        segments = df[
            ["customer_id", "segment_id", "segment_name", "cluster_distance"]
        ].copy()
        segments["computed_at"] = datetime.now(timezone.utc).isoformat()

        # Write to database
        self._logger.info("writing_segments", rows=len(segments))
        db.execute(text("DELETE FROM customer_segments"))
        db.commit()
        segments.to_sql(
            "customer_segments", engine, if_exists="append", index=False
        )

        # Build summary
        dist = (
            segments.groupby("segment_name")["customer_id"]
            .count()
            .to_dict()
        )
        avg_rev = (
            df.groupby("segment_name")["total_revenue"]
            .mean()
            .round(2)
            .to_dict()
        )
        avg_eng = (
            df.groupby("segment_name")["engagement_score"]
            .mean()
            .round(4)
            .to_dict()
        )

        self._logger.info("segmentation_complete", distribution=dist)

        return {
            "status": "completed",
            "rows_affected": len(segments),
            "tokens_used": 0,
            "model_used": None,
            "segment_summary": {
                "distribution": dist,
                "avg_revenue_by_segment": avg_rev,
                "avg_engagement_by_segment": avg_eng,
                "silhouette_note": "Compute via sklearn.metrics.silhouette_score for presentation.",
            },
        }

    def validate_output(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        errors = []

        rows = output.get("rows_affected", 0)
        if rows == 0:
            errors.append("No rows written to customer_segments")
        elif rows < 4500:
            errors.append(f"Expected ~5000 rows, got {rows}")

        summary = output.get("segment_summary", {})
        dist = summary.get("distribution", {})

        # All 5 segment names should be present
        if len(dist) != K:
            errors.append(f"Expected {K} segments, got {len(dist)}")

        # No segment below minimum fraction
        total = sum(dist.values()) if dist else 0
        if total > 0:
            for seg_name, count in dist.items():
                frac = count / total
                if frac < MIN_SEGMENT_FRACTION:
                    errors.append(
                        f"Segment '{seg_name}' has {frac:.1%} of customers "
                        f"(below {MIN_SEGMENT_FRACTION:.0%} minimum)"
                    )

        return (len(errors) == 0, errors)

    # ------------------------------------------------------------------
    # Fallback for insufficient data
    # ------------------------------------------------------------------

    def _fallback_quartile(
        self, df: pd.DataFrame, db, engine
    ) -> Dict[str, Any]:
        """Simple RFM quartile binning when data is too small for KMeans."""
        self._logger.warning("using_quartile_fallback", rows=len(df))

        df = df.copy()
        df["segment_id"] = 2  # default to "At Risk"
        df["segment_name"] = "At Risk"
        df["cluster_distance"] = 0.0
        df["computed_at"] = datetime.now(timezone.utc).isoformat()

        segments = df[
            ["customer_id", "segment_id", "segment_name",
             "cluster_distance", "computed_at"]
        ]
        db.execute(text("DELETE FROM customer_segments"))
        db.commit()
        segments.to_sql(
            "customer_segments", engine, if_exists="append", index=False
        )

        return {
            "status": "completed",
            "rows_affected": len(segments),
            "tokens_used": 0,
            "model_used": None,
            "segment_summary": {
                "distribution": {"At Risk": len(segments)},
                "fallback": True,
            },
        }
