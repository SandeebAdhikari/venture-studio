# Alerting production readiness

Assessment for Production Readiness Remediation **#11** (and prior **#7** delivery work): make alerting operationally actionable without redesigning observability architecture.

## Readiness assessment

| Area | Status | Notes |
|------|--------|-------|
| Seven domain alert types | **PASS** | All wired in `checks.py` / monitor / orchestrator |
| Slack + webhook delivery | **PASS** | `httpx` providers with URL validation |
| Failover logging | **PASS** | `ALERT_FAILOVER_LOGGING` default true |
| Production external delivery enforcement | **PASS** | Validation error + startup fail (exit 14 / lifespan) |
| Production readiness status | **PASS** | `check_alerting_status` → `error` when misconfigured |
| Configuration documentation | **PASS** | [alert-configuration-guide.md](./alert-configuration-guide.md) |
| Deployment documentation | **PASS** | [alert-deployment.md](./alert-deployment.md) |
| Operator docs (matrix, examples, runbook) | **PASS** | Linked below |
| Automated validation tests | **PASS** | [alert-validation-report.md](./alert-validation-report.md) |

**Overall: PASS** (was **PARTIAL** before #11 — logging-only production and warn-only readiness).

## Remediation #11 — completed

| Gap (before) | Remediation |
|--------------|-------------|
| Production missing external delivery was WARNING | `validate_alert_config` → **error** |
| Only `ALERT_VALIDATION_STRICT` blocked startup | `should_fail_on_alert_errors()` — production + `ALERTING_ENABLED` |
| `.env.example` dev-only defaults | Commented production profile block |
| Partial operator docs | Full doc set + cross-links |
| Readiness `warn` on production misconfig | `error` in production |

## Production configuration

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

## Pre-deploy checklist

- [ ] `ALERT_PROVIDERS` includes `slack` and/or `webhook` with valid URLs
- [ ] `python -m app.observability.alerting.cli validate` exits 0
- [ ] Bootstrap does not exit 14
- [ ] Test alert received (`cli test` or `POST .../alerts/test`)
- [ ] `/health/ready` shows `alerting` status `ok`
- [ ] On-call has [alert-runbook.md](./alert-runbook.md)

## Documentation index

| Document | Purpose |
|----------|---------|
| [alert-configuration-guide.md](./alert-configuration-guide.md) | All env vars |
| [alert-deployment.md](./alert-deployment.md) | Bootstrap, Compose, startup |
| [alert-matrix.md](./alert-matrix.md) | Types, severity, cooldown, dedup |
| [alert-examples.md](./alert-examples.md) | Webhook JSON payloads |
| [alert-validation-report.md](./alert-validation-report.md) | Test coverage map |
| [alert-operational-impact.md](./alert-operational-impact.md) | Runtime/ops impact |
| [alert-routing.md](./alert-routing.md) | Provider routing |
| [alert-runbook.md](./alert-runbook.md) | Incident response |

## Related

- [observability-alerting.md](./observability-alerting.md) — architecture
- [deployment.md](./deployment.md) — platform deploy
