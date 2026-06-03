# Production alerting

Production alerting sits on top of existing metrics, tracing, readiness, and worker heartbeats. It is **config-driven** and has **no required external SaaS** — providers are optional and default to structured logging.

## Architecture

```
Domain events (pipeline, collectors, LLM budget)
        │
        ▼
  Alert checks (checks.py) ──► AlertEngine.fire()
        │                         │
        │                         ├─ CooldownStore (Redis TTL keys)
        │                         └─ Providers (logging | webhook | slack | email stub)
        │
Background AlertMonitor (lifespan)
        ├─ worker offline
        ├─ scheduler offline
        ├─ ARQ queue backlog growth
        └─ pipeline stall (long-running DB run)
```

### Alert types

| Type | Severity (typical) | Trigger |
|------|-------------------|---------|
| `worker_offline` | critical | No Redis heartbeats when worker monitor enabled |
| `scheduler_offline` | critical | `SCHEDULER_ENABLED` but APScheduler not running |
| `pipeline_failure` | warning/critical | Orchestrator ends `failed` or `partial` |
| `pipeline_stall` | warning | Running pipeline exceeds `ALERT_PIPELINE_STALL_SEC` |
| `queue_backlog_growth` | warning | ARQ queue depth crosses threshold and grows by delta |
| `llm_budget_exhausted` | warning/critical | Budget thresholds (50/75/90%) or hard block at 100% |
| `collector_repeated_failure` | warning | Same source fails ≥ `ALERT_COLLECTOR_FAILURE_THRESHOLD` in window |

### Deduplication and cooldown

- Cooldown key: `{alert_type}:{dedup_key}` stored in Redis (`ALERT_COOLDOWN_KEY_PREFIX`, default `observability:alert:cooldown:`).
- Per-type cooldown seconds are configurable (defaults 5–60 minutes).
- Suppressed alerts increment `avs_alerts_suppressed_total`.

### Providers

| Provider | Config | Notes |
|----------|--------|-------|
| `logging` | Always available if listed | Structured logs with `alert=true` |
| `webhook` | `ALERT_WEBHOOK_URL` | JSON `Alert.to_payload()` POST |
| `slack` | `ALERT_SLACK_WEBHOOK_URL` | Incoming webhook formatted message |
| `email` | Stub | Debug log only until SMTP is added |

Set providers: `ALERT_PROVIDERS=logging,webhook,slack`

## Example alert payloads

### Webhook / logging JSON

```json
{
  "alert_type": "pipeline_failure",
  "severity": "critical",
  "title": "Pipeline failed",
  "message": "stage classify failed",
  "dedup_key": "550e8400-e29b-41d4-a716-446655440000",
  "fired_at": "2026-06-03T12:00:00+00:00",
  "context": {
    "pipeline_run_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "failed",
    "trigger": "api"
  }
}
```

### Log line (extra fields)

```text
Pipeline failed — stage classify failed
  alert_type=pipeline_failure severity=critical dedup_key=550e8400-...
```

## Prometheus metrics

| Metric | Labels | Meaning |
|--------|--------|---------|
| `avs_alerts_fired_total` | `alert_type`, `severity` | Delivered to ≥1 provider |
| `avs_alerts_suppressed_total` | `alert_type` | Skipped due to cooldown |
| `avs_alert_provider_errors_total` | `provider` | Provider delivery failure |

## Health integration

`GET /health/ready` includes an **`alerting`** check:

- `ok` / `disabled` when alerting is off
- `ok` / `providers=[logging,...]` when the engine initialized
- `error` if initialization fails

This check is **informational** and does not fail readiness when alerting is misconfigured (only reports status).

## Configuration reference

```env
ALERTING_ENABLED=true
ALERT_PROVIDERS=logging
ALERT_WEBHOOK_URL=
ALERT_SLACK_WEBHOOK_URL=
ALERT_DEFAULT_COOLDOWN_SEC=300
ALERT_MONITOR_ENABLED=true
ALERT_MONITOR_INTERVAL_SEC=60
ALERT_WORKER_MONITOR_ENABLED=true
ALERT_QUEUE_BACKLOG_THRESHOLD=10
ALERT_QUEUE_GROWTH_DELTA=5
ALERT_PIPELINE_STALL_SEC=3600
ALERT_COLLECTOR_FAILURE_THRESHOLD=3
```

## Operational impact assessment

| Area | Impact |
|------|--------|
| **API process** | One background asyncio task (`alert-monitor`) when `ALERT_MONITOR_ENABLED=true`; negligible CPU at 60s interval |
| **Redis** | Cooldown keys (TTL), collector failure counters, existing heartbeats/queue — low extra memory |
| **Logs** | Default `logging` provider adds warning/critical lines; tune `ALERT_PROVIDERS` for external routing |
| **Noise** | Cooldowns per alert type reduce storms; pipeline/collector alerts keyed by run/source |
| **Dependencies** | No new required packages; webhook/slack use existing `httpx` |
| **Failure mode** | Provider errors are logged and counted; engine still marks cooldown only after successful delivery |

## Testing

```bash
cd api && pytest tests/observability/test_alerting.py tests/observability/test_alerting_integration.py -q
cd api && ruff check app/observability/alerting app/config.py app/observability/readiness.py app/core/lifespan.py
```
