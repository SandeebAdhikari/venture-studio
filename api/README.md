# Backend API — AI Venture Studio

FastAPI backend for the AI Venture Studio platform.

## Prerequisites

- Python 3.12+ (`python3.12 -m venv .venv`)
- Docker & Docker Compose (for PostgreSQL and Redis)

If ports `5432` or `6379` are already in use locally, either stop those services or override
`POSTGRES_PORT` / `REDIS_PORT` in `.env` and adjust `docker-compose.yml` host mappings.

## Quick Start

```bash
# From repository root
cp .env.example .env
# Edit .env — set API_KEY to a secure random string

docker compose up -d postgres redis

cd api
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start background worker (separate terminal)
arq app.workers.worker.WorkerSettings
```

Or run everything with Docker Compose (includes `worker` service):

```bash
docker compose up -d
```

## Endpoints

All `/api/v1/*` resource routes require the `X-API-Key` header.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/health/ready` | Readiness probe (PostgreSQL + Redis) |
| GET | `/api/v1/sources` | List sources (filter: `enabled`, `source_type`) |
| POST | `/api/v1/sources` | Create source |
| GET | `/api/v1/sources/{id}` | Get source |
| PATCH | `/api/v1/sources/{id}` | Update source |
| DELETE | `/api/v1/sources/{id}` | Delete source (local/staging only) |
| GET | `/api/v1/categories` | List categories (filter: `kind`, `code`) |
| GET | `/api/v1/complaints` | List complaints (filter: category/domain/persona/severity) |
| GET | `/api/v1/opportunities` | List opportunities (filter: `review_status`, `min_confidence`) |
| POST | `/api/v1/opportunities/{id}/review` | Set review status |
| GET | `/api/v1/reports` | List reports (filter: `opportunity_id`, `report_type`, `status`) |
| POST | `/api/v1/reports/top-opportunities/generate` | Generate Top Opportunities markdown report |
| GET | `/api/v1/reports/{id}/markdown` | Retrieve report markdown body |
| GET | `/docs` | OpenAPI UI (local/staging only) |

List endpoints support `limit` (1–100) and `offset` pagination.

## Collection Service

Raw complaint data is ingested via `ComplaintCollectionService` (no LLM). Items are
normalized, deduplicated, and stored as `signals` with `processing_status=pending`
for later classification.

```python
from app.collection.schemas import RawComplaintInput
from app.repositories import get_repositories
from app.collection.service import ComplaintCollectionService

# services.collection.ingest(source_id, RawComplaintInput(...))
```

Dedup layers: `(source_id, external_id)`, canonical URL, normalized content hash.

## Opportunity Generator

Classified complaints are analyzed for recurring topics via `OpportunityGeneratorService`.
Each eligible pattern produces an opportunity brief with supporting complaints, confidence
score, and explanation (stored in `problem_statement` and `opportunity_scores.scoring_notes`).

```python
# services.generation.generate(limit=500)
```

Pattern detection groups complaints by repeated phrases in summaries (min cluster size 3).
No market research — synthesis uses complaint evidence only.

## Opportunity Scoring Engine

Opportunities are ranked 0–100 via `OpportunityScoringService` using complaint volume,
severity, evidence-based market indicators, implementation ease, and founder fit.
Each rescore appends to `opportunity_scores` history (one `is_current` row per opportunity).

```python
# services.scoring.score_opportunity(opportunity_id)
# services.scoring.get_score_history(opportunity_id)
```

## Executive Report Engine

Generates a **Top Opportunities Report** in markdown from highest-scored opportunities.
Each entry includes title, score, confidence, supporting evidence, key complaints,
and a recommendation. Reports are stored in `reports` with full structured content.

```python
# services.executive_reports.generate_top_opportunities_report(limit=10)
# services.executive_reports.get_report_markdown(report_id)
```

## Classification Agent

Pending signals are classified via `ComplaintClassificationService` using a LangGraph
workflow (`classify_complaint`) with OpenAI structured output.

```python
from app.repositories import get_repositories
from app.services.container import get_services

# services.classification.classify_signal(signal_id)
# services.classification.classify_pending(limit=50)
```

Output fields: `industry`, `customer_type`, `problem_category`, `severity_score`, `summary`.
Results are stored in `complaints`; each LLM attempt is logged in `llm_calls`.

Set `OPENAI_API_KEY` in `.env` for live classification. Tests use a mock LLM client.

## Tests

```bash
cd api
POSTGRES_PORT=5433 pytest tests/ -v
```

## Docker (full stack)

```bash
cp .env.example .env
docker compose up --build
```

## Migrations

```bash
cd api
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

## Project Layout

See repository `docs/architecture.md` for the full system design.
