"""
Workspace generation orchestration.

Generates synthetic data and runs the full 8-agent pipeline for a workspace.
Runs in a background thread, updating workspace status at each stage.

Stage map (14 total):
    1-7:  Data generation (customers, subscriptions, orders, events, tickets, feedback, campaigns)
    8-13: Agent pipeline (Behavior, Segmentation, Sentiment, Churn, Recommendation, Narrative)
    14:   Finalizing (AuditAgent + QueryAgent)
"""

import importlib
import json
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy.orm import sessionmaker

from app.db.workspace_db import (
    ensure_workspace_dirs,
    get_workspace_db_path,
    get_workspace_engine,
)
from app.services.workspace_manager import (
    get_workspace,
    prepare_for_regeneration,
    update_workspace_status,
)

# ── Import path for scripts/generate_data.py ───────────────────
PROJ_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS_DIR = str(PROJ_ROOT / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

# ── Constants ──────────────────────────────────────────────────
TOTAL_STAGES = 14


@dataclass(frozen=True)
class AgentSpec:
    """One node in the pipeline DAG.

    `critical=True` agents produce data the dashboard depends on, so a hard
    failure must stop the run. Non-critical agents (narrative, audit, query
    indexing) degrade gracefully — a failure is recorded as a warning but the
    workspace still completes.
    """

    label: str
    module: str
    class_name: str
    critical: bool


PIPELINE = [
    AgentSpec("BehaviorAgent", "app.agents.behavior_agent", "BehaviorAgent", True),
    AgentSpec("SegmentationAgent", "app.agents.segmentation_agent", "SegmentationAgent", True),
    AgentSpec("SentimentAgent", "app.agents.sentiment_agent", "SentimentAgent", True),
    AgentSpec("ChurnAgent", "app.agents.churn_agent", "ChurnAgent", True),
    AgentSpec("RecommendationAgent", "app.agents.recommendation_agent", "RecommendationAgent", True),
    AgentSpec("NarrativeAgent", "app.agents.narrative_agent", "NarrativeAgent", False),
    AgentSpec("AuditAgent", "app.agents.audit_agent", "AuditAgent", False),
    AgentSpec("QueryAgent", "app.agents.query_agent", "QueryAgent", False),
]


def generation_timeout_seconds(customer_count: int) -> int:
    """Generous timeout budget that scales with workspace size.

    Data generation and the ML/SHAP agents grow with customer count, so a
    fixed 5-minute cap killed legitimate large runs. Floor of 15 minutes,
    plus ~0.25s per customer, so a 5k workspace gets ~30 minutes.
    """
    return max(900, 600 + int((customer_count or 0) * 0.25))


def classify_agent_outcome(
    label: str, critical: bool, status: str
) -> Tuple[str, Optional[str]]:
    """Decide what a single agent's `_status` means for the run.

    Returns (action, message) where action is:
      - "ok":    agent completed cleanly
      - "warn":  degraded — record a warning but keep going
      - "fatal": a required agent failed — abort the run
    """
    if status == "completed":
        return "ok", None
    if status == "failed" and critical:
        return "fatal", f"{label} failed and is required for the dashboard"
    if status == "failed":
        return "warn", f"{label} failed (non-critical) — its section may be unavailable"
    return "warn", f"{label} completed with warnings"


def start_generation(workspace_id: str) -> bool:
    """Start workspace generation in a background thread.

    Marks the workspace as 'generating' immediately and spawns the
    generation thread. Returns False if the workspace doesn't exist
    or is not in a valid state for generation.
    """
    ws = get_workspace(workspace_id)
    if not ws:
        return False
    if ws.status not in ("created", "failed", "ready"):
        return False

    # For failed/ready workspaces, delete stale DB and reset progress
    if ws.status in ("failed", "ready"):
        if not prepare_for_regeneration(workspace_id):
            return False
    else:
        # Fresh workspace — just mark as generating
        update_workspace_status(
            workspace_id, "generating",
            current_stage="Initializing workspace",
            stage_index=0,
            total_stages=TOTAL_STAGES,
        )

    thread = threading.Thread(
        target=_run_generation,
        args=(workspace_id,),
        daemon=True,
    )
    thread.start()
    return True


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

        # ── Phase 1: Synthetic Data Generation (stages 1-7) ────────
        _check_timeout()
        ensure_workspace_dirs()
        ws_engine = get_workspace_engine(workspace_id)

        # Map generate_data.py stage indices to the names the frontend expects
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
            stage_label = _DATA_STAGE_NAMES.get(index, name)
            update_workspace_status(
                workspace_id, "generating",
                current_stage=stage_label,
                stage_index=index,
                total_stages=TOTAL_STAGES,
            )

        from generate_data import generate_dataset

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

        # ── Write workspace context for agents/routes ──────────────
        _write_workspace_context(ws_engine, config)

        # ── Phase 2: Agent Pipeline (stages 8-14) ─────────────────
        WsSession = sessionmaker(bind=ws_engine)
        warnings: list[str] = []

        for i, spec in enumerate(PIPELINE):
            _check_timeout()
            # Stages 8-13: individual agents, stage 14: finalize
            if i <= 5:
                stage_name = f"Running {spec.label}"
                stage_index = 8 + i
            elif i == 6:
                stage_name = "Finalizing workspace"
                stage_index = 14
            else:
                # i == 7 (QueryAgent) — still in "Finalizing" stage
                stage_name = None

            if stage_name:
                update_workspace_status(
                    workspace_id, "generating",
                    current_stage=stage_name,
                    stage_index=stage_index,
                    total_stages=TOTAL_STAGES,
                )

            module = importlib.import_module(spec.module)
            agent_class = getattr(module, spec.class_name)
            agent = agent_class()

            db = WsSession()
            try:
                result = agent.execute(db)
            finally:
                db.close()

            # BaseAgent.execute swallows agent exceptions and returns a status
            # dict — inspect it so a crashed agent doesn't silently yield a
            # "ready" workspace with empty tables.
            agent_status = (result or {}).get("_status", "failed")
            action, message = classify_agent_outcome(
                spec.label, spec.critical, agent_status
            )
            if action == "fatal":
                raise RuntimeError(message)
            if action == "warn":
                warnings.append(message)

        # ── Done ───────────────────────────────────────────────────
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
        for key, value in context_rows.items():
            conn.execute(
                text("INSERT INTO workspace_context (key, value) VALUES (:k, :v)"),
                {"k": key, "v": value},
            )
