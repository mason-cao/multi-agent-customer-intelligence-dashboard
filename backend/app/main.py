import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import structlog

from app.db.database import Base, engine
from app.utils.logging import setup_logging
from app.routes.agents import router as agents_router
from app.routes.workspaces import router as workspaces_router
from app.routes.churn import router as churn_router
from app.routes.customers import router as customers_router
from app.routes.overview import router as overview_router
from app.routes.query import router as query_router
from app.routes.recommendations import router as recommendations_router
from app.routes.segments import router as segments_router
from app.routes.sentiment import router as sentiment_router

logger = structlog.get_logger(__name__)


SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def parse_cors_origins(raw_origins: str) -> list[str]:
    """Parse a comma-separated CORS origin list from configuration."""
    return [
        origin.strip()
        for origin in raw_origins.split(",")
        if origin.strip()
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # Ensure all ORM-defined tables exist with proper constraints
    import app.models  # noqa: F401 — register all models with Base
    Base.metadata.create_all(bind=engine)

    # Initialize workspace metadata database
    from app.services.workspace_manager import (
        init_metadata_db,
        reconcile_orphaned_workspaces,
    )
    init_metadata_db()

    # Generation runs in daemon threads that don't survive a restart; fail any
    # workspace left mid-generation so it never hangs forever.
    reconciled = reconcile_orphaned_workspaces()
    if reconciled:
        logger.info("reconciled_orphaned_workspaces", count=reconciled)

    yield


app = FastAPI(
    title="Nova Core API",
    description="Multi-Agent Customer Intelligence Dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

# In production, set CORS_ORIGINS to the deployed frontend URL.
cors_origins = parse_cors_origins(
    os.getenv("CORS_ORIGINS", "http://localhost:5173")
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "X-Admin-Token",
        "X-Workspace-ID",
        "X-Workspace-Token",
    ],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response


app.include_router(overview_router)
app.include_router(segments_router)
app.include_router(churn_router)
app.include_router(recommendations_router)
app.include_router(sentiment_router)
app.include_router(agents_router)
app.include_router(customers_router)
app.include_router(query_router)
app.include_router(workspaces_router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Safety net for any exception not caught by route-level handling."""
    logger.exception(
        "unhandled_exception", path=request.url.path, method=request.method
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
