# Luminosity Intelligence Overhaul — Implementation Plan

> **For agentic workers:** Implement task-by-task. Each top-level task = one logical commit. **Pause after each commit point** and present a suggested commit message (`type(scope): description`). Never auto-commit.

**Goal:** Fix the reported generation/UX bugs, guarantee workspaces reach a terminal state, unify the design system (keep dark glass), and upgrade Ask Anything (rich + optional LLM).

**Architecture:** FastAPI backend (per-workspace SQLite, threaded generation, 8-agent pipeline) + React/TS frontend (TanStack Query polling, WorkspaceContext, Tailwind v4 + custom CSS tokens). Mock-first is mandatory.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2, Pydantic 2, scikit-learn/SHAP; React 19, TypeScript, Vite, Tailwind v4, Recharts.

Reference: approved high-level plan at `~/.claude/plans/load-claude-md-and-readme-md-gentle-cosmos.md`.

---

## Commit 1 — fix: correct generation elapsed-time (timezone) + dead "Enter Dashboard" button

**Why:** Elapsed shows "60m 6s" (naive-UTC serialization parsed as local in JS); the completion button is a no-op because it never clears `wasGenerating`.

**Files:**
- Modify: `backend/app/schemas/workspace.py` — add `field_serializer` for `created_at`/`completed_at`/`generation_started_at` → ISO-8601 UTC with `Z`; import `timezone`, `field_serializer`.
- Modify: `frontend/src/pages/GenerationView.tsx:316` (clamp elapsed ≥ 0); `:424` (compute "Generated in" from `completed_at − generation_started_at`); `:427-433` (button `onClick={() => { onComplete?.(); navigate('/'); }}`).
- Test: `backend/tests/test_workspaces.py` — assert serialized datetimes end with `Z`.

**Verify:** `cd backend && pytest -q tests/test_workspaces.py`; `cd frontend && npm run build`. Manual: generate → elapsed counts real seconds; click Enter Dashboard immediately → dashboard loads.

**Suggested commit:** `fix(generation): correct elapsed-time timezone and unresponsive Enter Dashboard button`

---

## Commit 2 — fix: guarantee workspace completion (agent-aware pipeline, degraded state, generous timeout, startup recovery)

**Why:** 300s timeout kills legit 5k runs; generator ignores `agent.execute()` results so crashed agents still mark `ready` with empty tables; orphaned `generating` after restart never recovers.

**Files:**
- Modify: `backend/app/services/workspace_generator.py` — make `PIPELINE` a declarative spec (`key,label,module,class,critical,depends_on,output_table`); capture `result = agent.execute(db)` and branch on `result["_status"]` (critical→raise, non-critical→collect warning); scale `GENERATION_TIMEOUT_SECONDS` with `customer_count`; pass warnings to final `ready`.
- Modify: `backend/app/models/workspace.py` — add `pipeline_warnings = Column(Text, nullable=True)`.
- Modify: `backend/app/services/workspace_manager.py` — `init_metadata_db` migration for new column; `update_workspace_status(..., pipeline_warnings=...)`; clear `completed_at`/`pipeline_warnings` in `prepare_for_regeneration`; add `reconcile_orphaned_workspaces()`.
- Modify: `backend/app/main.py` — call `reconcile_orphaned_workspaces()` in lifespan startup.
- Modify: `backend/app/routes/workspaces.py` — use shared scaled timeout for poll-side check.
- Modify: `backend/app/schemas/workspace.py` — add `pipeline_warnings` + computed `health: "ok"|"degraded"`.
- Modify frontend: `frontend/src/types/workspace.ts` (+`pipeline_warnings`,`health`); `GenerationView.tsx` + `pages/Overview.tsx` degraded badge.
- Test: `backend/tests/test_workspaces.py` (or new) — abort-on-critical, degraded-on-noncritical, reconcile flips stale `generating`→`failed`.

**Verify:** `cd backend && pytest -q`. Manual: force a non-critical agent failure → completes with degraded badge; force critical → fails clearly; restart mid-gen → reconciled.

**Suggested commit:** `fix(pipeline): guarantee terminal workspace state with degraded reporting and startup recovery`

---

## Design Skills Toolkit (for Commits 3, 4, 6)

More UI skills are available than the four originally named. Curated set for this project — a premium **dark-glass analytics dashboard redesign** (keep the identity):

- **`redesign-existing-projects`** — audit-first redesign of an existing app (our exact situation). Use first to frame each UI commit.
- **`impeccable`** — hierarchy, IA, color, spacing, motion, reusable tokens/design systems.
- **`high-end-visual-design`** — "make it feel expensive": fonts, shadows, card structure, animation; blocks cheap defaults.
- **`ui-ux-pro-max`** — styles, palettes, font pairings, **25 chart types**, accessibility (use for the chart-palette fix).
- **`frontend-design`** — distinctive, production-grade, anti-generic output.
- **`design-taste-frontend`** — the anti-slop "taste" skill (audit-first on redesigns).
- **`minimalist-ui`** — restraint for dense analytics surfaces.
- **`react-components`** — clean reusable component implementation (StatCard/Card/DataTable).
- **`gpt-taste`** — GSAP motion + editorial typography polish (use sparingly).

Not applicable here: `shadcn-ui` (custom CSS + Tailwind v4, no shadcn), `industrial-brutalist-ui` (wrong aesthetic), `image`/`imagegen-*`/`stitch-*` (image/reference generation, not a code refactor).

---

## Commit 3 — refactor(ui): unified design tokens & glass system (single source of truth)

**Why:** 4 competing color sources, 6 overlapping glass variants, no type/spacing scale.

**Design skills:** lead with `redesign-existing-projects` + `impeccable`; pull palette/typography/chart decisions from `ui-ux-pro-max` + `high-end-visual-design`; sanity-check against `design-taste-frontend` / `minimalist-ui`. Keep the dark glassmorphism identity.

**Files:**
- Modify: `frontend/src/index.css` — refined cohesive palette; type/spacing/radius/shadow tokens; semantic + chart-color CSS vars; collapse glass variants to ~3 (`glass`, `glass-elevated`, `glass-overlay`) with aliases for old names.
- Modify: `frontend/src/utils/colors.ts`, `frontend/src/components/charts/chartTheme.ts` — derive from the token set; one coherent palette; fix sentiment/success mismatch.

**Verify:** `cd frontend && npm run build && npm run lint`; visual spot-check each page.

**Suggested commit:** `refactor(ui): unify design tokens and glass system into a single source of truth`

---

## Commit 4 — style(ui): adopt tokens across components & pages; standardize badges

**Why:** hardcoded hex/rgba, `?? '#6b7280'` fallbacks, ad-hoc badges scattered everywhere.

**Design skills:** `impeccable` + `react-components` for the component sweep; `high-end-visual-design` for the badge/card polish (see Design Skills Toolkit above).

**Files:**
- Modify: `frontend/src/components/shared/*` (StatCard, Card, ChartCard, DataTable, Badge, PageHeader, EmptyState), `frontend/src/components/layout/*` (Sidebar, Header, Layout), `frontend/src/pages/*` — replace hardcoded values with tokens; one Badge pattern; remove gray fallbacks.

**Verify:** `cd frontend && npm run build && npm run lint`; visual review of all 8 pages + hub + generation.

**Suggested commit:** `style(ui): adopt design tokens across components and pages`

---

## Commit 5 — feat(query): richer Ask Anything backend (params, matching, new intents, optional LLM routing)

**Why:** 10 brittle regex intents, no parameters, no LLM, results not typed for rendering.

**Files:**
- Modify: `backend/app/agents/query_agent.py` — parameterized handlers (bound params only), scored synonym matching, new intents (revenue-by-segment, industry breakdown, customer lookup, ticket topics), optional LLM routing (whitelist intent + params only — never raw SQL), set `result_kind` + `suggested_followups`.
- Modify: `backend/app/services/llm_client.py` — intent-routing / answer-synthesis method with mock fallback.
- Modify: `backend/app/schemas/query.py` — add `result_kind`, `suggested_followups`.
- Modify: `backend/app/routes/query.py` — add `GET /query/suggestions` from intent registry.
- Test: `backend/tests/test_query_agent.py`, `test_query.py` — param extraction, new intents, LLM fallback with no key.

**Verify:** `cd backend && pytest -q tests/test_query_agent.py tests/test_query.py`.

**Suggested commit:** `feat(query): parameterized intents, smarter matching, and optional LLM routing for Ask Anything`

---

## Commit 6 — feat(query): Ask Anything UI (structured rendering, follow-ups, suggestions, drill-down)

**Design skills:** `impeccable` + `ui-ux-pro-max` (result tables/cards/charts), `react-components` for the renderers (see Design Skills Toolkit above).

**Files:**
- Modify: `frontend/src/pages/AskAnything.tsx` — render `structured_result` as tables/metric cards/charts by `result_kind` (reuse DataTable/StatCard/charts); follow-up chips; suggestions from `/query/suggestions`; drill-down links; better loading/errors.
- Modify: `frontend/src/api/hooks.ts` (`useQuerySuggestions`), `frontend/src/types/index.ts` (extend `QueryResult`).

**Verify:** `cd frontend && npm run build && npm run lint`. Manual: ask the suggested + reworded + unsupported questions; results render richly; mock mode works.

**Suggested commit:** `feat(query): rich result rendering and guided follow-ups in Ask Anything`

---

## Commit 7 — chore(architecture): pipeline/audit observability + doc reconciliation

**Files:**
- Modify: `frontend/src/pages/AgentAudit.tsx` — surface per-agent status (completed/partial/failed) + duration clearly (lineage legibility).
- Modify: `README.md`, `CLAUDE.md`, `ARCHITECTURE.md` — reconcile metadata DB naming (`data/workspaces.db` vs vestigial `data/nexus.db`); document the declarative pipeline + degraded state.

**Verify:** `cd frontend && npm run build`; docs read correctly.

**Suggested commit:** `chore(architecture): improve pipeline observability and reconcile documentation`

---

## Notes
- TDD for backend logic (Commits 1, 2, 5): write/extend the failing test first where practical.
- Mock-first: every change must work with zero API keys.
- Follow-up (not in scope unless it surfaces): SQLite cross-thread `check_same_thread=False` + WAL if locking errors appear.
