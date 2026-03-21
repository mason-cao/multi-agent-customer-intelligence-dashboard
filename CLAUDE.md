# Nexus Intelligence — Multi-Agent Customer Intelligence Dashboard

## Project Summary
Production-grade customer intelligence platform for fictional B2B SaaS company "Nexus Analytics" (5K customers, 18 months of data). Uses 8 coordinated AI agents to transform raw customer data into actionable insights via an executive dashboard with natural language querying and full agent explainability.

**Capstone context**: High school flagship project. Must demonstrate systems architecture, AI engineering, product thinking, and software maturity.

## Active Features (Tier 2 Target)
- 8 AI agents: Sentiment, Segmentation, Behavior, Churn, Anomaly, Recommendation, Narrative, Query
- DAG-based parallel orchestration (custom, no LangChain)
- 8 dashboard pages: Overview, Customer 360, Segments, Churn, Sentiment, Recommendations, Agent Audit, Ask Anything
- ChromaDB vector search for NL queries
- Full agent audit trail with validation logging

## Tech Stack
- **Frontend**: React 18 + Vite + TypeScript + Tremor + Tailwind CSS + Recharts + TanStack Query
- **Backend**: FastAPI + SQLAlchemy + Pydantic + Python 3.9+
- **Database**: SQLite (file-based, `data/nexus.db`)
- **Vector Store**: ChromaDB (embedded mode, `data/chroma/`)
- **LLMs**: Claude 3.5 Sonnet (reasoning/explanations) + GPT-4o-mini (sentiment/high-volume)
- **ML**: scikit-learn (KMeans, GradientBoosting), SHAP, pandas, numpy
- **Data Gen**: faker + numpy
- **Deploy**: Railway (backend) + Vercel (frontend)
- **Testing**: pytest (backend) + Vitest (frontend)

## Code Style & Conventions
- **Python**: snake_case, type hints, Pydantic models for all API schemas, SQLAlchemy ORM models
- **TypeScript**: camelCase for variables/functions, PascalCase for components/types
- **API**: RESTful, all routes under `/api/`, JSON responses
- **Agents**: All inherit from `BaseAgent` ABC with `run()`, `validate_output()`, `get_status()`
- **Imports**: Group stdlib → third-party → local. No star imports.
- **Error handling**: Agents use retry + fallback pattern. API returns proper HTTP status codes.
- **No LangChain**: Custom orchestration is intentional (more impressive, easier to explain)

## Key Directories
- `backend/app/agents/` — All 8 agents + orchestrator + base class
- `backend/app/routes/` — FastAPI route files (one per dashboard page)
- `backend/app/models/` — SQLAlchemy ORM models (one per table)
- `backend/app/schemas/` — Pydantic request/response schemas
- `backend/app/services/` — Shared services (LLM client, vector store, feature engine)
- `frontend/src/pages/` — Dashboard pages (one per route)
- `frontend/src/components/` — Reusable UI components
- `frontend/src/api/` — API client + TanStack Query hooks
- `scripts/` — Data generation, ChromaDB seeding, pipeline runner

## Current Phase
Phase 1: Planning & Setup

## Next TODOs
- [ ] Initialize repo structure (dirs, gitignore, env.example)
- [ ] Set up Python backend (pyproject.toml, FastAPI hello-world)
- [ ] Set up React frontend (Vite + TypeScript + Tremor + Tailwind)
- [ ] Create SQLAlchemy models for all tables
- [ ] Build synthetic data generator

## Known Risks
- NL query SQL generation needs strict whitelisting (no mutation queries)
- LLM costs ~$2-4 per full pipeline run — use GPT-4o-mini for volume tasks
- Demo must work offline from cached agent outputs (never depend on live API during presentation)
