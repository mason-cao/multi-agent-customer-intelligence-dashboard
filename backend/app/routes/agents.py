from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.utils.error_handling import handle_errors
from app.models.agent_run import AgentRun
from app.models.audit_result import AuditResult

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/summary")
@handle_errors("get_agents_summary")
def get_agents_summary(db: Session = Depends(get_db)):
    """Combined audit summary and agent run history."""
    # Audit summary
    total_checks = db.query(func.count(AuditResult.audit_id)).scalar() or 0
    passed = (
        db.query(func.count(AuditResult.audit_id))
        .filter(AuditResult.passed == 1)
        .scalar()
        or 0
    )
    failed = total_checks - passed
    critical_failures = (
        db.query(func.count(AuditResult.audit_id))
        .filter(AuditResult.passed == 0, AuditResult.severity == "critical")
        .scalar()
        or 0
    )
    warnings = (
        db.query(func.count(AuditResult.audit_id))
        .filter(AuditResult.passed == 0, AuditResult.severity == "warning")
        .scalar()
        or 0
    )

    category_rows = (
        db.query(
            AuditResult.check_category,
            func.sum(AuditResult.passed).label("pass_count"),
            func.count(AuditResult.audit_id).label("total"),
        )
        .group_by(AuditResult.check_category)
        .all()
    )
    check_categories = {
        r.check_category: {"passed": int(r.pass_count), "total": r.total}
        for r in category_rows
    }

    # Agent runs — latest completed run per agent
    runs = (
        db.query(AgentRun)
        .filter(AgentRun.status == "completed")
        .order_by(desc(AgentRun.completed_at))
        .all()
    )

    # Deduplicate to latest per agent
    seen = set()
    latest_runs = []
    for r in runs:
        if r.agent_name not in seen:
            seen.add(r.agent_name)
            latest_runs.append(
                {
                    "id": r.id,
                    "agent_name": r.agent_name,
                    "run_id": r.run_id,
                    "status": r.status,
                    "started_at": r.started_at,
                    "completed_at": r.completed_at,
                    "duration_ms": r.duration_ms,
                    "tokens_used": r.tokens_used,
                    "model_used": r.model_used,
                }
            )

    # Audit check details
    checks = (
        db.query(AuditResult)
        .order_by(AuditResult.check_category, AuditResult.check_name)
        .all()
    )
    audit_checks = [
        {
            "audit_id": c.audit_id,
            "check_category": c.check_category,
            "check_name": c.check_name,
            "severity": c.severity,
            "passed": bool(c.passed),
            "audit_message": c.audit_message,
        }
        for c in checks
    ]

    return {
        "audit": {
            "total_checks": total_checks,
            "passed": passed,
            "failed": failed,
            "critical_failures": critical_failures,
            "warnings": warnings,
            "check_categories": check_categories,
        },
        "runs": latest_runs,
        "checks": audit_checks,
    }
