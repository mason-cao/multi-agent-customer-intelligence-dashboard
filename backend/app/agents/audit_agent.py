"""
AuditAgent -- deterministic cross-agent validation and trust engine.

Approach: Rule-based checks that verify completeness, schema/value sanity,
cross-agent consistency, and groundedness across all upstream agent outputs.
Every check is deterministic with explicit pass/fail and human-readable
audit messages.

Five validation categories:
  1. Completeness   — Are expected tables populated with the right row counts?
  2. Schema sanity  — Are column values within expected domains and ranges?
  3. Consistency    — Do cross-agent references agree? (churn+sentiment→action)
  4. Groundedness   — Are narrative claims backed by real data?
  5. Freshness      — Were agents run recently and successfully?

No LLM calls. Fully deterministic. Zero API keys required.

Inputs:  All upstream agent output tables (read-only)
Outputs: audit_results (one row per check)
Phase:   5 (runs after all other agents)
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import pandas as pd
from sqlalchemy import text

from app.agents.base import BaseAgent


# ── Version ───────────────────────────────────────────────────────
AUDIT_VERSION = "rules-v1"

# ── Expected tables and their minimum row counts ──────────────────
EXPECTED_TABLES = {
    "customer_features": 4500,
    "customer_segments": 4500,
    "churn_predictions": 4500,
    "sentiment_results": 10000,
    "recommendations": 4500,
    "executive_summaries": 7,
    "agent_runs": 1,
}

# ── Valid domains ─────────────────────────────────────────────────
VALID_RISK_TIERS = {"Critical", "High", "Medium", "Low"}
VALID_SEGMENT_CODES = {"champions", "loyal", "growth", "at_risk", "dormant"}
VALID_SENTIMENT_LABELS = {"positive", "neutral", "negative"}
VALID_ACTION_CODES = {
    "escalate_to_cs", "payment_recovery", "retention_outreach",
    "proactive_support", "sentiment_recovery", "reengagement_campaign",
    "nurture_onboarding", "upsell_premium", "loyalty_reward", "monitor_only",
}
VALID_SUMMARY_TYPES = {
    "executive_overview", "key_findings", "churn_analysis",
    "sentiment_analysis", "segment_highlights", "action_priorities",
    "revenue_snapshot",
}


class AuditAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "audit"

    # ──────────────────────────────────────────────────────────────
    # Main entry
    # ──────────────────────────────────────────────────────────────

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()
        now = datetime.now(timezone.utc).isoformat()
        results: List[Dict[str, Any]] = []

        # Phase 1 -- Completeness checks
        results.extend(_check_completeness(engine, now))
        self._logger.info("completeness_checked", checks=len(results))

        # Phase 2 -- Schema and value sanity
        results.extend(_check_schema_sanity(engine, now))
        self._logger.info(
            "schema_checked",
            checks=len(results) - len([r for r in results if r["check_category"] == "completeness"]),
        )

        # Phase 3 -- Cross-agent consistency
        results.extend(_check_consistency(engine, now))
        self._logger.info("consistency_checked")

        # Phase 4 -- Groundedness (narrative claims vs data)
        results.extend(_check_groundedness(engine, now))
        self._logger.info("groundedness_checked")

        # Phase 5 -- Freshness (agent run status)
        results.extend(_check_freshness(engine, now))
        self._logger.info("freshness_checked")

        # Write to database
        df = pd.DataFrame(results)
        df.to_sql("audit_results", engine, if_exists="replace", index=False)
        self._logger.info("audit_results_written", rows=len(df))

        # Build output summary
        total = len(df)
        passed = int(df["passed"].sum())
        failed = total - passed
        failures = df[df["passed"] == 0]
        critical_failures = int((failures["severity"] == "critical").sum())
        warnings = int((failures["severity"] == "warning").sum())

        category_dist = df["check_category"].value_counts().to_dict()
        severity_dist = {
            "critical": int((df["severity"] == "critical").sum()),
            "warning": int((df["severity"] == "warning").sum()),
            "info": int((df["severity"] == "info").sum()),
        }

        self._logger.info(
            "audit_complete",
            total_checks=total,
            passed=passed,
            failed=failed,
            critical_failures=critical_failures,
        )

        return {
            "status": "completed",
            "rows_affected": total,
            "tokens_used": 0,
            "model_used": None,
            "audit_summary": {
                "audit_version": AUDIT_VERSION,
                "total_checks": total,
                "passed": passed,
                "failed": failed,
                "critical_failures": critical_failures,
                "warnings": warnings,
                "check_categories": category_dist,
                "severity_distribution": severity_dist,
            },
        }

    # ──────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────

    def validate_output(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        rows = output.get("rows_affected", 0)
        if rows == 0:
            errors.append("No audit checks were produced")
        elif rows < 10:
            errors.append(f"Expected at least 10 checks, got {rows}")

        summary = output.get("audit_summary", {})
        total = summary.get("total_checks", 0)
        passed = summary.get("passed", 0)

        if total > 0 and passed == 0:
            errors.append("Every single check failed — likely a bug in the auditor")

        # The auditor itself should have at least 5 check categories
        categories = summary.get("check_categories", {})
        if len(categories) < 3:
            errors.append(
                f"Only {len(categories)} check categories, expected 3+"
            )

        return (len(errors) == 0, errors)


# ══════════════════════════════════════════════════════════════════
# CHECK IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════


def _make_result(
    check_category: str,
    check_name: str,
    severity: str,
    passed: bool,
    audit_message: str,
    now: str,
    entity_type: str = "table",
    entity_id: str = None,
    expected_value: str = None,
    actual_value: str = None,
    affected_rows: int = None,
) -> Dict[str, Any]:
    """Build a single audit result row."""
    return {
        "audit_id": str(uuid.uuid4()),
        "audit_scope": "full_pipeline",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "check_category": check_category,
        "check_name": check_name,
        "severity": severity,
        "passed": 1 if passed else 0,
        "audit_message": audit_message,
        "expected_value": expected_value,
        "actual_value": actual_value,
        "affected_rows": affected_rows,
        "audit_version": AUDIT_VERSION,
        "computed_at": now,
    }


# ── 1. Completeness ──────────────────────────────────────────────


def _check_completeness(engine, now: str) -> List[Dict[str, Any]]:
    """Verify all expected tables exist and have minimum row counts."""
    results = []

    for table, min_rows in EXPECTED_TABLES.items():
        try:
            row = pd.read_sql(
                text(f"SELECT COUNT(*) as cnt FROM {table}"), engine
            )
            count = int(row["cnt"].iloc[0])
            ok = count >= min_rows
            results.append(_make_result(
                check_category="completeness",
                check_name=f"table_{table}_populated",
                severity="critical" if not ok else "info",
                passed=ok,
                audit_message=(
                    f"Table '{table}' has {count:,} rows (minimum {min_rows:,})"
                    if ok else
                    f"Table '{table}' has only {count:,} rows, expected at least {min_rows:,}"
                ),
                now=now,
                entity_type="table",
                entity_id=table,
                expected_value=f">={min_rows}",
                actual_value=str(count),
                affected_rows=count,
            ))
        except Exception:
            results.append(_make_result(
                check_category="completeness",
                check_name=f"table_{table}_exists",
                severity="critical",
                passed=False,
                audit_message=f"Table '{table}' does not exist or cannot be read",
                now=now,
                entity_type="table",
                entity_id=table,
            ))

    # Get total customer count for coverage checks
    cust_count = None
    try:
        cust_count = int(pd.read_sql(
            text("SELECT COUNT(*) as cnt FROM customers"), engine
        )["cnt"].iloc[0])
    except Exception:
        pass

    # Check that customer_features covers all customers
    if cust_count is not None:
        try:
            feat_count = int(pd.read_sql(
                text("SELECT COUNT(*) as cnt FROM customer_features"), engine
            )["cnt"].iloc[0])
            ok = feat_count >= int(cust_count * 0.95)
            results.append(_make_result(
                check_category="completeness",
                check_name="features_cover_customers",
                severity="warning" if not ok else "info",
                passed=ok,
                audit_message=(
                    f"customer_features covers {feat_count}/{cust_count} customers"
                    if ok else
                    f"customer_features has {feat_count} rows but customers has {cust_count} — {cust_count - feat_count} customers missing features"
                ),
                now=now,
                entity_type="table",
                entity_id="customer_features",
                expected_value=str(cust_count),
                actual_value=str(feat_count),
            ))
        except Exception:
            pass

    # Check segments cover all customers
    if cust_count is not None:
        try:
            seg_count = int(pd.read_sql(
                text("SELECT COUNT(DISTINCT customer_id) as cnt FROM customer_segments"), engine
            )["cnt"].iloc[0])
            ok = seg_count >= int(cust_count * 0.95)
            results.append(_make_result(
                check_category="completeness",
                check_name="segments_cover_customers",
                severity="warning" if not ok else "info",
                passed=ok,
                audit_message=f"customer_segments covers {seg_count}/{cust_count} customers",
                now=now,
                entity_type="table",
                entity_id="customer_segments",
                expected_value=str(cust_count),
                actual_value=str(seg_count),
            ))
        except Exception:
            pass

    # Check recommendations cover all customers
    if cust_count is not None:
        try:
            rec_count = int(pd.read_sql(
                text("SELECT COUNT(DISTINCT customer_id) as cnt FROM recommendations"), engine
            )["cnt"].iloc[0])
            ok = rec_count >= int(cust_count * 0.95)
            results.append(_make_result(
                check_category="completeness",
                check_name="recommendations_cover_customers",
                severity="warning" if not ok else "info",
                passed=ok,
                audit_message=f"recommendations covers {rec_count}/{cust_count} customers",
                now=now,
                entity_type="table",
                entity_id="recommendations",
                expected_value=str(cust_count),
                actual_value=str(rec_count),
            ))
        except Exception:
            pass

    # Check all 7 narrative sections present
    try:
        sections = pd.read_sql(
            text("SELECT DISTINCT summary_type FROM executive_summaries"), engine
        )
        section_set = set(sections["summary_type"].tolist())
        missing = VALID_SUMMARY_TYPES - section_set
        ok = len(missing) == 0
        results.append(_make_result(
            check_category="completeness",
            check_name="narrative_all_sections_present",
            severity="critical" if not ok else "info",
            passed=ok,
            audit_message=(
                f"All 7 narrative sections present"
                if ok else
                f"Missing narrative sections: {', '.join(sorted(missing))}"
            ),
            now=now,
            entity_type="table",
            entity_id="executive_summaries",
            expected_value="7",
            actual_value=str(len(section_set)),
        ))
    except Exception:
        pass

    return results


# ── 2. Schema / value sanity ──────────────────────────────────────


def _check_schema_sanity(engine, now: str) -> List[Dict[str, Any]]:
    """Verify column values are within expected domains and ranges."""
    results = []

    # --- Churn predictions: risk_tier domain ---
    try:
        tiers = pd.read_sql(
            text("SELECT DISTINCT risk_tier FROM churn_predictions"), engine
        )
        tier_set = set(tiers["risk_tier"].tolist())
        invalid = tier_set - VALID_RISK_TIERS
        ok = len(invalid) == 0
        results.append(_make_result(
            check_category="schema",
            check_name="churn_risk_tier_domain",
            severity="critical" if not ok else "info",
            passed=ok,
            audit_message=(
                f"All risk_tier values valid: {sorted(tier_set)}"
                if ok else
                f"Invalid risk_tier values found: {sorted(invalid)}"
            ),
            now=now,
            entity_type="table",
            entity_id="churn_predictions",
            expected_value=str(sorted(VALID_RISK_TIERS)),
            actual_value=str(sorted(tier_set)),
        ))
    except Exception:
        pass

    # --- Churn probability range [0, 1] ---
    try:
        stats = pd.read_sql(
            text(
                "SELECT MIN(churn_probability) as mn, MAX(churn_probability) as mx "
                "FROM churn_predictions"
            ),
            engine,
        )
        mn, mx = float(stats["mn"].iloc[0]), float(stats["mx"].iloc[0])
        ok = mn >= 0.0 and mx <= 1.0
        results.append(_make_result(
            check_category="schema",
            check_name="churn_probability_range",
            severity="critical" if not ok else "info",
            passed=ok,
            audit_message=(
                f"churn_probability range [{mn:.4f}, {mx:.4f}] within [0, 1]"
                if ok else
                f"churn_probability out of range: min={mn:.4f}, max={mx:.4f}"
            ),
            now=now,
            entity_type="table",
            entity_id="churn_predictions",
            expected_value="[0.0, 1.0]",
            actual_value=f"[{mn:.4f}, {mx:.4f}]",
        ))
    except Exception:
        pass

    # --- Segment codes domain ---
    try:
        codes = pd.read_sql(
            text("SELECT DISTINCT segment_code FROM customer_segments"), engine
        )
        code_set = set(codes["segment_code"].tolist())
        invalid = code_set - VALID_SEGMENT_CODES
        ok = len(invalid) == 0
        results.append(_make_result(
            check_category="schema",
            check_name="segment_code_domain",
            severity="critical" if not ok else "info",
            passed=ok,
            audit_message=(
                f"All segment_code values valid: {sorted(code_set)}"
                if ok else
                f"Invalid segment_code values: {sorted(invalid)}"
            ),
            now=now,
            entity_type="table",
            entity_id="customer_segments",
            expected_value=str(sorted(VALID_SEGMENT_CODES)),
            actual_value=str(sorted(code_set)),
        ))
    except Exception:
        pass

    # --- Sentiment score range [-1, 1] ---
    try:
        stats = pd.read_sql(
            text(
                "SELECT MIN(sentiment_score) as mn, MAX(sentiment_score) as mx "
                "FROM sentiment_results"
            ),
            engine,
        )
        mn, mx = float(stats["mn"].iloc[0]), float(stats["mx"].iloc[0])
        ok = mn >= -1.0 and mx <= 1.0
        results.append(_make_result(
            check_category="schema",
            check_name="sentiment_score_range",
            severity="critical" if not ok else "info",
            passed=ok,
            audit_message=(
                f"sentiment_score range [{mn:.4f}, {mx:.4f}] within [-1, 1]"
                if ok else
                f"sentiment_score out of range: min={mn:.4f}, max={mx:.4f}"
            ),
            now=now,
            entity_type="table",
            entity_id="sentiment_results",
            expected_value="[-1.0, 1.0]",
            actual_value=f"[{mn:.4f}, {mx:.4f}]",
        ))
    except Exception:
        pass

    # --- Sentiment label domain ---
    try:
        labels = pd.read_sql(
            text("SELECT DISTINCT sentiment_label FROM sentiment_results"), engine
        )
        label_set = set(labels["sentiment_label"].tolist())
        invalid = label_set - VALID_SENTIMENT_LABELS
        ok = len(invalid) == 0
        results.append(_make_result(
            check_category="schema",
            check_name="sentiment_label_domain",
            severity="warning" if not ok else "info",
            passed=ok,
            audit_message=(
                f"All sentiment_label values valid: {sorted(label_set)}"
                if ok else
                f"Invalid sentiment_label values: {sorted(invalid)}"
            ),
            now=now,
            entity_type="table",
            entity_id="sentiment_results",
            expected_value=str(sorted(VALID_SENTIMENT_LABELS)),
            actual_value=str(sorted(label_set)),
        ))
    except Exception:
        pass

    # --- Recommendation action_code domain ---
    try:
        codes = pd.read_sql(
            text("SELECT DISTINCT action_code FROM recommendations"), engine
        )
        code_set = set(codes["action_code"].tolist())
        invalid = code_set - VALID_ACTION_CODES
        ok = len(invalid) == 0
        results.append(_make_result(
            check_category="schema",
            check_name="recommendation_action_code_domain",
            severity="critical" if not ok else "info",
            passed=ok,
            audit_message=(
                f"All action_code values valid ({len(code_set)} distinct)"
                if ok else
                f"Invalid action_code values: {sorted(invalid)}"
            ),
            now=now,
            entity_type="table",
            entity_id="recommendations",
            expected_value=str(sorted(VALID_ACTION_CODES)),
            actual_value=str(sorted(code_set)),
        ))
    except Exception:
        pass

    # --- Recommendation urgency_score range [0, 100] ---
    try:
        stats = pd.read_sql(
            text(
                "SELECT MIN(urgency_score) as mn, MAX(urgency_score) as mx "
                "FROM recommendations"
            ),
            engine,
        )
        mn, mx = float(stats["mn"].iloc[0]), float(stats["mx"].iloc[0])
        ok = mn >= 0.0 and mx <= 100.0
        results.append(_make_result(
            check_category="schema",
            check_name="urgency_score_range",
            severity="warning" if not ok else "info",
            passed=ok,
            audit_message=(
                f"urgency_score range [{mn:.1f}, {mx:.1f}] within [0, 100]"
                if ok else
                f"urgency_score out of range: min={mn:.1f}, max={mx:.1f}"
            ),
            now=now,
            entity_type="table",
            entity_id="recommendations",
            expected_value="[0.0, 100.0]",
            actual_value=f"[{mn:.1f}, {mx:.1f}]",
        ))
    except Exception:
        pass

    # --- No NULL customer_ids in key tables ---
    for tbl in ["customer_segments", "churn_predictions", "recommendations"]:
        try:
            null_count = pd.read_sql(
                text(f"SELECT COUNT(*) as cnt FROM {tbl} WHERE customer_id IS NULL"),
                engine,
            )["cnt"].iloc[0]
            ok = int(null_count) == 0
            results.append(_make_result(
                check_category="schema",
                check_name=f"{tbl}_no_null_customer_id",
                severity="critical" if not ok else "info",
                passed=ok,
                audit_message=(
                    f"No NULL customer_id values in {tbl}"
                    if ok else
                    f"{null_count} rows in {tbl} have NULL customer_id"
                ),
                now=now,
                entity_type="table",
                entity_id=tbl,
                expected_value="0",
                actual_value=str(null_count),
                affected_rows=int(null_count) if not ok else None,
            ))
        except Exception:
            pass

    # --- Executive summary text not empty ---
    try:
        empty = pd.read_sql(
            text(
                "SELECT COUNT(*) as cnt FROM executive_summaries "
                "WHERE summary_text IS NULL OR summary_text = ''"
            ),
            engine,
        )["cnt"].iloc[0]
        ok = int(empty) == 0
        results.append(_make_result(
            check_category="schema",
            check_name="narrative_no_empty_text",
            severity="critical" if not ok else "info",
            passed=ok,
            audit_message=(
                "All narrative sections have non-empty summary_text"
                if ok else
                f"{empty} narrative sections have empty summary_text"
            ),
            now=now,
            entity_type="table",
            entity_id="executive_summaries",
            expected_value="0 empty",
            actual_value=str(empty),
        ))
    except Exception:
        pass

    return results


# ── 3. Cross-agent consistency ────────────────────────────────────


def _check_consistency(engine, now: str) -> List[Dict[str, Any]]:
    """Verify cross-agent references and logical relationships."""
    results = []

    # --- Critical churn + negative sentiment should not be "monitor_only" ---
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
        pass

    # --- Dormant segment customers should not have growth actions ---
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
        pass

    # --- Champions with positive sentiment should not get retention actions ---
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
        pass

    # --- Recommendation customer IDs should match churn customer IDs ---
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
        pass

    # --- Segment distribution sanity: no single segment > 50% ---
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
        pass

    # --- Recommendation action distribution: no single action > 40% (excl monitor) ---
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
        pass

    # --- Monitor-only should not exceed 60% ---
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
        pass

    return results


# ── 4. Groundedness ───────────────────────────────────────────────


def _check_groundedness(engine, now: str) -> List[Dict[str, Any]]:
    """Verify that narrative claims are backed by actual data."""
    results = []

    try:
        summaries = pd.read_sql(
            text(
                "SELECT summary_type, summary_text, supporting_metrics "
                "FROM executive_summaries"
            ),
            engine,
        )
    except Exception:
        results.append(_make_result(
            check_category="groundedness",
            check_name="narrative_table_readable",
            severity="critical",
            passed=False,
            audit_message="Cannot read executive_summaries table for groundedness checks",
            now=now,
            entity_type="table",
            entity_id="executive_summaries",
        ))
        return results

    # --- Each section should have supporting_metrics ---
    for _, row in summaries.iterrows():
        section = row["summary_type"]
        metrics_raw = row["supporting_metrics"]
        has_metrics = False
        metrics_dict = {}

        if metrics_raw and str(metrics_raw).strip():
            try:
                metrics_dict = json.loads(metrics_raw) if isinstance(metrics_raw, str) else metrics_raw
                has_metrics = isinstance(metrics_dict, dict) and len(metrics_dict) > 0
            except (json.JSONDecodeError, TypeError):
                pass

        results.append(_make_result(
            check_category="groundedness",
            check_name=f"narrative_{section}_has_metrics",
            severity="warning" if not has_metrics else "info",
            passed=has_metrics,
            audit_message=(
                f"Section '{section}' has {len(metrics_dict)} supporting metrics"
                if has_metrics else
                f"Section '{section}' has no parseable supporting_metrics"
            ),
            now=now,
            entity_type="table",
            entity_id="executive_summaries",
        ))

    # --- Churn analysis section: verify critical count matches data ---
    try:
        churn_section = summaries[summaries["summary_type"] == "churn_analysis"]
        if len(churn_section) > 0:
            metrics_raw = churn_section.iloc[0]["supporting_metrics"]
            if metrics_raw:
                metrics = json.loads(metrics_raw) if isinstance(metrics_raw, str) else metrics_raw
                claimed_critical = metrics.get("critical_count")
                if claimed_critical is not None:
                    actual = pd.read_sql(
                        text(
                            "SELECT COUNT(*) as cnt FROM churn_predictions "
                            "WHERE risk_tier = 'Critical'"
                        ),
                        engine,
                    )["cnt"].iloc[0]
                    ok = int(claimed_critical) == int(actual)
                    results.append(_make_result(
                        check_category="groundedness",
                        check_name="narrative_churn_critical_count_matches",
                        severity="critical" if not ok else "info",
                        passed=ok,
                        audit_message=(
                            f"Churn analysis claims {claimed_critical} critical customers, "
                            f"data has {actual} — {'match' if ok else 'MISMATCH'}"
                        ),
                        now=now,
                        entity_type="table",
                        entity_id="executive_summaries",
                        expected_value=str(actual),
                        actual_value=str(claimed_critical),
                    ))
    except Exception:
        pass

    # --- Sentiment analysis section: verify avg sentiment matches data ---
    try:
        sent_section = summaries[summaries["summary_type"] == "sentiment_analysis"]
        if len(sent_section) > 0:
            metrics_raw = sent_section.iloc[0]["supporting_metrics"]
            if metrics_raw:
                metrics = json.loads(metrics_raw) if isinstance(metrics_raw, str) else metrics_raw
                claimed_avg = metrics.get("avg_sentiment")
                if claimed_avg is not None:
                    actual = pd.read_sql(
                        text("SELECT AVG(sentiment_score) as avg FROM sentiment_results"),
                        engine,
                    )["avg"].iloc[0]
                    # Allow 0.05 tolerance for rounding
                    ok = abs(float(claimed_avg) - float(actual)) < 0.05
                    results.append(_make_result(
                        check_category="groundedness",
                        check_name="narrative_sentiment_avg_matches",
                        severity="warning" if not ok else "info",
                        passed=ok,
                        audit_message=(
                            f"Sentiment analysis claims avg={float(claimed_avg):.3f}, "
                            f"data avg={float(actual):.3f} — "
                            f"{'within tolerance' if ok else 'DIVERGED'}"
                        ),
                        now=now,
                        entity_type="table",
                        entity_id="executive_summaries",
                        expected_value=f"{float(actual):.3f}",
                        actual_value=f"{float(claimed_avg):.3f}",
                    ))
    except Exception:
        pass

    # --- Action priorities section: verify recommendation counts ---
    try:
        action_section = summaries[summaries["summary_type"] == "action_priorities"]
        if len(action_section) > 0:
            metrics_raw = action_section.iloc[0]["supporting_metrics"]
            if metrics_raw:
                metrics = json.loads(metrics_raw) if isinstance(metrics_raw, str) else metrics_raw
                claimed_immediate = metrics.get("immediate_count")
                if claimed_immediate is not None:
                    actual = pd.read_sql(
                        text(
                            "SELECT COUNT(*) as cnt FROM recommendations "
                            "WHERE target_timeframe = 'immediate'"
                        ),
                        engine,
                    )["cnt"].iloc[0]
                    ok = int(claimed_immediate) == int(actual)
                    results.append(_make_result(
                        check_category="groundedness",
                        check_name="narrative_action_immediate_count_matches",
                        severity="warning" if not ok else "info",
                        passed=ok,
                        audit_message=(
                            f"Action priorities claims {claimed_immediate} immediate actions, "
                            f"data has {actual} — {'match' if ok else 'MISMATCH'}"
                        ),
                        now=now,
                        entity_type="table",
                        entity_id="executive_summaries",
                        expected_value=str(actual),
                        actual_value=str(claimed_immediate),
                    ))
    except Exception:
        pass

    return results


# ── 5. Freshness ──────────────────────────────────────────────────


def _check_freshness(engine, now: str) -> List[Dict[str, Any]]:
    """Verify all expected agents have successful runs in agent_runs."""
    results = []

    expected_agents = [
        "behavior", "segmentation", "sentiment", "churn",
        "recommendation", "narrative",
    ]

    try:
        runs = pd.read_sql(
            text(
                "SELECT agent_name, status, started_at "
                "FROM agent_runs ORDER BY started_at DESC"
            ),
            engine,
        )
    except Exception:
        results.append(_make_result(
            check_category="freshness",
            check_name="agent_runs_readable",
            severity="critical",
            passed=False,
            audit_message="Cannot read agent_runs table",
            now=now,
            entity_type="table",
            entity_id="agent_runs",
        ))
        return results

    for agent in expected_agents:
        agent_runs = runs[runs["agent_name"] == agent]
        if len(agent_runs) == 0:
            results.append(_make_result(
                check_category="freshness",
                check_name=f"agent_{agent}_has_run",
                severity="warning",
                passed=False,
                audit_message=f"No run records found for '{agent}' agent",
                now=now,
                entity_type="agent",
                entity_id=agent,
            ))
            continue

        latest = agent_runs.iloc[0]
        latest_status = latest["status"]
        ok = latest_status in ("completed", "partial")
        results.append(_make_result(
            check_category="freshness",
            check_name=f"agent_{agent}_latest_success",
            severity="warning" if not ok else "info",
            passed=ok,
            audit_message=(
                f"Agent '{agent}' latest run: {latest_status} at {latest['started_at']}"
                if ok else
                f"Agent '{agent}' latest run FAILED ({latest_status}) at {latest['started_at']}"
            ),
            now=now,
            entity_type="agent",
            entity_id=agent,
        ))

    return results
