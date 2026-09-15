"""Execute agents with validation, atomic output writes, and an audit record."""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import structlog

from app.models.agent_run import AgentRun


class BaseAgent(ABC):
    """Abstract base class for all agents in the pipeline."""

    def __init__(self):
        self._logger = structlog.get_logger().bind(agent=self.name)

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent (e.g. 'behavior', 'churn')."""
        ...

    @abstractmethod
    def run(self, db) -> Dict[str, Any]:
        """Produce output in db's transaction; return status and rows_affected.

        Commit is owned by execute(), so failure can roll back all agent writes.
        """
        ...

    @abstractmethod
    def validate_output(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Return (is_valid, errors) for the produced output."""
        ...

    def save_run(
        self,
        db,
        run_id: str,
        status: str,
        started_at: datetime,
        duration_ms: int,
        output_summary: Dict[str, Any] | None = None,
        tokens_used: int = 0,
        model_used: str | None = None,
        error_message: str | None = None,
    ) -> str:
        """
        Write an entry to the agent_runs audit table.

        Returns the generated row ID.
        """
        row_id = str(uuid.uuid4())

        run = AgentRun(
            id=row_id,
            agent_name=self.name,
            run_id=run_id,
            status=status,
            started_at=started_at.isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=duration_ms,
            input_summary=None,
            output_data=None,
            output_summary=json.dumps(output_summary) if output_summary else None,
            error_message=error_message,
            tokens_used=tokens_used,
            model_used=model_used,
        )
        db.add(run)
        db.commit()

        self._logger.info(
            "agent_run_saved",
            run_id=run_id,
            status=status,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
        )
        return row_id

    def execute(self, db, run_id: str | None = None) -> Dict[str, Any]:
        """Run and validate, then commit the output with its audit record.

        Partial validation results are retained; execution failures roll back
        output changes and get a separate failure record.
        """
        run_id = run_id or str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        self._logger.info("agent_starting", run_id=run_id)

        try:
            output = self.run(db)
            if output.get("status") == "failed":
                raise RuntimeError(output.get("error") or f"{self.name} failed")
            elapsed_ms = int(
                (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
            )

            is_valid, errors = self.validate_output(output)

            if is_valid:
                status = "completed"
                self._logger.info(
                    "agent_completed",
                    run_id=run_id,
                    duration_ms=elapsed_ms,
                    rows=output.get("rows_affected", 0),
                )
            else:
                status = "partial"
                self._logger.warning(
                    "agent_partial",
                    run_id=run_id,
                    duration_ms=elapsed_ms,
                    validation_errors=errors,
                )

            output["_validation"] = {"is_valid": is_valid, "errors": errors}
            output["_status"] = status

            self.save_run(
                db=db,
                run_id=run_id,
                status=status,
                started_at=started_at,
                duration_ms=elapsed_ms,
                output_summary={
                    "rows_affected": output.get("rows_affected", 0),
                    "validation_passed": is_valid,
                },
                tokens_used=output.get("tokens_used", 0),
                model_used=output.get("model_used"),
                error_message="; ".join(errors) if errors else None,
            )

            return output

        except Exception as exc:
            elapsed_ms = int(
                (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
            )
            self._logger.error(
                "agent_failed",
                run_id=run_id,
                duration_ms=elapsed_ms,
                error=str(exc),
            )

            # A failed flush leaves the session unusable until rolled back;
            # without this, the audit write below would raise instead of
            # recording the failure.
            try:
                db.rollback()
                self.save_run(
                    db=db,
                    run_id=run_id,
                    status="failed",
                    started_at=started_at,
                    duration_ms=elapsed_ms,
                    error_message=str(exc),
                )
            except Exception:
                self._logger.error("agent_failure_audit_write_failed", run_id=run_id)

            return {
                "status": "failed",
                "error": str(exc),
                "_status": "failed",
                "_validation": {"is_valid": False, "errors": [str(exc)]},
            }
