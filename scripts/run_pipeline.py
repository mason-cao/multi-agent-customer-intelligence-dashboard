#!/usr/bin/env python3
"""
run_pipeline.py — Run all 8 Nova Core agents in dependency order.

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
from app.services.pipeline import PIPELINE, execute_pipeline

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


def main():
    parser = argparse.ArgumentParser(description="Run the Nova Core agent pipeline")
    parser.add_argument("--clean", action="store_true", help="Drop derived tables and recreate with ORM constraints before running")
    args = parser.parse_args()

    if args.clean:
        clean_tables()

    print("=== NOVA CORE PIPELINE ===\n")
    total_start = time.time()
    results = {}

    def announce(spec):
        print(f"Running {spec.label}...", end=" ", flush=True)

    for outcome in execute_pipeline(SessionLocal, before_agent=announce):
        output = outcome.output
        status = output.get("_status", "failed")
        rows = output.get("rows_affected", "?")
        print(f"{status} ({rows} rows, {outcome.duration_seconds:.1f}s)")
        results[outcome.spec.label] = output
        if outcome.message:
            print(f"  {outcome.message}")

    total_elapsed = time.time() - total_start
    print(f"\n=== PIPELINE COMPLETE ({total_elapsed:.1f}s) ===\n")

    # Summary
    succeeded = sum(1 for r in results.values() if r.get("_status") == "completed")
    failed = sum(1 for r in results.values() if r.get("_status") == "failed")
    print(f"  Succeeded: {succeeded}/{len(PIPELINE)}")
    if failed:
        print(f"  Failed:    {failed}/{len(PIPELINE)}")
        for label, r in results.items():
            if r.get("_status") == "failed":
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
