"""Shared pipeline order, run identity, and failure policy for CLI and workers."""

import importlib
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class AgentSpec:
    label: str
    module: str
    class_name: str
    critical: bool
    stage_index: int

    @property
    def stage_name(self) -> str:
        return "Finalizing workspace" if self.stage_index == 14 else f"Running {self.label}"


PIPELINE = (
    AgentSpec("BehaviorAgent", "app.agents.behavior_agent", "BehaviorAgent", True, 8),
    AgentSpec("SegmentationAgent", "app.agents.segmentation_agent", "SegmentationAgent", True, 9),
    AgentSpec("SentimentAgent", "app.agents.sentiment_agent", "SentimentAgent", True, 10),
    AgentSpec("ChurnAgent", "app.agents.churn_agent", "ChurnAgent", True, 11),
    AgentSpec("RecommendationAgent", "app.agents.recommendation_agent", "RecommendationAgent", True, 12),
    AgentSpec("NarrativeAgent", "app.agents.narrative_agent", "NarrativeAgent", False, 13),
    AgentSpec("AuditAgent", "app.agents.audit_agent", "AuditAgent", False, 14),
    AgentSpec("QueryAgent", "app.agents.query_agent", "QueryAgent", False, 14),
)
TOTAL_STAGES = max(spec.stage_index for spec in PIPELINE)


def classify_agent_outcome(
    label: str, critical: bool, status: str,
) -> tuple[Literal["ok", "warn", "fatal"], str | None]:
    if status == "completed":
        return "ok", None
    if status != "partial":
        if critical:
            return "fatal", f"{label} failed and is required for the dashboard"
        return "warn", f"{label} failed (non-critical) — its section may be unavailable"
    return "warn", f"{label} completed with warnings"


@dataclass(frozen=True)
class AgentOutcome:
    spec: AgentSpec
    output: dict[str, Any]
    duration_seconds: float
    action: Literal["ok", "warn", "fatal"]
    message: str | None


def execute_pipeline(
    session_factory: Callable[[], Session],
    *,
    before_agent: Callable[[AgentSpec], None] | None = None,
    specs: tuple[AgentSpec, ...] = PIPELINE,
) -> Iterator[AgentOutcome]:
    """Yield outcomes in dependency order, stopping after a critical failure."""
    run_id = str(uuid.uuid4())
    for spec in specs:
        if before_agent:
            before_agent(spec)
        started = time.monotonic()
        try:
            module = importlib.import_module(spec.module)
            agent = getattr(module, spec.class_name)()
            with session_factory() as db:
                output = agent.execute(db, run_id=run_id)
            status = output.get("_status", "failed")
        except Exception as exc:
            status = "failed"
            output = {"status": status, "_status": status, "error": str(exc)}

        action, message = classify_agent_outcome(spec.label, spec.critical, status)
        yield AgentOutcome(spec, output, time.monotonic() - started, action, message)
        if action == "fatal":
            return
