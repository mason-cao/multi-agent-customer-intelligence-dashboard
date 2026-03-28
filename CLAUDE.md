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
| **5** | **Infrastructure & Polish** | **In Progress — Tickets 1–5.1 done, Ticket 6 remaining** |
| 6 | Deployment & Presentation | Planned |

### Phase 5 — Infrastructure & Polish (Current)
Reliability, consistency, and maintainability improvements. No new features.

**Completed:**
- Ticket 1: Frontend resilience layer — error boundaries, loading states, API error handling
- Ticket 2: Backend error handling standardization — `handle_errors` decorator on all 19 endpoints, structlog
- Ticket 3: Dashboard empty states for all 8 pages + catch-all 404 route
- Ticket 4: Test infrastructure — pytest conftest with full DB isolation + 10 backend smoke tests
- Ticket 5: Workspace lifecycle hardening — generation timeout, human-readable errors, stale cache invalidation
- Ticket 5.1: Corrective fixes — timestamp transition guard, timeout prefix match, cleanup

**Next:** Implement Ticket 6 — Code consistency pass (final planned Phase 5 ticket).

## Current State

**Branch:** `main`
**HEAD:** `03ae2e1`
**Uncommitted:** Cinematic glassmorphism UI overhaul + Ticket 5/5.1 changes

## UI/Design Baseline

**Cinematic premium glassmorphism** — established direction, preserve unless intentionally changed:
- Deep blue / indigo / violet gradient palette
- Premium layered shell (6 ambient orbs + vignette overlay)
- 4-tier glass panel system (`.glass`, `.glass-surface`, `.glass-elevated`, `.glass-strong`)
- Geist Sans (UI) + Geist Mono (data/numbers) typography
- Recharts for all data visualizations
- `.btn-primary` / `.btn-secondary` button classes
- `.shimmer` skeleton animations

## Tech Stack
- **Frontend**: React 19 + Vite 8 + TypeScript + Tailwind CSS 4 + TanStack Query + Recharts + Lucide React
- **Backend**: FastAPI + SQLAlchemy + Pydantic + Python 3.11.9
- **Database**: SQLite — global `data/nexus.db` + per-workspace `data/workspaces/{id}.db`
- **LLMs**: Mock-first (zero API keys) → Claude 3.5 Sonnet → GPT-4o-mini
- **ML**: scikit-learn (GradientBoosting), SHAP, pandas, numpy
- **Testing**: pytest + pytest-asyncio + httpx (ASGI transport)
- **Deploy**: Railway (backend) + Vercel (frontend) — not yet configured

## Code Style & Conventions
- **Python**: snake_case, type hints, Pydantic models for API schemas, SQLAlchemy ORM models
- **TypeScript**: camelCase variables/functions, PascalCase components/types
- **API**: RESTful, all routes under `/api/`, JSON responses, `{"detail": "..."}` error shape
- **Agents**: All inherit `BaseAgent` ABC with `run()`, `validate_output()`, `execute()`, `save_run()`
- **Write pattern**: All agents use DELETE+INSERT (not `to_sql("replace")`)
- **Error handling**: All route endpoints use `@handle_errors("endpoint_name")` decorator
- **Imports**: Group stdlib → third-party → local. No star imports.
- **Mock-first**: Every agent must work with zero API keys.

## Key Directories
- `backend/app/agents/` — 8 agents + BaseAgent ABC
- `backend/app/routes/` — 8 dashboard route files + workspace routes
- `backend/app/models/` — 17 ORM models + workspace model
- `backend/app/schemas/` — Pydantic schemas + workspace schemas
- `backend/app/services/` — LLM client, feature engine, workspace generator/manager
- `backend/app/utils/` — error_handling.py, logging.py
- `backend/tests/` — conftest.py, test_health.py, test_scenarios.py, test_workspaces.py
- `frontend/src/pages/` — 8 dashboard pages + WorkspaceHub
- `frontend/src/components/charts/` — GlassTooltip, chartTheme, barrel export

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
1. **Commit** uncommitted work (UI overhaul + Ticket 5/5.1)
2. **Implement Ticket 6** — Code consistency pass (response shapes, CORS, README)
3. **Audit Ticket 6**
4. **Determine whether Phase 5 is complete**
5. If Phase 5 closed, move to Phase 6 (Deployment & Presentation)

## Scope Constraints

### Do
- Follow the phase plan in order
- Preserve mock-first architecture in all new work
- Keep the workspace-based synthetic-data product framing
- Maintain the BaseAgent ABC pattern for any agent changes
- Use DELETE+INSERT write pattern for all database writes
- Use `@handle_errors` decorator on all new route endpoints
- Preserve the cinematic glassmorphism UI direction

### Do Not
- Create new agents beyond the 8 implemented
- Add real data ingestion or third-party connectors (not in scope)
- Add stretch features (D3 graphs, cohort heatmaps, PDF export)
- Skip phases or reorder the phase plan
- Describe the project as a "static dashboard"
- Add auth/accounts infrastructure (out of scope)
- Jump into deployment before Phase 5 is complete
