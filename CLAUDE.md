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
| 5 | Infrastructure & Polish | Complete |
| — | UI/UX Elevation | Complete |
| **6** | **Deployment & Presentation** | **In Progress** |

### Phase 5 — Infrastructure & Polish (Complete)
All 6 tickets committed. Reliability, consistency, and maintainability improvements.

### UI/UX Elevation (Complete)
Premium UI/UX improvement pass using Google Stitch MCP + UI-UX Pro Max design intelligence. Plan at `.claude/plans/luminous-bouncing-aurora.md`.

**All 8 tickets committed:**
- A1: Glassmorphism perfection pass — gradient borders, noise texture, hero variant, colored shadows, semantic hover glows, press states, glass scrollbars, nested glass
- A2: Generation Experience Overhaul — full-content-area GenerationView with 14-stage SVG progress ring, vertical timeline, completion celebration, auto-redirect
- B1: Component System Standardization — StatCard, ChartCard, Badge, DataTable reusable components
- B2: Overview Dashboard Hierarchy — hero KPI row, secondary metrics, 60/40 narrative + pipeline health split
- C1: Ask Anything Reimagination — conversational chat thread with user/AI bubbles, auto-scroll, suggested prompts
- C2: Sidebar & Navigation Enhancement — workspace indicator card, page transition animations
- D1: Chart & Table Polish — ChartCard adoption across all chart pages, stagger animations, `formatCompact` helper
- D2: Microinteraction Pass — `useCountUp` animated number hook in StatCard, `prefers-reduced-motion` support

## Current State

**Branch:** `main`
**Working tree:** Modified (Phase 6 deployment prep)

## UI/Design Baseline

**Cinematic premium glassmorphism** — established direction, preserve unless intentionally changed:
- Deep blue / indigo / violet gradient palette
- Premium layered shell (6 ambient orbs + vignette overlay)
- 5-tier glass panel system (`.glass`, `.glass-surface`, `.glass-elevated`, `.glass-strong`, `.glass-hero`)
- `.glass-nested` variant for glass-within-glass composition
- Gradient borders via `background-clip: padding-box, border-box` technique
- SVG noise texture overlay at 3% opacity on all glass surfaces
- Dark-indigo-tinted shadows (`rgba(6,8,20,x)`) — not pure black
- `--glass-hover-glow` CSS custom property for semantic hover colors
- Geist Sans (UI) + Geist Mono (data/numbers) typography
- Recharts for all data visualizations
- `.btn-primary` / `.btn-secondary` button classes
- `.shimmer` skeleton animations
- `.page-transition` CSS animation on route changes
- `useCountUp` hook for animated stat numbers (respects `prefers-reduced-motion`)
- Reusable component kit: StatCard, ChartCard, Badge, DataTable
- GenerationView with SVG progress ring + vertical timeline for workspace generation

## Tech Stack
- **Frontend**: React 19 + Vite 8 + TypeScript + Tailwind CSS 4 + TanStack Query + Recharts + Lucide React
- **Backend**: FastAPI + SQLAlchemy + Pydantic + Python 3.11.9
- **Database**: SQLite — global `data/nexus.db` + per-workspace `data/workspaces/{id}.db`
- **LLMs**: Mock-first (zero API keys) → Claude 3.5 Sonnet → GPT-4o-mini
- **ML**: scikit-learn (GradientBoosting), SHAP, pandas, numpy
- **Testing**: pytest + pytest-asyncio + httpx (ASGI transport)
- **Deploy**: Railway (backend, Docker + persistent volume) + Vercel (frontend, API rewrites)

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
- `frontend/src/pages/` — 8 dashboard pages + WorkspaceHub + GenerationView
- `frontend/src/components/shared/` — StatCard, ChartCard, Badge, DataTable, Card, PageHeader, EmptyState
- `frontend/src/components/charts/` — GlassTooltip, chartTheme, barrel export
- `frontend/src/hooks/` — useCountUp (animated number hook)
- `frontend/public/fonts/` — Geist Sans + Geist Mono variable font files
- `Dockerfile` — Railway container definition (copies backend + scripts)
- `railway.toml` — Railway deployment config (healthcheck, restart policy)
- `ARCHITECTURE.md` — Technical architecture documentation

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
1. **Deploy to Railway** — create project, configure persistent volume at `/app/data`, set env vars, deploy
2. **Deploy to Vercel** — create project, set root to `frontend/`, update `vercel.json` with Railway URL, deploy
3. **Verify** — end-to-end test of deployed app (workspace creation, generation, dashboard pages)
4. **Finalize** — uncomment live demo link in README, update CLAUDE.md to mark Phase 6 complete

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
- Jump into deployment before UI/UX elevation is complete
