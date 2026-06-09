# Nova Core

**Workspace-Based Customer Intelligence Platform**

Nova Core is a full-stack customer intelligence application for creating isolated company workspaces, generating realistic customer datasets, and exploring computed insights through an executive dashboard. The system turns customer profiles, behavior, revenue, support, sentiment, churn risk, recommendations, audit checks, and natural language queries into a single operating view.

[Live Application](https://multi-agent-customer-intelligence-d.vercel.app)

---

## What It Does

1. Create a workspace for a company scenario or custom configuration.
2. Generate realistic synthetic customer, subscription, order, event, support, feedback, and campaign data.
3. Run an eight-stage intelligence pipeline over the workspace database.
4. Review computed KPIs, segments, churn risk, recommendations, audit results, and query answers.
5. Rotate workspace access tokens or delete isolated workspaces when they are no longer needed.

The synthetic data source is intentional: teams can evaluate workflows without importing customer data. The architecture is designed so generated data can later be replaced by CSV uploads, CRM connectors, or warehouse ingestion while preserving the same pipeline and dashboard surfaces.

---

## Key Capabilities

| Area | Capability |
| ---- | ---------- |
| Workspaces | Isolated per-workspace SQLite databases, metadata tracking, token-gated access, regeneration, deletion |
| Data generation | Correlated customer, subscription, order, event, ticket, feedback, and campaign records |
| Intelligence pipeline | Behavior features, segmentation, sentiment scoring, churn prediction, recommendations, narrative summaries, audit checks, query indexing |
| Dashboard | Executive overview, Customer 360, segments, churn and retention, sentiment and support, recommendations, audit, Ask Anything |
| Explainability | SHAP churn attributions, segmentation reasons, audit checks, run history, source-table metadata |
| Security | Admin token for workspace management, per-workspace access tokens for dashboard data, explicit CORS, hardened headers, safe query templates |
| Operations | Workspace quota, single-generation concurrency guard, startup reconciliation for interrupted runs, structured production logging |

---

## Architecture

```
React / TypeScript / Vite
        |
        | /api requests with admin or workspace headers
        v
FastAPI / SQLAlchemy / Pydantic
        |
        | metadata routing
        v
data/workspaces.db
        |
        | per-workspace isolation
        v
data/workspaces/{workspace_id}.db
```

The backend stores workspace metadata in `data/workspaces.db`. Each workspace gets its own SQLite database under `data/workspaces/`, which keeps generated datasets and computed pipeline outputs isolated from every other workspace.

Dashboard routes require:

- `X-Workspace-ID`
- `X-Workspace-Token`

Workspace management routes require:

- `X-Admin-Token`

The frontend sends these headers through the shared Axios client. Workspace tokens are returned once on create or rotation and then stored client-side for the active workspace. Admin tokens can come from a trusted frontend build or from the Workspaces screen token prompt, which stores the token in that browser.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the detailed topology, data model, pipeline order, and deployment notes.

---

## Tech Stack

| Layer | Technology |
| ----- | ---------- |
| Frontend | React 19, TypeScript 5.9, Vite 8, Tailwind CSS 4 |
| State | TanStack Query 5, React Router 7 |
| Backend | FastAPI, Uvicorn, Python 3.11 |
| ORM / Validation | SQLAlchemy 2, Pydantic 2 |
| Database | SQLite, file-per-workspace storage |
| Modeling | scikit-learn, SHAP, pandas, NumPy |
| UI | Recharts, Lucide React, local Geist font assets |
| Logging | structlog with JSON output in production |

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ADMIN_API_TOKEN=dev-admin-token uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
VITE_ADMIN_API_TOKEN=dev-admin-token npm run dev
```

Open [http://localhost:5173](http://localhost:5173), create a workspace, generate data, and enter the dashboard.

The backend and frontend admin tokens must match. In shared environments, use a strong random token and avoid exposing it in client builds intended for untrusted users.

---

## Environment Variables

| Variable | Service | Required | Description |
| -------- | ------- | -------- | ----------- |
| `ADMIN_API_TOKEN` | Backend | Yes for workspace management | Shared secret required by workspace create/list/generate/delete/token routes |
| `VITE_ADMIN_API_TOKEN` | Frontend | Local/admin deployments | Token sent by the frontend for workspace management routes |
| `CORS_ORIGINS` | Backend | Production | Comma-separated allowed frontend origins |
| `APP_ENV` | Backend | No | Set to `production` for JSON logs and production behavior |
| `LOG_LEVEL` | Backend | No | Logging threshold, default `INFO` |
| `MAX_WORKSPACES` | Backend | No | Workspace quota, default `25` |
| `MAX_CONCURRENT_GENERATIONS` | Backend | No | Generation concurrency limit, default `1` |
| `ANTHROPIC_API_KEY` | Backend | No | Optional provider key for narrative/query routing |
| `OPENAI_API_KEY` | Backend | No | Optional provider key for narrative/query routing |

No external provider key is required for local operation.

`ADMIN_TOKEN` and `VITE_ADMIN_TOKEN` are accepted as compatibility aliases. If a frontend build does not include `VITE_ADMIN_API_TOKEN`, the Workspaces screen prompts for an admin token and stores it in that browser under `novacore_admin_token`.

---

## Verification

```bash
cd backend
.venv/bin/pytest
```

```bash
cd frontend
npm run lint
npm run build
npm audit --json
```

Current expected baseline:

- Backend test suite passes.
- Frontend lint and production build pass.
- npm audit reports zero vulnerabilities.
- Browser checks pass on desktop and mobile.

---

## Deployment

The current deployment uses:

| Service | Platform | Role |
| ------- | -------- | ---- |
| Backend | Railway | FastAPI container with persistent volume at `/app/data` |
| Frontend | Vercel | Static React build with `/api/*` rewrites |

Production checklist:

- Set a strong `ADMIN_API_TOKEN` on the backend.
- Set `VITE_ADMIN_API_TOKEN` only for trusted admin-facing deployments.
- Set `CORS_ORIGINS` to the exact frontend origin.
- Keep the Railway data volume mounted and backed up.
- Keep Vercel security headers in `frontend/vercel.json` aligned with backend API origin.
- Rotate workspace tokens when access should be revoked.

---

## Repository Structure

```
backend/
  app/
    agents/          Pipeline stages and shared BaseAgent
    db/              Database connections and workspace routing
    models/          SQLAlchemy models
    routes/          FastAPI route modules
    schemas/         Pydantic schemas
    security/        Token helpers
    services/        Workspace lifecycle, generation, feature services
    utils/           Error handling, privacy, logging
  tests/             pytest suite

frontend/
  public/fonts/      Local font assets
  src/
    api/             Axios client and TanStack Query hooks
    components/      Layout and reusable UI
    contexts/        Workspace state
    pages/           Dashboard and workspace views
    types/           TypeScript interfaces
    utils/           Formatting and color utilities

scripts/             Data generation, validation, and pipeline utilities
data/                Runtime SQLite databases, gitignored
```

---

## License

See [LICENSE](LICENSE).
