from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import Base, engine
from app.routes.agents import router as agents_router
from app.routes.workspaces import router as workspaces_router
from app.routes.churn import router as churn_router
from app.routes.customers import router as customers_router
from app.routes.overview import router as overview_router
from app.routes.query import router as query_router
from app.routes.recommendations import router as recommendations_router
from app.routes.segments import router as segments_router
from app.routes.sentiment import router as sentiment_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all ORM-defined tables exist with proper constraints
    import app.models  # noqa: F401 — register all models with Base
    Base.metadata.create_all(bind=engine)

    # Initialize workspace metadata database
    from app.services.workspace_manager import init_metadata_db
    init_metadata_db()

    yield


app = FastAPI(
    title="Nexus Intelligence API",
    description="Multi-Agent Customer Intelligence Dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
