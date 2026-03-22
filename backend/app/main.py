from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import Base, engine
from app.routes.overview import router as overview_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all ORM-defined tables exist with proper constraints
    import app.models  # noqa: F401 — register all models with Base
    Base.metadata.create_all(bind=engine)
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


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}
