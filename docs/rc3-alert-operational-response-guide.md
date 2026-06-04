# RC3 — Alert operational response guide

On-call procedures for each production alert type. Complements [alert-runbook.md](./alert-runbook.md) with RC3-validated trigger semantics.

## Before an incident

1. Confirm alerting status: `GET /api/v1/observability/alerts/status` (API key).
2. After deploy, send test delivery: `POST /api/v1/observability/alerts/test` (bypasses cooldown).
3. Watch metrics: `avs_alerts_fired_total`, `avs_alerts_suppressed_total`, `avs_alert_provider_errors_total`.

## Response by alert type

### `worker_offline` (critical)

**Validated trigger:** Monitor finds zero keys under worker heartbeat prefix (TTL ~90s, check every ≥15s).

| Step | Action |
|------|--------|
| 1 | `docker compose ps worker` — container healthy? |
| 2 | `docker compose logs worker --tail=100` — ARQ crash loop? |
| 3 | `python -m app.workers.healthcheck` inside worker container |
| 4 | Restart worker; confirm `/health/ready` shows `worker` ok |
| 5 | If repeat within cooldown (600s), check Redis connectivity for heartbeats |

**Do not:** Disable `WORKER_READINESS_REQUIRED` in production (startup exit 15).

---

### `scheduler_offline` (critical)

**Validated trigger:** `SCHEDULER_ENABLED=true` but APScheduler not running in API process.

| Step | Action |
|------|--------|
| 1 | Restart API container |
| 2 | Check API logs for scheduler startup errors |
| 3 | Verify only one API replica runs scheduler if using horizontal scale |

---

### `pipeline_failure` (critical / warning)

**Validated trigger:** Orchestrator completes run with status `failed` (critical) or `partial` (warning). Dedup per `pipeline_run_id`, cooldown 300s.

| Step | Action |
|------|--------|
| 1 | Fetch run via API/DB: `pipeline_run_id` in alert context |
| 2 | Identify failed stage and `error_summary` |
| 3 | Check LLM budget, external API rate limits, stage-specific logs |
| 4 | Re-run stage or full pipeline after fix |

---

### `pipeline_stall` (warning)

**Validated trigger:** Single `RUNNING` pipeline exceeds `ALERT_PIPELINE_STALL_SEC` (default 3600). Set to `0` to disable.

| Step | Action |
|------|--------|
| 1 | Identify running stage (DB stage runs) |
| 2 | Check for hung LLM call, lock, or external timeout |
| 3 | Consider cancel/retry; review `ARQ_JOB_TIMEOUT_SEC` |

---

### `queue_backlog_growth` (warning)

**Validated trigger:** Second monitor cycle: `LLEN(arq_queue) ≥ threshold` (10) **and** growth ≥ delta (5). First cycle never alerts.

| Step | Action |
|------|--------|
| 1 | Inspect queue depth trend in Redis |
| 2 | Scale or restart worker |
| 3 | Find slow/failing jobs blocking dequeue |

---

### `llm_budget_exhausted` (warning / critical)

**Validated trigger:** Thresholds 50/75/90% (warning) or hard block at 100% (`dedup_key` `threshold:N` or `exhausted`). Cooldown 3600s.

| Step | Action |
|------|--------|
| 1 | Review daily spend via budget API |
| 2 | Wait for UTC reset or raise `LLM_DAILY_BUDGET_USD` (requires deploy) |
| 3 | Pause non-essential pipeline runs until budget restored |

---

### `collector_repeated_failure` (warning)

**Validated trigger:** ≥ `ALERT_COLLECTOR_FAILURE_THRESHOLD` (3) consecutive failures per `source_id` within window (3600s). Success clears counter.

| Step | Action |
|------|--------|
| 1 | Check source credentials, rate limits, upstream API status |
| 2 | Pause source in DB if upstream is down |
| 3 | After fix, successful collection resets Redis failure key |

---

## Cooldown and duplicate alerts

- Repeating the same condition within the cooldown window **does not** re-notify (by design).
- Escalation requires different `dedup_key` (e.g. new pipeline run) or waiting for cooldown expiry.
- Test alerts **always** deliver (`skip_cooldown`).

## Provider failures

If Slack/webhook fail but logs show **logging failover**, fix external endpoints; alerts are not lost locally. Production still requires valid external URLs at **startup**.

## Misconfiguration

| Symptom | Fix |
|---------|-----|
| Startup exit 14 | Add slack/webhook URLs; see [alert-configuration-guide.md](./alert-configuration-guide.md) |
| `alerting` readiness `error` in production | Same — logging-only not allowed |
| Suppressed storm in metrics | Normal during sustained incident |

## References

- [production-failure-matrix.md](./production-failure-matrix.md) — bootstrap exit codes
- [rc3-alert-validation-report.md](./rc3-alert-validation-report.md) — test evidence
- [alert-runbook.md](./alert-runbook.md) — CLI and curl commands
