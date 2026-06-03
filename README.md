# AI Venture Studio

An autonomous opportunity discovery and validation platform for solo founders. AI Venture Studio ingests public signals from Reddit and RSS feeds, classifies complaints, generates ranked business opportunities, runs eight research agents, produces executive rankings, and delivers venture recommendation reports — orchestrated by a 14-stage pipeline with background workers, daily scheduling, and a founder dashboard.

---

## Overview

The system replaces manual signal hunting with a repeatable pipeline:

**Internet → Collection → Classification → Opportunity Generation → Scoring → Research Agents → Executive Ranking → Reports**

A solo founder reviews the dashboard daily (~30 minutes), approves rankings and venture reports, and decides which opportunities deserve deeper action. LLM spend is capped by a daily budget with threshold warnings.

---

## Key Features

### V1 Features

- **Collection** — Reddit and RSS collectors with deduplication and rate limiting
- **Classification** — LangGraph agent extracts structured complaints from signals
- **Opportunity Generation** — Pattern detection + LLM synthesis with evidence linkage
- **Scoring** — Deterministic 0–100 scoring engine with dimension breakdown and history
- **Reporting** — Top opportunities and executive venture recommendation markdown reports

### V2 Features

- **Market Research Agent** — Market briefs per opportunity
- **Competitor Agent** — Competitor intelligence and profiles
- **Customer Research Agent** — Customer pain and persona analysis
- **Revenue Validation Agent** — Revenue potential assessment
- **Product Strategy Agent** — Product positioning and wedge
- **Go-To-Market Agent** — GTM plan generation
- **Growth Strategy Agent** — Growth channel evaluation
- **Human Proxy Agent** — Founder-fit scoring with configurable profiles
- **Executive Ranking Agent** — Deterministic composite ranking from all agent outputs

### Operational Features

- **Pipeline Orchestrator** — 14-stage sequential execution with retries and audit trail
- **Workers** — ARQ background jobs on Redis (15 registered jobs)
- **Scheduler** — APScheduler daily cron slots enqueue stage jobs
- **Dashboard** — Next.js founder dashboard with 7 pages
- **Approval Workflow** — Founder approve/reject/research for rankings and reports
- **Budget Controls** — Daily LLM cap with 50/75/90% warnings
- **CI/CD** — GitHub Actions: Ruff, pytest, migration validation, API Docker build, frontend typecheck/lint/test/build

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌─────────────────────────────┐
│   Reddit     │     │  RSS Feeds   │     │     Next.js Dashboard       │
│   Public API │     │              │     │     (web/ — BFF proxy)        │
└──────┬───────┘     └──────┬───────┘     └──────────────┬──────────────┘
       │                    │                              │
       └────────┬───────────┘                              │ REST
                ▼                                          ▼
       ┌────────────────────────────────────────────────────────────┐
       │                    FastAPI (api/)                          │
       │  Pipeline Orchestrator · APScheduler · 25 REST routers     │
       └────────┬───────────────────────────────┬───────────────────┘
                │ enqueue                      │
                ▼                              ▼
       ┌──────────────┐              ┌─────────────────┐
       │    Redis     │◄─────────────│   ARQ Worker    │
       │  ARQ + locks │              │  15 stage jobs  │
       └──────────────┘              └────────┬────────┘
                                              │
                ┌─────────────────────────────┼─────────────────┐
                ▼                             ▼                 ▼
       ┌──────────────┐              ┌──────────────┐   ┌────────────┐
       │ PostgreSQL   │              │  LangGraph   │   │  Scoring & │
       │  + pgvector  │              │  10 agents   │   │  Ranking   │
       └──────────────┘              └──────────────┘   └────────────┘
                                              │
                                              ▼
                                     ┌──────────────┐
                                     │  OpenAI API  │
                                     └──────────────┘
```

See [docs/architecture.md](docs/architecture.md) for full system design.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS v4, SWR |
| **Backend** | FastAPI, Python 3.12, SQLAlchemy 2.0, Pydantic |
| **Database** | PostgreSQL 16 + pgvector |
| **Workers** | ARQ on Redis 7 |
| **Scheduler** | APScheduler 3.x (in-process with API) |
| **Agent Framework** | LangGraph + OpenAI structured output |
| **Infrastructure** | Docker Compose, GitHub Actions |

---

## System Workflow

```
Internet
  → Collection (Reddit, RSS)
  → Classification (LangGraph)
  → Opportunity Generation (patterns + LangGraph)
  → Scoring (deterministic engine)
  → Research (8 LangGraph agents)
  → Executive Ranking (deterministic engine)
  → Venture Report (markdown + approval workflow)
```

Daily automation runs stages at 02:00–07:00 UTC via APScheduler. Full pipeline also available on demand via `POST /api/v1/pipeline/run`.

---

## Getting Started

### Prerequisites

- Python 3.12+, Node.js 20+, Docker & Docker Compose

### Setup

```bash
git clone <repository-url>
cd agent
cp .env.example .env
# Edit .env — set API_KEY and OPENAI_API_KEY

docker compose up -d postgres redis

cd api
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
```

---

## Running the Platform

```bash
# Terminal 1 — API
cd api && uvicorn app.main:app --reload --port 8000

# Terminal 2 — Worker
cd api && arq app.workers.worker.WorkerSettings

# Terminal 3 — Dashboard
cd web
echo 'API_URL=http://localhost:8000' > .env.local
echo 'API_KEY=your-key-from-env' >> .env.local
npm install && npm run dev
```

Or run backend via Docker:

```bash
docker compose up --build
docker compose exec api alembic upgrade head
```

- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:3000

---

## Testing

```bash
docker compose up -d postgres redis
cd api
pip install -e ".[dev]"
alembic upgrade head
PYTHONPATH=. pytest tests/ -q
```

**230 tests** across collection, classification, opportunity generation, scoring, all agents, pipeline, workers, scheduler, dashboard, approval, and budget.

Lint:

```bash
cd api
ruff check app tests alembic
ruff format --check app tests alembic
```

See [docs/ci.md](docs/ci.md) for CI workflow details.

Frontend:

```bash
cd web
npm ci
npm run validate
```

---

## Deployment

Production deployment typically splits:

- **Dashboard** → Vercel or container (`web/`)
- **API + Worker** → VPS or container platform (`api/` Docker image)
- **PostgreSQL** → Managed service with pgvector (Neon, Supabase)
- **Redis** → Managed Redis (Upstash)

See [docs/deployment.md](docs/deployment.md) for full instructions.

---

## Project Structure

```
agent/
├── api/                  # FastAPI backend, workers, agents, migrations
│   ├── app/
│   │   ├── agents/       # LangGraph agents (classification, opportunity, 8 research)
│   │   ├── api/v1/       # REST routers (25 modules)
│   │   ├── collectors/   # Reddit, RSS
│   │   ├── pipeline/     # Orchestrator + executor
│   │   ├── ranking/      # Executive ranking engine
│   │   ├── scoring/      # Opportunity scoring engine
│   │   ├── workers/      # ARQ jobs
│   │   └── scheduler/    # APScheduler
│   ├── alembic/          # 19 database migrations
│   └── tests/            # 230 pytest functions
├── web/                  # Next.js founder dashboard
│   └── src/app/(founder)/  # 7 dashboard pages
├── docs/                 # Documentation
├── docker-compose.yml    # postgres, redis, api, worker
└── .github/workflows/    # CI/CD
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/vision.md](docs/vision.md) | Product vision and principles |
| [docs/mvp.md](docs/mvp.md) | Implemented scope and status |
| [docs/architecture.md](docs/architecture.md) | System architecture |
| [docs/database.md](docs/database.md) | Schema and migrations |
| [docs/pipeline.md](docs/pipeline.md) | Pipeline stage reference |
| [docs/pipeline-orchestration.md](docs/pipeline-orchestration.md) | Orchestrator, workers, scheduler |
| [docs/agents.md](docs/agents.md) | LangGraph agents and engines |
| [docs/api-overview.md](docs/api-overview.md) | REST API reference |
| [docs/dashboard.md](docs/dashboard.md) | Founder dashboard |
| [docs/operations.md](docs/operations.md) | Runbook |
| [docs/deployment.md](docs/deployment.md) | Deployment guide |
| [docs/ci.md](docs/ci.md) | GitHub Actions |

---

## Roadmap

### Current Status

Core platform is functional: full 14-stage pipeline, 8 research agents, founder dashboard, approval workflow, LLM budget, backend CI, and frontend CI (typecheck, lint, build, Docker).

### Known Gaps

- HN Algolia collector (enum exists, not implemented)
- Score stage omitted from default scheduler cron
- No automated E2E tests (frontend or backend)
- No production observability stack (Prometheus, Sentry)
- Web service not in docker-compose

### Future Phases

- Additional source collectors (HN Algolia, Twitter/X with API compliance)
- Scheduler HA / external cron for multi-replica API
- OpenAPI codegen for dashboard types
- Email/Slack notifications for pipeline failures
- Multi-user auth when moving beyond solo-founder deployment

---

## Screenshots

_Screenshots coming soon._ The founder dashboard includes pages for overview, opportunities, pipeline monitoring, reports, approvals, budget tracking, and agent activity.

To capture locally: run the platform and visit http://localhost:3000/dashboard.

---

## License

See repository license file if present.
