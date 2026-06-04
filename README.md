# AI Venture Studio

An autonomous opportunity discovery and validation platform for solo founders. AI Venture Studio ingests public signals from Reddit, RSS feeds, and Hacker News (Algolia search), classifies complaints, generates ranked business opportunities, runs eight research agents, produces executive rankings, and delivers venture recommendation reports — orchestrated by a 14-stage pipeline with background workers, nightly scheduling, production observability, and a founder dashboard.

---

## Overview

The system replaces manual signal hunting with a repeatable pipeline:

**Internet → Collection → Classification → Opportunity Generation → Scoring → Research Agents → Executive Ranking → Reports**

A solo founder reviews the dashboard daily (~30 minutes), approves rankings and venture reports, and decides which opportunities deserve deeper action. LLM spend is capped by a daily budget with threshold warnings.

---

## Key Features

### V1 Features

- **Collection** — Reddit, RSS, and HN Algolia collectors with deduplication and rate limiting
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

- **Pipeline Orchestrator** — 14-stage sequential execution with retries, audit trail, and unified `pipeline_runs`
- **Workers** — ARQ background jobs on Redis (15 registered jobs: 14 stages + `run_pipeline`)
- **Scheduler** — APScheduler nightly cron enqueues one orchestrated `run_pipeline` job (02:00 UTC)
- **Observability** — Prometheus metrics (`GET /metrics`), request tracing, expanded readiness, alerting (logging/webhook/Slack)
- **Deployment** — Docker entrypoint runs Alembic migrations and startup validation before Uvicorn
- **Dashboard** — Next.js founder dashboard with 7 pages
- **Approval Workflow** — Founder approve/reject/research for rankings and reports
- **Budget Controls** — Daily LLM cap with 50/75/90% warnings
- **CI/CD** — GitHub Actions: Ruff, pytest, migration validation, API Docker compose-smoke, frontend typecheck/lint/test/build

---

## Architecture

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────┐
│   Reddit     │  │  RSS Feeds   │  │  HN Algolia  │  │     Next.js Dashboard       │
│   Public API │  │              │  │   Search     │  │     (web/ — BFF proxy)      │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────────────┬──────────────┘
       │                 │                 │                         │ REST
       └─────────────────┴─────────────────┘                         ▼
                         ▼
       ┌────────────────────────────────────────────────────────────┐
       │                    FastAPI (api/)                          │
       │  Pipeline Orchestrator · APScheduler · Observability       │
       └────────┬───────────────────────────────┬───────────────────┘
                │ enqueue run_pipeline          │
                ▼                               ▼
       ┌──────────────┐              ┌─────────────────┐
       │    Redis     │◄─────────────│   ARQ Worker    │
       │  ARQ + locks │              │  orchestrator + │
       └──────────────┘              │  orchestrator + │
                                     │  stage handlers │
                                     └────────┬────────┘
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

| Layer               | Technology                                             |
| ------------------- | ------------------------------------------------------ |
| **Frontend**        | Next.js 15, React 19, TypeScript, Tailwind CSS v4, SWR |
| **Backend**         | FastAPI, Python 3.12, SQLAlchemy 2.0, Pydantic         |
| **Database**        | PostgreSQL 16 + pgvector                               |
| **Workers**         | ARQ on Redis 7                                         |
| **Scheduler**       | APScheduler 3.x (in-process with API)                  |
| **Agent Framework** | LangGraph + OpenAI structured output                   |
| **Infrastructure**  | Docker Compose, GitHub Actions                         |

---

## System Workflow

```
Internet
  → Collection (Reddit, RSS, HN Algolia)
  → Classification (LangGraph)
  → Opportunity Generation (patterns + LangGraph)
  → Scoring (deterministic engine)
  → Research (8 LangGraph agents)
  → Executive Ranking (deterministic engine)
  → Venture Report (markdown + approval workflow)
```

Nightly automation: APScheduler `nightly_pipeline` @ 02:00 UTC enqueues `run_pipeline` → full 14-stage orchestrator run. On-demand: `POST /api/v1/pipeline/run`.

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
python -m app.deployment.bootstrap --mode api --alembic-cwd .
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
# Migrations run automatically on API container start (see docs/deployment.md)
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

**250+ tests** across collection (Reddit, RSS, HN Algolia), classification, opportunity generation, scoring, all agents, pipeline, workers, scheduler, observability, deployment bootstrap, dashboard, approval, and budget.

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
│   │   ├── collectors/   # Reddit, RSS, HN Algolia
│   │   ├── deployment/   # Bootstrap (migrations, startup validation)
│   │   ├── observability/ # Metrics, tracing, alerting
│   │   ├── pipeline/     # Orchestrator + executor
│   │   ├── ranking/      # Executive ranking engine
│   │   ├── scoring/      # Opportunity scoring engine
│   │   ├── workers/      # ARQ jobs
│   │   └── scheduler/    # APScheduler
│   ├── alembic/          # 19 database migrations
│   └── tests/            # 250+ pytest functions
├── web/                  # Next.js founder dashboard
│   └── src/app/(founder)/  # 7 dashboard pages (+ Vitest unit tests)
├── docs/                 # Documentation
├── docker-compose.yml    # postgres, redis, api, worker (web optional — see deployment.md)
└── .github/workflows/    # quality, test, deployment-check, web-quality, web-deployment-check
```

---

## Documentation

| Document                                                         | Description                                   |
| ---------------------------------------------------------------- | --------------------------------------------- |
| [docs/vision.md](docs/vision.md)                                 | Product vision and principles                 |
| [docs/mvp.md](docs/mvp.md)                                       | Implemented scope and status                  |
| [docs/architecture.md](docs/architecture.md)                     | System architecture                           |
| [docs/database.md](docs/database.md)                             | Schema and migrations                         |
| [docs/pipeline.md](docs/pipeline.md)                             | Pipeline stage reference                      |
| [docs/pipeline-orchestration.md](docs/pipeline-orchestration.md) | Orchestrator, workers, scheduler              |
| [docs/agents.md](docs/agents.md)                                 | LangGraph agents and engines                  |
| [docs/api-overview.md](docs/api-overview.md)                     | REST API reference                            |
| [docs/dashboard.md](docs/dashboard.md)                           | Founder dashboard                             |
| [docs/operations.md](docs/operations.md)                         | Runbook                                       |
| [docs/deployment.md](docs/deployment.md)                         | Deployment guide (auto-migrations, bootstrap) |
| [docs/observability.md](docs/observability.md)                   | Metrics, tracing, readiness                   |
| [docs/observability-alerting.md](docs/observability-alerting.md) | Production alerting                           |
| [docs/collection-hn-algolia.md](docs/collection-hn-algolia.md)   | HN Algolia collector                          |
| [docs/ci.md](docs/ci.md)                                         | GitHub Actions                                |
| [docs/documentation-audit.md](docs/documentation-audit.md)       | Documentation accuracy audit (remediation #5) |

---

## Roadmap

### Current Status

Core platform is functional: full 14-stage pipeline, 8 research agents, founder dashboard, approval workflow, LLM budget, backend CI, and frontend CI (typecheck, lint, build, Docker).

### Known Gaps

- No automated E2E tests (frontend or full-stack BFF ↔ API)
- Web service not in default docker-compose (intentional — see [docs/deployment.md](docs/deployment.md))
- Dashboard BFF has no user authentication (solo-founder / network-restricted deployment)
- Multi-replica APScheduler requires external cron or single scheduler-enabled API instance
- Full nightly pipeline runs may need `ARQ_JOB_TIMEOUT_SEC=7200` under heavy LLM load (default 3600)

### Future Phases

- Additional source collectors (Twitter/X with API compliance)
- OpenAPI codegen for dashboard types
- Multi-user auth when moving beyond solo-founder deployment
- Full-stack CI smoke (web container + live API)
- Worker Docker healthcheck

---

## Screenshots

_Screenshots coming soon._ The founder dashboard includes pages for overview, opportunities, pipeline monitoring, reports, approvals, budget tracking, and agent activity.

To capture locally: run the platform and visit http://localhost:3000/dashboard.

---

## License

See repository license file if present.
