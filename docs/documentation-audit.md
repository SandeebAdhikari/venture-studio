# Documentation Accuracy Audit

Production Readiness Remediation #5 — audit of documentation drift against the current codebase (June 2026).

**Method:** Compared core docs to implementation in `api/app/pipeline/*`, `api/app/scheduler/*`, `api/app/observability/*`, `api/app/collectors/*`, `api/app/deployment/*`, `web/*`, and `.github/workflows/*`.

**Outcome:** Stale statements removed or corrected. No application code was modified.

---

## Audit Table

| File | Outdated statement | Corrected statement |
|------|-------------------|---------------------|
| `README.md` | Collection limited to Reddit and RSS | Collection includes Reddit, RSS, and HN Algolia collectors |
| `README.md` | APScheduler daily cron slots enqueue stage jobs | Single `nightly_pipeline` cron @ 02:00 UTC enqueues ARQ `run_pipeline` |
| `README.md` | No mention of observability or alerting | Prometheus `/metrics`, tracing middleware, expanded readiness, alerting (logging/webhook/Slack) documented |
| `README.md` | No mention of deployment bootstrap | Docker entrypoint runs Alembic migrations and startup validation via `app.deployment.bootstrap` |
| `README.md` | Architecture diagram showed only Reddit + RSS sources | Diagram includes HN Algolia collector |
| `README.md` | Daily automation 02:00–07:00 UTC via discrete stage crons | Nightly `nightly_pipeline` → full 14-stage orchestrator; on-demand via `POST /api/v1/pipeline/run` |
| `README.md` | Local setup: `alembic upgrade head` | `python -m app.deployment.bootstrap --mode api --alembic-cwd .` |
| `README.md` | 230 pytest functions | 250+ backend tests; frontend Vitest unit tests |
| `README.md` | Known gap: HN Algolia collector not implemented | HN Algolia collector implemented; removed from gaps |
| `README.md` | Known gap: score stage omitted from scheduler | Score runs inside orchestrated `run_pipeline`; removed from gaps |
| `README.md` | Known gap: no production observability stack | Observability implemented; remaining gaps are E2E tests, BFF auth, multi-replica scheduler |
| `README.md` | Future phase: HN Algolia, email/Slack notifications | Removed (implemented); future phases updated to reflect actual remaining work |
| `docs/scheduler.md` | Six daily cron jobs enqueue independent stage jobs | Single `nightly_pipeline` @ 02:00 UTC enqueues `run_pipeline` |
| `docs/pipeline-orchestration.md` | Scheduler does not call orchestrator; fragmented stage execution | Scheduler enqueues orchestrated `run_pipeline`; orchestrator runs all 14 stages |
| `docs/architecture.md` | Collectors: Reddit, RSS only | Collectors: Reddit, RSS, HN Algolia |
| `docs/architecture.md` | Scheduler enqueues discrete stage jobs — not `run_pipeline` | Scheduler enqueues single orchestrated `run_pipeline` nightly |
| `docs/architecture.md` | Scheduled automation: `enqueue_stage()` per cron | Scheduled automation: `nightly_pipeline` → `run_pipeline` → orchestrator |
| `docs/architecture.md` | 230 tests; no frontend tests | 250+ backend tests; Vitest in `web/`; CI runs both |
| `docs/architecture.md` | No observability layer in diagram | Observability block added (metrics, tracing, alerting, readiness) |
| `docs/mvp.md` | HN Algolia: enum only, no collector registered | HN Algolia collector registered in lifespan and worker context |
| `docs/mvp.md` | Scheduled collection: `collect` @ 02:00 UTC | `nightly_pipeline` @ 02:00 UTC → `run_pipeline` (includes collect) |
| `docs/mvp.md` | APScheduler: 6 daily cron slots | Single `nightly_pipeline` cron |
| `docs/mvp.md` | Out of scope: HN collector, email/Slack, Prometheus | Removed implemented items; observability and alerting marked implemented |
| `docs/mvp.md` | Out of scope: no frontend CI | Frontend CI via `web-quality.yml` and `web-deployment-check.yml` |
| `docs/mvp.md` | Default scheduler table (02:00–07:00, six jobs); score not scheduled | Single row: 02:00 `nightly_pipeline` → `run_pipeline` (all 14 stages) |
| `docs/mvp.md` | Definition of done: HN, score scheduler, frontend CI, observability unchecked | Updated to reflect current implementation status |
| `docs/pipeline.md` | HN Algolia listed under "Not implemented" | HN Algolia collector documented with config, rate limits, registration |
| `docs/api-overview.md` | `hn_algolia` enum only (no collector) | `hn_algolia` listed as implemented collector |
| `docs/api-overview.md` | `/health/ready` checks PostgreSQL + Redis only | Readiness checks PostgreSQL, Redis, worker, scheduler, alerting |
| `docs/api-overview.md` | No `/metrics` endpoint documented | `GET /metrics` Prometheus scrape endpoint documented |
| `docs/api-overview.md` | Scheduler job names: collect, classify, … (six jobs) | Scheduler job name: `nightly_pipeline` |
| `docs/operations.md` | Default schedule: six UTC cron slots (02:00–07:00) | Single `nightly_pipeline` @ 02:00 UTC |
| `docs/operations.md` | Score not in default schedule | Score included in orchestrated pipeline |
| `docs/operations.md` | Manual trigger: `/scheduler/run/collect` | Manual trigger: `/scheduler/run/nightly_pipeline` |
| `docs/operations.md` | 230 tests | 250+ backend tests + frontend Vitest |
| `api/README.md` | Collectors: Reddit, RSS only | Collectors: Reddit, RSS, HN Algolia; deployment and observability packages added |
| `api/README.md` | 230 tests; backend CI only | 250+ tests; backend + frontend CI workflows |

---

## Corrected Architecture Descriptions

### 1. Scheduler and orchestration

**Before:** APScheduler ran six independent daily cron jobs (collect @ 02:00 through venture_report @ 07:00 UTC), each enqueueing a separate ARQ stage job. The score stage was omitted from the default schedule.

**After:** APScheduler registers one job — `nightly_pipeline` at 02:00 UTC — which enqueues a single ARQ `run_pipeline` job. The worker executes `PipelineOrchestrator.run_pipeline()`, running all 14 stages sequentially including score. Per-stage jobs remain available for manual debugging via `POST /api/v1/jobs/{stage}` but are not used by cron.

**Source of truth:** `api/app/scheduler/definitions.py`, `api/app/scheduler/jobs.py`, `docs/scheduler-orchestrator.md`

### 2. Collection sources

**Before:** Reddit and RSS collectors implemented; HN Algolia was enum-only with no registered collector.

**After:** Three collectors registered at API lifespan and worker startup: `reddit`, `rss`, `hn_algolia`. HN Algolia uses the Algolia search API with Redis rate limiting and standard deduplication.

**Source of truth:** `api/app/collectors/hn_algolia/`, `api/app/core/lifespan.py`, `docs/collection-hn-algolia.md`

### 3. Observability and alerting

**Before:** Docs described JSON logs and basic health probes only; Prometheus/Sentry listed as not implemented.

**After:** Production observability includes Prometheus metrics at `GET /metrics`, request tracing via `ObservabilityMiddleware`, expanded readiness at `GET /health/ready` (PostgreSQL, Redis, worker, scheduler, alerting), and configurable alerting backends (logging, webhook, Slack) in `api/app/observability/alerting/`.

**Source of truth:** `api/app/observability/`, `docs/observability.md`, `docs/observability-alerting.md`

### 4. Deployment

**Before:** Docs implied manual `alembic upgrade head` before starting the API.

**After:** Docker entrypoint and local bootstrap use `python -m app.deployment.bootstrap` to run migrations and startup validation. CI includes compose-smoke via `deployment-check.yml` and `verify-deployment.sh`.

**Source of truth:** `api/app/deployment/bootstrap.py`, `docs/deployment.md`

### 5. CI/CD

**Before:** Backend CI only (Ruff, pytest, Docker build).

**After:** Five GitHub Actions workflows: `quality.yml`, `test.yml`, `deployment-check.yml`, `web-quality.yml` (typecheck, ESLint, Vitest), `web-deployment-check.yml` (Next.js build, Docker).

**Source of truth:** `.github/workflows/`, `docs/ci.md`

### 6. Data flow (scheduled automation)

**Before:**
```
APScheduler cron → enqueue_stage() → ARQ → Worker → single stage
```

**After:**
```
APScheduler nightly_pipeline (02:00 UTC)
  → enqueue run_pipeline
  → ARQ Worker
  → PipelineOrchestrator.run_pipeline()
  → 14 stages via PipelineStageExecutor
```

### 7. System architecture diagram

**Before:** Ingestion sources limited to Reddit and RSS; no observability layer; worker described as "15 stage jobs" without orchestrator context.

**After:** Ingestion includes HN Algolia; FastAPI layer includes observability; scheduler enqueues orchestrated pipeline; worker runs orchestrator plus stage handlers.

---

## Files Updated

| File | Action |
|------|--------|
| `README.md` | Updated features, architecture diagram, data flow, setup, gaps, doc links |
| `docs/scheduler.md` | Rewritten (prior session) |
| `docs/pipeline-orchestration.md` | Rewritten (prior session) |
| `docs/architecture.md` | Scheduler, collectors, data flow, testing, diagram |
| `docs/mvp.md` | Full scope/status refresh |
| `docs/pipeline.md` | HN Algolia collector section |
| `docs/api-overview.md` | Collectors, health, metrics, scheduler names |
| `docs/operations.md` | Scheduler schedule and triggers |
| `api/README.md` | Collectors, observability, deployment, test count |
| `docs/documentation-audit.md` | Created (this file) |

---

## Remaining Documentation Notes (not drift)

These are accurate limitations documented after remediation — not stale claims:

- Dashboard BFF has no user authentication (solo-founder deployment model)
- Web service not in default `docker-compose.yml` (optional profile documented in `deployment.md`)
- Default alerting backend is logging; webhook/Slack require configuration
- Multi-replica APScheduler requires external cron or single scheduler-enabled API instance
- ARQ default job timeout (600s) may be tight for full nightly pipeline runs
- No full-stack E2E tests (BFF ↔ API)

---

## Verification Commands

```bash
# Confirm single scheduler job
grep -A5 'DEFAULT_SCHEDULER_JOBS' api/app/scheduler/definitions.py

# Confirm HN collector registration
grep register_hn api/app/core/lifespan.py api/app/workers/context.py

# Confirm observability routes
grep -r '"/metrics"' api/app/

# Confirm CI workflows
ls .github/workflows/
```
