# Production deployment guide

Code-verified checklist for deploying AI Venture Studio (V2 stabilization). Local defaults in `.env.example` intentionally stay permissive; production uses `ENVIRONMENT=production` to enable startup enforcement.

## Quick start

```bash
cp .env.production.example .env
# Fill all REPLACE_* values and secrets
docker compose up --build -d
```

API bootstrap runs migrations, validates production settings, then readiness. Invalid production config exits **14** (alerts) or **15** (general production profile).

## Local vs production

| Variable | Local (default) | Production (required / recommended) |
|----------|-----------------|-------------------------------------|
| `ENVIRONMENT` | `local` | **`production`** |
| `API_KEY` | 16+ chars, dev placeholder | **32+ chars**, not example/CI values |
| `OPENAI_API_KEY` | optional in dev | **required** |
| `ALERT_PROVIDERS` | `logging` | **`slack` and/or `webhook`** with URLs |
| `ALERT_VALIDATION_STRICT` | `false` | **`true`** (redundant with prod enforcement) |
| `WORKER_READINESS_REQUIRED` | `false` | **`true`** |
| `ARQ_JOB_TIMEOUT_SEC` | `3600` | **`7200`** for heavy nightly runs |
| `REQUIRE_FOUNDER_APPROVAL` | `true` | **`true`** (Model A — see below) |
| `LLM_DAILY_BUDGET_USD` | `2.0` | **`10.0+`** recommended |
| `DEBUG` | `false` | **`false`** |
| FastAPI `/docs` | enabled | **disabled** (`main.py`) |
| CORS | `*` (local) | **empty** (no wildcard) |

## Startup enforcement (code)

| Check | Module | Exit code |
|-------|--------|-----------|
| External alert delivery | `observability/alerting/validation.py` | **14** |
| API key strength, worker readiness, OpenAI key | `deployment/production_validation.py` | **15** |
| Lifespan | Same rules → `RuntimeError` before serving | — |

## Web dashboard (separate deploy)

Compose does **not** include `web`. Deploy Next.js with:

| Variable | Purpose |
|----------|---------|
| `AUTH_SECRET` | 32+ char session signing |
| `DASHBOARD_USERS` | JSON user list (founder/admin/viewer) |
| `API_URL` | Internal API base URL |
| `API_KEY` | Same strong key as API (BFF only) |

Do not expose the API key to browsers. See [dashboard-auth.md](./dashboard-auth.md) and [api-authorization-production.md](./api-authorization-production.md).

## Worker

- Container healthcheck: `python -m app.workers.healthcheck`
- Co-deploy worker with API; set `WORKER_READINESS_REQUIRED=true` so `/health/ready` fails if heartbeats are missing

## Founder approval (Model A)

Keep `REQUIRE_FOUNDER_APPROVAL=true`. Pipeline completes nightly; venture reports stay `draft` until `/approvals` approve. See [autonomy-policy-recommendation.md](./autonomy-policy-recommendation.md).

## RC5 full pipeline validation

- [rc5-full-pipeline-validation-report.md](./rc5-full-pipeline-validation-report.md)
- [rc5-production-confidence-score.md](./rc5-production-confidence-score.md)

## RC4 API authorization (analysis)

- [rc4-security-report.md](./rc4-security-report.md)
- [rc4-threat-assessment.md](./rc4-threat-assessment.md)
- [rc4-authorization-recommendations.md](./rc4-authorization-recommendations.md)

## RC2 production package

- [production-readiness-checklist.md](./production-readiness-checklist.md)
- [production-deployment-runbook.md](./production-deployment-runbook.md)
- [production-failure-matrix.md](./production-failure-matrix.md)
- [rc2-validation-report.md](./rc2-validation-report.md)
- [rc2-deployment-confidence-assessment.md](./rc2-deployment-confidence-assessment.md)

## Related

- [deployment.md](./deployment.md) — architecture and Compose
- [alert-configuration-guide.md](./alert-configuration-guide.md)
- [worker-readiness-recommendations.md](./worker-readiness-recommendations.md)
- [v2-final-stabilization-sprint.md](./v2-final-stabilization-sprint.md) — sprint summary
