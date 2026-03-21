"""
SegmentationAgent — assigns customers to business-friendly segments
using deterministic rule-based logic on RFM + engagement features.

Approach: Waterfall rules evaluated in priority order.  Thresholds are
percentile-based, computed from customer_features at runtime so they
adapt to the data while remaining 100 % deterministic for the same input.

Explainability: Every assignment traces to specific feature thresholds.
Each customer receives a primary_reason explaining their classification.

Inputs:  customer_features (5K rows)
Outputs: customer_segments (5K rows)
Phase:   1 (depends on BehaviorAgent having populated customer_features)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import text

from app.agents.base import BaseAgent


# ── Version ───────────────────────────────────────────────────────
# Bump when rules, thresholds, or segment definitions change.
SEGMENTATION_VERSION = "rules-v1"

# ── Segment definitions (priority order — first match wins) ──────
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

# ── Feature columns consumed ─────────────────────────────────────
FEATURE_COLS = [
    "customer_id",
    "total_revenue",
    "order_count",
    "days_since_last_order",
    "engagement_score",
    "avg_order_value",
    "support_ticket_count_30d",
]


class SegmentationAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "segmentation"

    # ──────────────────────────────────────────────────────────────
    # Main entry
    # ──────────────────────────────────────────────────────────────

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()

        # Step 1 — Load customer features
        df = pd.read_sql(
            text("SELECT " + ", ".join(FEATURE_COLS) + " FROM customer_features"),
            engine,
        )
        self._logger.info("loaded_features", rows=len(df))

        # Step 2 — Compute percentile thresholds from the data
        thresholds = _compute_thresholds(df)
        self._logger.info(
            "thresholds_computed",
            thresholds={k: round(v, 2) for k, v in thresholds.items()},
        )

        # Step 3 — Assign segments via waterfall rules (vectorized)
        df["segment_code"] = _assign_segments(df, thresholds)

        # Step 4 — Enrich with segment metadata and per-customer reasons
        segments = _build_output(df, thresholds)

        # Step 5 — Write to database (replace handles schema migration)
        self._write_segments(segments, engine)

        # Step 6 — Build summary statistics
        dist = segments.groupby("segment_name")["customer_id"].count().to_dict()

        merged = segments.merge(
            df[["customer_id", "total_revenue", "engagement_score"]],
            on="customer_id",
        )
        avg_rev = (
            merged.groupby("segment_name")["total_revenue"]
            .mean()
            .round(2)
            .to_dict()
        )
        avg_eng = (
            merged.groupby("segment_name")["engagement_score"]
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
                "segmentation_version": SEGMENTATION_VERSION,
                "distribution": dist,
                "avg_revenue_by_segment": avg_rev,
                "avg_engagement_by_segment": avg_eng,
                "thresholds_used": {
                    k: round(v, 4) for k, v in thresholds.items()
                },
            },
        }

    # ──────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────

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

        # All 5 segments should be represented
        expected = {s["name"] for s in SEGMENTS}
        present = set(dist.keys())
        missing = expected - present
        if missing:
            errors.append(f"Missing segments: {missing}")

        # No segment should exceed 40% or fall below 5%
        total = sum(dist.values()) if dist else 0
        if total > 0:
            for seg_name, count in dist.items():
                frac = count / total
                if frac > 0.40:
                    errors.append(
                        f"Segment '{seg_name}' exceeds 40% at {frac:.1%}"
                    )
                if frac < 0.05:
                    errors.append(
                        f"Segment '{seg_name}' below 5% at {frac:.1%}"
                    )

        return (len(errors) == 0, errors)

    # ──────────────────────────────────────────────────────────────
    # Database persistence
    # ──────────────────────────────────────────────────────────────

    def _write_segments(self, segments, engine):
        """Write segments using 'replace' to handle schema migration."""
        self._logger.info("writing_segments", rows=len(segments))
        segments.to_sql(
            "customer_segments", engine, if_exists="replace", index=False
        )


# ── Module-level helpers ──────────────────────────────────────────


def _compute_thresholds(df: pd.DataFrame) -> Dict[str, float]:
    """Derive percentile-based thresholds from the feature distribution."""
    return {
        "revenue_p75": float(df["total_revenue"].quantile(0.75)),
        "revenue_p50": float(df["total_revenue"].quantile(0.50)),
        "revenue_p25": float(df["total_revenue"].quantile(0.25)),
        "engagement_p60": float(df["engagement_score"].quantile(0.60)),
        "engagement_p40": float(df["engagement_score"].quantile(0.40)),
        "recency_p50": float(df["days_since_last_order"].quantile(0.50)),
        "order_count_p50": float(df["order_count"].quantile(0.50)),
    }


def _assign_segments(
    df: pd.DataFrame, t: Dict[str, float]
) -> np.ndarray:
    """Assign segment codes via waterfall rules (vectorized).

    Rules are evaluated in priority order — first match wins.
    ``np.select`` short-circuits on the first True condition per row.
    """
    rev = df["total_revenue"]
    eng = df["engagement_score"]
    rec = df["days_since_last_order"]
    orders = df["order_count"]

    conditions = [
        # Champions: high revenue + high engagement + recent activity
        (rev >= t["revenue_p75"])
        & (eng >= t["engagement_p60"])
        & (rec <= t["recency_p50"]),
        # Loyal: solid revenue + good purchase frequency
        (rev >= t["revenue_p50"]) & (orders >= t["order_count_p50"]),
        # Growth: recent activity + moderate engagement
        (rec <= t["recency_p50"]) & (eng >= t["engagement_p40"]),
        # At Risk: had value but declining signals
        (rev >= t["revenue_p25"])
        & ((rec > t["recency_p50"]) | (eng < t["engagement_p40"])),
    ]
    choices = ["champions", "loyal", "growth", "at_risk"]

    return np.select(conditions, choices, default="dormant")


def _build_output(
    df: pd.DataFrame, thresholds: Dict[str, float]
) -> pd.DataFrame:
    """Build the full output DataFrame with metadata and per-customer reasons."""
    now = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        code = row["segment_code"]
        seg = SEGMENT_BY_CODE[code]
        reason = _explain_assignment(row, code, thresholds)

        rows.append(
            {
                "customer_id": row["customer_id"],
                "segment_id": seg["id"],
                "segment_code": code,
                "segment_name": seg["name"],
                "segment_description": seg["description"],
                "primary_reason": reason,
                "segmentation_version": SEGMENTATION_VERSION,
                "computed_at": now,
            }
        )

    return pd.DataFrame(rows)


def _explain_assignment(
    row: pd.Series, code: str, thresholds: Dict[str, float]
) -> str:
    """Generate a human-readable reason for this customer's segment."""
    rev = row["total_revenue"]
    eng = row["engagement_score"]
    rec = int(row["days_since_last_order"])
    orders = int(row["order_count"])

    if code == "champions":
        return (
            f"High revenue (${rev:,.0f}), strong engagement ({eng:.2f}), "
            f"and recent activity ({rec}d ago)"
        )

    if code == "loyal":
        return (
            f"Solid revenue (${rev:,.0f}) with {orders} orders "
            f"and engagement of {eng:.2f}"
        )

    if code == "growth":
        return (
            f"Recent activity ({rec}d ago) with moderate engagement "
            f"({eng:.2f}) and room to expand"
        )

    if code == "at_risk":
        issues: List[str] = []
        if rec > thresholds["recency_p50"]:
            issues.append(f"stale activity ({rec}d since last purchase)")
        if eng < thresholds["engagement_p40"]:
            issues.append(f"low engagement ({eng:.2f})")
        issue_text = " and ".join(issues) if issues else "declining signals"
        return f"Revenue of ${rev:,.0f} but {issue_text}"

    # dormant
    return (
        f"Low engagement ({eng:.2f}), {rec}d since last purchase, "
        f"${rev:,.0f} total revenue"
    )
