# Operations Runbook

Day-to-day operations for running AI Venture Studio.

---

## Daily Founder Workflow

1. Open dashboard at `/dashboard` — review summary metrics
2. Check `/pipeline` — confirm overnight scheduler jobs completed
3. Review `/opportunities` — triage new opportunities (approve/reject/defer via API or future UI)
4. Check `/approvals` — approve/reject venture reports and rankings
5. Monitor `/budget` — verify LLM spend within daily cap
6. Read `/reports` — review latest venture recommendation markdown

Expected time: 30–60 minutes.

---

## Running the Pipeline

### Full pipeline (all 14 stages)

```bash
# Synchronous (blocks until done)
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"trigger": "manual"}'

# Background (returns job ID)
curl -X POST "http://localhost:8000/api/v1/pipeline/run?background=true" \
  -H "X-API-Key: $API_KEY"

# Poll job status
curl http://localhost:8000/api/v1/jobs/{job_id} -H "X-API-Key: $API_KEY"
```

### Single stage

```bash
curl -X POST http://localhost:8000/api/v1/jobs/classify \
  -H "X-API-Key: $API_KEY"
```

Valid stage jobs: `collect`, `classify`, `generate_opportunities`, `score`, `market_research`, `competitor_analysis`, `customer_research`, `revenue_validation`, `product_strategy`, `go_to_market`, `growth_strategy`, `human_proxy`, `executive_ranking`, `venture_report`

### Scheduled automation

With `SCHEDULER_ENABLED=true` (default), APScheduler enqueues one orchestrated pipeline nightly at 02:00 UTC. Ensure at least one ARQ worker is running.

Manual scheduler trigger:

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/run/nightly_pipeline \
  -H "X-API-Key: $API_KEY"
```

List scheduler status:

```bash
curl http://localhost:8000/api/v1/scheduler/jobs -H "X-API-Key: $API_KEY"
```

---

## Worker Queue

### Start worker

```bash
cd api
arq app.workers.worker.WorkerSettings
```

Or via Docker Compose: `docker compose up worker`

### Monitor jobs

```bash
# Recent jobs
curl http://localhost:8000/api/v1/jobs?limit=20 -H "X-API-Key: $API_KEY"

# Specific job
curl http://localhost:8000/api/v1/jobs/{job_id} -H "X-API-Key: $API_KEY"
```

Job status stored in Redis (`job:status:{id}`, 7-day TTL).

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ARQ_MAX_JOBS` | 5 | Concurrent jobs per worker |
| `ARQ_JOB_TIMEOUT_SEC` | 600 | Per-job timeout |
| `ARQ_MAX_TRIES` | 3 | Retry attempts |

See [workers.md](./workers.md).

---

## Scheduler

### Default schedule (UTC)

| Time | Scheduler job | ARQ job |
|------|---------------|---------|
| 02:00 | `nightly_pipeline` | `run_pipeline` (full 14-stage orchestrator) |

Per-stage cron slots were removed. The orchestrator runs all stages including `score`. Manual per-stage execution: `POST /api/v1/jobs/{stage}`.

### Enable/disable jobs

```bash
curl -X PATCH http://localhost:8000/api/v1/scheduler/jobs/nightly_pipeline \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Disable scheduler entirely

Set `SCHEDULER_ENABLED=false` in `.env` (used in CI).

See [scheduler.md](./scheduler.md).

---

## Approval Workflow

When `REQUIRE_FOUNDER_APPROVAL=true` (default):

- Executive ranking runs create `approval_requests` with status `pending`
- Venture reports remain in draft until approved

### Actions

```bash
# List pending approvals
curl "http://localhost:8000/api/v1/approvals?status=pending" -H "X-API-Key: $API_KEY"

# Approve
curl -X POST http://localhost:8000/api/v1/approvals/{id}/approve \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"comment": "Looks good"}'

# Reject
curl -X POST http://localhost:8000/api/v1/approvals/{id}/reject \
  -H "X-API-Key: $API_KEY"

# Request more research (comment required)
curl -X POST http://localhost:8000/api/v1/approvals/{id}/research \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"comment": "Need more competitor data"}'
```

Use the dashboard `/approvals` page for the same actions via BFF.

---

## Budget Controls

### Check current spend

```bash
curl http://localhost:8000/api/v1/budget -H "X-API-Key: $API_KEY"
```

Response includes: daily limit, spent, remaining, per-agent breakdown, active warnings (50/75/90%).

### History

```bash
curl "http://localhost:8000/api/v1/budget/history?days=30" -H "X-API-Key: $API_KEY"
```

### When budget is exceeded

Agent LLM calls fail with budget error. Stages mark partial failure. Options:

1. Wait for UTC day rollover (budget resets daily)
2. Increase `LLM_DAILY_BUDGET_USD` in `.env` and restart API/worker
3. Re-run failed stage via `POST /jobs/{name}`

---

## Monitoring

### What exists

- Structured JSON logs (`LOG_JSON=true`)
- Health probes: `/health`, `/health/ready`
- Dashboard aggregates: `/api/v1/dashboard/summary`
- Pipeline history: `/api/v1/pipeline/runs`
- Scheduler history: embedded in `/api/v1/scheduler/jobs`
- Job monitor: `/api/v1/jobs`

### What does not exist

- Prometheus `/metrics` endpoint
- Sentry, Datadog, or OpenTelemetry integration
- Email/Slack alerting
- Worker health in readiness probe

Operational monitoring is manual: check dashboard, logs, and failed runs daily.

---

## Failure Recovery

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| No new signals | Collector failure | Check `sources.last_error`; test `POST /jobs/collect` |
| Pending signals backlog | Classify not running | Ensure worker running; `POST /jobs/classify` |
| No new opportunities | Generation gates | Check complaint count ≥ `MIN_CLUSTER_SIZE`; review logs |
| Agent stages empty | Missing OpenAI key or budget | Verify `OPENAI_API_KEY` and `GET /budget` |
| Pipeline lock stuck | Crashed worker | Wait for TTL (3600s) or delete Redis key `lock:pipeline:run` |
| Scheduler not firing | API not running or disabled | Check `SCHEDULER_ENABLED`; review API logs |
| Readiness failing | Postgres/Redis down | `docker compose ps`; restart services |

### Database reset (dev only)

```bash
cd api
alembic downgrade base
alembic upgrade head
```

---

## Testing

```bash
docker compose up -d postgres redis
cd api
pip install -e ".[dev]"
alembic upgrade head
PYTHONPATH=. pytest tests/ -q
```

250+ backend tests plus frontend Vitest. CI runs with `SCHEDULER_ENABLED=false` and `REQUIRE_FOUNDER_APPROVAL=false`.

---

## Related Documentation

- [deployment.md](./deployment.md) — deployment guide
- [pipeline-orchestration.md](./pipeline-orchestration.md) — orchestration details
- [workers.md](./workers.md) — ARQ reference
- [ci.md](./ci.md) — CI workflows
