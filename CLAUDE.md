# Luminosity Intelligence — Project Context

## Project Purpose
Workspace-based customer intelligence platform. Users create workspaces, generate realistic synthetic company data inside the app, and explore AI-driven insights through an executive dashboard. Eight coordinated AI agents transform raw customer data into behavioral profiles, segments, sentiment analysis, churn predictions, recommendations, executive narratives, validation audits, and natural language answers.

**Capstone context**: High school flagship project. Must demonstrate systems architecture, AI engineering, product thinking, and software maturity.

**Critical framing**: This is NOT a static dashboard with pre-loaded fake data. It is an interactive application where the user triggers synthetic data generation and the intelligence layer processes it. The data is synthetic by design — no real company integrations exist or are planned for the current scope.

## Official Phase Plan

| Phase | Name | Status |
|-------|------|--------|
| 1 | Agent Buildout | Complete |
| 2 | Validation & Hardening | Complete |
| 3 | Integration | Complete |
| 4 | Productization | Complete |
| **5** | **Infrastructure & Polish** | **In Progress — Tickets 1–4 committed** |
| 6 | Deployment & Presentation | Planned |

### Phase 5 — Infrastructure & Polish (Current)
Reliability, consistency, and maintainability improvements. No new features.

**Completed:**
- Ticket 1: Frontend resilience layer — error boundaries, loading states, API error handling
- Ticket 2: Backend error handling standardization — `handle_errors` decorator on all 19 endpoints, structlog integration
- Ticket 3: Dashboard empty states for all 8 pages + catch-all 404 route
- Ticket 4: Test infrastructure — pytest conftest with full DB isolation + 10 backend smoke tests

**Next:** Audit Ticket 4, then continue Phase 5 roadmap (Ticket 5+).

## Current State

**Branch:** `main`
**HEAD:** `c8bae3d`

## Tech Stack
- **Frontend**: React 19 + Vite 8 + TypeScript + Tailwind CSS 4 + TanStack Query + Lucide React
- **Backend**: FastAPI + SQLAlchemy + Pydantic + Python 3.11.9
- **Database**: SQLite — global `data/nexus.db` + per-workspace `data/workspaces/{id}.db`
- **LLMs**: Mock-first (zero API keys) → Claude 3.5 Sonnet → GPT-4o-mini
- **ML**: scikit-learn (GradientBoosting), SHAP, pandas, numpy
- **Data Gen**: Faker + numpy (`scripts/`)
- **Testing**: pytest + pytest-asyncio + httpx (ASGI transport)
- **Deploy**: Railway (backend) + Vercel (frontend) — not yet configured

## Code Style & Conventions
- **Python**: snake_case, type hints, Pydantic models for all API schemas, SQLAlchemy ORM models
- **TypeScript**: camelCase for variables/functions, PascalCase for components/types
- **API**: RESTful, all routes under `/api/`, JSON responses, `{"detail": "..."}` error shape
- **Agents**: All inherit from `BaseAgent` ABC with `run()`, `validate_output()`, `execute()`, `save_run()`
- **Write pattern**: All agents use DELETE+INSERT (not `to_sql("replace")`) to preserve ORM constraints
- **Error handling**: All route endpoints use `@handle_errors("endpoint_name")` decorator
- **Imports**: Group stdlib → third-party → local. No star imports.
- **No LangChain**: Custom orchestration is intentional
- **Mock-first**: Every agent must work with zero API keys. LLMClient auto-selects mock → anthropic → openai.

## Key Directories
- `backend/app/agents/` — 8 agents + BaseAgent ABC
- `backend/app/routes/` — 8 dashboard route files + workspace routes
- `backend/app/models/` — 17 ORM models + workspace model
- `backend/app/schemas/` — Pydantic schemas + workspace schemas
- `backend/app/services/` — LLM client, feature engine, workspace generator/manager
- `backend/app/utils/` — error_handling.py, logging.py
- `backend/app/db/` — database.py (workspace-aware get_db), workspace_db.py
- `backend/tests/` — conftest.py, test_health.py, test_scenarios.py, test_workspaces.py
- `frontend/src/pages/` — 8 dashboard pages + WorkspaceHub
- `frontend/src/contexts/` — WorkspaceContext
- `frontend/src/api/` — Axios client (with workspace header), hooks, workspace hooks
- `scripts/` — Data generation (parameterized), pipeline runner

## Pipeline Order
1. BehaviorAgent → `customer_features`
2. SegmentationAgent → `customer_segments`
3. SentimentAgent → `sentiment_results`
4. ChurnAgent → `churn_predictions`
5. RecommendationAgent → `recommendations`
6. NarrativeAgent → `executive_summaries`
7. AuditAgent → `audit_results`
8. QueryAgent → `query_results`

## Known Issues
- `customer_features.avg_sentiment` is NULL for all rows (BehaviorAgent DELETE wipes SentimentAgent updates). Agents compute avg_sentiment from `sentiment_results` directly.
- NL query layer uses strict intent classification + whitelisted SQL — no user text composes SQL.
- Demo must work offline from cached agent outputs.

## Next Session
1. **Audit Ticket 4** (test infrastructure implementation)
2. **Continue Phase 5 roadmap** — define and implement Ticket 5+

## Scope Constraints

### Do
- Follow the phase plan in order
- Preserve mock-first architecture in all new work
- Keep the workspace-based synthetic-data product framing
- Maintain the BaseAgent ABC pattern for any agent changes
- Use DELETE+INSERT write pattern for all database writes
- Use `@handle_errors` decorator on all new route endpoints

### Do Not
- Create new agents beyond the 8 implemented
- Add real data ingestion or third-party connectors (not in scope)
- Add stretch features (D3 graphs, cohort heatmaps, PDF export, dark mode)
- Skip phases or reorder the phase plan
- Describe the project as a "static dashboard"
- Add auth/accounts infrastructure (out of scope)
- Jump into deployment before Phase 5 is complete
