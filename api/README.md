# Backend API — AI Venture Studio

FastAPI backend for the AI Venture Studio platform: ingestion, LangGraph agents, pipeline orchestration, ARQ workers, scheduler, and dashboard APIs.

Full API reference: [docs/api-overview.md](../docs/api-overview.md)

---

## Prerequisites

- Python 3.12+ (`python3.12 -m venv .venv`)
- Docker & Docker Compose (PostgreSQL + Redis)

If ports `5432` or `6379` are in use, override `POSTGRES_PORT` / `REDIS_PORT` in `.env`.

---

## Quick Start

```bash
# From repository root
cp .env.example .env
# Edit .env — set API_KEY (min 16 chars) and OPENAI_API_KEY

docker compose up -d postgres redis

cd api
pip install -e ".[dev]"
python -m app.deployment.bootstrap --mode api

# API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Worker (separate terminal)
arq app.workers.worker.WorkerSettings
```

Or run API + worker via Docker Compose:

```bash
docker compose up -d
# Migrations run automatically on API start; verify with:
../api/scripts/verify-deployment.sh
```

---

## Authentication

All `/api/v1/*` routes require:

```
X-API-Key: <API_KEY>
```

Public endpoints: `GET /health`, `GET /health/ready`

OpenAPI UI: `GET /docs` (local/staging only)

---

## Endpoint Summary

See [docs/api-overview.md](../docs/api-overview.md) for the complete reference.

| Area | Prefix | Key operations |
|------|--------|----------------|
| Health | `/health` | Liveness, readiness |
| Sources | `/api/v1/sources` | CRUD for ingestion sources |
| RSS Feeds | `/api/v1/rss-feeds` | Create, list, delete feeds |
| Categories | `/api/v1/categories` | Taxonomy CRUD |
| Complaints | `/api/v1/complaints` | List, get, CRUD |
| Opportunities | `/api/v1/opportunities` | List, review, score |
| Reports | `/api/v1/reports` | CRUD, top-opportunities generate, markdown |
| Executive Reports | `/api/v1/executive-reports` | Venture report generate, markdown, download |
| Market Research | `/api/v1/market-research` | List, generate, per-opportunity |
| Competitor Intelligence | `/api/v1/competitor-intelligence` | List, generate, per-opportunity |
| Customer Research | `/api/v1/customer-research` | List, generate, per-opportunity |
| Revenue Validation | `/api/v1/revenue-validation` | List, generate, per-opportunity |
| Product Strategy | `/api/v1/product-strategy` | List, generate, per-opportunity |
| Go-To-Market | `/api/v1/go-to-market` | List, generate, per-opportunity |
| Growth Strategy | `/api/v1/growth-strategy` | List, generate, per-opportunity |
| Human Proxy | `/api/v1/human-proxy` | Evaluations, founder profiles |
| Executive Ranking | `/api/v1/executive-ranking` | Generate, current, history |
| Pipeline | `/api/v1/pipeline` | Run full pipeline, list runs |
| Jobs | `/api/v1/jobs` | Enqueue pipeline or individual stage jobs, poll status |
| Scheduler | `/api/v1/scheduler` | Cron jobs, enable/disable, manual run |
| Dashboard | `/api/v1/dashboard` | Summary, opportunities, pipeline, reports |
| Approvals | `/api/v1/approvals` | List, approve, reject, research |
| Budget | `/api/v1/budget` | Daily spend, history |

List endpoints support `limit` (1–100) and `offset` pagination.

---

## Core Services

### Collection

`ComplaintCollectionService` ingests via registered collectors (Reddit, RSS). No LLM.

```python
# services.collection.collect_enabled_sources()
```

Dedup: `(source_id, external_id)`, URL, content hash.

### Classification

LangGraph `classify_complaint` via `ComplaintClassificationService`:

```python
# services.classification.classify_pending(limit=50)
```

### Opportunity Generation

`OpportunityGeneratorService` — pattern detection + LangGraph synthesis:

```python
# services.generation.generate(limit=500)
```

### Scoring

Deterministic `OpportunityScoringEngine` (no LLM):

```python
# services.scoring.score_opportunity(opportunity_id)
# services.scoring.score_all(limit=1000)
```

### Pipeline

```python
# services.pipeline.run_pipeline(trigger="manual")
# POST /api/v1/pipeline/run?background=true
# POST /api/v1/jobs/{job_name}
```

14 stages — see [docs/pipeline.md](../docs/pipeline.md).

### Executive Ranking

Deterministic engine combining agent outputs:

```python
# services.executive_ranking.generate_ranking(top_n=5)
```

### Venture Reports

```python
# services.venture_reports.generate_venture_report(top_n=5)
```

---

## Tests

```bash
cd api
docker compose up -d postgres redis   # from repo root
pip install -e ".[dev]"
alembic upgrade head
PYTHONPATH=. pytest tests/ -q
```

**250+ tests.** CI runs Ruff, pytest, migration validation, API Docker compose-smoke, and frontend quality workflows on every push/PR to `main`.

See [docs/ci.md](../docs/ci.md).

---

## Migrations

19 revisions in `alembic/versions/` (001–019). Single linear chain.

```bash
cd api
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

---

## Project Layout

```
api/app/
├── agents/           # LangGraph agents + deterministic engines
├── api/v1/           # REST routers (25 modules)
├── collectors/       # Reddit, RSS, HN Algolia
├── deployment/       # Bootstrap (migrations, startup validation)
├── observability/    # Metrics, tracing, alerting
├── collection/       # ComplaintCollectionService
├── pipeline/         # Orchestrator, executor
├── ranking/          # Executive ranking engine
├── scoring/          # Opportunity scoring engine
├── reports/          # Report generators
├── services/         # Service layer
├── repositories/     # Data access
├── workers/          # ARQ jobs
└── scheduler/        # APScheduler
```

See [docs/architecture.md](../docs/architecture.md).

---

## Configuration

Key environment variables (see `.env.example` at repo root):

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | — | Shared auth key (required, min 16 chars) |
| `OPENAI_API_KEY` | — | LLM provider key |
| `LLM_DAILY_BUDGET_USD` | 2.0 | Daily spend cap |
| `SCHEDULER_ENABLED` | true | Start APScheduler on API boot |
| `REQUIRE_FOUNDER_APPROVAL` | true | Gate rankings and venture reports |
| `CLASSIFY_BATCH_SIZE` | 50 | Classification batch size |
| `MIN_CLUSTER_SIZE` | 3 | Min complaints per opportunity pattern |

Full list in `app/config.py`.
