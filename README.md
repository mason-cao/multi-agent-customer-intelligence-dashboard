# Nova Core

**Workspace-Based Customer Intelligence Platform**

Nova Core is a full-stack customer intelligence application for creating isolated company workspaces, generating realistic customer datasets, and exploring computed insights through an executive dashboard. The system turns customer profiles, behavior, revenue, support, sentiment, churn risk, recommendations, audit checks, and natural language queries into a single operating view. Originally designed as a Capstone Project.

[Live Application](https://nova-core-systems.vercel.app)

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
| Security | Owner access for workspace management, per-workspace access tokens for dashboard data, explicit CORS, hardened headers, safe query templates |
| Operations | Workspace quota, single-generation concurrency guard, startup reconciliation for interrupted runs, structured production logging |

---

## Architecture

```
React / TypeScript / Vite
        |
        | /api requests with owner or workspace headers
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

Owner workspace management routes require:

- `X-Admin-Token`

The frontend sends these headers through the shared Axios client. Workspace tokens are returned once on create or rotation and then stored client-side for the active workspace.

Owner access lets one trusted person create, delete, regenerate, and manage every workspace. If no deployment token is configured, the app asks the first owner to create an owner passcode in the Workspaces screen. The app stores a protected hash of that passcode in `data/workspaces.db`; it does not store the plaintext passcode.

Advanced deployments can set `ADMIN_API_TOKEN` instead. In that mode, the owner passcode setup screen is disabled and workspace-management requests must send the configured value in the `X-Admin-Token` header.

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
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173), create a workspace, generate data, and enter the dashboard.

Use **Start Demo Workspace** if you only want to explore. Use **Owner Mode** if you want to create, delete, regenerate, or manage all workspaces.

### Owner Access Setup

No command line setup is required for the default owner flow.

1. Open the app.
2. Choose **Start Demo Workspace** to explore without owner access.
3. Choose **Owner Mode** when you need full workspace management.
4. If owner access has not been created yet, choose a passcode. It can be any exact phrase at least 8 characters long. Longer is safer, for example `correct horse battery staple`.
5. Save the passcode somewhere private. Future owner access uses the same passcode.

Demo workspaces stay separate from Owner Mode. The first owner login starts with a clean workspace list, and workspaces created from Owner Mode are saved for future owner sessions.

Use **Log out** to clear the saved owner passcode and active workspace from the current browser. Logging out does not delete workspaces; enter the owner passcode again to return to Owner Mode later.

For advanced private deployments, a site owner can preconfigure owner access instead:

1. Generate a strong random value:

   ```bash
   openssl rand -hex 32
   ```

2. Set that value as `ADMIN_API_TOKEN` on the backend service.
3. For private admin-only frontend deployments, set the same value as `VITE_ADMIN_API_TOKEN` on the frontend service.
4. For public frontend deployments, do not set `VITE_ADMIN_API_TOKEN`. Owner users can enter the passcode in the Workspaces screen, and public users can still start demo workspaces when `PUBLIC_SYNTHETIC_ACCESS=true`.

---

## Environment Variables

| Variable | Service | Required | Description |
| -------- | ------- | -------- | ----------- |
| `ADMIN_API_TOKEN` | Backend | Advanced owner setup | Optional deployment-level owner secret compared against the `X-Admin-Token` header |
| `VITE_ADMIN_API_TOKEN` | Frontend | Private admin deployments | Optional way to send the deployment owner secret automatically from trusted frontend builds |
| `CORS_ORIGINS` | Backend | Production | Comma-separated allowed frontend origins |
| `APP_ENV` | Backend | No | Set to `production` for JSON logs and production behavior |
| `LOG_LEVEL` | Backend | No | Logging threshold, default `INFO` |
| `MAX_WORKSPACES` | Backend | No | Workspace quota, default `25` |
| `MAX_CONCURRENT_GENERATIONS` | Backend | No | Generation concurrency limit, default `1` |
| `PUBLIC_SYNTHETIC_ACCESS` | Backend | No | Enables the bounded public demo workspace starter, default `true` |
| `ANTHROPIC_API_KEY` | Backend | No | Optional provider key for narrative/query routing |
| `OPENAI_API_KEY` | Backend | No | Optional provider key for narrative/query routing |

No external provider key is required for local operation.

`ADMIN_TOKEN` and `VITE_ADMIN_TOKEN` are accepted as compatibility aliases. If no deployment owner secret is configured, the Workspaces screen lets the first owner create an owner passcode and then stores entered passcodes in that browser under `novacore_admin_token`.

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

- Decide whether owner access should use first-run setup or a preconfigured `ADMIN_API_TOKEN`.
- Set `VITE_ADMIN_API_TOKEN` only for trusted admin-facing deployments.
- Set `PUBLIC_SYNTHETIC_ACCESS=false` when public visitors should not be able to start demo workspaces.
- Set `CORS_ORIGINS` to the exact frontend origin.
- Keep the Railway data volume mounted and backed up.
- `MIN_DATA_VOLUME_FREE_BYTES` defaults to `67108864` (64 MiB); set it lower or to `0` to disable startup pruning of oldest workspace database files.
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
