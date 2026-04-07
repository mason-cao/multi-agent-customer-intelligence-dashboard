# LUMINOSITY INTELLIGENCE — Claude Code Instructions

## Project Purpose

Luminosity Intelligence is a workspace-based customer intelligence platform. Users create a workspace, choose a company scenario, generate realistic synthetic company data, run an 8-agent intelligence pipeline, and explore computed insights in a polished dashboard.

This is a real full-stack product demo, not a static dashboard and not a notebook project. The current scope is synthetic-data-first. Do not present real third-party connectors, live ingestion, or production integrations as already implemented.

Core product pillars:
- Workspace-based product flow
- Explainable multi-agent intelligence
- Premium product UX

## Run / Build / Test Commands

```bash
# Backend
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

uvicorn app.main:app --reload --port 8000   # dev server
pytest -q                                    # all backend tests

# Frontend
cd frontend
npm install --legacy-peer-deps
npm run dev                                  # Vite dev server
npm run build                                # production build
npm run lint                                 # ESLint

# Dev scripts
python scripts/generate_data.py --seed 42    # generate raw synthetic data
python scripts/validate_data.py              # validate generated data
python scripts/run_pipeline.py --clean       # run full pipeline
```

## Architecture Map

```text
backend/                           # FastAPI backend
  app/
    main.py                        # app entry, lifespan, CORS, routers
    agents/                        # 8 agents + BaseAgent
      base.py                      # shared agent contract and audit logging
    db/                            # database setup + workspace routing
      database.py                  # global DB + per-workspace session routing
      workspace_db.py              # workspace DB helpers
    models/                        # SQLAlchemy models
    schemas/                       # Pydantic schemas
    routes/                        # API routes
    services/                      # workspace manager, generation, LLM client, feature logic
    utils/                         # error handling, logging
  tests/                           # pytest tests
  pyproject.toml

frontend/                          # React + TypeScript frontend
  src/
    api/                           # Axios client + query hooks
    components/                    # reusable UI components
    contexts/                      # WorkspaceContext
    pages/                         # dashboard pages + hub/generation views
    types/                         # TypeScript interfaces

scripts/                           # generation, validation, pipeline runners
frontend/vercel.json               # API rewrites
railway.toml                       # Railway deploy config
Dockerfile                         # backend container
```

## Non-Obvious Coding Rules

- **Workspace isolation is critical**: The app uses a global metadata DB at `data/nexus.db` and per-workspace DBs at `data/workspaces/{workspace_id}.db`. Dashboard data must stay workspace-aware.
- **`X-Workspace-ID` is required for dashboard data**: The frontend stores the active workspace in `localStorage` as `luminosity_active_workspace`, and the shared Axios client sends `X-Workspace-ID`. Do not bypass this pattern for normal dashboard requests.
- **No silent fallback for workspace data**: If a workspace DB is missing, fail clearly. Do not fall back to the global DB for workspace-scoped routes.
- **All agents inherit from `BaseAgent`**: Do not break the shared contract: `name`, `run(db)`, `validate_output(output)`, `execute(...)`, and `save_run(...)`.
- **Audit logging is not optional**: Agent execution history in `agent_runs` is part of the project's credibility. Never remove or bypass it.
- **Mock-first is mandatory**: The app must work locally with zero API keys. Anthropic/OpenAI are optional enhancements, not baseline requirements.
- **Explainability matters**: Keep churn outputs interpretable, segment assignments explainable, audit results meaningful, and query behavior constrained and safe.
- **Business logic belongs in services and agents**: Keep route handlers thin. Do not move large logic into routes.
- **Pydantic at API boundaries**: Use schemas for request and response validation. Do not return ad hoc dicts when a schema should exist.
- **No fake productization**: Do not hardcode dashboard data or add complete-looking integrations that are not actually wired.
- **No LangChain**: Keep orchestration custom unless explicitly asked otherwise.
- **Reuse the design system**: Prefer existing shared components and the current premium glassmorphism direction over one-off UI patterns.
- **Keep TypeScript types honest**: Update frontend types when backend contracts change. Avoid broad `any`.

## Testing and Verification

- **Backend**: Use `pytest -q`. If a backend change affects models, routes, workspace flow, or agents, run backend tests and manually verify the changed flow.
- **Frontend**: Run `npm run build` and `npm run lint` after frontend changes.
- **Workspace flow changes**: Manually verify workspace creation, workspace selection, generation start/progress, dashboard load, and missing/deleted workspace behavior.
- **Agent or contract changes**: Verify downstream dependencies. If agent outputs change, review affected schemas, routes, tests, frontend types, and pages.
- **Before claiming work is done**: State the root cause, files changed, checks run, anything not verified, and remaining risks.

## Workflow Rules

- **Never auto-commit**. Tell Mason when it is a good time to commit and suggest a commit message instead.
- **Suggested commit format**: `type(scope): description`
- **Prefer minimal diffs**: Modify existing files before creating new ones. Do not refactor unrelated code during a focused task.
- **Read first, edit second**: Inspect relevant files before changing code.
- **Preserve architecture unless explicitly asked to redesign it**.
- **For larger tasks**: organize work as objective, files to inspect/change, implementation notes, verification steps, and risks/follow-ups.
- **Do not dump large file contents unless explicitly asked**. Summarize by file and path when possible.
- **If unsure, say so clearly instead of guessing**.

## Repo-Specifics

- **Monorepo**: `backend/` and `frontend/` live in one repo.
- **Python**: 3.11+, using venv and `backend/pyproject.toml`
- **Node**: npm-based frontend
- **Database**: SQLite, with one metadata DB and one DB per workspace
- **Frontend state**: Workspace state lives in `WorkspaceContext`; server state uses TanStack Query
- **Deployment**: Vercel frontend + Railway backend
- **Health check**: `/api/health`
- **Current scope**: synthetic company generation inside the app, not real external ingestion

## Output Format

- Respond concisely and lead with the action, fix, or answer.
- When referencing code, use `file_path:line_number` format when possible.
- For multi-step work, use short task lists.
- When suggesting commits, format them as: `type(scope): description`
- Keep PR descriptions short: brief summary + test plan.
- Do not output large file contents unless explicitly asked.
- State uncertainty clearly instead of guessing.
