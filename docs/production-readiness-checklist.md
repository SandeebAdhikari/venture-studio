# Production readiness checklist (RC2)

Use before promoting V2 to production traffic. All items are **code-verified** unless marked *ops*.

## Environment profile

- [ ] `ENVIRONMENT=production` set on API and worker (not `local` / `staging` unless intentionally staging rules)
- [ ] `DEBUG=false`
- [ ] `LOG_JSON=true`, `LOG_LEVEL=INFO` (or stricter)
- [ ] Secrets not committed; `.env` from `.env.production.example` with all `REPLACE_*` filled

## Authentication and API surface

- [ ] `API_KEY` ≥ 32 characters, cryptographically random
- [ ] `API_KEY` not in blocked list (`ci-github-actions-api-key`, `change-me`, etc.)
- [ ] FastAPI `/docs` disabled in production (`main.py` when `is_production`)
- [ ] CORS not left at `*` for production hosts

## LLM and pipeline

- [ ] `OPENAI_API_KEY` set (required in production validation)
- [ ] `LLM_DAILY_BUDGET_USD` ≥ 5 recommended (warning below 5)
- [ ] `ARQ_JOB_TIMEOUT_SEC` ≥ 3600 (example uses 7200 for heavy runs)

## Worker

- [ ] Worker container/process deployed alongside API
- [ ] `WORKER_READINESS_REQUIRED=true` (enforced in production — startup exit **15** if false)
- [ ] `WORKER_HEARTBEAT_TTL_SEC` aligned with healthcheck interval (example: 90s)
- [ ] Worker healthcheck: `python -m app.workers.healthcheck` (Compose `worker` service)
- [ ] After deploy, `GET /health/ready` shows `worker` ok with active heartbeats

## Data stores

- [ ] PostgreSQL reachable from API/worker (`POSTGRES_*` or URL)
- [ ] Redis reachable (`REDIS_*` or URL)
- [ ] Migrations applied (`bootstrap` api mode or `alembic upgrade head`)
- [ ] pgvector image / extension requirements met (Compose: `pgvector/pgvector:pg16`)

## Alerting (mandatory in production)

- [ ] `ALERTING_ENABLED=true`
- [ ] `ALERT_PROVIDERS` includes **`slack` and/or `webhook`** with valid `http(s)` URLs
- [ ] `ALERT_SLACK_WEBHOOK_URL` set if `slack` listed
- [ ] `ALERT_WEBHOOK_URL` set if `webhook` listed
- [ ] `ALERT_VALIDATION_STRICT=true` recommended (production already enforces via `ENVIRONMENT`)
- [ ] Test delivery: `python -m app.observability.alerting.cli validate` (or documented smoke)

## Founder / publication policy (Model A)

- [ ] `REQUIRE_FOUNDER_APPROVAL=true` (recommended; warning if false)
- [ ] Dashboard users and roles configured for `/approvals` workflow

## Observability and probes

- [ ] Liveness: `GET /health` → 200
- [ ] Readiness: `GET /health/ready` → 200 only when PG, Redis, worker (if required), scheduler (if enabled) are ok
- [ ] Understand: alerting status on `/health/ready` is informational — misconfig must be caught at **startup** (exit 14)

## Web dashboard (*ops*, separate from Compose)

- [ ] Next.js deployed separately (Compose has no `web` service)
- [ ] `AUTH_SECRET` ≥ 32 chars, `DASHBOARD_USERS` JSON, `API_URL`, `API_KEY` on server only
- [ ] See [dashboard-auth.md](./dashboard-auth.md)

## CI vs production

- [ ] CI continues `ENVIRONMENT=local` (`.env.example`) — production rules covered by `api/tests/deployment/test_production_behavior_rc2.py` and related tests
- [ ] Staging/prod deploy pipeline injects production env vars

## Validation evidence (RC2)

- [ ] Run: `cd api && PYTHONPATH=. API_KEY=ci-github-actions-api-key pytest tests/deployment/ tests/observability/test_alerting_delivery.py tests/observability/test_readiness.py -q`
- [ ] Review [rc2-validation-report.md](./rc2-validation-report.md) and [production-failure-matrix.md](./production-failure-matrix.md)
- [ ] *Ops:* One full `docker compose` bring-up with production `.env` and confirm bootstrap + `/health/ready` (see [production-deployment-runbook.md](./production-deployment-runbook.md))
