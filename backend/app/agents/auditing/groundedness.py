"""Groundedness checks for pipeline outputs."""

import json
from typing import Any, Dict, List
import pandas as pd
from sqlalchemy import text
from app.agents.auditing.results import _make_result, unavailable_result


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

    try:
        churn_section = summaries[summaries["summary_type"] == "churn_analysis"]
        if len(churn_section) > 0:
            metrics_raw = churn_section.iloc[0]["supporting_metrics"]
            if metrics_raw:
                metrics = json.loads(metrics_raw) if isinstance(metrics_raw, str) else metrics_raw
                risk_dist = metrics.get("risk_tier_dist", {})
                claimed_critical = risk_dist.get("Critical", metrics.get("critical_count"))
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
        results.append(unavailable_result("groundedness", "narrative_churn_critical_count_matches", now))

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
        results.append(unavailable_result("groundedness", "narrative_sentiment_avg_matches", now))

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
        results.append(unavailable_result("groundedness", "narrative_action_immediate_count_matches", now))

    return results
