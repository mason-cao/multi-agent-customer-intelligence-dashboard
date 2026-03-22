from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.overview import router as overview_router

app = FastAPI(
    title="Nexus Intelligence API",
    description="Multi-Agent Customer Intelligence Dashboard",
    version="0.1.0",
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
