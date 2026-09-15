#!/usr/bin/env python3
"""Generate a demo dataset: python scripts/generate_data.py --seed 42."""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db.database import Base, engine, DATABASE_PATH
from app.services.data_generation.dataset import generate_dataset


def main(seed: int = 42):
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    # Drop existing tables for clean regeneration of global DB
    import app.models  # noqa: F401
    Base.metadata.drop_all(engine)

    def on_stage(index, name):
        print(f"  [{index}/7] {name}...")

    print("Generating synthetic dataset...\n")
    summary = generate_dataset(
        target_engine=engine,
        seed=seed,
        on_stage=on_stage,
    )

    print("\nDone! Summary:")
    for table_name, count in summary.items():
        print(f"  {table_name}: {count:,} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic Nova Analytics data")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()
    main(args.seed)
