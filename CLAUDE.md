# Nexus Intelligence — Multi-Agent Customer Intelligence Dashboard

## Project Summary
Production-grade customer intelligence platform for fictional B2B SaaS company "Nexus Analytics" (5K customers, 18 months of synthetic data). 8 coordinated AI agents transform raw customer data into actionable insights via an executive dashboard with natural language querying and full agent explainability.

**Capstone context**: High school flagship project. Must demonstrate systems architecture, AI engineering, product thinking, and software maturity.

## Active Features (Tier 2 Target)
- 8 AI agents: Behavior, Segmentation, Sentiment, Churn, Recommendation, Narrative, Audit, Query
- DAG-based parallel orchestration (custom, no LangChain) — planned, not yet implemented
- 8 dashboard pages: Overview, Customer 360, Segments, Churn, Sentiment, Recommendations, Agent Audit, Ask Anything
- ChromaDB vector search for NL queries — planned, not yet implemented
- Full agent audit trail with validation logging

## Tech Stack
- **Frontend**: React 19 + Vite 8 + TypeScript + Tailwind CSS 4 + TanStack Query + Lucide React
- **Backend**: FastAPI + SQLAlchemy + Pydantic + Python 3.11.9
- **Database**: SQLite (file-based, `data/nexus.db`, gitignored)
- **LLMs**: Mock-first (works with zero API keys) → Claude 3.5 Sonnet → GPT-4o-mini
- **ML**: scikit-learn (KMeans, GradientBoosting), SHAP, pandas, numpy
- **Data Gen**: faker + numpy (`scripts/`)
- **Deploy**: Railway (backend) + Vercel (frontend) — not yet configured
- **Testing**: pytest (backend) + Vitest (frontend) — infrastructure exists, no tests written yet

## Code Style & Conventions
- **Python**: snake_case, type hints, Pydantic models for all API schemas, SQLAlchemy ORM models
- **TypeScript**: camelCase for variables/functions, PascalCase for components/types
- **API**: RESTful, all routes under `/api/`, JSON responses
- **Agents**: All inherit from `BaseAgent` ABC with `run()`, `validate_output()`, `execute()`, `save_run()`
- **Imports**: Group stdlib → third-party → local. No star imports.
- **Error handling**: Agents use retry + fallback pattern. API returns proper HTTP status codes.
- **No LangChain**: Custom orchestration is intentional (more impressive, easier to explain)
- **Mock-first**: Every agent must work with zero API keys. LLMClient auto-selects mock → anthropic → openai.

## Key Directories
- `backend/app/agents/` — All 8 agents + base class (no orchestrator yet)
- `backend/app/routes/` — FastAPI route files
- `backend/app/models/` — SQLAlchemy ORM models (17 models)
- `backend/app/schemas/` — Pydantic request/response schemas
- `backend/app/services/` — LLM client, feature engine
- `frontend/src/pages/` — 8 dashboard pages
- `frontend/src/components/` — Layout + shared UI components
- `frontend/src/api/` — API client + TanStack Query hooks
- `scripts/` — Data generation, pipeline runner

## Current Phase
Agent buildout complete. Entering validation and integration.

**Branch:** `agent-validation-and-integration`
**HEAD:** `e069c99`

## Next TODOs (strict order)
- [ ] Audit Ticket 9 (QueryAgent) — formal 8-step audit protocol
- [ ] Full-system pipeline check — all 8 agents end-to-end
- [ ] Integration — wire routes → API → frontend for all 8 pages
- [ ] Orchestrator, ChromaDB, tests, deployment, presentation prep

## Known Issues
- `customer_features.avg_sentiment` is NULL for all rows (BehaviorAgent's `to_sql(replace)` wipes SentimentAgent updates). Agents compute avg_sentiment from `sentiment_results` directly.
- `agent_runs` has 22 rows including stale partial/failed runs from development. Needs cleanup during full-system check.
- Pipeline must run in order: Behavior → Segmentation → Sentiment → Churn → Recommendation → Narrative → Audit → Query
- NL query layer uses strict intent classification + whitelisted SQL — no user text composes SQL
- Demo must work offline from cached agent outputs (never depend on live API during presentation)

## Scope Constraints
- Do not create new agents beyond the 8 implemented
- Do not add stretch features (D3 graph, cohort heatmap, SSE, PDF export, dark mode)
- Do not add orchestration before full-system validation
- Do not add ChromaDB before integration is complete
