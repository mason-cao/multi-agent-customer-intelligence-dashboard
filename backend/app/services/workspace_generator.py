"""
Workspace generation orchestration.

Generates synthetic data and runs the full 8-agent pipeline for a workspace.
Runs in a background thread, updating workspace status at each stage.

Stage map (14 total):
    1-7:  Data generation (customers, subscriptions, orders, events, tickets, feedback, campaigns)
    8-13: Agent pipeline (Behavior, Segmentation, Sentiment, Churn, Recommendation, Narrative)
    14:   Finalizing (AuditAgent + QueryAgent)
"""

import json
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services.pipeline import AgentSpec, TOTAL_STAGES, execute_pipeline
from app.db.workspace_db import (
    ensure_workspace_dirs,
    get_workspace_engine,
)
from app.services.workspace_manager import (
    get_workspace,
    prepare_for_regeneration,
    update_workspace_status,
)

_GENERATION_LOCK = threading.RLock()
_ACTIVE_GENERATIONS: set[str] = set()


class GenerationStartStatus(str, Enum):
    """Outcome of attempting to start a workspace generation job."""

    STARTED = "started"
    NOT_FOUND = "not_found"
    INVALID_STATUS = "invalid_status"
    CAPACITY_REACHED = "capacity_reached"
    START_FAILED = "start_failed"


@dataclass(frozen=True)
class GenerationStartResult:
    status: GenerationStartStatus
    detail: str


def generation_timeout_seconds(customer_count: int) -> int:
    """Generous timeout budget that scales with workspace size.

    Data generation and the ML/SHAP agents grow with customer count, so a
    fixed 5-minute cap killed legitimate large runs. Floor of 15 minutes,
    plus ~0.25s per customer, so a 5k workspace gets ~30 minutes.
    """
    return max(900, 600 + int((customer_count or 0) * 0.25))


def active_generation_count() -> int:
    """Return the number of generation workers reserved in this process."""
    with _GENERATION_LOCK:
        return len(_ACTIVE_GENERATIONS)


@contextmanager
def generation_start_guard():
    """Serialize demo admission/cleanup with all generation starts.

    The lock is reentrant because demo admission calls start_generation().
    Keep live workers protected even if a poll has marked their record failed.
    """
    with _GENERATION_LOCK:
        yield frozenset(_ACTIVE_GENERATIONS)


def reset_generation_registry():
    """Clear in-process generation reservations.

    Used by tests and startup reconciliation. It does not cancel running
    threads; production recovery of interrupted jobs is handled by workspace
    status reconciliation.
    """
    with _GENERATION_LOCK:
        _ACTIVE_GENERATIONS.clear()


def _release_generation_slot(workspace_id: str):
    with _GENERATION_LOCK:
        _ACTIVE_GENERATIONS.discard(workspace_id)


def _run_generation_with_release(workspace_id: str):
    try:
        _run_generation(workspace_id)
    finally:
        _release_generation_slot(workspace_id)


def start_generation(workspace_id: str) -> GenerationStartResult:
    """Start workspace generation in a background thread.

    Marks the workspace as 'generating' immediately and spawns the
    generation thread. Returns a status describing whether the job was accepted.
    """
    with _GENERATION_LOCK:
        ws = get_workspace(workspace_id)
        if not ws:
            return GenerationStartResult(
                GenerationStartStatus.NOT_FOUND, "This workspace doesn't exist.",
            )
        if ws.status not in ("created", "failed", "ready"):
            return GenerationStartResult(
                GenerationStartStatus.INVALID_STATUS, "This workspace is already being set up.",
            )
        if workspace_id in _ACTIVE_GENERATIONS:
            return GenerationStartResult(
                GenerationStartStatus.INVALID_STATUS,
                "This workspace is already being set up.",
            )
        if len(_ACTIVE_GENERATIONS) >= settings.max_concurrent_generations:
            return GenerationStartResult(
                GenerationStartStatus.CAPACITY_REACHED,
                "Generation capacity reached. Try again later.",
            )
        _ACTIVE_GENERATIONS.add(workspace_id)

    try:
        if ws.status in ("failed", "ready"):
            if not prepare_for_regeneration(workspace_id):
                _release_generation_slot(workspace_id)
                return GenerationStartResult(
                    GenerationStartStatus.NOT_FOUND,
                    "This workspace doesn't exist.",
                )
        else:
            update_workspace_status(
                workspace_id, "generating",
                current_stage="Initializing workspace",
                stage_index=0,
                total_stages=TOTAL_STAGES,
            )

        thread = threading.Thread(
            target=_run_generation_with_release,
            args=(workspace_id,),
            daemon=True,
        )
        thread.start()
    except Exception as exc:
        _release_generation_slot(workspace_id)
        update_workspace_status(workspace_id, "failed", error_message=str(exc))
        return GenerationStartResult(
            GenerationStartStatus.START_FAILED, "Could not start workspace generation.",
        )

    return GenerationStartResult(
        GenerationStartStatus.STARTED,
        "Generation started.",
    )


def _run_generation(workspace_id: str):
    """Full workspace generation: data gen + agent pipeline.

    Called in a background thread. Updates workspace status at each
    stage so the frontend can poll for progress.
    """
    try:
        gen_start = time.monotonic()

        ws = get_workspace(workspace_id)
        if not ws:
            return

        config = json.loads(ws.config_json) if ws.config_json else {}
        timeout_limit = generation_timeout_seconds(config.get("customer_count", 5000))

        def _check_timeout():
            if time.monotonic() - gen_start > timeout_limit:
                raise TimeoutError(
                    f"Generation exceeded {timeout_limit}s limit"
                )

        _check_timeout()
        ensure_workspace_dirs()
        ws_engine = get_workspace_engine(workspace_id)

        # These labels are part of the frontend progress contract.
        _DATA_STAGE_NAMES = {
            1: "Customers",
            2: "Subscriptions",
            3: "Orders",
            4: "Events",
            5: "Tickets",
            6: "Feedback",
            7: "Campaigns",
        }

        def on_data_stage(index, name):
            _check_timeout()
            stage_label = _DATA_STAGE_NAMES.get(index, name)
            update_workspace_status(
                workspace_id, "generating",
                current_stage=stage_label,
                stage_index=index,
                total_stages=TOTAL_STAGES,
            )

        from app.services.data_generation.dataset import generate_dataset

        seed = config.get("seed")
        if seed is None:
            seed = 42

        generate_dataset(
            target_engine=ws_engine,
            customer_count=config.get("customer_count", 5000),
            churn_rate=config.get("churn_rate", 0.15),
            primary_industry=config.get("industry"),
            seed=seed,
            on_stage=on_data_stage,
            include_outage=config.get("include_outage", True),
        )

        _write_workspace_context(ws_engine, config)

        WsSession = sessionmaker(bind=ws_engine)
        warnings: list[str] = []

        def before_agent(spec: AgentSpec):
            _check_timeout()
            update_workspace_status(
                workspace_id, "generating",
                current_stage=spec.stage_name,
                stage_index=spec.stage_index,
                total_stages=TOTAL_STAGES,
            )

        for outcome in execute_pipeline(WsSession, before_agent=before_agent):
            if outcome.action == "fatal":
                raise RuntimeError(outcome.message)
            if outcome.message:
                warnings.append(outcome.message)
        _check_timeout()

        # Guard: if poll-side timeout already marked this failed, don't override
        ws_final = get_workspace(workspace_id)
        if ws_final and ws_final.status == "failed":
            return
        update_workspace_status(
            workspace_id, "ready",
            pipeline_warnings="\n".join(warnings) if warnings else None,
        )

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        update_workspace_status(
            workspace_id, "failed",
            error_message=error_msg,
        )


def _write_workspace_context(engine, config: dict):
    """Write scenario metadata to the workspace_context table."""
    from sqlalchemy import text

    context_rows = {
        "company_name": config.get("company_name", ""),
        "scenario": config.get("scenario", ""),
        "scenario_description": config.get("scenario_description", ""),
        "industry": config.get("industry", ""),
        "profile": config.get("profile", ""),
    }

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM workspace_context"))
        conn.execute(
            text("INSERT INTO workspace_context (key, value) VALUES (:k, :v)"),
            [{"k": key, "v": value} for key, value in context_rows.items()],
        )
