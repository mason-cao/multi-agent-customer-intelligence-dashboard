"""Shared test helpers."""

from sqlalchemy.orm import sessionmaker

from tests.conftest import ADMIN_HEADERS


async def create_workspace_with_token(
    client,
    name: str = "Authorized Workspace",
    scenario: str = "velocity_saas",
) -> tuple[dict, dict]:
    """Create a workspace and return its API body plus data-route headers."""
    resp = await client.post(
        "/api/workspaces",
        headers=ADMIN_HEADERS,
        json={"name": name, "scenario": scenario},
    )
    assert resp.status_code == 201
    body = resp.json()
    headers = {
        "X-Workspace-ID": body["id"],
        "X-Workspace-Token": body["access_token"],
    }
    return body, headers


def workspace_session(workspace_id: str):
    """Create tables and return a SQLAlchemy session for a workspace DB."""
    from app.db.database import Base
    from app.db.workspace_db import get_workspace_engine

    engine = get_workspace_engine(workspace_id)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()
