"""Consistency checks for pipeline outputs."""

from typing import Any, Dict, List
import pandas as pd
from sqlalchemy import text
from app.agents.auditing.results import _make_result, unavailable_result


def _check_consistency(engine, now: str) -> List[Dict[str, Any]]:
    """Verify cross-agent references and logical relationships."""
    results = []

    try:
        df = pd.read_sql(
            text(
                "SELECT r.customer_id, r.action_code, c.risk_tier, "
                "AVG(s.sentiment_score) as avg_sent "
                "FROM recommendations r "
                "JOIN churn_predictions c ON r.customer_id = c.customer_id "
                "LEFT JOIN sentiment_results s ON r.customer_id = s.customer_id "
                "GROUP BY r.customer_id, r.action_code, c.risk_tier"
            ),
            engine,
        )
        # Customers with Critical churn AND negative sentiment AND monitor_only
        violations = df[
            (df["risk_tier"] == "Critical")
            & (df["avg_sent"].fillna(0) < -0.15)
            & (df["action_code"] == "monitor_only")
        ]
        count = len(violations)
        ok = count == 0
        results.append(_make_result(
            check_category="consistency",
            check_name="critical_churn_negative_sent_not_monitor",
            severity="critical" if not ok else "info",
            passed=ok,
            audit_message=(
                "No Critical-churn + negative-sentiment customers assigned monitor_only"
                if ok else
                f"{count} customers with Critical churn + negative sentiment are incorrectly assigned monitor_only"
            ),
            now=now,
            entity_type="customer",
            entity_id=None,
            expected_value="0",
            actual_value=str(count),
            affected_rows=count if not ok else None,
        ))
    except Exception:
        results.append(unavailable_result("consistency", "critical_churn_negative_sent_not_monitor", now))

    try:
        df = pd.read_sql(
            text(
                "SELECT r.customer_id, r.action_code, r.action_category, "
                "cs.segment_code "
                "FROM recommendations r "
                "JOIN customer_segments cs ON r.customer_id = cs.customer_id"
            ),
            engine,
        )
        # Dormant customers with upsell_premium or loyalty_reward
        growth_on_dormant = df[
            (df["segment_code"] == "dormant")
            & (df["action_code"].isin(["upsell_premium", "loyalty_reward"]))
        ]
        count = len(growth_on_dormant)
        ok = count == 0
        results.append(_make_result(
            check_category="consistency",
            check_name="dormant_no_growth_actions",
            severity="warning" if not ok else "info",
            passed=ok,
            audit_message=(
                "No Dormant customers assigned growth-only actions (upsell/loyalty)"
                if ok else
                f"{count} Dormant customers incorrectly assigned growth actions"
            ),
            now=now,
            entity_type="customer",
            entity_id=None,
            expected_value="0",
            actual_value=str(count),
            affected_rows=count if not ok else None,
        ))
    except Exception:
        results.append(unavailable_result("consistency", "dormant_no_growth_actions", now))

    try:
        # Exclude payment_recovery: it fires on payment failures regardless of
        # segment or sentiment, so champion+positive+payment_recovery is correct
        # behavior, not a consistency violation.
        retention_codes = (
            "'escalate_to_cs','retention_outreach',"
            "'proactive_support','sentiment_recovery','reengagement_campaign'"
        )
        df = pd.read_sql(
            text(
                f"SELECT r.customer_id, r.action_code, cs.segment_code, "
                f"AVG(s.sentiment_score) as avg_sent "
                f"FROM recommendations r "
                f"JOIN customer_segments cs ON r.customer_id = cs.customer_id "
                f"LEFT JOIN sentiment_results s ON r.customer_id = s.customer_id "
                f"WHERE cs.segment_code = 'champions' "
                f"AND r.action_code IN ({retention_codes}) "
                f"GROUP BY r.customer_id, r.action_code, cs.segment_code"
            ),
            engine,
        )
        # Only flag if sentiment is actually positive
        violations = df[df["avg_sent"].fillna(0) > 0.15]
        count = len(violations)
        ok = count == 0
        results.append(_make_result(
            check_category="consistency",
            check_name="champions_positive_no_retention",
            severity="warning" if not ok else "info",
            passed=ok,
            audit_message=(
                "No Champion + positive-sentiment customers assigned retention actions"
                if ok else
                f"{count} Champion customers with positive sentiment assigned retention actions"
            ),
            now=now,
            entity_type="customer",
            entity_id=None,
            expected_value="0",
            actual_value=str(count),
            affected_rows=count if not ok else None,
        ))
    except Exception:
        results.append(unavailable_result("consistency", "champions_positive_no_retention", now))

    try:
        rec_ids = pd.read_sql(
            text("SELECT DISTINCT customer_id FROM recommendations"), engine
        )
        churn_ids = pd.read_sql(
            text("SELECT DISTINCT customer_id FROM churn_predictions"), engine
        )
        rec_set = set(rec_ids["customer_id"].tolist())
        churn_set = set(churn_ids["customer_id"].tolist())
        in_rec_not_churn = rec_set - churn_set
        in_churn_not_rec = churn_set - rec_set
        ok = len(in_rec_not_churn) == 0 and len(in_churn_not_rec) == 0
        total_mismatch = len(in_rec_not_churn) + len(in_churn_not_rec)
        results.append(_make_result(
            check_category="consistency",
            check_name="rec_churn_customer_id_alignment",
            severity="warning" if not ok else "info",
            passed=ok,
            audit_message=(
                f"Recommendation and churn customer sets aligned ({len(rec_set)} customers)"
                if ok else
                f"Customer ID mismatch: {len(in_rec_not_churn)} in recommendations only, "
                f"{len(in_churn_not_rec)} in churn only"
            ),
            now=now,
            entity_type="table",
            entity_id="recommendations",
            expected_value="0 mismatches",
            actual_value=str(total_mismatch),
            affected_rows=total_mismatch if not ok else None,
        ))
    except Exception:
        results.append(unavailable_result("consistency", "rec_churn_customer_id_alignment", now))

    try:
        dist = pd.read_sql(
            text(
                "SELECT segment_code, COUNT(*) as cnt "
                "FROM customer_segments GROUP BY segment_code"
            ),
            engine,
        )
        total = int(dist["cnt"].sum())
        if total > 0:
            max_row = dist.loc[dist["cnt"].idxmax()]
            max_frac = float(max_row["cnt"]) / total
            ok = max_frac <= 0.50
            results.append(_make_result(
                check_category="consistency",
                check_name="segment_distribution_balanced",
                severity="warning" if not ok else "info",
                passed=ok,
                audit_message=(
                    f"Largest segment '{max_row['segment_code']}' is {max_frac:.1%} of population — balanced"
                    if ok else
                    f"Segment '{max_row['segment_code']}' dominates at {max_frac:.1%} (>50%)"
                ),
                now=now,
                entity_type="table",
                entity_id="customer_segments",
                expected_value="<=50%",
                actual_value=f"{max_frac:.1%}",
            ))
    except Exception:
        results.append(unavailable_result("consistency", "segment_distribution_balanced", now))

    try:
        dist = pd.read_sql(
            text(
                "SELECT action_code, COUNT(*) as cnt "
                "FROM recommendations GROUP BY action_code"
            ),
            engine,
        )
        total = int(dist["cnt"].sum())
        active = dist[dist["action_code"] != "monitor_only"]
        if total > 0 and len(active) > 0:
            max_row = active.loc[active["cnt"].idxmax()]
            max_frac = float(max_row["cnt"]) / total
            ok = max_frac <= 0.40
            results.append(_make_result(
                check_category="consistency",
                check_name="recommendation_action_balance",
                severity="warning" if not ok else "info",
                passed=ok,
                audit_message=(
                    f"Most common active action '{max_row['action_code']}' is {max_frac:.1%} — balanced"
                    if ok else
                    f"Action '{max_row['action_code']}' dominates at {max_frac:.1%} (>40%)"
                ),
                now=now,
                entity_type="table",
                entity_id="recommendations",
                expected_value="<=40%",
                actual_value=f"{max_frac:.1%}",
            ))
    except Exception:
        results.append(unavailable_result("consistency", "recommendation_action_balance", now))

    try:
        monitor = pd.read_sql(
            text(
                "SELECT COUNT(*) as cnt FROM recommendations "
                "WHERE action_code = 'monitor_only'"
            ),
            engine,
        )["cnt"].iloc[0]
        total_recs = pd.read_sql(
            text("SELECT COUNT(*) as cnt FROM recommendations"), engine
        )["cnt"].iloc[0]
        if int(total_recs) > 0:
            frac = int(monitor) / int(total_recs)
            ok = frac <= 0.60
            results.append(_make_result(
                check_category="consistency",
                check_name="monitor_only_not_dominant",
                severity="warning" if not ok else "info",
                passed=ok,
                audit_message=(
                    f"monitor_only at {frac:.1%} of recommendations — acceptable"
                    if ok else
                    f"monitor_only at {frac:.1%} (>60%), recommendation rules may be too narrow"
                ),
                now=now,
                entity_type="table",
                entity_id="recommendations",
                expected_value="<=60%",
                actual_value=f"{frac:.1%}",
            ))
    except Exception:
        results.append(unavailable_result("consistency", "monitor_only_not_dominant", now))

    return results
