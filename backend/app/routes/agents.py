from fastapi import APIRouter, Depends
from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.utils.error_handling import handle_errors
from app.models.agent_run import AgentRun
from app.models.audit_result import AuditResult
from app.schemas.agent import AgentsSummaryResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/summary", response_model=AgentsSummaryResponse)
@handle_errors("get_agents_summary")
def get_agents_summary(db: Session = Depends(get_db)):
    """Combined audit summary and agent run history."""
    total_checks, passed, critical_failures, warnings = db.query(
        func.count(AuditResult.audit_id),
        func.coalesce(func.sum(AuditResult.passed), 0),
        func.coalesce(func.sum(case(((AuditResult.passed == 0) & (AuditResult.severity == "critical"), 1), else_=0)), 0),
        func.coalesce(func.sum(case(((AuditResult.passed == 0) & (AuditResult.severity == "warning"), 1), else_=0)), 0),
    ).one()
    failed = total_checks - passed

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

    ranked_runs = select(
        AgentRun.id,
        func.row_number().over(
            partition_by=AgentRun.agent_name,
            order_by=(desc(AgentRun.started_at), desc(AgentRun.id)),
        ).label("rank"),
    ).subquery()
    runs = db.query(AgentRun).filter(AgentRun.id.in_(
        select(ranked_runs.c.id).where(ranked_runs.c.rank == 1)
    )).order_by(desc(AgentRun.started_at)).all()
    latest_runs = [
        {field: getattr(run, field) for field in (
            "id", "agent_name", "run_id", "status", "started_at",
            "completed_at", "duration_ms", "tokens_used", "model_used",
        )}
        for run in runs
    ]

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
