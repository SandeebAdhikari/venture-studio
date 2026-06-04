# Alert deployment guide

Wire alerting into AVS production deploys without changing the observability architecture.

## Startup order

1. PostgreSQL and Redis reachable (`bootstrap --mode api` waits)
2. Alembic migrations (`avs_migrations_ok`)
3. **Alert config validation** (`enforce_alert_config` in `verify_in_process_readiness`)
4. In-process PG/Redis readiness checks
5. Uvicorn + lifespan: re-validates alerts, `init_alerting`, `start_alert_monitor`

If step 3 fails in production (or `ALERT_VALIDATION_STRICT=true`), the API container exits with code **14** (`STARTUP_EXIT_ALERT_CONFIG_INVALID`).

## Required production env (API container)

Set on the API service (Compose, Kubernetes, or host env):

```env
ENVIRONMENT=production
ALERTING_ENABLED=true
ALERT_PROVIDERS=slack,webhook,logging
ALERT_SLACK_WEBHOOK_URL=<secret>
ALERT_WEBHOOK_URL=<secret>
ALERT_VALIDATION_STRICT=true
```

Store webhook URLs in your secret manager; do not commit them. See commented blocks in `.env.example` and `api/.env.example`.

## Worker container

The worker bootstrap (`--mode worker`) does **not** run alert validation. Alerts are fired from the API process (monitor, orchestrator, collection, LLM budget). Ensure the **API** has correct alert env.

## Post-deploy verification

```bash
# Authenticated test delivery
curl -X POST "$API_BASE/api/v1/observability/alerts/test" -H "X-API-Key: $API_KEY"

curl "$API_BASE/api/v1/observability/alerts/status" -H "X-API-Key: $API_KEY"

curl "$API_BASE/health/ready"
```

CLI (on API host):

```bash
cd api && PYTHONPATH=. python -m app.observability.alerting.cli validate
cd api && PYTHONPATH=. python -m app.observability.alerting.cli test
```

## Docker Compose

Add alert variables to the `api` service `environment` or `env_file`. Redeploy API after changing URLs; worker restart is not required for routing changes.

## Failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Exit 14 on start | Missing Slack/webhook in production | Set `ALERT_PROVIDERS` + URLs per [alert-configuration-guide.md](./alert-configuration-guide.md) |
| `alerting` status `error` on `/health/ready` | Same misconfig while process running | Fix env and restart API |
| Alerts only in logs | `ALERT_PROVIDERS=logging` in prod | Add external providers |
| No alerts at all | `ALERTING_ENABLED=false` or monitor off | Enable alerting and monitor |

## Related

- [deployment.md](./deployment.md) — full stack deploy
- [alert-runbook.md](./alert-runbook.md) — incident response
