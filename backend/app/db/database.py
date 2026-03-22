import os

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

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
    """Yield a DB session, routing to the workspace DB when the header is set."""
    db = None
    workspace_id = request.headers.get("x-workspace-id")
    if workspace_id:
        from app.db.workspace_db import get_workspace_db_path, get_workspace_engine

        db_path = get_workspace_db_path(workspace_id)
        if db_path.exists():
            ws_engine = get_workspace_engine(workspace_id)
            WsSession = sessionmaker(bind=ws_engine)
            db = WsSession()

    if db is None:
        db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
