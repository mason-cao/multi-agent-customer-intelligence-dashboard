"""Run deterministic audit categories and persist their findings."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import pandas as pd
from app.agents.base import BaseAgent
from app.db.outputs import replace_output
from app.agents.auditing.definitions import AUDIT_VERSION
from app.agents.auditing.completeness import _check_completeness
from app.agents.auditing.schema_sanity import _check_schema_sanity
from app.agents.auditing.consistency import _check_consistency
from app.agents.auditing.groundedness import _check_groundedness
from app.agents.auditing.freshness import _check_freshness


class AuditAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "audit"

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()
        now = datetime.now(timezone.utc).isoformat()
        results: List[Dict[str, Any]] = []

        checks = (
            _check_completeness, _check_schema_sanity, _check_consistency,
            _check_groundedness, _check_freshness,
        )
        for check in checks:
            findings = check(engine, now)
            results.extend(findings)
            self._logger.info("audit_category_checked", category=check.__name__, checks=len(findings))

        df = pd.DataFrame(results)
        replace_output(db, "audit_results", df)
        self._logger.info("audit_results_written", rows=len(df))

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
            errors.append("No audit checks passed")

        critical = summary.get("critical_failures", 0)
        if critical:
            errors.append(f"{critical} critical audit checks failed")
        categories = summary.get("check_categories", {})
        if len(categories) < 5:
            errors.append(
                f"Only {len(categories)} check categories, expected 5"
            )

        return (len(errors) == 0, errors)
