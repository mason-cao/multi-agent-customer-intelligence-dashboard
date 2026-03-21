"""
ChurnAgent — predicts customer-level churn risk with GradientBoosting + SHAP.

Scoring: GradientBoostingClassifier trained on is_churned labels from the
customers table, using 17 features from customer_features, customer_segments,
and subscriptions.

Explainability: SHAP TreeExplainer computes per-customer feature contributions.
Each customer receives a human-readable explanation derived from their top
SHAP risk factors — no LLM calls required.

Inputs:  customer_features (5K), customer_segments (5K),
         subscriptions (5K), customers (5K)
Outputs: churn_predictions (5K rows)
Phase:   2 (depends on Behavior, Segmentation, and Sentiment agents)
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_predict
from sqlalchemy import text

from app.agents.base import BaseAgent


# ── Scoring version ───────────────────────────────────────────────
# Bump when scoring logic, features, or hyperparameters change.
SCORING_VERSION = "gb-v1"

# ── Feature set ───────────────────────────────────────────────────
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

# Display names for dashboard and explanations
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

# Human-readable descriptors for SHAP-based explanations.
# Tuple: (descriptor when SHAP > 0 / increases risk,
#          descriptor when SHAP < 0 / decreases risk)
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

# ── Risk tier percentile breaks ───────────────────────────────────
# Tiers are assigned by population-relative ranking, not fixed
# probability thresholds. This is standard in risk scoring and
# produces meaningful tier distribution regardless of model calibration.
# Thresholds are computed at runtime from the prediction distribution.
TIER_PERCENTILE_BREAKS = [
    (85, "Critical"),   # top 15%
    (65, "High"),       # next 20%
    (35, "Medium"),     # next 30%
    (0, "Low"),         # bottom 35%
]

# ── Model hyperparameters ─────────────────────────────────────────
# Conservative regularization for stable results on 5K samples.
MODEL_PARAMS = {
    "n_estimators": 100,
    "max_depth": 4,
    "learning_rate": 0.1,
    "min_samples_leaf": 20,
    "subsample": 0.8,
    "random_state": 42,
}

# Reference date matching the synthetic data window (from feature_engine)
REFERENCE_DATE = datetime(2025, 12, 31)


class ChurnAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "churn"

    # ──────────────────────────────────────────────────────────────
    # Main entry
    # ──────────────────────────────────────────────────────────────

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()

        # Step 1 — Load all input tables
        features_df, segments_df, subs_df, customers_df = self._load_inputs(
            engine
        )

        # Step 2 — Build unified feature matrix (17 features)
        X, customer_ids = self._build_feature_matrix(
            features_df, segments_df, subs_df
        )
        y = (
            customers_df.set_index("customer_id")
            .loc[customer_ids, "is_churned"]
            .values.astype(int)
        )

        # Step 3 — Cross-validated predictions (each customer scored by
        # a model that never saw them during training — no data leakage)
        probabilities = self._cross_validate(X, y)

        # Step 4 — Train final model on ALL data for SHAP explanations
        model = self._train_model(X, y)

        # Step 5 — SHAP explanations (per-customer + global)
        shap_matrix, global_importance = self._compute_shap(model, X)

        # Step 6 — Assemble predictions with tiers and explanations
        predictions = self._build_predictions(
            customer_ids, probabilities, shap_matrix, X
        )

        # Step 7 — Persist to churn_predictions table
        self._write_predictions(predictions, db, engine)

        # Step 8 — Build output summary
        tier_dist = predictions["risk_tier"].value_counts().to_dict()
        avg_prob = round(float(probabilities.mean()), 4)
        cv_accuracy = round(
            float(((probabilities >= 0.5).astype(int) == y).mean()), 4
        )

        self._logger.info(
            "churn_complete",
            rows=len(predictions),
            tier_distribution=tier_dist,
            avg_probability=avg_prob,
            cv_accuracy=cv_accuracy,
        )

        return {
            "status": "completed",
            "rows_affected": len(predictions),
            "tokens_used": 0,
            "model_used": None,
            "churn_summary": {
                "scoring_version": SCORING_VERSION,
                "model_type": "GradientBoostingClassifier",
                "model_params": MODEL_PARAMS,
                "tier_distribution": tier_dist,
                "avg_churn_probability": avg_prob,
                "cv_accuracy": cv_accuracy,
                "global_feature_importance": global_importance,
                "total_customers_scored": len(predictions),
                "known_churned": int(y.sum()),
                "known_active": int(len(y) - y.sum()),
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
            errors.append("No rows written to churn_predictions")
        elif rows < 4500:
            errors.append(f"Expected ~5000 rows, got {rows}")

        summary = output.get("churn_summary", {})

        # All four risk tiers should be represented
        tier_dist = summary.get("tier_distribution", {})
        valid_tiers = {"Critical", "High", "Medium", "Low"}
        present = set(tier_dist.keys())
        missing = valid_tiers - present
        if missing:
            errors.append(f"Missing risk tiers: {missing}")
        invalid = present - valid_tiers
        if invalid:
            errors.append(f"Invalid risk_tier values: {invalid}")

        # With percentile-based tiers, no single tier should exceed 50%
        # (expected max is ~35% for Low)
        total = sum(tier_dist.values()) if tier_dist else 0
        if total > 0:
            for tier, count in tier_dist.items():
                frac = count / total
                if frac > 0.50:
                    errors.append(
                        f"Tier '{tier}' dominates at {frac:.1%} (>50%)"
                    )

        # Average probability should be reasonable (15% base churn rate)
        avg = summary.get("avg_churn_probability", -1)
        if not (0.05 <= avg <= 0.50):
            errors.append(
                f"avg_churn_probability {avg} outside range [0.05, 0.50]"
            )

        # Cross-validated accuracy sanity check
        acc = summary.get("cv_accuracy", 0)
        if acc < 0.65:
            errors.append(f"cv_accuracy {acc} below 0.65")

        return (len(errors) == 0, errors)

    # ──────────────────────────────────────────────────────────────
    # Data loading
    # ──────────────────────────────────────────────────────────────

    def _load_inputs(self, engine):
        """Load the four input tables needed for churn scoring."""
        features_df = pd.read_sql(
            text("SELECT * FROM customer_features"), engine
        )
        segments_df = pd.read_sql(
            text("SELECT customer_id, segment_id FROM customer_segments"),
            engine,
        )
        subs_df = pd.read_sql(
            text(
                "SELECT customer_id, mrr, payment_failures_90d, "
                "auto_renew, renewal_date FROM subscriptions"
            ),
            engine,
        )
        customers_df = pd.read_sql(
            text("SELECT customer_id, is_churned FROM customers"), engine
        )

        self._logger.info(
            "loaded_inputs",
            features=len(features_df),
            segments=len(segments_df),
            subscriptions=len(subs_df),
            customers=len(customers_df),
        )
        return features_df, segments_df, subs_df, customers_df

    # ──────────────────────────────────────────────────────────────
    # Feature engineering
    # ──────────────────────────────────────────────────────────────

    def _build_feature_matrix(
        self, features_df, segments_df, subs_df
    ):
        """Merge input tables into a 17-feature matrix aligned to customer_ids."""
        df = features_df.copy()

        # Merge segment ID (from SegmentationAgent)
        df = df.merge(segments_df, on="customer_id", how="left")
        df["segment_id"] = df["segment_id"].fillna(4)  # default "Dormant"

        # Compute days_until_renewal and aggregate per-customer subscriptions
        subs = subs_df.copy()
        subs["days_until_renewal"] = subs["renewal_date"].apply(
            lambda d: max(
                0,
                (pd.to_datetime(d) - pd.Timestamp(REFERENCE_DATE)).days,
            )
            if pd.notna(d)
            else 180
        )
        subs_agg = (
            subs.groupby("customer_id")
            .agg(
                {
                    "mrr": "sum",
                    "payment_failures_90d": "sum",
                    "auto_renew": "min",  # 0 if any sub is not auto-renew
                    "days_until_renewal": "min",  # nearest renewal
                }
            )
            .reset_index()
        )
        df = df.merge(subs_agg, on="customer_id", how="left")

        # Fill defaults for sparse columns
        defaults = {
            "avg_sentiment": 0.0,   # neutral
            "nps_score": 5.0,       # mid-scale
            "mrr": 0.0,
            "payment_failures_90d": 0,
            "auto_renew": 1,
            "days_until_renewal": 180,
            "segment_id": 4,
        }
        for col, val in defaults.items():
            if col in df.columns:
                df[col] = df[col].fillna(val)

        # Safety: ensure every MODEL_FEATURES column exists
        for feat in MODEL_FEATURES:
            if feat not in df.columns:
                df[feat] = 0

        customer_ids = df["customer_id"].values
        X = df[MODEL_FEATURES].values.astype(float)
        X = np.nan_to_num(X, nan=0.0)

        self._logger.info("feature_matrix_built", shape=list(X.shape))
        return X, customer_ids

    # ──────────────────────────────────────────────────────────────
    # Cross-validated scoring
    # ──────────────────────────────────────────────────────────────

    def _cross_validate(self, X, y):
        """Generate out-of-fold churn probabilities via 5-fold CV."""
        probabilities = cross_val_predict(
            GradientBoostingClassifier(**MODEL_PARAMS),
            X, y, cv=5, method="predict_proba",
        )[:, 1]

        self._logger.info(
            "cross_validation_complete",
            avg_probability=round(float(probabilities.mean()), 4),
        )
        return probabilities

    # ──────────────────────────────────────────────────────────────
    # Model training (for SHAP explanations)
    # ──────────────────────────────────────────────────────────────

    def _train_model(self, X, y):
        """Train a GradientBoosting classifier on the full dataset for SHAP."""
        model = GradientBoostingClassifier(**MODEL_PARAMS)
        model.fit(X, y)
        self._logger.info(
            "model_trained",
            samples=len(y),
            churn_rate=round(float(y.mean()), 4),
        )
        return model

    # ──────────────────────────────────────────────────────────────
    # SHAP analysis
    # ──────────────────────────────────────────────────────────────

    def _compute_shap(self, model, X):
        """Compute per-customer SHAP values and global feature importance."""
        import shap

        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        # Handle both list and ndarray returns (SHAP version differences)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # positive class

        # Global importance: mean |SHAP| per feature, sorted descending
        global_importance = {}
        for i, name in enumerate(MODEL_FEATURES):
            display = FEATURE_DISPLAY_NAMES.get(name, name)
            importance = round(float(np.abs(shap_values[:, i]).mean()), 4)
            global_importance[display] = importance

        global_importance = dict(
            sorted(global_importance.items(), key=lambda x: -x[1])
        )

        self._logger.info(
            "shap_computed",
            top_features=list(global_importance.keys())[:5],
        )
        return shap_values, global_importance

    # ──────────────────────────────────────────────────────────────
    # Prediction assembly
    # ──────────────────────────────────────────────────────────────

    def _build_predictions(
        self, customer_ids, probabilities, shap_matrix, X
    ):
        """Build the output DataFrame with tiers, risk factors, and explanations."""
        now = datetime.now(timezone.utc).isoformat()

        # Assign risk tiers by population-relative rank
        tiers = _assign_tiers_by_rank(probabilities)
        tier_counts = dict(zip(*np.unique(tiers, return_counts=True)))
        self._logger.info("tiers_assigned", distribution=tier_counts)

        rows = []

        for i, cid in enumerate(customer_ids):
            prob = round(float(probabilities[i]), 4)
            tier = tiers[i]
            factors = _top_shap_factors(shap_matrix[i], X[i])
            explanation = _generate_explanation(prob, tier, factors)

            rows.append(
                {
                    "customer_id": cid,
                    "churn_probability": prob,
                    "risk_tier": tier,
                    "top_risk_factors": json.dumps(factors),
                    "explanation": explanation,
                    "computed_at": now,
                }
            )

        return pd.DataFrame(rows)

    # ──────────────────────────────────────────────────────────────
    # Database persistence
    # ──────────────────────────────────────────────────────────────

    def _write_predictions(self, predictions, db, engine):
        """Write predictions via DELETE + INSERT pattern."""
        self._logger.info("writing_predictions", rows=len(predictions))
        db.execute(text("DELETE FROM churn_predictions"))
        db.commit()
        predictions.to_sql(
            "churn_predictions", engine, if_exists="append", index=False
        )


# ── Module-level helpers ──────────────────────────────────────────


def _assign_tiers_by_rank(probabilities: np.ndarray) -> np.ndarray:
    """Assign risk tiers by population-relative rank.

    Uses percentile rank (not value-based thresholds) so that the
    tier distribution is meaningful even when probabilities cluster
    around a few values.  Standard practice in credit and churn
    risk scoring.
    """
    n = len(probabilities)
    # argsort twice gives the 0-indexed rank for each element
    ranks = np.argsort(np.argsort(probabilities))
    # Convert to percentile (0-100)
    percentiles = (ranks + 1) / n * 100

    tiers = np.empty(n, dtype=object)
    for percentile_floor, tier_name in TIER_PERCENTILE_BREAKS:
        mask = percentiles >= percentile_floor
        # Only assign if not already assigned by a higher tier
        unassigned = tiers == None  # noqa: E711
        tiers[mask & unassigned] = tier_name

    return tiers


def _top_shap_factors(
    shap_row: np.ndarray, feature_row: np.ndarray, top_n: int = 3
) -> List[Dict[str, Any]]:
    """Extract the top-N SHAP-based risk factors for one customer."""
    indices = np.argsort(-np.abs(shap_row))[:top_n]
    factors = []

    for idx in indices:
        name = MODEL_FEATURES[idx]
        shap_val = float(shap_row[idx])
        descriptors = RISK_DESCRIPTORS.get(name, ("elevated", "healthy"))
        descriptor = descriptors[0] if shap_val > 0 else descriptors[1]

        factors.append(
            {
                "feature": FEATURE_DISPLAY_NAMES.get(name, name),
                "importance": round(abs(shap_val), 4),
                "value": round(float(feature_row[idx]), 2),
                "direction": "increases risk" if shap_val > 0 else "decreases risk",
                "descriptor": descriptor,
            }
        )

    return factors


def _generate_explanation(
    prob: float, tier: str, factors: List[Dict[str, Any]]
) -> str:
    """Build a human-readable churn explanation from SHAP-based factors.

    Separates risk-increasing and risk-decreasing (protective) factors so
    explanations remain honest when rank-based tiers diverge from absolute
    probability values.
    """
    if not factors:
        return "Insufficient data for detailed risk factor analysis."

    risk_drivers = [f for f in factors if f["direction"] == "increases risk"]
    protective = [f for f in factors if f["direction"] == "decreases risk"]

    if risk_drivers and protective:
        risk_text = _join_natural([f["descriptor"] for f in risk_drivers])
        prot_text = _join_natural([f["descriptor"] for f in protective])
        return f"Risk driven by {risk_text}, offset by {prot_text}."

    if risk_drivers:
        risk_text = _join_natural([f["descriptor"] for f in risk_drivers])
        return f"Risk driven by {risk_text}."

    prot_text = _join_natural([f["descriptor"] for f in protective])
    return f"Risk mitigated by {prot_text}."


def _join_natural(items: List[str]) -> str:
    """Join a list with commas and 'and' for the last item."""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"
