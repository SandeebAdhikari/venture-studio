# RC3 — Operational readiness assessment (alerting)

Companion to [rc3-alert-validation-report.md](./rc3-alert-validation-report.md).

## Readiness scorecard

| Capability | Code + unit tests | Staging live delivery | Production |
|------------|-------------------|----------------------|------------|
| Alert engine + cooldown | **Ready** | N/A | Ready |
| Seven alert types | **Ready** | Monitor latency depends on interval | Ready |
| Slack provider | **Ready** | **Pending** one `alerts/test` | Pending secrets |
| Webhook provider | **Ready** | **Pending** one `alerts/test` | Pending secrets |
| Logging fallback | **Ready** | Log aggregation should capture | Ready |
| Production startup enforcement | **Ready** (RC2) | Apply `.env.production.example` | Pending deploy |
| On-call runbooks | **Ready** (RC3 guide) | Tabletop optional | Ready |

**Alerting operational readiness:** **~85%** (framework validated; live delivery proof is ops gate).

## Audit point resolution

Prior audits deducted points because **operational delivery was not fully validated**. RC3 addresses:

| Prior gap | RC3 outcome |
|-----------|-------------|
| Monitor paths untested | Scheduler, queue (2-cycle), stall, worker — integration tests |
| Cooldown only in-memory | Redis `RedisCooldownStore` unit test added |
| Budget/collector wiring | `_emit_budget_alert` and `_maybe_alert_collector_failure` tested |
| Provider routing | Multi-provider + failover tests |
| Production conditions | Config enforcement unchanged; documented ops steps |

**Remaining for full points:** Documented post-deploy `alerts/test` to real Slack/webhook in staging/production.

## Go / no-go

| Decision | Recommendation |
|----------|----------------|
| Enable alerting in production config | **Yes** — enforcement prevents logging-only |
| Rely on framework without live test | **No** — run one test alert per environment |
| Block V2 RC on alerting code | **No** — code path is validated |

## Checklist (ops)

- [ ] `ALERT_PROVIDERS` includes `slack` and/or `webhook` with real URLs
- [ ] `POST /api/v1/observability/alerts/test` returns 200 and message appears in Slack/bridge
- [ ] Worker running so monitor does not false-positive `worker_offline` during deploy window
- [ ] Prometheus scrapes `avs_alerts_*` metrics
- [ ] On-call has [rc3-alert-operational-response-guide.md](./rc3-alert-operational-response-guide.md)

## Related

- [rc3-alert-production-confidence.md](./rc3-alert-production-confidence.md)
- [alerting-readiness.md](./alerting-readiness.md)
