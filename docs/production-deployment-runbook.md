# Production deployment runbook (RC2)

Operational steps to deploy AI Venture Studio API + worker with `ENVIRONMENT=production`. No application code changes — configuration and verification only.

## Prerequisites

- Docker and Docker Compose (or equivalent: K8s with same env vars and probes)
- Filled production `.env` from [.env.production.example](../.env.production.example)
- External alert endpoints (Slack incoming webhook and/or generic webhook URL)
- Strong `API_KEY` (32+ chars) and `OPENAI_API_KEY`

## 1. Prepare configuration

```bash
cp .env.production.example .env
# Edit .env: set ENVIRONMENT=production and all secrets
```

Minimum production variables (enforced at startup):

| Variable | Requirement |
|----------|-------------|
| `ENVIRONMENT` | `production` |
| `API_KEY` | ≥ 32 chars, not example/CI values |
| `OPENAI_API_KEY` | Non-empty |
| `WORKER_READINESS_REQUIRED` | `true` |
| `ALERTING_ENABLED` | `true` |
| `ALERT_PROVIDERS` | Must include `slack` and/or `webhook` with URLs |

## 2. Pre-flight validation (no stack required)

From `api/`:

```bash
export PYTHONPATH=.
python -m app.observability.alerting.cli validate
```

Expect errors before deploy if URLs or keys are missing.

Run automated production matrix:

```bash
API_KEY=ci-github-actions-api-key pytest tests/deployment/test_production_behavior_rc2.py \
  tests/deployment/test_production_validation.py \
  tests/observability/test_alerting_delivery.py -q
```

## 3. Start infrastructure and services

```bash
docker compose up --build -d postgres redis
# Wait for healthy DB/Redis, then:
docker compose up --build -d api worker
```

**Startup sequence (API container):**

1. `wait_for_dependencies` — PG + Redis (exit **11** on timeout)
2. `alembic upgrade head` (exit **10** on failure)
3. `enforce_alert_config` (exit **14**)
4. `enforce_production_settings` (exit **15**)
5. In-process PG/Redis readiness (exit **12**)

Worker container: dependency wait only (`bootstrap --mode worker` pattern); production validation runs on worker process per its entrypoint if configured.

## 4. Verify health

```bash
curl -sS http://localhost:8000/health
curl -sS http://localhost:8000/health/ready | jq .
```

**Pass criteria:**

- `/health` → 200, `status: ok`
- `/health/ready` → 200, `status: ok`, checks include `postgresql`, `redis`, `worker` (when required) all `ok`

If worker was slow to start, retry readiness until heartbeats appear (within `WORKER_HEARTBEAT_TTL_SEC`).

Optional bootstrap HTTP verify:

```bash
cd api && python -m app.deployment.bootstrap --mode verify --ready-url http://127.0.0.1:8000/health/ready
```

Exit **13** if readiness never returns 200.

## 5. Failure response

| Symptom | Action |
|---------|--------|
| Container exits 14 | Fix `ALERT_*` URLs and providers; see [production-failure-matrix.md](./production-failure-matrix.md) |
| Container exits 15 | Fix `API_KEY`, `OPENAI_API_KEY`, `WORKER_READINESS_REQUIRED` |
| Container exits 11 | Check `POSTGRES_HOST` / `REDIS_HOST`, network, credentials |
| API up but `/health/ready` 503, `worker` error | Scale/start worker; confirm Redis heartbeats |
| Migration exit 10 | Inspect Alembic logs; fix DB permissions/schema |

## 6. Rollback

```bash
docker compose down
# Restore previous image tag / .env backup
docker compose up -d
```

Keep previous `.env` and DB snapshot if schema migrated.

## 7. Web dashboard (*separate*)

Compose does not run `web`. Deploy Next.js per [production-deployment.md](./production-deployment.md) § Web dashboard with `AUTH_SECRET`, `DASHBOARD_USERS`, `API_URL`, `API_KEY`.

## 8. Post-deploy monitoring

- Alert monitor enabled via `ALERT_MONITOR_ENABLED` / worker monitor flags in `.env.production.example`
- Confirm test alert or monitor heartbeat in logs
- Nightly pipeline: confirm worker completes jobs within `ARQ_JOB_TIMEOUT_SEC`

## Related documents

- [production-readiness-checklist.md](./production-readiness-checklist.md)
- [production-failure-matrix.md](./production-failure-matrix.md)
- [rc2-validation-report.md](./rc2-validation-report.md)
- [rc2-deployment-confidence-assessment.md](./rc2-deployment-confidence-assessment.md)
