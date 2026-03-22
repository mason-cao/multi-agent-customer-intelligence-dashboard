# Nexus Intelligence — Project Context for Claude Sessions

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
| **4** | **Productization** | **Next — not yet started** |
| 5 | Infrastructure & Polish | Planned |
| 6 | Deployment & Presentation | Planned |

### Phase 4 — Productization (Current Target)
Transforms the system from a developer-run pipeline into a user-facing application:
- Setup/onboarding flow where users create workspaces
- Company scenario selection (predefined archetypes + custom)
- User-triggered synthetic data generation inside the product
- Processing state with real-time pipeline status
- Workspace-aware dashboard entry
- Workspace isolation via separate SQLite files per workspace

This phase does NOT include: real data ingestion, auth/accounts, third-party connectors, or production SaaS infrastructure.

### Phase 5 — Infrastructure & Polish
DAG-based agent orchestrator, ChromaDB vector search for NL queries, automated tests, code cleanup.

### Phase 6 — Deployment & Presentation
Railway (backend) + Vercel (frontend) deployment, demo mode, presentation preparation.

## Current State

**Branch:** `main`
**HEAD:** `e2b5dc4`

### What Is Built
- 8 AI agents, all implemented, validated, hardened, and audited
- 8 FastAPI route files with 12+ API endpoints
- 8 React dashboard pages wired to real backend data
- 15 TypeScript interfaces, 12 TanStack Query hooks
- Pipeline runner script (`scripts/run_pipeline.py`)
- Synthetic data generator (`scripts/generate_data.py`)
- 17 SQLAlchemy ORM models, Pydantic schemas
- Mock-first LLM client (works with zero API keys)

### What Is NOT Built Yet
- Workspace model / onboarding flow (Phase 4)
- User-triggered data generation from within the app (Phase 4)
- Company scenario selection UI (Phase 4)
- DAG-based agent orchestrator (Phase 5)
- ChromaDB vector search (Phase 5)
- Automated tests (Phase 5)
- Deployment configuration (Phase 6)
- Auth / user accounts (not in current scope)
- Real data ingestion / third-party connectors (not in current scope)

## Tech Stack
- **Frontend**: React 19 + Vite 8 + TypeScript + Tailwind CSS 4 + TanStack Query + Lucide React
- **Backend**: FastAPI + SQLAlchemy + Pydantic + Python 3.11.9
- **Database**: SQLite (file-based, `data/nexus.db`, gitignored)
- **LLMs**: Mock-first (zero API keys) → Claude 3.5 Sonnet → GPT-4o-mini
- **ML**: scikit-learn (GradientBoosting), SHAP, pandas, numpy
- **Data Gen**: Faker + numpy (`scripts/`)
- **Deploy**: Railway (backend) + Vercel (frontend) — not yet configured
- **Testing**: pytest (backend) + Vitest (frontend) — infrastructure exists, no tests written yet

## Code Style & Conventions
- **Python**: snake_case, type hints, Pydantic models for all API schemas, SQLAlchemy ORM models
- **TypeScript**: camelCase for variables/functions, PascalCase for components/types
- **API**: RESTful, all routes under `/api/`, JSON responses
- **Agents**: All inherit from `BaseAgent` ABC with `run()`, `validate_output()`, `execute()`, `save_run()`
- **Write pattern**: All agents use DELETE+INSERT (not `to_sql("replace")`) to preserve ORM constraints
- **Imports**: Group stdlib → third-party → local. No star imports.
- **Error handling**: Agents use retry + fallback pattern. API returns proper HTTP status codes.
- **No LangChain**: Custom orchestration is intentional (more impressive, easier to explain)
- **Mock-first**: Every agent must work with zero API keys. LLMClient auto-selects mock → anthropic → openai.

## Key Directories
- `backend/app/agents/` — All 8 agents + BaseAgent ABC
- `backend/app/routes/` — 8 FastAPI route files (12+ endpoints)
- `backend/app/models/` — 17 SQLAlchemy ORM models
- `backend/app/schemas/` — Pydantic request/response schemas
- `backend/app/services/` — LLM client, feature engine
- `frontend/src/pages/` — 8 dashboard pages (all wired to real data)
- `frontend/src/components/` — Layout + shared UI components
- `frontend/src/api/` — Axios client + 12 TanStack Query hooks
- `frontend/src/types/` — 15 TypeScript interfaces
- `scripts/` — Data generation, pipeline runner, validation

## Pipeline Order
Agents must run in this dependency order:
1. BehaviorAgent → `customer_features`
2. SegmentationAgent → `customer_segments`
3. SentimentAgent → `sentiment_results`
4. ChurnAgent → `churn_predictions`
5. RecommendationAgent → `recommendations`
6. NarrativeAgent → `executive_summaries`
7. AuditAgent → `audit_results`
8. QueryAgent → `query_results`

Use `python scripts/run_pipeline.py --clean` for a full clean pipeline run.

## Known Issues
- `customer_features.avg_sentiment` is NULL for all rows (BehaviorAgent DELETE wipes SentimentAgent updates). Agents compute avg_sentiment from `sentiment_results` directly.
- NL query layer uses strict intent classification + whitelisted SQL — no user text composes SQL.
- Demo must work offline from cached agent outputs (never depend on live API keys during presentation).

## Scope Constraints — READ CAREFULLY

### Do
- Follow the phase plan in order (Phase 4 next)
- Preserve mock-first architecture in all new work
- Keep the workspace-based synthetic-data product framing
- Maintain the BaseAgent ABC pattern for any agent changes
- Use DELETE+INSERT write pattern for all database writes

### Do Not
- Create new agents beyond the 8 implemented
- Add real data ingestion or third-party connectors (not in scope)
- Add stretch features (D3 graphs, cohort heatmaps, PDF export, dark mode)
- Add orchestration before Phase 5
- Add ChromaDB before Phase 5
- Skip phases or reorder the phase plan
- Describe the project as a "static dashboard" — it is a workspace-based application
- Add auth/accounts infrastructure (out of scope for capstone)
- Jump into deployment before Phases 4-5 are complete

### Product Direction Guidance
Future Claude sessions must preserve:
1. The workspace-based synthetic-data product model
2. The 6-phase roadmap order
3. The distinction between current synthetic scope and future production vision
4. The mock-first, no-external-dependency architecture
