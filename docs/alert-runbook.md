# Alert operations runbook

Operational procedures for AI Venture Studio production alerting.

## Quick checks

1. **Is alerting configured?**

   ```bash
   curl -s http://localhost:8000/health/ready | jq '.checks[] | select(.name=="alerting")'
   ```

   Or authenticated status:

   ```bash
   curl -s http://localhost:8000/api/v1/observability/alerts/status \
     -H "X-API-Key: $API_KEY" | jq
   ```

2. **Send test alert**

   Authenticated endpoint (bypasses cooldown; `severity=info`, `dedup_key=test-delivery`):

   ```bash
   curl -X POST http://localhost:8000/api/v1/observability/alerts/test \
     -H "X-API-Key: $API_KEY"
   ```

   Expect `200` and delivery to all active providers (Slack text message or webhook JSON). Repeat safely — cooldown does not apply to test delivery.

   CLI equivalent:

   ```bash
   cd api && PYTHONPATH=. python -m app.observability.alerting.cli test
   ```

3. **Prometheus**

   - `avs_alerts_fired_total` — successful deliveries
   - `avs_alerts_suppressed_total` — cooldown suppressions
   - `avs_alert_provider_errors_total` — per-provider failures

## Alert response guide

| Alert | Likely cause | First actions |
|-------|--------------|---------------|
| `worker_offline` | ARQ worker down or not heartbeating | Check worker process / `docker compose ps worker`; restart worker |
| `scheduler_offline` | APScheduler not running in API | Restart API; check `SCHEDULER_ENABLED` and logs |
| `pipeline_failure` | Stage error during run | Inspect pipeline run in DB/API; check stage logs and LLM budget |
| `pipeline_stall` | Long-running or stuck pipeline | Check lock holder, running stage, external API latency |
| `queue_backlog_growth` | Jobs enqueue faster than workers process | Scale workers; inspect slow/failing jobs |
| `collector_repeated_failure` | Source API/auth/rate limit issues | Check source config; pause source if needed |
| `llm_budget_exhausted` | Daily spend cap reached | Review `/budget`; raise cap or wait for reset |

## Misconfiguration

### Symptom: `alerting` check shows `error` or `warn` with `errors=...`

In **production**, validation errors (including logging-only providers) surface as **`error`**. Common fixes:

| Error | Fix |
|-------|-----|
| `ALERT_WEBHOOK_URL is required...` | Set URL or remove `webhook` from `ALERT_PROVIDERS` |
| `ALERT_SLACK_WEBHOOK_URL is required...` | Set Slack incoming webhook URL or remove `slack` |
| `must be a valid http(s) URL` | Fix URL scheme/host |
| `ALERT_WEBHOOK_HEADERS must be valid JSON` | Fix JSON object string |

Production startup already fails on validation errors when `ALERTING_ENABLED=true`. Optionally set:

```env
ALERT_VALIDATION_STRICT=true
```

to enforce the same rules in staging/non-production environments.

### Symptom: alerts only in logs

- Confirm `ALERT_PROVIDERS` includes `webhook` and/or `slack`
- Confirm URLs are set and reachable from the API network
- Run test delivery (above)
- Check `avs_alert_provider_errors_total` for delivery failures

### Symptom: provider errors but no alert received

The engine tries all configured providers, then **logging failover** if every provider failed. Check API logs for `Alert provider delivery failed` and provider error metrics.

## Cooldown tuning

If alerts are too noisy, increase per-type cooldown env vars (e.g. `ALERT_WORKER_OFFLINE_COOLDOWN_SEC`). If critical alerts are delayed too long, decrease the relevant cooldown.

Test cooldown behavior does not block verification: the test endpoint uses `skip_cooldown=True`.

## Escalation

1. Verify dependency health: `/health/ready` (PostgreSQL, Redis, worker, scheduler)
2. Review recent pipeline runs and worker job failures
3. If external webhook/Slack is down, rely on logging + Prometheus until routing is restored
4. After incident, confirm test alert delivers to all configured channels

## Related docs

- [alert-routing.md](./alert-routing.md) — configuration and routing
- [alert-deployment.md](./alert-deployment.md) — bootstrap exit 14
- [alert-examples.md](./alert-examples.md) — webhook payload shapes
- [operations.md](./operations.md) — day-to-day operations
- [alerting-readiness.md](./alerting-readiness.md) — production readiness assessment
