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
from pathlib import Path

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

PIPELINE = [
    ("BehaviorAgent", "app.agents.behavior_agent", "BehaviorAgent"),
    ("SegmentationAgent", "app.agents.segmentation_agent", "SegmentationAgent"),
    ("SentimentAgent", "app.agents.sentiment_agent", "SentimentAgent"),
    ("ChurnAgent", "app.agents.churn_agent", "ChurnAgent"),
    ("RecommendationAgent", "app.agents.recommendation_agent", "RecommendationAgent"),
    ("NarrativeAgent", "app.agents.narrative_agent", "NarrativeAgent"),
    ("AuditAgent", "app.agents.audit_agent", "AuditAgent"),
    ("QueryAgent", "app.agents.query_agent", "QueryAgent"),
]


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
        ws = get_workspace(workspace_id)
        if not ws:
            return

        config = json.loads(ws.config_json) if ws.config_json else {}

        # ── Phase 1: Synthetic Data Generation (stages 1-7) ────────
        ensure_workspace_dirs()
        ws_engine = get_workspace_engine(workspace_id)

        def on_data_stage(index, name):
            update_workspace_status(
                workspace_id, "generating",
                current_stage=name,
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

        for i, (label, module_path, class_name) in enumerate(PIPELINE):
            # Stages 8-13: individual agents, stage 14: finalize
            if i <= 5:
                stage_name = f"Running {label}"
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

            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            agent = agent_class()

            db = WsSession()
            try:
                agent.execute(db)
            finally:
                db.close()

        # ── Done ───────────────────────────────────────────────────
        update_workspace_status(workspace_id, "ready")

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
