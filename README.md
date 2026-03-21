# Nexus Intelligence

**Multi-Agent Customer Intelligence Dashboard**

A full-stack customer intelligence platform that coordinates specialized AI agents to transform raw customer data into actionable insights. Built for a fictional B2B SaaS company ("Nexus Analytics") with 5,000 customers and 18 months of behavioral, transactional, and support data.

Each agent owns a specific analytical domain — behavioral feature engineering, customer segmentation, sentiment analysis, churn prediction — and writes structured, explainable outputs to a shared database. The frontend surfaces these outputs through an executive dashboard designed for non-technical stakeholders.

> Built as a flagship capstone project to demonstrate systems architecture, AI/ML engineering, full-stack development, and product thinking.

---

## What This Project Does

Traditional dashboards show static metrics. Nexus Intelligence runs a coordinated pipeline of AI agents that each produce a different layer of customer understanding:

- **Behavioral profiling** — Computes per-customer engagement scores, login patterns, revenue metrics, and activity trends from 750K+ raw events
- **Customer segmentation** — Classifies every customer into business-friendly segments (Champions, Loyal, Growth Potential, At Risk, Dormant) using rule-based waterfall logic on RFM features
- **Sentiment analysis** — Scores 18K+ customer feedback entries and aggregates sentiment at the customer level
- **Churn prediction** — Trains a GradientBoosting classifier with cross-validation, then uses SHAP to explain *why* each customer is at risk — not just *that* they are

The result is a system where every insight traces back to specific data points and every prediction comes with a human-readable explanation.

### Questions This System Helps Answer

- Which customers are most likely to churn, and what's driving their risk?
- What distinguishes Champions from At-Risk customers?
- How does customer sentiment correlate with engagement and revenue?
- Which behavioral signals are the strongest predictors of churn?
- What does the overall health of the customer base look like?

---

## Features

### Currently Implemented

**Agent System**
- 4 production agents (Behavior, Segmentation, Sentiment, Churn) inheriting from a shared `BaseAgent` ABC
- Full agent audit trail — every execution is logged with timing, validation results, and output summaries
- Mock-first LLM client — all agents run locally with zero API keys; real LLM providers (Anthropic, OpenAI) activate automatically when keys are present
- Per-customer explainability via SHAP feature attributions and template-based natural language explanations

**Data Layer**
- Synthetic data generator producing correlated, realistic customer data across 7 source tables (752K behavior events, 36K orders, 18K sentiment results, 11K support tickets, 7.6K feedback entries)
- Feature engineering service with pure functions for login, engagement, revenue, support, activity, and tenure features
- SQLite database with full ORM models and Pydantic schemas

**Backend**
- FastAPI application with CORS, health check, and structured logging via structlog
- SQLAlchemy ORM models for all 14 tables
- Pydantic schemas for all API response contracts
- Python 3.11 with type hints throughout

**Frontend**
- React 19 + TypeScript + Tailwind CSS 4 dashboard
- 8 page routes: Overview, Customer 360, Segments, Churn & Retention, Sentiment & Support, Recommendations, Agent Audit, Ask Anything
- TanStack Query for server state management
- Vite dev server with API proxy to backend

### Planned (Next Phase)

- DAG-based agent orchestrator for parallel execution
- API routes wired to agent output tables
- Live dashboard data from backend
- ChromaDB vector store for natural language querying
- Anomaly detection and recommendation agents
- Agent Audit page with execution history and validation logs

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  Dashboard Pages ─── TanStack Query ─── Axios Client    │
└──────────────────────────┬──────────────────────────────┘
                           │ /api proxy
┌──────────────────────────┴──────────────────────────────┐
│                   FastAPI Backend                         │
│  Routes ─── Schemas ─── Services ─── Agent Layer         │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│                    Agent Pipeline                         │
│                                                          │
│  BehaviorAgent ──→ SegmentationAgent ──→ SentimentAgent  │
│                           │                              │
│                     ChurnAgent (depends on all three)    │
│                                                          │
│  BaseAgent ABC: run() → validate_output() → save_run()  │
│  LLMClient: mock → anthropic → openai (auto-detected)   │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│               SQLite Database (data/nexus.db)            │
│                                                          │
│  Source tables:  customers, orders, behavior_events,     │
│                  support_tickets, feedback,              │
│                  subscriptions, campaigns                │
│                                                          │
│  Derived tables: customer_features, customer_segments,   │
│                  sentiment_results, churn_predictions,   │
│                  agent_runs                              │
└─────────────────────────────────────────────────────────┘
```

### Mock-First Development

Every agent runs locally without API keys. The `LLMClient` auto-detects available providers:

1. **No keys set** → Mock mode with deterministic canned responses
2. **`ANTHROPIC_API_KEY` set** → Claude 3.5 Sonnet
3. **`OPENAI_API_KEY` set** → GPT-4o-mini

This means the full pipeline — data generation, feature engineering, segmentation, sentiment scoring, churn prediction with SHAP explanations — works entirely offline. LLM providers enhance explanations when available but are never required.

---

## Agent System

### BehaviorAgent

Computes 17 per-customer behavioral features from raw event, order, and support data. Pure Python/pandas — no ML or LLM dependency.

**Inputs**: `behavior_events` (752K rows), `orders`, `support_tickets`, `customers`
**Outputs**: `customer_features` (5,000 rows, 17 features + engagement score)

Features include login frequency (7d/30d), feature usage breadth, session duration, trend direction, total revenue, order count, recency, average order value, support ticket volume, total event count, last active date, tenure, and average resolution time.

The composite engagement score is a weighted combination of normalized login frequency (0.3), feature breadth (0.3), session duration (0.2), and trend direction (0.2).

### SegmentationAgent

Assigns every customer to one of five business-friendly segments using deterministic waterfall rules on RFM and engagement features. Percentile thresholds are computed at runtime from the data distribution.

**Inputs**: `customer_features`
**Outputs**: `customer_segments` (5,000 rows with segment code, name, description, and per-customer explanation)

| Segment | Rule Logic |
|---------|-----------|
| Champions | Revenue ≥ P75 AND engagement ≥ P60 AND recent activity |
| Loyal Customers | Revenue ≥ P50 AND order count ≥ P50 |
| Growth Potential | Recent activity AND engagement ≥ P40 |
| At Risk | Revenue ≥ P25 AND (stale activity OR low engagement) |
| Dormant | Default — none of the above |

Each customer receives a `primary_reason` field explaining their classification in plain English.

### SentimentAgent

Scores customer feedback entries using deterministic keyword-based sentiment analysis. Aggregates per-customer average sentiment and NPS scores back into `customer_features`.

**Inputs**: `feedback` (7,651 rows), `support_tickets` (11,080 rows)
**Outputs**: `sentiment_results` (18,731 rows with label, score, confidence, and source text)

Sentiment distribution: ~35% negative, ~42% neutral, ~23% positive.

### ChurnAgent

Trains a GradientBoosting classifier on 17 features from customer features, segments, and subscriptions. Uses 5-fold cross-validation to generate out-of-fold predictions (preventing data leakage), then SHAP TreeExplainer for per-customer feature attribution.

**Inputs**: `customer_features`, `customer_segments`, `subscriptions`, `customers`
**Outputs**: `churn_predictions` (5,000 rows with probability, risk tier, top risk factors, and natural language explanation)

Key design decisions:
- **Cross-validated scoring**: Each customer's probability comes from a model that never saw them during training
- **Rank-based risk tiers**: Population-relative percentile ranking (Critical 15%, High 20%, Medium 30%, Low 35%) produces meaningful tier distribution regardless of probability clustering
- **SHAP explanations**: Top-3 risk factors per customer with direction-aware natural language ("Risk driven by declining login frequency, offset by auto-renewal active")
- **99.6% cross-validated accuracy** on synthetic data with 14.2% base churn rate

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript 5.9, Vite 8 |
| **Styling** | Tailwind CSS 4, Tremor (installed) |
| **State Management** | TanStack Query 5 |
| **Routing** | React Router 7 |
| **Backend** | FastAPI, Uvicorn, Python 3.11 |
| **ORM / Validation** | SQLAlchemy 2, Pydantic 2 |
| **Database** | SQLite (file-based, `data/nexus.db`) |
| **ML** | scikit-learn (GradientBoosting), SHAP |
| **Data Processing** | pandas, NumPy |
| **LLM Support** | Anthropic SDK, OpenAI SDK (optional) |
| **Synthetic Data** | Faker, NumPy |
| **Logging** | structlog (structured JSON logging) |
| **Testing** | pytest (backend), Vitest (frontend) |

---

## Repository Structure

```
nexus-intelligence/
├── backend/
│   ├── app/
│   │   ├── agents/          # AI agent implementations
│   │   │   ├── base.py      #   BaseAgent ABC (run, validate, execute, audit)
│   │   │   ├── behavior_agent.py
│   │   │   ├── segmentation_agent.py
│   │   │   ├── sentiment_agent.py
│   │   │   └── churn_agent.py
│   │   ├── db/              # Database connection and initialization
│   │   ├── models/          # SQLAlchemy ORM models (14 tables)
│   │   ├── routes/          # FastAPI route handlers
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Shared services
│   │   │   ├── feature_engine.py  # Pure feature computation functions
│   │   │   └── llm_client.py     # Mock-first LLM client
│   │   ├── utils/           # Logging configuration
│   │   ├── config.py        # Settings via pydantic-settings
│   │   └── main.py          # FastAPI application entry point
│   ├── tests/               # pytest test structure
│   └── pyproject.toml       # Python project configuration
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios client + TanStack Query hooks
│   │   ├── components/      # Layout (Sidebar, Header) + shared components
│   │   ├── pages/           # 8 dashboard pages
│   │   ├── types/           # TypeScript interfaces
│   │   ├── utils/           # Color maps, formatters
│   │   ├── App.tsx          # Router + QueryClient setup
│   │   └── main.tsx         # React entry point
│   ├── package.json
│   └── vite.config.ts       # Vite + Tailwind + API proxy
├── scripts/
│   ├── generate_data.py     # Synthetic data generator
│   └── validate_data.py     # Data quality checks
├── data/                    # SQLite database (gitignored)
├── docs/                    # Project documentation
└── CLAUDE.md                # AI assistant project context
```

---

## Getting Started

### Prerequisites

- **Python 3.11+** (developed on 3.11.9)
- **Node.js 18+** (for frontend)
- **Git**

No API keys are required. The entire pipeline runs locally in mock mode.

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/nexus-intelligence.git
cd nexus-intelligence

# Create and activate Python virtual environment
cd backend
python3.11 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -e ".[dev]"

# Generate synthetic data (creates data/nexus.db, ~175MB)
cd ..
python scripts/generate_data.py --seed 42

# Verify data generation
python scripts/validate_data.py

# Start the backend server
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# In a separate terminal
cd frontend

# Install dependencies
npm install --legacy-peer-deps

# Start the dev server (proxies /api to backend)
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) to see the dashboard.

### Running the Agent Pipeline

```bash
cd backend
source .venv/bin/activate

# Run agents in dependency order
python -c "
from app.db.database import SessionLocal
from app.agents.behavior_agent import BehaviorAgent
from app.agents.segmentation_agent import SegmentationAgent
from app.agents.sentiment_agent import SentimentAgent
from app.agents.churn_agent import ChurnAgent

db = SessionLocal()

# Phase 1: Feature engineering
BehaviorAgent().execute(db)

# Phase 1: Segmentation (depends on customer_features)
SegmentationAgent().execute(db)

# Phase 1: Sentiment (updates customer_features)
SentimentAgent().execute(db)

# Phase 2: Churn (depends on all Phase 1 outputs)
ChurnAgent().execute(db)

db.close()
print('Pipeline complete.')
"
```

Each agent logs its progress, validates its output, and writes an audit trail to the `agent_runs` table.

### Optional: Enable LLM Providers

Create a `.env` file in `backend/` to activate real LLM providers:

```env
ANTHROPIC_API_KEY=sk-ant-...
# or
OPENAI_API_KEY=sk-...
```

The `LLMClient` automatically detects available keys and upgrades from mock to live mode. All agents continue to work identically without keys — LLM integration enhances narrative explanations but is never required for core scoring.

---

## Example Workflow

Once the backend is running and agents have executed:

1. **Inspect customer features** — 5,000 customers with 17 behavioral features and composite engagement scores
2. **Review segments** — Every customer classified into one of 5 segments with a written explanation
3. **Check sentiment** — 18,731 feedback and support entries scored with sentiment labels
4. **Analyze churn risk** — Every customer has a churn probability, risk tier (Critical/High/Medium/Low), top-3 SHAP-based risk factors, and a natural language explanation
5. **Audit agent runs** — `agent_runs` table tracks execution time, validation status, and output summaries for every agent execution

```bash
# Quick inspection via SQLite
python -c "
import sqlite3, json
conn = sqlite3.connect('data/nexus.db')
cur = conn.cursor()

# Segment distribution
cur.execute('SELECT segment_name, COUNT(*) FROM customer_segments GROUP BY segment_name')
print('Segments:', dict(cur.fetchall()))

# Churn tier distribution
cur.execute('SELECT risk_tier, COUNT(*) FROM churn_predictions GROUP BY risk_tier')
print('Churn tiers:', dict(cur.fetchall()))

# Sample churn explanation
cur.execute('SELECT explanation FROM churn_predictions WHERE risk_tier=\"Critical\" LIMIT 1')
print('Sample explanation:', cur.fetchone()[0])
conn.close()
"
```

---

## Dashboard Views

The frontend includes 8 dashboard pages designed for executive-level insight consumption:

| Page | Purpose | Status |
|------|---------|--------|
| **Executive Overview** | KPI cards, AI-generated narrative summary | Scaffolded with placeholder data |
| **Customer 360** | Individual customer deep-dive (profile, features, risk, sentiment) | Page structure ready |
| **Segments** | Segment distribution, characteristics, cross-segment comparison | Page structure ready |
| **Churn & Retention** | Risk tier distribution, top churn drivers, at-risk customer list | Page structure ready |
| **Sentiment & Support** | Sentiment trends, topic analysis, support ticket insights | Page structure ready |
| **Recommendations** | AI-generated retention and upsell recommendations per customer | Page structure ready |
| **Agent Audit** | Execution history, validation results, timing, token usage | Page structure ready |
| **Ask Anything** | Natural language queries over customer data | Page structure ready |

> Dashboard pages are scaffolded and routed. Data wiring to backend agent outputs is the next implementation phase.

---

## Why This Project Is Interesting

**It's not just a dashboard.** Most student projects either build a frontend with fake data or train a model in a notebook. This project connects both ends through a coordinated agent system with real data flow.

**The agents are independently useful.** Each agent reads from specific tables, computes something meaningful, validates its own output, and writes structured results. They compose together but don't depend on a monolithic orchestrator.

**Explainability is built in, not bolted on.** The ChurnAgent doesn't just output a probability — it uses SHAP to identify the top factors driving each customer's risk and generates a natural language explanation. The SegmentationAgent writes a `primary_reason` for every classification. This makes the system auditable and presentable.

**Mock-first is a real engineering choice.** The LLM client auto-detects providers and falls back to deterministic mock responses. This means the entire pipeline runs without API keys, costs $0 to develop locally, and produces reproducible results for testing — while still supporting real LLM providers when they're available.

**The data is realistic.** The synthetic data generator produces correlated behavioral patterns — customers who churn show declining logins, increasing support tickets, and lower engagement before they leave. Segments have distinct behavioral distributions. This makes the ML models learn real-ish patterns, not random noise.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No LangChain** | Custom agent orchestration is more explainable, easier to debug, and demonstrates deeper understanding of the architecture |
| **Rule-based segmentation over KMeans** | Business-friendly labels with deterministic, explainable assignments. KMeans produced unstable cluster labels and low silhouette scores (0.17) on this dataset |
| **Cross-validated churn predictions** | Each customer's score comes from a model that never saw them during training — prevents data leakage and overfitting |
| **Rank-based risk tiers** | Population-relative percentile ranking guarantees meaningful tier distribution even when probability values cluster bimodally |
| **SHAP over feature importance** | Per-customer attribution (not just global) — "why is *this* customer at risk" rather than "what features matter in general" |
| **SQLite over PostgreSQL** | Zero-config, file-based, portable. Appropriate for a single-user capstone with 5K customers. Easy to upgrade later |
| **Mock-first LLM client** | Develop and demo without API keys or costs. Live providers enhance but never gate functionality |
| **Ticket-driven development** | Each feature was built, validated, and committed as a discrete ticket — mirrors production engineering workflows |

---

## Roadmap

**Near-term (actively planned):**
- [ ] DAG-based agent orchestrator with parallel execution
- [ ] API routes wired to agent output tables
- [ ] Live dashboard data rendering with charts and tables
- [ ] Anomaly detection agent
- [ ] Recommendation agent
- [ ] Narrative summary agent (LLM-powered)
- [ ] Natural language query agent with ChromaDB vector search

**Future:**
- [ ] Agent Audit page with execution timeline and validation logs
- [ ] Full Customer 360 detail view
- [ ] Deployment (Railway backend + Vercel frontend)

---

## License

This project was built as a capstone / portfolio project. See the repository for license details.

## Author

**Mason** — Full-stack development, AI/ML engineering, system architecture, and product design.

Built incrementally over multiple development sessions using a ticket-based workflow. Every agent was implemented, tested, validated, and hardened before moving to the next.

---

<p align="center">
  <sub>Built with Python, React, scikit-learn, SHAP, and too much structured logging.</sub>
</p>
