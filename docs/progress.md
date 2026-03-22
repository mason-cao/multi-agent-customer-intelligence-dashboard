# Luminosity Intelligence — Progress Tracker

---

## Current Status

**Branch:** `main`
**HEAD:** `48232ed` — Workspace setup flow + workspace-aware dashboard entry
**Working tree:** Clean
**Current phase:** Phase 4 (Productization) — in progress. Tickets 1–3.1 committed.
---

## Phase Summary

| Phase | Name | Status | Key Deliverable |
|-------|------|--------|----------------|
| 1 | Agent Buildout | Complete | 8 agents implemented and committed |
| 2 | Validation & Hardening | Complete | Full-system hardening pass, pipeline runner |
| 3 | Integration | Complete | All 8 pages wired to real backend data |
| **4** | **Productization** | **In Progress** | Tickets 1–3.1 committed; Tickets 4/5 next |
| 5 | Infrastructure & Polish | Planned | Orchestrator, ChromaDB, tests |
| 6 | Deployment & Presentation | Planned | Railway + Vercel, demo prep |

---

## Phase 1 — Agent Buildout (Complete)

All 8 agents implemented with BaseAgent ABC pattern, mock-first LLM support, and structured output validation.

| Agent | Output Table | Rows | Key Details |
|-------|-------------|------|-------------|
| BehaviorAgent | `customer_features` | 5,000 | 17 behavioral features + engagement score |
| SegmentationAgent | `customer_segments` | 5,000 | 5 segments: Champions, Loyal, Growth Potential, At Risk, Dormant |
| SentimentAgent | `sentiment_results` | 18,731 | Deterministic keyword-based scoring |
| ChurnAgent | `churn_predictions` | 5,000 | GradientBoosting + SHAP + per-customer explanations |
| RecommendationAgent | `recommendations` | 5,000 | 12-rule priority cascade, 10 action types |
| NarrativeAgent | `executive_summaries` | 7 | 7 executive summary sections |
| AuditAgent | `audit_results` | 44 | 44 checks across 5 categories, 0 failures |
| QueryAgent | `query_results` | on demand | 10 intents, whitelisted SQL handlers |

---

## Phase 2 — Validation & Hardening (Complete)

- Fixed overview.py sentiment threshold bug (scale is [-1,1], thresholds were wrong)
- Improved churn explanation diversity with `_fmt_factor` helper
- Added `scoring_version` to churn prediction output
- Fixed AuditAgent groundedness key lookup
- Standardized all 8 agents to DELETE+INSERT write pattern (replaced `to_sql("replace")`)
- Added `Base.metadata.create_all` lifespan to `main.py`
- Created `scripts/run_pipeline.py` with `--clean` flag for full pipeline runs
- Fixed churn route feature importance computation (from `top_risk_factors` JSON, not null `output_data`)
- Fixed Python truthiness bug in customer route (0.0 values returning None)

---

## Phase 3 — Integration (Complete)

### Backend — 8 Route Files, 12+ Endpoints

| Route File | Endpoints |
|-----------|-----------|
| `overview.py` | `GET /api/overview/kpis`, `GET /api/overview/narrative` |
| `segments.py` | `GET /api/segments/summary` |
| `churn.py` | `GET /api/churn/distribution`, `GET /api/churn/at-risk`, `GET /api/churn/feature-importance` |
| `recommendations.py` | `GET /api/recommendations/summary`, `GET /api/recommendations/top` |
| `sentiment.py` | `GET /api/sentiment/summary` |
| `agents.py` | `GET /api/agents/summary` |
| `customers.py` | `GET /api/customers` |
| `query.py` | `POST /api/query` |

### Frontend — All 8 Pages Wired

| Page | Data Source | Key UI |
|------|-----------|--------|
| Overview | KPI endpoint + narrative | KPI cards, AI-generated summary |
| Customer 360 | Paginated customer list (5-table join) | 9-column table, pagination |
| Segments | Segment summary (3-table join) | Distribution bar, segment cards |
| Churn & Retention | Distribution + at-risk + feature importance | Risk tier cards, customer table, importance bars |
| Recommendations | Summary + top priority | Action distribution bars, priority table |
| Sentiment & Support | Sentiment summary | Stacked bar, topic table |
| Agent Audit | Combined audit + runs + checks | Pass rate cards, run history, check table |
| Ask Anything | Live QueryAgent invocation | Input + example chips + result history |

### Frontend Infrastructure

- 15 TypeScript interfaces in `types/index.ts`
- 12 TanStack Query hooks in `api/hooks.ts`
- Shared utilities: `colors.ts` (segment, risk, sentiment color maps), `formatters.ts`
- All pages have skeleton loading states and error handling

---

## Phase 4 — Productization (In Progress)

### Ticket 1 — Workspace Metadata Model (Committed: `9a4ef00`)
- Workspace ORM model with 15 columns on WorkspaceBase
- Metadata SQLite DB at `data/workspaces.db` (separate from per-workspace data DBs)
- CRUD API: GET /scenarios, GET /, POST /, GET /{id}, POST /{id}/generate, DELETE /{id}
- 4 predefined scenario archetypes: velocity_saas, atlas_enterprise, beacon_analytics, meridian_data
- Pydantic schemas: WorkspaceCreate, WorkspaceResponse, WorkspaceListResponse, ScenarioResponse

### Ticket 2 — Workspace Generation Pipeline (Committed: `a3baee5`)
- Background thread orchestration in `workspace_generator.py`
- 14-stage progress tracking (7 data gen + 6 agents + 1 finalize)
- Parameterized `generate_data.py` with customer_count, churn_rate, primary_industry
- Per-workspace SQLite isolation at `data/workspaces/{id}.db`
- POST /{id}/generate returns 202 Accepted, generation runs async

### Ticket 3 — Frontend Workspace Hub & Dashboard Entry (Committed: `48232ed`)
- WorkspaceHub page (655 lines): list/create views, scenario cards, progress polling
- WorkspaceContext: React Context + localStorage persistence, optimistic fallback
- TanStack Query hooks with auto-polling (2s interval during generation)
- Layout guard: loading spinner during rehydration, redirect if no active ready workspace
- Header: shows active workspace company_name, industry, customer count
- Combined create + generate UX chains two API calls in single user action
- Auto-redirect with 800ms delay when workspace becomes ready

### Ticket 3.1 — Workspace-Scoped DB Routing (Committed: `48232ed`)
- Axios request interceptor sets `X-Workspace-ID` header from localStorage
- Backend `get_db` reads header and routes to workspace DB when present
- All 8 dashboard route files automatically workspace-aware (zero route changes needed)
- Fallback to global DB when header absent or workspace DB doesn't exist

### Remaining Phase 4 Work
- Ticket 4 / 5 — to be defined and implemented in next session
---

## What Is Not Built Yet

### Phase 5 — Infrastructure & Polish
- DAG-based agent orchestrator for parallel execution
- ChromaDB vector store for NL query semantic search
- Automated tests (pytest backend, Vitest frontend)
- Code cleanup and documentation

### Phase 6 — Deployment & Presentation
- Railway backend deployment
- Vercel frontend deployment
- Demo mode / presentation preparation
- Offline cached agent outputs for demo reliability

### Not In Scope
- Auth / user accounts
- Real company data ingestion
- Third-party data connectors (CRM, warehouse)
- Stretch UI features (D3 graphs, cohort heatmaps, PDF export, dark mode)

---

## Database State

16 tables total in `data/nexus.db` (gitignored, ~175MB):

**Source tables (7):** customers (5K), orders (36.6K), subscriptions (5K), support_tickets (11K), feedback (7.7K), behavior_events (752K), campaigns (25)

**Derived tables (9):** customer_features (5K), customer_segments (5K), churn_predictions (5K), sentiment_results (18.7K), recommendations (5K), executive_summaries (7), audit_results (44), query_results (variable), agent_runs (variable)

17 ORM models across all tables.

---

## Known Issues

1. `customer_features.avg_sentiment` is NULL for all rows — BehaviorAgent DELETE wipes SentimentAgent updates. Agents compute avg_sentiment from `sentiment_results` directly.
2. NL query layer uses strict intent classification + whitelisted SQL. No user text composes SQL.
3. Demo must work offline from cached agent outputs.

---

## Architectural Constraints

- All agents inherit BaseAgent ABC (`run`, `validate_output`, `execute`, `save_run`)
- Mock-first: every agent works with zero API keys
- No LangChain — custom orchestration is intentional
- DELETE+INSERT write pattern for all agent database writes
- Pipeline runs in strict dependency order (Behavior → Segmentation → Sentiment → Churn → Recommendation → Narrative → Audit → Query)
- Phase plan must be followed in order — do not skip phases

---

## Next Steps

1. **Create and implement Ticket 4 / 5** for Phase 4 Productization
2. **Complete Phase 4** — remaining productization work
4. After Phase 4: orchestrator, ChromaDB, tests (Phase 5)
5. After Phase 5: deployment, demo prep (Phase 6)

### Do Not Do Yet
- Do not add orchestration before Phase 5
- Do not add ChromaDB before Phase 5
- Do not add deployment before Phase 6
- Do not create new agents
- Do not add stretch UI features
- Do not add real data ingestion

---

## Session Log

### Session — 2026-03-22 (Phase 4 Productization)

**Work completed:**
- Implemented and committed Tickets 1, 2, 3, and 3.1 for Phase 4 Productization
- Ticket 1: Workspace metadata model, CRUD API, 4 scenario archetypes
- Ticket 2: Background generation pipeline, 14-stage progress, per-workspace SQLite isolation
- Ticket 3: Full workspace hub UI, context/state management, layout guard, auto-polling
- Ticket 3.1: Workspace-scoped DB routing via X-Workspace-ID header (2-file fix)
- Strict audit of each ticket before proceeding to the next

**Key decisions:**
- Dashboard-entry limitation identified during Ticket 3 audit: dashboard routes were reading from global DB instead of workspace DB. Resolved with Ticket 3.1 header-based routing.
- Product framing firmly established: workspace-based synthetic-data application, NOT a static dashboard
- Platform rename to **Luminosity Intelligence** decided for next session

**Next session priorities:**
1. Rename platform to Luminosity Intelligence
2. Create Ticket 4 / 5 for Phase 4
3. Continue Phase 4 implementation
