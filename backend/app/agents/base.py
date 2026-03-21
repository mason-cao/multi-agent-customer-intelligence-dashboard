"""
BaseAgent — abstract base class for all Nexus Intelligence agents.

Every agent inherits from this and implements:
  - name (property): unique agent identifier
  - run(db): execute the agent's logic, return result dict
  - validate_output(output): check result validity

The base class provides:
  - save_run(): writes execution metadata to agent_runs table
  - Structured logging with agent name context
"""

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

    # ------------------------------------------------------------------
    # Abstract interface — every agent must implement these
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent (e.g. 'behavior', 'churn')."""
        ...

    @abstractmethod
    def run(self, db) -> Dict[str, Any]:
        """
        Execute the agent's core logic.

        Args:
            db: SQLAlchemy Session

        Returns:
            Dict with agent-specific output data.
            Must include at minimum: {"status": "completed", "rows_affected": int}
        """
        ...

    @abstractmethod
    def validate_output(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate the agent's output for correctness.

        Args:
            output: The dict returned by run()

        Returns:
            (is_valid, error_messages) — True with empty list if valid,
            False with list of error descriptions if invalid.
        """
        ...

    # ------------------------------------------------------------------
    # Concrete helpers — shared by all agents
    # ------------------------------------------------------------------

    def save_run(
        self,
        db,
        run_id: str,
        status: str,
        started_at: datetime,
        duration_ms: int,
        output_summary: Dict[str, Any] = None,
        tokens_used: int = 0,
        model_used: str = None,
        error_message: str = None,
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

    def execute(self, db, run_id: str = None) -> Dict[str, Any]:
        """
        Full execution wrapper: run + validate + save audit trail.

        This is the method the orchestrator calls. It handles timing,
        error catching, validation, and audit logging.

        Args:
            db: SQLAlchemy Session
            run_id: Pipeline run identifier (groups agents from same execution).
                    If None, generates a standalone run ID.

        Returns:
            The agent's output dict, augmented with validation info.
        """
        run_id = run_id or str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        self._logger.info("agent_starting", run_id=run_id)

        try:
            output = self.run(db)
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

            self.save_run(
                db=db,
                run_id=run_id,
                status="failed",
                started_at=started_at,
                duration_ms=elapsed_ms,
                error_message=str(exc),
            )

            return {
                "status": "failed",
                "error": str(exc),
                "_status": "failed",
                "_validation": {"is_valid": False, "errors": [str(exc)]},
            }
