#!/usr/bin/env python3
"""
run_pipeline.py — Run all 8 Nexus Intelligence agents in dependency order.

Usage:
    python scripts/run_pipeline.py              # normal run
    python scripts/run_pipeline.py --clean      # drop derived tables, clean agent_runs, recreate with ORM constraints, then run

Pipeline order (each agent depends on predecessors):
    1. BehaviorAgent      → customer_features
    2. SegmentationAgent  → customer_segments
    3. SentimentAgent     → sentiment_results
    4. ChurnAgent         → churn_predictions
    5. RecommendationAgent → recommendations
    6. NarrativeAgent     → executive_summaries
    7. AuditAgent         → audit_results
    8. QueryAgent         → query_results
"""

import argparse
import sys
import time
from pathlib import Path

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import text

from app.db.database import Base, SessionLocal, engine

# ── Derived tables (pipeline outputs) ────────────────────────────
DERIVED_TABLES = [
    "query_results",
    "audit_results",
    "executive_summaries",
    "recommendations",
    "churn_predictions",
    "sentiment_results",
    "customer_segments",
    "customer_features",
]

# ── Pipeline order ───────────────────────────────────────────────
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


def clean_tables():
    """Drop derived tables, clean agent_runs, and recreate with ORM constraints."""
    print("\n=== CLEAN MODE ===")

    with engine.connect() as conn:
        # Drop derived tables in reverse dependency order
        for table in DERIVED_TABLES:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            print(f"  Dropped {table}")

        # Clean stale agent_runs
        conn.execute(text("DELETE FROM agent_runs"))
        print("  Cleaned agent_runs")

        conn.commit()

    # Recreate all tables with ORM-defined constraints (PKs, NOT NULLs, indexes)
    import app.models  # noqa: F401 — register all models
    Base.metadata.create_all(bind=engine)
    print("  Recreated tables with ORM constraints\n")


def run_agent(label: str, module_path: str, class_name: str) -> dict:
    """Import, instantiate, and execute a single agent."""
    import importlib
    module = importlib.import_module(module_path)
    agent_class = getattr(module, class_name)
    agent = agent_class()

    db = SessionLocal()
    try:
        output = agent.execute(db)
        return output
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Run the Nexus Intelligence agent pipeline")
    parser.add_argument("--clean", action="store_true", help="Drop derived tables and recreate with ORM constraints before running")
    args = parser.parse_args()

    if args.clean:
        clean_tables()

    print("=== NEXUS INTELLIGENCE PIPELINE ===\n")
    total_start = time.time()
    results = {}

    for i, (label, module_path, class_name) in enumerate(PIPELINE, 1):
        print(f"[{i}/8] Running {label}...", end=" ", flush=True)
        start = time.time()

        try:
            output = run_agent(label, module_path, class_name)
            elapsed = time.time() - start
            status = output.get("status", "unknown")
            rows = output.get("rows_affected", "?")
            print(f"{status} ({rows} rows, {elapsed:.1f}s)")
            results[label] = output
        except Exception as e:
            elapsed = time.time() - start
            print(f"FAILED ({elapsed:.1f}s): {e}")
            results[label] = {"status": "failed", "error": str(e)}
            # Continue pipeline — downstream agents may still produce partial results

    total_elapsed = time.time() - total_start
    print(f"\n=== PIPELINE COMPLETE ({total_elapsed:.1f}s) ===\n")

    # Summary
    succeeded = sum(1 for r in results.values() if r.get("status") == "completed")
    failed = sum(1 for r in results.values() if r.get("status") == "failed")
    print(f"  Succeeded: {succeeded}/8")
    if failed:
        print(f"  Failed:    {failed}/8")
        for label, r in results.items():
            if r.get("status") == "failed":
                print(f"    - {label}: {r.get('error', 'unknown')}")

    # Verify table row counts
    print("\n=== TABLE VERIFICATION ===\n")
    with engine.connect() as conn:
        for table in reversed(DERIVED_TABLES):
            try:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"  {table}: {count:,} rows")
            except Exception:
                print(f"  {table}: MISSING")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
