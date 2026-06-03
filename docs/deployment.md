# Deployment

How to deploy AI Venture Studio locally and in production.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.12+ |
| Node.js | 20+ (for dashboard) |
| Docker & Docker Compose | Latest stable |
| PostgreSQL | 16 with pgvector |
| Redis | 7 |

---

## Local Development

### 1. Environment

```bash
cp .env.example .env
# Edit .env — set API_KEY (min 16 chars) and OPENAI_API_KEY
```

### 2. Infrastructure

```bash
docker compose up -d postgres redis
```

Services:
- PostgreSQL: `localhost:5432` (user/pass/db: `avs`/`avs`/`ai_venture_studio`)
- Redis: `localhost:6379`

### 3. Backend

```bash
cd api
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Worker (separate terminal)

```bash
cd api
arq app.workers.worker.WorkerSettings
```

### 5. Dashboard (separate terminal)

```bash
cd web
npm install
# Create web/.env.local:
#   API_URL=http://localhost:8000
#   API_KEY=<same as root .env>
npm run dev
```

Open http://localhost:3000 (dashboard) and http://localhost:8000/docs (API docs, local only).

---

## Docker Compose (API + Worker)

Run the full backend stack:

```bash
cp .env.example .env
docker compose up --build
```

| Service | Port | Command |
|---------|------|---------|
| postgres | 5432 | pgvector/pgvector:pg16 |
| redis | 6379 | redis:7-alpine |
| api | 8000 | uvicorn (from Dockerfile) |
| worker | — | arq WorkerSettings |

**Note:** Migrations are not auto-run on container start. Run manually:

```bash
docker compose exec api alembic upgrade head
```

**Note:** The `web` service is not in docker-compose. Run the dashboard separately or add a custom service.

---

## Production Architecture

Recommended split deployment for a solo founder:

```
┌─────────────┐     ┌──────────────────────────────┐
│  Vercel /   │     │  VPS or container platform   │
│  Next.js    │────►│  FastAPI + ARQ worker        │
│  (web/)     │ BFF │  (api/ Docker image)         │
└─────────────┘     └──────────┬───────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        Managed PG       Managed Redis      OpenAI API
        (Neon/Supabase)  (Upstash)
        + pgvector
```

### Environment variables (production)

| Variable | Required | Notes |
|----------|----------|-------|
| `ENVIRONMENT` | Yes | Set to `production` (disables `/docs`) |
| `API_KEY` | Yes | Secure random string, min 16 chars |
| `OPENAI_API_KEY` | Yes | For LLM agents |
| `POSTGRES_*` | Yes | Managed PostgreSQL with pgvector |
| `REDIS_*` | Yes | Managed Redis |
| `LLM_DAILY_BUDGET_USD` | Recommended | Default 2.00 |
| `REQUIRE_FOUNDER_APPROVAL` | Recommended | Default true |
| `SCHEDULER_ENABLED` | Optional | true for automated daily runs |
| `LOG_JSON` | Recommended | true for structured logs |

### API deployment

```bash
docker build -t ai-venture-studio-api ./api
docker run -d --env-file .env -p 8000:8000 ai-venture-studio-api
```

Run worker as separate container with same image:

```bash
docker run -d --env-file .env ai-venture-studio-api \
  arq app.workers.worker.WorkerSettings
```

### Dashboard deployment

```bash
cd web
npm run build
npm start   # or deploy to Vercel
```

Set `API_URL` to internal backend URL. Set `API_KEY` in server environment (not `NEXT_PUBLIC_`).

### Scheduler considerations

APScheduler runs **inside the API process**. If you scale API to multiple replicas, each replica will register cron jobs unless you:

- Run exactly one API instance with `SCHEDULER_ENABLED=true`, or
- Disable scheduler on replicas and use external cron → `POST /api/v1/jobs/{name}`

---

## Health Checks

| Endpoint | Purpose | Checks |
|----------|---------|--------|
| `GET /health` | Liveness | Returns `{ "status": "ok" }` |
| `GET /health/ready` | Readiness | PostgreSQL + Redis connectivity |

Docker Compose configures API healthcheck against `/health`.

Worker health is not included in readiness probe. Monitor via `GET /api/v1/jobs` and logs.

---

## Migrations

Always run before deploying new API/worker versions:

```bash
cd api
alembic upgrade head
```

CI validates: single head, upgrade, `alembic check` (schema drift).

---

## CI/CD

GitHub Actions on push/PR to `main`:

| Workflow | Purpose |
|----------|---------|
| `quality.yml` | Ruff lint + format |
| `test.yml` | Migrations + pytest (230 tests) |
| `deployment-check.yml` | Docker build, packaging, import smoke |

See [ci.md](./ci.md). Frontend build is not in CI.

---

## Security Checklist

- [ ] `API_KEY` is a cryptographically random string
- [ ] `OPENAI_API_KEY` only in server/worker env
- [ ] `ENVIRONMENT=production` (disables OpenAPI UI)
- [ ] HTTPS termination at reverse proxy (Caddy, nginx, load balancer)
- [ ] Database and Redis not publicly exposed
- [ ] Firewall restricts API access if not using public dashboard

---

## Related Documentation

- [operations.md](./operations.md) — day-to-day runbook
- [architecture.md](./architecture.md) — system design
- [ci.md](./ci.md) — GitHub Actions
