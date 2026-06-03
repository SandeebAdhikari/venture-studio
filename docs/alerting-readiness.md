# Alerting production readiness

Assessment for Production Readiness Remediation **#7**: make alerting operationally useful without vendor lock-in.

## What was reviewed

| Area | Location | Finding |
|------|----------|---------|
| Alert engine | `api/app/observability/alerting/engine.py` | Cooldown + multi-provider loop existed; defaulted to logging-only |
| Providers | `providers/logging_provider.py`, `webhook.py`, `slack.py` | Webhook/Slack present but skipped silently when URLs missing |
| Domain triggers | `checks.py`, `monitor.py`, orchestrator, collection, LLM budget | All seven required categories already wired |
| Health | `readiness.py`, `status.py`, `/health/ready` | Basic alerting check; misconfig did not surface clearly |
| Bootstrap | `deployment/bootstrap.py` | No alert config validation at startup |
| Config | `config.py` | Provider URLs present; no headers, strict mode, or failover flag |
| Docs | `observability-alerting.md` | Architecture documented; lacked routing/runbook/readiness |

## What changed

### Delivery

- **Slack**: incoming webhook via `httpx` POST; clear `ValueError` messages when URL missing/invalid
- **Webhook**: JSON payload + optional `ALERT_WEBHOOK_HEADERS`; same validation pattern
- **Failover**: when all configured providers fail, optional logging fallback (`ALERT_FAILOVER_LOGGING`, default `true`)

### Configuration validation

- New `validation.py`: validates provider names, URLs, webhook headers JSON
- **Bootstrap**: warns on misconfig; exits with code `14` when `ALERT_VALIDATION_STRICT=true`
- **Lifespan**: logs validation errors/warnings; strict mode raises before serving

### Operational visibility

- `/health/ready` → `alerting` check reports providers, warnings, errors (informational; does not fail readiness)
- `GET /api/v1/observability/alerts/status` — detailed config state (authenticated)
- `POST /api/v1/observability/alerts/test` — test delivery, bypasses cooldown
- CLI: `python -m app.observability.alerting.cli validate|test`

### Tests

- `tests/observability/test_alerting_delivery.py` — validation, failover, cooldown storm, categories, providers
- `tests/observability/test_alerting_api.py` — status and test endpoints
- Existing alerting tests updated for provider init changes

## Required alert categories — status

| Category | Status | Trigger location |
|----------|--------|------------------|
| Worker offline | ✅ | `monitor.py` → `alert_worker_offline` |
| Scheduler offline | ✅ | `monitor.py` → `alert_scheduler_offline` |
| Pipeline failure | ✅ | `pipeline/orchestrator.py` → `alert_pipeline_failure` |
| Pipeline stall | ✅ | `monitor.py` → `alert_pipeline_stall` |
| Queue backlog | ✅ | `monitor.py` → `alert_queue_backlog_growth` |
| Repeated collector failures | ✅ | `collection/service.py` → `alert_collector_repeated_failure` |
| LLM budget exhaustion | ✅ | `services/llm_budget.py` → `alert_llm_budget_exhausted` |

No new domain triggers were required; work focused on delivery, validation, and operability.

## Production configuration example

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

## Readiness checklist

- [ ] `ALERT_PROVIDERS` includes at least one external channel (`webhook` or `slack`) in production
- [ ] URLs validated (`cli validate` or bootstrap with strict mode)
- [ ] Test alert received in Slack/webhook (`cli test` or API)
- [ ] `/health/ready` shows `alerting` with expected providers
- [ ] Prometheus alerts metrics scraping configured
- [ ] On-call runbook shared ([alert-runbook.md](./alert-runbook.md))

## Residual risks

| Risk | Mitigation |
|------|------------|
| Logging-only in prod if URLs wrong | Strict validation + readiness warnings |
| Redis unavailable for cooldown | In-memory fallback in dev; prod requires Redis |
| Email provider still stub | Documented; use webhook for paging |

## Related documentation

- [alert-routing.md](./alert-routing.md)
- [alert-runbook.md](./alert-runbook.md)
- [observability-alerting.md](./observability-alerting.md)
