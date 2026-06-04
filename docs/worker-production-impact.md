# Worker reliability — production impact assessment

Remediation **#12** changes and their runtime effect.

## Changes

| Change | Impact |
|--------|--------|
| `arq_job_timeout_sec` default **600 → 3600** | Nightly `run_pipeline` less likely to be killed mid-run; longer stuck-job window if orchestrator hangs |
| Worker Docker **healthcheck** | Compose/K8s can restart unhealthy worker containers; `docker compose ps` shows worker health |
| Documentation | Production env profile: `ARQ_JOB_TIMEOUT_SEC=7200`, `WORKER_READINESS_REQUIRED=true` |

## No orchestration redesign

- Still one `run_pipeline` ARQ job for 14 stages
- Stage order and retry logic unchanged
- Scheduler still enqueues single nightly job

## Failure and recovery (unchanged mechanisms)

| Failure | Detection | Recovery |
|---------|-------------|----------|
| Worker process crash | Heartbeats expire; `worker_offline` alert | `restart: unless-stopped` / orchestrator restart |
| ARQ job timeout | Job marked failed; up to `arq_max_tries` | Re-enqueue manual or wait next cron |
| Stage failure | `pipeline_runs` partial/failed; `pipeline_failure` alert | Fix data/config; re-run pipeline |
| Stuck lock | Lock TTL 3600 s; stall alert at 3600 s | Wait TTL or delete `lock:pipeline:run` |

## Ops actions after deploy

1. Set `WORKER_READINESS_REQUIRED=true` on API when worker is co-deployed
2. Set `ARQ_JOB_TIMEOUT_SEC=7200` if first nightly run still times out
3. Confirm worker container health: `docker inspect avs-worker --format '{{.State.Health.Status}}'`
4. Confirm heartbeats: dashboard metrics or `list_active_workers` via Redis CLI

## Risk if readiness left disabled

API `/health/ready` can pass while worker is down → scheduler enqueues `run_pipeline` → queue grows → `queue_backlog_growth` / `worker_offline` alerts only after monitor interval.
