"""Churn pipeline stage."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_predict
from sqlalchemy import text
from app.agents.base import BaseAgent
from app.db.outputs import replace_output
from app.agents.churn.definitions import SCORING_VERSION, MODEL_FEATURES, FEATURE_DISPLAY_NAMES, MODEL_PARAMS, REFERENCE_DATE
from app.agents.churn.explanations import _assign_tiers_by_rank, _top_shap_factors, _generate_explanation


class ChurnAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "churn"

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()

        features_df, segments_df, subs_df, customers_df = self._load_inputs(
            engine
        )

        X, customer_ids = self._build_feature_matrix(
            features_df, segments_df, subs_df
        )

        if len(customer_ids) == 0:
            return {
                "status": "failed",
                "rows_affected": 0,
                "tokens_used": 0,
                "model_used": None,
                "error": "No customers in feature matrix — upstream agents may have failed",
            }

        y = (
            customers_df.set_index("customer_id")
            .loc[customer_ids, "is_churned"]
            .values.astype(int)
        )

        # a model that never saw them during training — no data leakage)
        probabilities = self._cross_validate(X, y)

        model = self._train_model(X, y)

        shap_matrix, global_importance = self._compute_shap(model, X)

        predictions = self._build_predictions(
            customer_ids, probabilities, shap_matrix, X
        )

        replace_output(db, "churn_predictions", predictions)

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
            "input_count": len(customer_ids),
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

    def validate_output(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        errors = []

        rows = output.get("rows_affected", 0)
        input_count = output.get("input_count", 0)
        if rows == 0:
            errors.append("No rows written to churn_predictions")
        elif input_count > 0 and rows < input_count * 0.9:
            errors.append(f"Expected ~{input_count} rows, got {rows}")

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

    # Data loading

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

    # Feature engineering

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

    # Cross-validated scoring

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

    # Model training (for SHAP explanations)

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

    # SHAP analysis

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

    # Prediction assembly

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
                    "scoring_version": SCORING_VERSION,
                    "computed_at": now,
                }
            )

        return pd.DataFrame(rows)
