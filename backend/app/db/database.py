import os

from fastapi import HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.security.auth import WORKSPACE_ID_HEADER, WORKSPACE_TOKEN_HEADER

DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "nexus.db",
)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db(request: Request):
    """Yield a DB session, routing to the workspace DB when the header is set.

    Dashboard routes must provide both X-Workspace-ID and X-Workspace-Token.
    If the workspace database does not exist, a 404 is raised immediately —
    dashboard routes must never silently fall back to the global database.
    """
    workspace_id = request.headers.get(WORKSPACE_ID_HEADER)
    if not workspace_id:
        raise HTTPException(status_code=401, detail="Workspace ID required")

    from app.db.workspace_db import (
        get_workspace_db_path,
        get_workspace_engine,
        is_valid_workspace_id,
    )

    if not is_valid_workspace_id(workspace_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid workspace ID",
        )

    workspace_token = request.headers.get(WORKSPACE_TOKEN_HEADER)
    if not workspace_token:
        raise HTTPException(status_code=401, detail="Workspace token required")

    from app.services.workspace_manager import (
        get_workspace,
        validate_workspace_access_token,
    )

    if not get_workspace(workspace_id):
        raise HTTPException(
            status_code=404,
            detail="This workspace doesn't exist.",
        )
    if not validate_workspace_access_token(workspace_id, workspace_token):
        raise HTTPException(status_code=403, detail="Invalid workspace token")

    db_path = get_workspace_db_path(workspace_id)
    if not db_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Workspace database not found: {workspace_id}",
        )
    ws_engine = get_workspace_engine(workspace_id)
    WsSession = sessionmaker(bind=ws_engine)
    db = WsSession()

    try:
        yield db
    finally:
        db.close()
