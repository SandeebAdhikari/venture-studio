# Alert matrix

Operational alerts fired by AVS. Cooldowns apply after successful delivery to at least one provider.

**RC3 validation (2026-06-03):** See [rc3-alert-validation-report.md](./rc3-alert-validation-report.md). Automated coverage in `api/tests/observability/test_alerting_rc3_validation.py`.

| Alert type | Severity | Trigger | Dedup key | Cooldown (sec) | RC3 validated |
|------------|----------|---------|-----------|----------------|---------------|
| `worker_offline` | critical | Monitor: no ARQ heartbeats | `global` | 600 (`ALERT_WORKER_OFFLINE_COOLDOWN_SEC`) | Monitor + routing + cooldown |
| `scheduler_offline` | critical | Monitor: scheduler enabled but not running | `global` | 600 | Monitor cycle |
| `pipeline_failure` | critical / warning | Orchestrator run `failed` or `partial` | `pipeline_run_id` | 300 | Helper + dedup; orchestrator code path reviewed |
| `pipeline_stall` | warning | Monitor: run running > `ALERT_PIPELINE_STALL_SEC` | `pipeline_run_id` | 900 | Monitor cycle |
| `queue_backlog_growth` | warning | Monitor: depth ≥ threshold and +delta | `global` | 600 | Two-cycle monitor logic |
| `collector_repeated_failure` | warning | Collection: failures ≥ threshold in window | `source_id` | 1800 | Tracker + collection wiring |
| `llm_budget_exhausted` | warning / critical | Budget thresholds or hard block | `threshold:N` or `exhausted` | 3600 | `_emit_budget_alert` wiring |

## Code references

| Type | Helper | Primary caller |
|------|--------|----------------|
| `worker_offline` | `alert_worker_offline` | `observability/alerting/monitor.py` |
| `scheduler_offline` | `alert_scheduler_offline` | `monitor.py` |
| `pipeline_failure` | `alert_pipeline_failure` | `pipeline/orchestrator.py` |
| `pipeline_stall` | `alert_pipeline_stall` | `monitor.py` |
| `queue_backlog_growth` | `alert_queue_backlog_growth` | `monitor.py` |
| `collector_repeated_failure` | `alert_collector_repeated_failure` | `collection/service.py` |
| `llm_budget_exhausted` | `alert_llm_budget_exhausted` | `services/llm_budget.py` |

## Delivery

Provider order follows `ALERT_PROVIDERS`. See [alert-routing.md](./alert-routing.md) and [alert-examples.md](./alert-examples.md).
