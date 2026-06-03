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
