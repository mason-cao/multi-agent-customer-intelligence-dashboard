"""Recommendation pipeline stage."""

from typing import Any, Dict, List, Tuple
import pandas as pd
from sqlalchemy import text
from app.agents.base import BaseAgent
from app.db.outputs import replace_output
from app.agents.recommendation.definitions import RECOMMENDATION_VERSION
from app.agents.recommendation.rules import _compute_thresholds, _add_derived_columns, _evaluate_all


class RecommendationAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "recommendation"

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()

        df = self._load_and_merge(engine)
        self._logger.info("merged_signals", customers=len(df))

        if df.empty:
            return {
                "status": "failed",
                "rows_affected": 0,
                "tokens_used": 0,
                "model_used": None,
                "error": "No customer data after merge — upstream agents may have failed",
            }

        thresholds = _compute_thresholds(df)
        df = _add_derived_columns(df, thresholds)
        self._logger.info(
            "derived_columns_added",
            thresholds={k: round(v, 4) for k, v in thresholds.items()},
        )

        top_plan = df.loc[df["mrr"].idxmax(), "plan_tier"] if len(df) > 0 else "enterprise"

        recommendations = _evaluate_all(df, thresholds, top_plan)
        self._logger.info("rules_evaluated", recommendations=len(recommendations))

        replace_output(db, "recommendations", recommendations)

        action_dist = recommendations["action_code"].value_counts().to_dict()
        category_dist = recommendations["action_category"].value_counts().to_dict()
        priority_dist = recommendations["action_priority"].value_counts().to_dict()
        confidence_dist = recommendations["confidence"].value_counts().to_dict()
        timeframe_dist = recommendations["target_timeframe"].value_counts().to_dict()
        avg_urgency = round(float(recommendations["urgency_score"].mean()), 2)

        self._logger.info(
            "recommendation_complete",
            rows=len(recommendations),
            action_distribution=action_dist,
            avg_urgency=avg_urgency,
        )

        return {
            "status": "completed",
            "rows_affected": len(recommendations),
            "input_count": len(df),
            "tokens_used": 0,
            "model_used": None,
            "recommendation_summary": {
                "recommendation_version": RECOMMENDATION_VERSION,
                "total_recommendations": len(recommendations),
                "action_distribution": action_dist,
                "category_distribution": category_dist,
                "priority_distribution": {str(k): v for k, v in priority_dist.items()},
                "confidence_distribution": confidence_dist,
                "avg_urgency": avg_urgency,
                "timeframe_distribution": timeframe_dist,
            },
        }

    def validate_output(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        rows = output.get("rows_affected", 0)
        input_count = output.get("input_count", 0)
        if rows == 0:
            errors.append("No rows written to recommendations")
        elif input_count > 0 and rows < input_count * 0.9:
            errors.append(f"Expected ~{input_count} rows, got {rows}")

        summary = output.get("recommendation_summary", {})
        action_dist = summary.get("action_distribution", {})

        # Must have at least 3 distinct actions (not all monitor_only)
        if len(action_dist) < 3:
            errors.append(
                f"Only {len(action_dist)} distinct actions, expected 3+"
            )

        # monitor_only should not exceed 60% (most customers should get an action)
        total = sum(action_dist.values()) if action_dist else 0
        if total > 0:
            monitor_frac = action_dist.get("monitor_only", 0) / total
            if monitor_frac > 0.60:
                errors.append(
                    f"monitor_only at {monitor_frac:.1%} (>60%), rules too narrow"
                )

        # No single action should exceed 40%
        if total > 0:
            for action, count in action_dist.items():
                if action == "monitor_only":
                    continue
                frac = count / total
                if frac > 0.40:
                    errors.append(
                        f"Action '{action}' dominates at {frac:.1%} (>40%)"
                    )

        # Average urgency should be in a reasonable range
        avg_urg = summary.get("avg_urgency", -1)
        if not (10 <= avg_urg <= 80):
            errors.append(
                f"avg_urgency {avg_urg} outside expected range [10, 80]"
            )

        # Confidence distribution should include high and medium
        conf_dist = summary.get("confidence_distribution", {})
        if "high" not in conf_dist and "medium" not in conf_dist:
            errors.append("No high or medium confidence recommendations")

        return (len(errors) == 0, errors)

    # Data loading

    def _load_and_merge(self, engine) -> pd.DataFrame:
        """Load all signal tables and merge into one row per customer."""
        features = pd.read_sql(
            text(
                "SELECT customer_id, total_revenue, order_count, "
                "days_since_last_order, engagement_score, "
                "support_ticket_count_30d, tenure_days "
                "FROM customer_features"
            ),
            engine,
        )

        segments = pd.read_sql(
            text(
                "SELECT customer_id, segment_code, segment_name "
                "FROM customer_segments"
            ),
            engine,
        )

        churn = pd.read_sql(
            text(
                "SELECT customer_id, churn_probability, risk_tier "
                "FROM churn_predictions"
            ),
            engine,
        )

        # Aggregate sentiment from sentiment_results (more reliable than
        # customer_features.avg_sentiment which may be NULL after re-runs)
        sentiment = pd.read_sql(
            text(
                "SELECT customer_id, AVG(sentiment_score) as avg_sentiment "
                "FROM sentiment_results GROUP BY customer_id"
            ),
            engine,
        )

        # Subscription-level aggregation (per customer)
        subs = pd.read_sql(
            text(
                "SELECT customer_id, plan_tier, mrr, "
                "payment_failures_90d, auto_renew "
                "FROM subscriptions"
            ),
            engine,
        )
        # Keep the plan tier with the highest MRR per customer
        subs_sorted = subs.sort_values("mrr", ascending=False)
        subs_plan = subs_sorted.groupby("customer_id")["plan_tier"].first().reset_index()
        subs_agg = (
            subs.groupby("customer_id")
            .agg({
                "mrr": "sum",
                "payment_failures_90d": "sum",
                "auto_renew": "min",
            })
            .reset_index()
        )
        subs_merged = subs_agg.merge(subs_plan, on="customer_id", how="left")

        # Merge everything onto features
        df = features.copy()
        df = df.merge(segments, on="customer_id", how="left")
        df = df.merge(churn, on="customer_id", how="left")
        df = df.merge(sentiment, on="customer_id", how="left")
        df = df.merge(subs_merged, on="customer_id", how="left")

        # Fill defaults for missing data
        df["segment_code"] = df["segment_code"].fillna("dormant")
        df["segment_name"] = df["segment_name"].fillna("Dormant")
        df["churn_probability"] = df["churn_probability"].fillna(0.15)
        df["risk_tier"] = df["risk_tier"].fillna("Medium")
        df["avg_sentiment"] = df["avg_sentiment"].fillna(0.0)
        df["mrr"] = df["mrr"].fillna(0.0)
        df["payment_failures_90d"] = df["payment_failures_90d"].fillna(0)
        df["auto_renew"] = df["auto_renew"].fillna(1)
        df["plan_tier"] = df["plan_tier"].fillna("starter")
        df["tenure_days"] = df["tenure_days"].fillna(365)
        df["support_ticket_count_30d"] = df["support_ticket_count_30d"].fillna(0)
        df["days_since_last_order"] = df["days_since_last_order"].fillna(90)

        self._logger.info(
            "loaded_inputs",
            features=len(features),
            segments=len(segments),
            churn=len(churn),
            sentiment=len(sentiment),
            subscriptions=len(subs),
        )
        return df
