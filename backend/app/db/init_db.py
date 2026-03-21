"""Initialize the database with all tables."""

import os
import sys

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.database import Base, engine, DATABASE_PATH
import app.models  # noqa: F401 — registers all models with Base


def init_database():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    Base.metadata.create_all(engine)
    print(f"Database created at {DATABASE_PATH}")
    print(f"Tables: {list(Base.metadata.tables.keys())}")


if __name__ == "__main__":
    init_database()
