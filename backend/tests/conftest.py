"""
Test fixtures for Luminosity Intelligence backend.

Provides full database isolation using temp directories so tests
never touch production data/ files.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Create an isolated temp directory and monkeypatch all DB paths."""
    tmp = tmp_path_factory.mktemp("luminosity_test")
    ws_dir = tmp / "workspaces"
    ws_dir.mkdir()

    # -- Patch database.py paths --
    import app.db.database as db_mod

    test_db_path = str(tmp / "nexus.db")
    test_db_url = f"sqlite:///{test_db_path}"
    test_engine = create_engine(test_db_url, echo=False)
    test_session_local = sessionmaker(bind=test_engine)

    db_mod.DATABASE_PATH = test_db_path
    db_mod.DATABASE_URL = test_db_url
    db_mod.engine = test_engine
    db_mod.SessionLocal = test_session_local

    # -- Patch workspace_db.py paths --
    import app.db.workspace_db as ws_mod

    test_meta_path = tmp / "workspaces.db"
    test_meta_engine = create_engine(f"sqlite:///{test_meta_path}", echo=False)
    test_meta_session = sessionmaker(bind=test_meta_engine)

    ws_mod.DATA_DIR = tmp
    ws_mod.WORKSPACES_DIR = ws_dir
    ws_mod.METADATA_DB_PATH = test_meta_path
    ws_mod.metadata_engine = test_meta_engine
    ws_mod.MetadataSession = test_meta_session

    # -- Patch workspace_manager.py imported references --
    # workspace_manager captures MetadataSession/metadata_engine at import time,
    # so we must patch its local names too.
    import app.services.workspace_manager as wm_mod

    wm_mod.MetadataSession = test_meta_session
    wm_mod.metadata_engine = test_meta_engine

    return tmp


@pytest.fixture(scope="session")
def test_app(test_data_dir):
    """Import the FastAPI app after DB isolation is in place."""
    from app.db.database import Base, engine
    from app.db.workspace_db import WorkspaceBase, metadata_engine

    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    WorkspaceBase.metadata.create_all(bind=metadata_engine)

    from app.main import app
    return app


@pytest.fixture
async def client(test_app):
    """Async HTTP client wired to the test app."""
    import httpx

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
