"""Freshness checks for pipeline outputs."""

from typing import Any, Dict, List
import pandas as pd
from sqlalchemy import text
from app.agents.auditing.results import _make_result


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
