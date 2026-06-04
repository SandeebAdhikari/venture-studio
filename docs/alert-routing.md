# Alert routing

Route operational alerts from AI Venture Studio to on-call channels without vendor lock-in. Delivery uses **generic HTTP webhooks** and **Slack incoming webhooks** (plain POST, no SDK).

## Provider chain

Configure one or more providers in order:

```env
ALERT_PROVIDERS=webhook,slack,logging
```

The engine tries each provider in sequence. If **all** fail and `ALERT_FAILOVER_LOGGING=true` (default), a final delivery attempt is made via the logging provider (unless logging is already in the chain).

| Provider | Env vars | Payload |
|----------|----------|---------|
| `webhook` | `ALERT_WEBHOOK_URL`, optional `ALERT_WEBHOOK_HEADERS` | JSON from `Alert.to_payload()` |
| `slack` | `ALERT_SLACK_WEBHOOK_URL` | Slack `{ "text": "..." }` message |
| `logging` | — | Structured log with `alert_type`, `severity`, context |
| `email` | — | Stub (logs only) |

## Alert categories

| Type | Trigger | Typical severity |
|------|---------|------------------|
| `worker_offline` | Background monitor: no ARQ heartbeats | critical |
| `scheduler_offline` | `SCHEDULER_ENABLED` but APScheduler not running | critical |
| `pipeline_failure` | Orchestrator ends `failed` or `partial` | warning/critical |
| `pipeline_stall` | Running pipeline exceeds `ALERT_PIPELINE_STALL_SEC` | warning |
| `queue_backlog_growth` | ARQ depth ≥ threshold and grows by delta | warning |
| `collector_repeated_failure` | Same source fails ≥ threshold in window | warning |
| `llm_budget_exhausted` | Budget thresholds (50/75/90%) or hard block | warning/critical |

Each type has its own cooldown (see [observability-alerting.md](./observability-alerting.md)).

## Routing examples

### PagerDuty / Opsgenie (generic webhook)

Use the generic webhook provider and point at your integration URL:

```env
ALERT_PROVIDERS=webhook,logging
ALERT_WEBHOOK_URL=https://events.pagerduty.com/v2/enqueue
ALERT_WEBHOOK_HEADERS={"Content-Type":"application/json","Authorization":"Token token=YOUR_TOKEN"}
```

### Slack channel

```env
ALERT_PROVIDERS=slack,logging
ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T000/B000/XXXXXXXX
```

Create the URL in Slack: **Apps → Incoming Webhooks → Add to Slack**.

### Dual delivery (Slack + ticket webhook)

```env
ALERT_PROVIDERS=slack,webhook,logging
ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
ALERT_WEBHOOK_URL=https://your-ticketing-bridge.example/alerts
```

## Verification

### API (authenticated)

```bash
curl -X POST http://localhost:8000/api/v1/observability/alerts/test \
  -H "X-API-Key: $API_KEY"
```

```bash
curl http://localhost:8000/api/v1/observability/alerts/status \
  -H "X-API-Key: $API_KEY"
```

### CLI

```bash
cd api
PYTHONPATH=. python -m app.observability.alerting.cli validate
PYTHONPATH=. python -m app.observability.alerting.cli test
```

### Readiness

`GET /health/ready` includes an `alerting` check with provider list, warnings, and errors. In **production**, validation errors (including missing external delivery) return status **`error`** so misconfig is visible to probes.

## Startup validation

| Mode | Behavior |
|------|----------|
| Development (`ENVIRONMENT=local`) | Log errors/warnings; API starts unless `ALERT_VALIDATION_STRICT=true` |
| `ALERT_VALIDATION_STRICT=true` | Bootstrap exit **14** and lifespan failure on validation errors |
| Production + `ALERTING_ENABLED=true` | Same fail-fast as strict mode when errors exist (external delivery required) |

See [alert-deployment.md](./alert-deployment.md) and [alert-configuration-guide.md](./alert-configuration-guide.md).

## Cooldown and deduplication

Cooldown keys: `{alert_type}:{dedup_key}` in Redis. Suppressed alerts increment `avs_alerts_suppressed_total`. Cooldown is applied only after **successful** delivery to at least one provider.

## Related docs

- [observability-alerting.md](./observability-alerting.md) — architecture and metrics
- [alert-configuration-guide.md](./alert-configuration-guide.md) — environment variables
- [alert-deployment.md](./alert-deployment.md) — bootstrap exit 14 and secrets
- [alert-matrix.md](./alert-matrix.md) — severities, cooldowns, dedup keys
- [alert-examples.md](./alert-examples.md) — webhook JSON payloads
- [alert-runbook.md](./alert-runbook.md) — operational response
- [alerting-readiness.md](./alerting-readiness.md) — readiness assessment
