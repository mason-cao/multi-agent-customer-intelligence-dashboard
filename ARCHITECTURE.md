# Architecture

Technical architecture documentation for Nova Core.

---

## System Overview

```
                    ┌──────────────────────────────────┐
                    │           User Browser            │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
                    │         Vercel (Frontend)         │
                    │                                   │
                    │  React 19 + Vite 8 + TypeScript   │
                    │  Tailwind CSS 4 + TanStack Query  │
                    │  Recharts + Lucide React          │
                    │                                   │
                    │  /api/* → rewrite to Railway      │
                    └──────────────┬───────────────────┘
                                   │ HTTPS
                    ┌──────────────▼───────────────────┐
                    │        Railway (Backend)          │
                    │                                   │
                    │  FastAPI + Uvicorn + Python 3.11  │
                    │  SQLAlchemy 2 + Pydantic 2        │
                    │  scikit-learn + SHAP              │
                    │                                   │
                    │  Docker container                 │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
                    │    Railway Persistent Volume      │
                    │                                   │
                    │  /app/data/workspaces.db          │
                    │  /app/data/workspaces/{id}.db     │
                    │                                   │
                    │  SQLite (file-per-workspace)      │
                    └──────────────────────────────────┘
```

Vercel serves the static React frontend and proxies all `/api/*` requests to the Railway backend via rewrites. The backend runs in a Docker container on Railway with a persistent volume mounted at `/app/data` for SQLite database storage.

---

## Request Lifecycle

Dashboard API requests include both `X-Workspace-ID` and `X-Workspace-Token` headers, set by the frontend Axios interceptor from the active workspace in `localStorage`. Workspace management requests include `X-Admin-Token`, either from a trusted frontend build or from the Workspaces screen token prompt. The no-admin synthetic starter uses a dedicated bounded route and can be disabled with `PUBLIC_SYNTHETIC_ACCESS=false`. The backend validates tokens before routing protected requests to the correct per-workspace SQLite database.

```
Frontend                        Backend                          Database
   │                               │                                │
   │  GET /api/overview            │                                │
   │  X-Workspace-ID: abc123def456 │                                │
   │  X-Workspace-Token: ...       │                                │
   │──────────────────────────────▶│                                │
   │                               │  get_db() dependency           │
   │                               │  ─ validates workspace token   │
   │                               │  ─ reads X-Workspace-ID        │
   │                               │  ─ resolves db path            │
   │                               │    data/workspaces/{id}.db     │
   │                               │  ─ checks file exists          │
   │                               │──────────────────────────────▶│
   │                               │                                │
   │                               │  SQLAlchemy ORM query          │
   │                               │◀──────────────────────────────│
   │                               │                                │
   │                               │  Pydantic schema validation    │
   │  JSON response                │                                │
   │◀──────────────────────────────│                                │
```

If the workspace record or database file does not exist, the backend returns a 404. The frontend response interceptor clears the active workspace from `localStorage` and returns the user to `/workspaces`.

---

## Database Architecture

### Dual-Tier SQLite Design

Two independent database layers serve different purposes:

**1. Metadata Database** (`data/workspaces.db`)
- Stores workspace records: id, name, status, config, timestamps, error messages, workspace token hash
- Single table, managed by `WorkspaceBase` declarative base
- Shared across all workspaces
- Created on application startup via lifespan handler

**2. Per-Workspace Databases** (`data/workspaces/{id}.db`)
- One SQLite file per workspace, created during generation
- Contains 16 tables: 7 source data + 9 agent output tables
- Fully isolated — each workspace is a self-contained dataset
- Managed by the `Base` declarative base (distinct from the metadata DB's `WorkspaceBase`)

**3. Global Schema Database** (`data/nexus.db`)
- The default SQLAlchemy engine used to create the shared ORM schema at startup
- Dashboard routes require workspace credentials and never silently fall back to it
- Shares the `Base` schema with per-workspace DBs but is not populated by the workspace pipeline

### Schema Overview

**Source Tables** (generated by `scripts/generate_data.py`):

| Table | Rows (5K workspace) | Description |
|-------|---------------------|-------------|
| `customers` | 5,000 | Customer profiles with demographics and account info |
| `subscriptions` | 5,000 | Subscription plans, MRR, billing cycles |
| `orders` | ~90,000 | Transaction history with amounts and dates |
| `behavioral_events` | ~750,000 | Login, feature usage, page view events |
| `support_tickets` | ~15,000 | Support interactions with categories and resolution |
| `feedback` | ~3,700 | NPS scores and free-text feedback |
| `campaigns` | ~45,000 | Email/push campaign engagement records |

**Agent Output Tables**:

| Table | Rows | Producing Agent |
|-------|------|-----------------|
| `customer_features` | 5,000 | BehaviorAgent |
| `customer_segments` | 5,000 | SegmentationAgent |
| `sentiment_results` | ~18,700 | SentimentAgent |
| `churn_predictions` | 5,000 | ChurnAgent |
| `recommendations` | 5,000 | RecommendationAgent |
| `executive_summaries` | 7 | NarrativeAgent |
| `audit_results` | 44 | AuditAgent |
| `query_results` | on demand | QueryAgent |
| `agent_runs` | 8 | All agents (execution logs) |

### Database Routing

The `get_db()` dependency in `backend/app/db/database.py` implements workspace-aware routing:

```python
def get_db(request: Request):
    workspace_id = request.headers.get("x-workspace-id")
    workspace_token = request.headers.get("x-workspace-token")
    if not workspace_id:
        raise HTTPException(401, "Workspace ID required")
    if not workspace_token:
        raise HTTPException(401, "Workspace token required")
    if not validate_workspace_access_token(workspace_id, workspace_token):
        raise HTTPException(403, "Invalid workspace token")
    db_path = get_workspace_db_path(workspace_id)
    if not db_path.exists():
        raise HTTPException(404, "Workspace database not found")
    ws_engine = get_workspace_engine(workspace_id)
    db = sessionmaker(bind=ws_engine)()
    yield db
```

---

## Agent Pipeline

### BaseAgent Abstract Base Class

All 8 agents inherit from `BaseAgent` and implement a uniform interface:

```
BaseAgent (ABC)
├── run(db)            → orchestrates the full execution
├── validate_output()  → checks output quality/completeness
├── execute(db)        → public entry point (run + validate + save)
└── save_run(db)       → logs execution to agent_runs table
```

Every agent follows the DELETE+INSERT write pattern — existing output rows are deleted before new ones are inserted. This ensures idempotency: re-running an agent produces identical results without duplicates.

### Pipeline Execution Order

Agents run sequentially with explicit dependencies. Each agent reads from tables written by earlier agents:

```
Stage 8:  BehaviorAgent
          ├── Reads: customers, orders, behavioral_events, support_tickets, feedback
          └── Writes: customer_features (17 computed features per customer)
                │
Stage 9:  SegmentationAgent
          ├── Reads: customer_features
          └── Writes: customer_segments (RFM-based segment labels + reasons)
                │
Stage 10: SentimentAgent
          ├── Reads: feedback, support_tickets
          └── Writes: sentiment_results (per-text sentiment labels + scores)
                │
Stage 11: ChurnAgent
          ├── Reads: customer_features, customer_segments
          └── Writes: churn_predictions (probability + SHAP explanations)
                │
Stage 12: RecommendationAgent
          ├── Reads: customer_features, customer_segments, churn_predictions
          └── Writes: recommendations (next-best-action per customer)
                │
Stage 13: NarrativeAgent
          ├── Reads: all agent output tables
          └── Writes: executive_summaries (7 sections)
                │
Stage 14: AuditAgent + QueryAgent
          ├── AuditAgent reads: all tables → writes: audit_results (45 checks)
          └── QueryAgent: on-demand NL query processing
```

### Reliability & Degraded Completion

The pipeline is a declarative spec in `services/workspace_generator.py` (`PIPELINE`), where each agent is an `AgentSpec` carrying a `critical` flag. The generator inspects each agent's `_status` and branches on it:

- **Critical agents** — Behavior, Segmentation, Sentiment, Churn, Recommendation. A failure aborts the run; the workspace is marked `failed` with a message naming the agent.
- **Non-critical agents** — Narrative, Audit, Query. A `failed`/`partial` outcome does *not* abort: the run still completes to `ready` but is flagged **degraded** — the issue is recorded in `pipeline_warnings` and exposed via the computed `health` field (`"ok" | "degraded"`), so the dashboard can show which sections may be incomplete.

Two guarantees keep a workspace from getting stuck before it reaches a terminal state:

- **Scaled timeout** — `generation_timeout_seconds(customer_count)` grows the budget with workspace size (so large ML/SHAP runs aren't killed prematurely) and is shared by both the worker thread and the poll-side check.
- **Startup reconciliation** — background threads don't survive a restart, so `reconcile_orphaned_workspaces()` runs on app startup and flips any workspace still marked `generating` to `failed` with a retry message.

Every agent's outcome (status + duration + tokens) is logged to `agent_runs` and surfaced on the **Agent Audit** page, making the lineage of each insight legible.

### Optional Provider Architecture

The `LLMClient` service supports three modes, selected automatically by environment:

1. **Mock mode** (default) — deterministic canned responses, zero cost, fully offline
2. **Anthropic mode** — Anthropic SDK adapter (when `ANTHROPIC_API_KEY` is set)
3. **OpenAI mode** — OpenAI SDK adapter (when `OPENAI_API_KEY` is set)

Provider calls are used only for narrative generation and query intent classification. All scoring, segmentation, and prediction logic uses rule-based algorithms and scikit-learn models. The core intelligence layer remains deterministic and reproducible.

### ML Components

**ChurnAgent** trains a `GradientBoostingClassifier` on the generated customer data using cross-validation:
- Features: 17 behavioral metrics from `customer_features`
- Target: derived churn label from subscription and activity patterns
- Explainability: SHAP `TreeExplainer` computes per-customer feature attributions
- Risk tiers: rank-based percentile bucketing (High/Medium/Low) for population-relative risk

**SegmentationAgent** uses an RFM (Recency, Frequency, Monetary) waterfall classification:
- 5 segments: Champions, Loyal, At Risk, Needs Attention, New
- Each assignment includes a human-readable reason string
- Deterministic rules, not clustering — every classification is explainable

---

## Synthetic Data Generation

The generation pipeline produces correlated, realistic data across 7 source tables. It runs as a background thread, reporting progress through 14 stages.

### Generation Flow

```
POST /api/workspaces/{id}/generate
  │
  ├── Mark workspace status → "generating"
  ├── Spawn background thread
  │
  │   Stages 1-7: Data Generation (scripts/generate_data.py)
  │   ├── Stage 1: Customer profiles (Faker demographics + account dates)
  │   ├── Stage 2: Subscriptions (plan tiers, MRR, billing)
  │   ├── Stage 3: Orders (correlated with engagement patterns)
  │   ├── Stage 4: Behavioral events (login, feature, page view sequences)
  │   ├── Stage 5: Support tickets (category distribution, resolution times)
  │   ├── Stage 6: Feedback (NPS scores correlated with engagement)
  │   └── Stage 7: Campaigns (email/push with open/click rates)
  │
  │   Stages 8-14: Agent Pipeline
  │   ├── Stages 8-13: Individual agents (Behavior → Narrative)
  │   └── Stage 14: Finalization (Audit + Query)
  │
  └── Mark workspace status → "ready"
```

Data generation is seeded for reproducibility. The same seed + configuration always produces identical data. Cross-table correlations ensure realistic patterns — for example, high-engagement customers generate more orders, better NPS scores, and lower churn probability.

### Configuration Controls

Each workspace supports these generation parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `customer_count` | 5,000 | Number of customer profiles to generate |
| `churn_rate` | 0.15 | Target proportion of churned customers |
| `industry` | varies | Industry vertical (affects company naming and patterns) |
| `seed` | 42 | Random seed for reproducibility |
| `include_outage` | true | Whether to simulate a service outage event |

---

## Frontend Architecture

### Component Hierarchy

```
App (BrowserRouter)
├── WorkspaceHub              — workspace selection and creation
└── Layout                    — app shell (sidebar + content area)
    ├── Sidebar               — navigation + workspace indicator
    ├── GenerationView        — SVG progress ring + timeline (during generation)
    └── Page Routes
        ├── Overview          — hero KPIs + narrative + pipeline health
        ├── Customers         — paginated cross-agent customer table
        ├── Segments          — segment distribution + per-segment cards
        ├── ChurnRetention    — risk tiers + feature importance
        ├── Sentiment         — sentiment distribution + topic table
        ├── Recommendations   — action distribution + priority table
        ├── Agents            — audit results + agent run history
        └── AskAnything       — conversational NL query interface
```

### State Management

- **Server state**: TanStack Query manages all API data fetching, caching, and invalidation
- **Workspace state**: React Context (`WorkspaceContext`) holds the active workspace ID, synced to `localStorage`
- **No client-side state library**: Component-local state via `useState` for UI interactions

### Design System

The UI follows a cinematic glassmorphism direction:

- **5-tier glass panel system**: `.glass`, `.glass-surface`, `.glass-elevated`, `.glass-strong`, `.glass-hero`
- **Gradient borders**: `background-clip: padding-box, border-box` with gradient border-box
- **SVG noise texture**: Inline SVG `feTurbulence` at 3% opacity on all glass surfaces
- **6 ambient orbs**: Floating radial gradients with drift animations for atmospheric depth
- **Typography**: Geist Sans (UI text) + Geist Mono (numbers and data)

Reusable component kit: `StatCard`, `ChartCard`, `Badge`, `DataTable` — all glass-aware and animation-ready.

---

## Security & Validation

### Query Safety

The `QueryAgent` uses strict intent classification + whitelisted SQL patterns. No user-supplied text is interpolated into SQL queries. The agent:

1. Classifies the user's natural language query into a fixed set of intents
2. Maps the intent to a pre-defined, parameterized SQL template
3. Executes the template with safe parameter binding
4. Returns structured results

### Input Validation

- All API request/response data is validated through Pydantic schemas
- Route endpoints use the `@handle_errors` decorator for consistent error handling
- Workspace IDs are validated against the generated 12-character hexadecimal format before database path resolution
- Dashboard routes require a valid per-workspace token before opening a workspace database
- Workspace management routes require the configured admin token
- Database file existence is checked before opening connections

### Resource Controls

- `MAX_WORKSPACES` limits the number of retained workspaces
- `MAX_CONCURRENT_GENERATIONS` limits simultaneous background generation jobs
- Generation start requests return `429` when capacity is reached
- Startup reconciliation marks interrupted `generating` workspaces as failed with a retryable message

### Error Handling

A standardized `@handle_errors("endpoint_name")` decorator wraps all route handlers:
- Catches exceptions and logs structured context via `structlog`
- Returns consistent `{"detail": "...", "user_message": "..."}` error responses
- Prevents stack traces from leaking to the client

### CORS

CORS origins are configurable via the `CORS_ORIGINS` environment variable (comma-separated). In development, defaults to `http://localhost:5173`. In production, set to the Vercel frontend URL.

---

## Deployment

### Railway (Backend)

- **Container**: Python 3.11-slim Docker image
- **Entry point**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Persistent volume**: Mounted at `/app/data` for SQLite databases
- **Health check**: `GET /api/health` returns `{"status": "healthy"}`
- **Auto-deploy**: GitHub integration deploys on push to `main`

### Vercel (Frontend)

- **Framework**: Vite (auto-detected)
- **Root directory**: `frontend/`
- **Build**: `npm run build` → `dist/`
- **API proxy**: Vercel rewrites route `/api/*` to the Railway backend
- **Auto-deploy**: GitHub integration deploys on push to `main`

### Environment Variables

| Variable | Where | Required | Default |
|----------|-------|----------|---------|
| `PORT` | Railway | Auto-injected | — |
| `CORS_ORIGINS` | Railway | No | `http://localhost:5173` |
| `APP_ENV` | Railway | No | `development` |
| `LOG_LEVEL` | Railway | No | `INFO` |
| `ADMIN_API_TOKEN` | Railway | Yes | `""` |
| `MAX_WORKSPACES` | Railway | No | `25` |
| `MAX_CONCURRENT_GENERATIONS` | Railway | No | `1` |
| `PUBLIC_SYNTHETIC_ACCESS` | Railway | No | `true` |
| `ANTHROPIC_API_KEY` | Railway | No | `""` (mock mode) |
| `OPENAI_API_KEY` | Railway | No | `""` (mock mode) |
