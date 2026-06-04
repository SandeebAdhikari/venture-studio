# Worker operational risk report

Production Readiness Remediation **#12** — audit findings and remediation status.

**Date:** 2026-06-03  
**Scope:** `api/app/workers/*`, `config.py`, `docker-compose.yml`, readiness, orchestrator timing

## Executive summary

| Finding (audit) | Risk | Remediation status |
|-----------------|------|-------------------|
| `arq_job_timeout_sec = 600` vs 14-stage pipeline | **High** — premature ARQ kill, partial runs, lock contention | **Mitigated** — default raised to **3600**; prod profile **7200** documented |
| Worker Docker healthcheck missing | **Medium** — silent worker death | **Resolved** — `python -m app.workers.healthcheck` |
| `WORKER_READINESS_REQUIRED` default false | **Medium** — API ready without worker | **Documented** — recommend `true` in production |
| Heartbeat / monitor / recovery | **Low–Medium** — design sound; ops config dependent | **Reviewed** — no code change required |

**Orchestration redesign:** **Not recommended** — evidence supports timeout increase, not re-splitting stages.

## 1. `run_pipeline()` duration evaluation

See [worker-timeout-assessment.md](./worker-timeout-assessment.md).

**Conclusion:** Realistic full runs often exceed **10 minutes**; configured ceilings (classify batches, score limit, ten LLM agent stages) support **30–120+ minutes** in heavy workloads.

## 2. Timeout decision

**Recommendation: increase** (not keep, not redesign).

| Setting | Before | After |
|---------|--------|-------|
| Code default `arq_job_timeout_sec` | 600 | **3600** |
| Suggested production | 600 | **7200** (`.env.example` profile) |

Aligns with `pipeline_lock_ttl_sec` and `alert_pipeline_stall_sec` (both 3600).

## 3. Worker healthcheck

**Implementation:** `api/app/workers/healthcheck.py` — Redis scan for active worker heartbeats.

**Compose:** `worker.healthcheck` with 45 s `start_period`, 30 s interval.

**Limitation:** In multi-worker fleets, the probe confirms *some* worker is alive, not a specific replica. Use per-host process monitoring in addition for N>1.

## 4. `WORKER_READINESS_REQUIRED` for production

**Recommendation:** **`true`** on API when workers are required for product function (default AVS deployment).

See [worker-readiness-recommendations.md](./worker-readiness-recommendations.md).

## 5. Heartbeat, failure detection, recovery

### Heartbeat logic

- Written on worker startup and every `max(ttl//3, 10)` seconds
- Cleared on graceful shutdown
- Runs concurrently with ARQ jobs on the same event loop

### Failure detection

| Layer | Mechanism |
|-------|-----------|
| Docker | Worker healthcheck (new) |
| API readiness | Optional worker heartbeat check |
| Alerting | `worker_offline` when monitor finds zero heartbeats |
| Jobs | `JobMonitor` Redis records; ARQ timeouts |

### Recovery behavior

- Container `restart: unless-stopped`
- ARQ `max_tries=3` for transient worker failures
- Orchestrator stage retries independent of ARQ
- Pipeline lock expires after TTL; manual delete documented in operations runbooks

**Gap:** No automatic re-enqueue of timed-out `run_pipeline` — operational re-run required.

## 6. Deliverables index

| Deliverable | Document / code |
|-------------|-----------------|
| Timeout assessment | [worker-timeout-assessment.md](./worker-timeout-assessment.md) |
| Healthcheck implementation | `api/app/workers/healthcheck.py`, `docker-compose.yml` |
| Readiness recommendations | [worker-readiness-recommendations.md](./worker-readiness-recommendations.md) |
| Production impact | [worker-production-impact.md](./worker-production-impact.md) |
| Operational risk report | This file |

## Related

- [workers.md](./workers.md)
- [deployment.md](./deployment.md)
- [scheduler-orchestrator.md](./scheduler-orchestrator.md)
