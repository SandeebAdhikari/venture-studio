# Alert configuration guide

Configure operational alert delivery for AI Venture Studio (AVS). Local development may use logging only; **production requires external delivery** (Slack and/or webhook).

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ALERTING_ENABLED` | `true` | Master switch for alert engine and monitor |
| `ALERT_PROVIDERS` | `logging` | Comma-separated chain: `slack`, `webhook`, `logging`, `email` (stub) |
| `ALERT_SLACK_WEBHOOK_URL` | — | Slack incoming webhook URL |
| `ALERT_WEBHOOK_URL` | — | Generic HTTPS endpoint (PagerDuty, custom bridge, etc.) |
| `ALERT_WEBHOOK_HEADERS` | — | JSON object of extra HTTP headers |
| `ALERT_WEBHOOK_TIMEOUT_SEC` | `10` | HTTP timeout per delivery attempt |
| `ALERT_FAILOVER_LOGGING` | `true` | Log when all configured providers fail |
| `ALERT_VALIDATION_STRICT` | `false` | Fail startup on any validation error (recommended `true` in prod) |
| `ALERT_DEFAULT_COOLDOWN_SEC` | `300` | Fallback cooldown when type-specific unset |
| `ALERT_*_COOLDOWN_SEC` | see matrix | Per-type cooldown overrides |
| `ALERT_MONITOR_ENABLED` | `true` | Background worker/scheduler/queue/stall checks |
| `ALERT_WORKER_MONITOR_ENABLED` | `true` | ARQ heartbeat monitoring |
| `ALERT_QUEUE_BACKLOG_THRESHOLD` | `10` | Minimum depth before backlog alert |
| `ALERT_QUEUE_GROWTH_DELTA` | `5` | Depth increase to fire backlog alert |
| `ALERT_PIPELINE_STALL_SEC` | `3600` | Running pipeline age before stall alert |
| `ALERT_COLLECTOR_FAILURE_THRESHOLD` | `3` | Consecutive failures per source |
| `ALERT_COLLECTOR_FAILURE_WINDOW_SEC` | `3600` | Redis window for collector failure counts |

`ENVIRONMENT=production` with `ALERTING_ENABLED=true` **requires** at least one of `slack` or `webhook` in `ALERT_PROVIDERS` with valid URLs, even if `ALERT_VALIDATION_STRICT=false`.

## Profiles

### Local / CI

```env
ENVIRONMENT=local
ALERTING_ENABLED=true
ALERT_PROVIDERS=logging
ALERT_VALIDATION_STRICT=false
```

### Production

```env
ENVIRONMENT=production
ALERTING_ENABLED=true
ALERT_PROVIDERS=slack,webhook,logging
ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T000/B000/XXXXXXXX
ALERT_WEBHOOK_URL=https://your-bridge.example.com/alerts
ALERT_WEBHOOK_HEADERS={"Authorization":"Bearer YOUR_TOKEN"}
ALERT_FAILOVER_LOGGING=true
ALERT_VALIDATION_STRICT=true
ALERT_MONITOR_ENABLED=true
ALERT_WORKER_MONITOR_ENABLED=true
```

## Validation

```bash
cd api
PYTHONPATH=. python -m app.observability.alerting.cli validate
```

Startup paths that enforce config:

- API bootstrap (`deployment/bootstrap.py`) — exit **14** when validation errors and production or strict mode
- FastAPI lifespan — `RuntimeError` with same rules before serving traffic

## Related docs

- [alert-routing.md](./alert-routing.md) — provider chain and routing examples
- [alert-deployment.md](./alert-deployment.md) — deploy and secrets
- [alert-matrix.md](./alert-matrix.md) — alert types and cooldowns
- [alert-runbook.md](./alert-runbook.md) — on-call response
