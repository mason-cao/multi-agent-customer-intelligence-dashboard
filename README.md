# Luminosity Intelligence

**Workspace-Based Customer Intelligence Platform**

A full-stack customer intelligence application where users create workspaces, generate realistic synthetic company data, and explore AI-driven insights through an executive dashboard. Eight coordinated AI agents transform raw customer data into behavioral profiles, segments, sentiment analysis, churn predictions, recommendations, and natural language answers — all with full explainability and audit trails.

> Built as a flagship high school capstone project demonstrating systems architecture, AI/ML engineering, full-stack development, and product thinking.

**[Live Demo](https://multi-agent-customer-intelligence-d.vercel.app)**

---

## What This Is

Luminosity Intelligence is not a static dashboard with pre-loaded charts. It is an interactive workspace-based application where:

1. A user enters the app and creates a **workspace**
2. They select a **company scenario** (industry, size, behavioral profile)
3. The system **generates realistic synthetic data** -customers, transactions, support tickets, behavioral events
4. Eight AI agents **process that data** through a dependency-ordered pipeline
5. The dashboard displays **real computed insights** -every metric, prediction, and recommendation traces back to the generated data

The data is synthetic by design. This is a demonstration platform, not a production analytics tool. But the intelligence layer is real: the ML models train on the generated data, SHAP computes actual feature attributions, and every insight is explainable.

### Current Scope vs. Future Vision

**Current (capstone):** Users generate synthetic company data inside the app and explore AI-driven insights. No real company integrations, no third-party data connectors, no live ingestion. The synthetic data generator is the data source.

**Future (production path):** The synthetic data generator could be replaced with real data ingestion -CSV uploads, CRM connectors, warehouse integrations. The agent pipeline, dashboard, and explainability layer would work identically. But that is not the current scope.

---

## What Makes This Different

**It's not a notebook.** The ML models don't live in a Jupyter notebook -they're embedded in a coordinated agent system with structured output, validation, and audit logging.

**It's not a static dashboard.** The user triggers data generation and agent processing. Every chart, metric, and table renders from computed agent outputs, not hardcoded values.

**Explainability is built in.** The ChurnAgent doesn't just output a probability -it uses SHAP to identify the top factors driving each customer's risk. The SegmentationAgent writes a plain-English reason for every classification. The AuditAgent validates all agents against 44 cross-system checks.

**Mock-first architecture.** The entire system works with zero API keys. LLM providers (Anthropic, OpenAI) enhance explanations when available but are never required. This means the full pipeline runs offline, costs $0, and produces reproducible results.

**No LangChain.** All agent orchestration is custom-built -more explainable, easier to debug, and demonstrates deeper architectural understanding.

---

## System Capabilities

### Eight AI Agents

| # | Agent | What It Does | Output |
|---|-------|-------------|--------|
| 1 | **BehaviorAgent** | Computes 17 per-customer behavioral features from 750K+ raw events | `customer_features` (5,000 rows) |
| 2 | **SegmentationAgent** | Classifies customers into 5 business segments using RFM waterfall rules | `customer_segments` (5,000 rows) |
| 3 | **SentimentAgent** | Scores 18K+ feedback and support entries with sentiment labels | `sentiment_results` (18,731 rows) |
| 4 | **ChurnAgent** | GradientBoosting + SHAP per-customer churn prediction with explanations | `churn_predictions` (5,000 rows) |
| 5 | **RecommendationAgent** | 12-rule priority cascade assigning next-best-action per customer | `recommendations` (5,000 rows) |
| 6 | **NarrativeAgent** | Generates 7 executive summary sections from all agent outputs | `executive_summaries` (7 rows) |
| 7 | **AuditAgent** | 44-check cross-agent validation across 5 categories | `audit_results` (44 rows) |
| 8 | **QueryAgent** | Intent-classified natural language query layer with whitelisted SQL | `query_results` (on demand) |

All agents inherit from a shared `BaseAgent` ABC with uniform `run()`, `validate_output()`, `execute()`, and `save_run()` methods. Every execution is logged to `agent_runs` with timing, validation results, and output metadata.

### Eight Dashboard Pages

| Page | What It Shows |
|------|--------------|
| **Executive Overview** | KPI cards, AI-generated narrative summary, system health |
| **Customer 360** | Paginated customer table with cross-agent enrichment (segment, churn, sentiment, revenue) |
| **Segments** | Segment distribution bar, per-segment cards with avg revenue, engagement, churn risk |
| **Churn & Retention** | Risk tier distribution, at-risk customer table, feature importance bars |
| **Sentiment & Support** | Sentiment distribution, topic extraction table, avg score |
| **Recommendations** | Action distribution, priority table, category breakdown |
| **Agent Audit** | Audit pass rates, agent run history, all 44 validation checks |
| **Ask Anything** | Natural language query interface with result history |

All pages render real computed data from backend API endpoints. No hardcoded stub data remains.

### Data Layer

- Per-workspace SQLite databases with isolated synthetic datasets
- Synthetic data generator producing correlated, realistic customer data across 7 source tables
- Data volumes scale with scenario configuration (e.g., ~750K behavioral events for 5,000-customer workspaces)
- Feature engineering service with pure functions for login, engagement, revenue, support, and activity metrics
- Global metadata database (`data/nexus.db`) for workspace management
- 17 ORM models with full Pydantic schema validation

---

## Architecture

```
                        ┌─────────────────────────────────────┐
                        │          React Frontend             │
                        │  8 Pages ── TanStack Query ── Axios │
                        └──────────────┬──────────────────────┘
                                       │ /api proxy
                        ┌──────────────┴──────────────────────┐
                        │          FastAPI Backend             │
                        │  9 Route Files ── 19 Endpoints       │
                        │  Pydantic Schemas ── Services        │
                        └──────────────┬──────────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                │              Agent Pipeline                  │
                │                                              │
                │  Behavior → Segmentation → Sentiment         │
                │      → Churn → Recommendation → Narrative    │
                │          → Audit → Query                     │
                │                                              │
                │  BaseAgent ABC: run → validate → save_run    │
                │  LLMClient: mock → anthropic → openai        │
                └──────────────────────┬──────────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                │              SQLite (per-workspace)           │
                │                                              │
                │  Global:  data/nexus.db (workspace metadata) │
                │  Per-ws:  data/workspaces/{id}.db            │
                │           7 source + 9 agent tables each     │
                │  17 ORM models, full Pydantic schemas        │
                └──────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript 5.9, Vite 8, Tailwind CSS 4 |
| **State** | TanStack Query 5, React Router 7 |
| **Backend** | FastAPI, Uvicorn, Python 3.11 |
| **ORM / Validation** | SQLAlchemy 2, Pydantic 2 |
| **Database** | SQLite (file-based, portable) |
| **ML** | scikit-learn (GradientBoosting), SHAP |
| **Data** | pandas, NumPy, Faker |
| **LLM** | Anthropic SDK, OpenAI SDK (optional, mock-first) |
| **Logging** | structlog (structured JSON) |
| **Icons** | Lucide React |

---

## Getting Started

### Prerequisites

- **Python 3.11+** (developed on 3.11.9)
- **Node.js 18+**
- **Git**

No API keys required. The entire system runs locally in mock mode.

### Quick Start

```bash
# Clone
git clone https://github.com/mason-cao/multi-agent-customer-intelligence-dashboard.git
cd multi-agent-customer-intelligence-dashboard

# Backend
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

```bash
# Frontend (separate terminal)
cd frontend
npm install --legacy-peer-deps
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) — create a workspace, select a scenario, generate data, and explore the dashboard.

### Developer Scripts

These scripts exist for development and debugging. They are not needed for normal usage — the workspace UI handles data generation and pipeline execution automatically.

```bash
python scripts/generate_data.py --seed 42   # Generate raw synthetic data
python scripts/validate_data.py              # Validate data quality
python scripts/run_pipeline.py --clean       # Run the full agent pipeline
```

### Optional: LLM Providers

Create `backend/.env` to enable real LLM providers:

```env
ANTHROPIC_API_KEY=sk-ant-...
# or
OPENAI_API_KEY=sk-...
```

LLM providers enhance narrative explanations but are never required for core scoring and analysis.

---

## Project Roadmap

| Phase | Name | Status |
|-------|------|--------|
| 1 | Agent Buildout | Complete |
| 2 | Validation & Hardening | Complete |
| 3 | Integration | Complete |
| 4 | Productization | Complete |
| 5 | Infrastructure & Polish | Complete |
| — | UI/UX Elevation | Complete |
| 6 | Deployment & Presentation | Complete |

**Phase 4 (Productization)** transformed the system from a developer-run pipeline into a user-facing application: workspace creation with predefined scenarios + custom configuration, 14-stage generation progress tracking, per-workspace SQLite isolation, and full lifecycle management.

**Phase 5 (Infrastructure & Polish)** hardened reliability and consistency: error boundaries, `@handle_errors` decorator with structlog, empty states, pytest test infrastructure (10 smoke tests), workspace lifecycle hardening, and code consistency pass.

**UI/UX Elevation** applied a premium cinematic glassmorphism design system: 5-tier glass panels with gradient borders and noise texture, GenerationView with SVG progress ring, reusable component kit (StatCard, ChartCard, Badge, DataTable), conversational Ask Anything interface, animated number count-ups, and page transitions.

**Phase 6 (Deployment & Presentation)** deployed the full stack: Railway (backend with persistent volume) + Vercel (frontend with API rewrites), plus architecture documentation.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No LangChain** | Custom orchestration is more explainable and demonstrates deeper architectural understanding |
| **Rule-based segmentation** | Business-friendly labels with deterministic, explainable assignments |
| **Cross-validated churn** | Each customer's score comes from a model that never saw them during training |
| **SHAP over global importance** | Per-customer attribution -"why is *this* customer at risk" |
| **Rank-based risk tiers** | Population-relative percentile ranking guarantees meaningful tier distribution |
| **SQLite** | Zero-config, portable, appropriate for single-user capstone. Upgradeable to PostgreSQL |
| **Mock-first LLM** | Develop and demo without API keys. Live providers enhance but never gate functionality |
| **Synthetic data** | Intentionally generated inside the app. Realistic correlated patterns, not random noise |

---

## Deployment

The application deploys as two services:

| Service | Platform | What It Does |
|---------|----------|-------------|
| **Backend** | Railway | FastAPI container with persistent volume for SQLite databases |
| **Frontend** | Vercel | Static React build with API rewrites proxying to Railway |

Both platforms auto-deploy on push to `main` via GitHub integration. The backend health check is at `GET /api/health`. See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed deployment topology, database architecture, and agent pipeline documentation.

### Environment Variables (Railway)

| Variable | Required | Description |
|----------|----------|-------------|
| `CORS_ORIGINS` | No | Comma-separated allowed origins (default: `http://localhost:5173`) |
| `APP_ENV` | No | `development` or `production` |
| `ANTHROPIC_API_KEY` | No | Enables Anthropic LLM for narratives (mock mode without) |
| `OPENAI_API_KEY` | No | Enables OpenAI LLM alternative (mock mode without) |

---

## Repository Structure

```
multi-agent-customer-intelligence-dashboard/
├── backend/
│   ├── app/
│   │   ├── agents/          # 8 AI agents + BaseAgent ABC
│   │   ├── db/              # Database connection + workspace DB routing
│   │   ├── models/          # 17 SQLAlchemy ORM models + workspace model
│   │   ├── routes/          # 9 FastAPI route files (19 endpoints)
│   │   ├── schemas/         # Pydantic response schemas + workspace schemas
│   │   ├── services/        # LLM client, feature engine, workspace manager
│   │   ├── utils/           # Error handling decorator, structured logging
│   │   └── main.py          # FastAPI entry point
│   ├── tests/               # pytest smoke tests (10 tests)
│   └── pyproject.toml
├── frontend/
│   ├── public/fonts/        # Geist Sans + Geist Mono variable fonts
│   ├── src/
│   │   ├── api/             # Axios client + 12 TanStack Query hooks
│   │   ├── components/      # Layout + shared UI (StatCard, ChartCard, Badge, DataTable)
│   │   ├── contexts/        # WorkspaceContext (state + localStorage)
│   │   ├── hooks/           # useCountUp (animated numbers)
│   │   ├── pages/           # 8 dashboard pages + WorkspaceHub + GenerationView
│   │   ├── types/           # 15 TypeScript interfaces
│   │   └── utils/           # Color maps, formatters
│   ├── vercel.json          # Vercel rewrites + SPA config
│   └── package.json
├── scripts/
│   ├── generate_data.py     # Synthetic data generator
│   ├── run_pipeline.py      # Full 8-agent pipeline runner
│   └── validate_data.py     # Data quality checks
├── data/                    # SQLite databases (gitignored, generated at runtime)
├── Dockerfile               # Railway container definition
├── railway.toml             # Railway deployment config
├── ARCHITECTURE.md          # Technical architecture documentation
└── README.md
```

---

## License

This project was built as a capstone / portfolio project. See the repository for license details.

## Author

**Mason** -Full-stack development, AI/ML engineering, system architecture, and product design.

Built incrementally using ticket-driven development. Every agent was implemented, validated, hardened, and audited before moving to the next phase.

---

<p align="center">
  <sub>Built with Python, React, scikit-learn, SHAP, and custom agent orchestration.</sub>
</p>
