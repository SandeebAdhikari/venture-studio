# Alert matrix

Operational alerts fired by AVS. Cooldowns apply after successful delivery to at least one provider.

| Alert type | Severity | Trigger | Dedup key | Cooldown (sec) | Config override |
|------------|----------|---------|-----------|----------------|-----------------|
| `worker_offline` | critical | Monitor: no ARQ heartbeats | `global` | 600 | `ALERT_WORKER_OFFLINE_COOLDOWN_SEC` |
| `scheduler_offline` | critical | Monitor: scheduler enabled but not running | `global` | 600 | `ALERT_SCHEDULER_OFFLINE_COOLDOWN_SEC` |
| `pipeline_failure` | critical / warning | Orchestrator run `failed` or `partial` | `pipeline_run_id` | 300 | `ALERT_PIPELINE_FAILURE_COOLDOWN_SEC` |
| `pipeline_stall` | warning | Monitor: run running > `ALERT_PIPELINE_STALL_SEC` | `pipeline_run_id` | 900 | `ALERT_PIPELINE_STALL_COOLDOWN_SEC` |
| `queue_backlog_growth` | warning | Monitor: depth ≥ threshold and +delta | `global` | 600 | `ALERT_QUEUE_BACKLOG_COOLDOWN_SEC` |
| `collector_repeated_failure` | warning | Collection: failures ≥ threshold in window | `source_id` | 1800 | `ALERT_COLLECTOR_FAILURE_COOLDOWN_SEC` |
| `llm_budget_exhausted` | warning / critical | Budget thresholds or hard block | `threshold:N` or `exhausted` | 3600 | `ALERT_LLM_BUDGET_COOLDOWN_SEC` |

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
