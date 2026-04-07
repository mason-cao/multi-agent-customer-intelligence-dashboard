# Session Handoff — 2026-04-07

---

## 1. Current State

**Luminosity Intelligence** — workspace-based customer intelligence platform. Users create workspaces, select company scenarios (predefined, random, or custom), generate realistic synthetic data, and explore AI-driven insights through an executive dashboard. Eight AI agents process workspace data through a dependency-ordered pipeline.

High school capstone project. All data is synthetic by design — no real integrations.

**Branch:** `main`
**Deployed:** Backend on Railway, Frontend on Vercel

---

## 2. Phase Status

| Phase | Status |
|-------|--------|
| 1 — Agent Buildout | Complete |
| 2 — Validation & Hardening | Complete |
| 3 — Integration | Complete |
| 4 — Productization | Complete |
| 5 — Infrastructure & Polish | Complete |
| UI/UX Elevation | Complete |
| 6 — Deployment & Presentation | Complete |
| **Finalization** | **In Progress** — debugging, small UI tweaks, final polish |

---

## 3. What Remains

1. **Debug** any issues found during end-to-end testing on deployed environment
2. **Small UI tweaks** — minor visual polish and refinements
3. **Finalize** — uncomment live demo link in README, last commit, presentation prep

---

## 4. Current UI/Design Baseline

**Cinematic premium glassmorphism** — established and should be preserved:
- Deep blue / indigo / violet gradient palette
- Premium layered shell with 6 ambient orbs + vignette overlay
- 5-tier glass panel system (`.glass`, `.glass-surface`, `.glass-elevated`, `.glass-strong`, `.glass-hero`)
- `.glass-nested` for glass-within-glass composition
- Gradient borders, noise texture, dark-indigo shadows, specular highlights
- `--glass-hover-glow` CSS custom property for semantic card colors
- Geist Sans (UI) + Geist Mono (data/numbers) typography
- Recharts for all data visualizations
- `.btn-primary` / `.btn-secondary` button classes
- `.shimmer` skeleton animations
- `.page-transition` CSS animation on route changes
- `useCountUp` hook for animated stat numbers (respects `prefers-reduced-motion`)
- Reusable component kit: StatCard, ChartCard, Badge, DataTable
- GenerationView with SVG progress ring + vertical timeline for workspace generation
- Motion: `cubic-bezier(0.16, 1, 0.3, 1)`, 80ms stagger

---

## 5. What Exists Now

- **8 agents** in `backend/app/agents/` — all inheriting BaseAgent ABC
- **9 route files** in `backend/app/routes/` — 19 endpoints, all with `@handle_errors` decorator
- **10 pages** in `frontend/src/pages/` — 8 dashboard + WorkspaceHub + GenerationView, all with empty states
- **4 shared components** in `frontend/src/components/shared/` — StatCard, ChartCard, Badge, DataTable
- **1 custom hook** in `frontend/src/hooks/` — useCountUp
- **10 backend smoke tests** in `backend/tests/` — full DB isolation
- **Workspace infrastructure**: metadata DB, per-workspace SQLite, generation pipeline, timeout detection, lifecycle management
- **Custom scenario support**: 5 configurable controls + random scenario option
- **Error handling**: standardized decorator + structlog + human-readable `user_message` field
- **UI**: cinematic glassmorphism with perfected glass system (5-tier panels, gradient borders, noise texture, hero variant, semantic hover glows)
- **Deployment**: Backend on Railway (Dockerfile, persistent volume at /app/data), Frontend on Vercel (vercel.json with API rewrites to Railway)
- **Architecture docs**: ARCHITECTURE.md with deployment topology, data flow, agent pipeline, database design, frontend architecture, security
- **GitHub repo**: https://github.com/mason-cao/multi-agent-customer-intelligence-dashboard

---

## 6. Key Deployment Details

**Dockerfile path resolution** — critical constraint:
- `database.py` and `workspace_db.py` resolve `DATA_DIR` via `__file__` parent traversal (4 levels up to project root → `data/`)
- `workspace_generator.py` imports `scripts/generate_data.py` via `sys.path` from project root
- The Dockerfile copies both `backend/` and `scripts/` to `/app/`, sets WORKDIR to `/app/backend`, preserving all path chains
- Railway persistent volume mounts at `/app/data` for SQLite persistence across deploys

**Vercel rewrites** — the frontend's Axios client uses relative `/api` baseURL. Vercel rewrites proxy `/api/*` to the Railway backend, so no frontend code changes are needed for production API routing.

**CORS** — `backend/app/main.py` reads `CORS_ORIGINS` env var (comma-separated). Set to the Vercel URL on Railway for any direct API calls that bypass the rewrite proxy.

---

## 7. Constraints

- Follow phase plan in order
- Mock-first: all agents must work with zero API keys
- No LangChain — custom orchestration is intentional
- All agents use DELETE+INSERT write pattern
- All route endpoints use `@handle_errors` decorator
- Pipeline order: Behavior → Segmentation → Sentiment → Churn → Recommendation → Narrative → Audit → Query
- Preserve cinematic glassmorphism UI direction unless intentionally changed
- Do NOT describe the project as a "static dashboard"
- Do NOT add features from later phases prematurely
- Do NOT add real data ingestion or third-party connectors
- Do NOT add auth/accounts or stretch features
- Never auto-commit — suggest commit message to Mason instead

---

## 8. Resume Prompt

```
Resuming Luminosity Intelligence capstone project.

State: All phases (1–6) complete and deployed. Backend on Railway, frontend on Vercel. Currently in finalization — debugging, small UI tweaks, and final polish.

Product model: Workspace-based synthetic-data intelligence platform. Users create workspaces, select scenarios, generate synthetic data, explore AI-driven insights. Data is synthetic by design.

UI baseline: Cinematic premium glassmorphism with perfected glass system (5-tier panels, gradient borders, noise texture, hero variant, semantic hover glows, dark-indigo shadows). Reusable component kit (StatCard, ChartCard, Badge, DataTable). GenerationView with progress ring + timeline. Conversational Ask Anything. Animated number count-ups. Page transitions. Preserve this direction.

GitHub: https://github.com/mason-cao/multi-agent-customer-intelligence-dashboard

Remaining work:
1. Debug any issues from end-to-end testing
2. Small UI tweaks and visual polish
3. Finalize — uncomment live demo link in README, last commit, presentation prep

Do not skip phases. Do not add real data ingestion. Do not describe as a static dashboard. Never auto-commit — suggest commit messages instead.
```
