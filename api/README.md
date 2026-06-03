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

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/health/ready` | Readiness probe (PostgreSQL + Redis) |
| GET | `/docs` | OpenAPI UI (local/staging only) |

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
