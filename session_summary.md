# Session Handoff — 2026-03-22

---

## 1. Current State

**Nexus Intelligence** is a workspace-based customer intelligence platform where users create workspaces, generate realistic synthetic company data, and explore AI-driven insights through an executive dashboard. Eight AI agents process the generated data through a dependency-ordered pipeline, producing behavioral profiles, segments, sentiment analysis, churn predictions, recommendations, executive narratives, validation audits, and natural language answers.

This is a high school capstone project. All data is synthetic by design — no real company integrations exist. The synthetic data generator is the data source. The intelligence layer (ML models, SHAP, agent pipeline) is real.

**Branch:** `main`
**HEAD:** `e2b5dc4` — Integration for all 8 pages
**Working tree:** Clean

---

## 2. Completed Phases

### Phase 1 — Agent Buildout (Complete)

All 8 agents implemented with BaseAgent ABC pattern, mock-first LLM support, and structured output validation:

- BehaviorAgent, SegmentationAgent, SentimentAgent, ChurnAgent
- RecommendationAgent, NarrativeAgent, AuditAgent, QueryAgent

### Phase 2 — Validation & Hardening (Complete)

- Fixed sentiment thresholds, churn explanation diversity, AuditAgent key lookup
- Standardized all agents to DELETE+INSERT write pattern
- Created `scripts/run_pipeline.py` pipeline runner
- Fixed route-level bugs (feature importance, truthiness, thresholds)

### Phase 3 — Integration (Complete)

- 8 FastAPI route files with 12+ endpoints
- 8 React dashboard pages wired to real backend data
- 15 TypeScript interfaces, 12 TanStack Query hooks
- All pages have skeleton loaders and error states
- No hardcoded stub data remains

---

## 3. Current Phase: Phase 4 — Productization (Not Yet Started)

Phase 4 transforms the system from a developer-run pipeline into a user-facing application:

1. **Workspace model** — users create/enter workspaces, each with its own SQLite database
2. **Scenario selection** — predefined company archetypes (Velocity SaaS, Atlas Enterprise, Beacon Analytics, Meridian Data) + custom
3. **User-triggered generation** — synthetic data generation happens inside the app, triggered by the user
4. **Processing state** — real-time pipeline status (SSE or polling) during agent execution
5. **Workspace-aware dashboard** — dashboard reads from the active workspace's database

This phase does NOT include: auth, real data ingestion, third-party connectors, production SaaS infrastructure.

---

## 4. Immediate Next Priority

**Begin Phase 4 implementation.** The exact implementation plan has been designed but not yet executed. The user must explicitly direct when to start.

Suggested sequence:

1. Backend workspace model (metadata store, workspace-aware DB resolution)
2. Generation endpoint (parameterized `generate_data.py` + pipeline runner)
3. Frontend workspace creation/selection flow
4. Processing state UI
5. Workspace-aware dashboard wiring

---

## 5. What Exists Now

- **8 agents** in `backend/app/agents/` — all inheriting BaseAgent ABC
- **8 route files** in `backend/app/routes/` — 12+ endpoints serving real agent data
- **8 pages** in `frontend/src/pages/` — all wired to real backend data via TanStack Query
- **Pipeline runner** at `scripts/run_pipeline.py` with `--clean` flag
- **Data generator** at `scripts/generate_data.py`
- **17 ORM models**, Pydantic schemas, mock-first LLM client
- **Database** at `data/nexus.db` — 16 tables, 7 source + 9 derived

---

## 6. What Does NOT Exist Yet

- Workspace creation / onboarding UI
- Company scenario selection
- In-app data generation trigger
- Processing state / progress UI
- Workspace isolation (per-workspace SQLite files)
- DAG-based orchestrator (Phase 5)
- ChromaDB vector search (Phase 5)
- Automated tests (Phase 5)
- Deployment (Phase 6)
- Auth / user accounts (not in scope)
- Real data ingestion (not in scope)

---

## 7. Constraints

- Follow phase plan in order — Phase 4 next, then 5, then 6
- Mock-first: all agents must work with zero API keys
- No LangChain — custom orchestration is intentional
- All agents use DELETE+INSERT write pattern
- Pipeline order: Behavior → Segmentation → Sentiment → Churn → Recommendation → Narrative → Audit → Query
- Do not describe the project as a "static dashboard" — it is a workspace-based application
- Do not add features from later phases before completing Phase 4
- Do not add real data ingestion or third-party connectors

---

## 8. Documentation State

All project documentation was synchronized on 2026-03-22:

- `README.md` — public-facing project description, updated to workspace-based framing
- `CLAUDE.md` — internal engineering memo for Claude sessions
- `docs/progress.md` — operational progress tracker
- `session_summary.md` — this file

All four files reflect the same 6-phase plan, the same product framing, and the same current status. Future sessions should maintain this consistency.

---

## 9. Resume Prompt

```
Resuming Nexus Intelligence capstone project.

State: All 8 agents, routes, and dashboard pages are implemented and integrated on branch `main` at HEAD `e2b5dc4`. Phases 1-3 are complete. Working tree is clean.

Product model: Workspace-based synthetic-data intelligence platform. Users create workspaces, select company scenarios, generate synthetic data inside the app, and explore AI-driven insights. Data is synthetic by design — no real integrations.

Current phase: Phase 4 (Productization) — workspace model, onboarding flow, scenario selection, user-triggered data generation, processing state, workspace-aware dashboard. Not yet started.

Do not skip phases. Do not add features from Phase 5 or 6. Do not add real data ingestion. Do not describe the project as a static dashboard.
```
