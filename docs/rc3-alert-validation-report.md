# V2 RC3 — Alert validation report

**Sprint:** Release Candidate #3 — operational alert delivery  
**Date:** 2026-06-03  
**Scope:** `api/app/observability/alerting/*`, `monitor.py`, `providers/*`, deployment validation  
**No new alert types added.**

## Executive summary

| Area | Result | Evidence |
|------|--------|----------|
| Alert generation (7 types) | **PASS** | RC3 monitor + wiring tests; existing category helpers |
| Provider routing (Slack / webhook / logging) | **PASS** | Multi-provider order test; provider HTTP mocks (#11) |
| Cooldown / duplicate suppression | **PASS** | Storm test + RC3 dedup + Redis store test |
| Logging failover | **PASS** | RC3 slack/webhook failure → logging |
| Production config enforcement | **PASS** | RC2 + `test_alerting_delivery` exit 14 |
| Live Slack/webhook delivery | **OPS** | Not automated; requires staging `alerts/test` |

**Test run:** `pytest tests/observability/test_alerting*.py` — **55 passed** (13 in `test_alerting_rc3_validation.py`).

## Scenario validation matrix

| # | Scenario | Generation | Routing | Cooldown | Dedup | RC3 test |
|---|----------|------------|---------|----------|-------|----------|
| 1 | Worker offline | `monitor.py` → `alert_worker_offline` | All configured providers | 600s, key `worker_offline:global` | Same key suppresses repeats | `test_rc3_monitor_worker_offline_delivers` |
| 2 | Scheduler offline | Monitor when `scheduler_enabled` and not running | Same | 600s, `scheduler_offline:global` | Global | `test_rc3_monitor_scheduler_offline` |
| 3 | Pipeline failure | `orchestrator.py` on `failed`/`partial` | Same | 300s per `pipeline_run_id` | Per run ID | Helper + `test_rc3_different_pipeline_runs_not_suppressed`; orchestrator branch code-reviewed |
| 4 | Pipeline stall | Monitor + `get_running()` elapsed ≥ stall sec | Same | 900s per run ID | Per run ID | `test_rc3_monitor_pipeline_stall` |
| 5 | Queue backlog | Monitor: 2nd cycle, depth ≥ threshold + delta | Same | 600s `global` | Global | `test_rc3_monitor_queue_backlog_requires_two_cycles` |
| 6 | Budget exhaustion | `llm_budget.py` → `_emit_budget_alert` | Same | 3600s `threshold:N` / `exhausted` | Per threshold | `test_rc3_llm_budget_emit_calls_alert_helper` |
| 7 | Collector failures | `ComplaintCollectionService` + Redis tracker | Same | 1800s per `source_id` | Per source | `test_rc3_collector_tracker_threshold`, `test_rc3_collector_failure_wiring` |

## Provider validation

| Provider | Validation method | Result |
|----------|-------------------|--------|
| **Slack** | `SlackAlertProvider` POST mock; included in multi-provider routing | PASS |
| **Webhook** | JSON POST + headers mock; routing order | PASS |
| **Logging** | `LoggingAlertProvider`; default fallback; failover when external providers fail | PASS |

Production requires **slack and/or webhook** with valid URLs (`validate_alert_config`, bootstrap exit **14**).

## Cooldown and duplicate suppression

- **Key:** `{alert_type}:{dedup_key}` (`Alert.cooldown_key`)
- **Store:** `RedisCooldownStore` in production (`SET` + `EX`); `InMemoryCooldownStore` in tests
- **Suppression:** Second fire within cooldown → no delivery, `avs_alerts_suppressed_total` incremented
- **Bypass:** `send_test_alert` / `POST .../alerts/test` use `skip_cooldown=True`
- **RC3:** `test_rc3_duplicate_suppression_same_dedup_key`, `test_rc3_redis_cooldown_suppresses_until_expiry`

## Deployment validation (unchanged, verified)

- `enforce_alert_config` → exit **14** when production + invalid providers
- `validate_production_settings` merges alert errors → exit **15**
- Worker container does not re-run alert enforcement (API owns monitor)

## Gaps (ops, not code defects)

1. **No CI live webhook** — mocks only; run after each deploy:
   ```bash
   curl -X POST http://localhost:8000/api/v1/observability/alerts/test -H "X-API-Key: $API_KEY"
   ```
2. **Monitor loop interval** — default 60s; worker TTL 90s can produce brief gap before `worker_offline`
3. **Queue first cycle** — intentional: no alert until second sample establishes growth
4. **Email provider** — stub only

## Related deliverables

- [alert-matrix.md](./alert-matrix.md) — types, cooldowns, RC3 column
- [rc3-alert-operational-response-guide.md](./rc3-alert-operational-response-guide.md)
- [rc3-operational-readiness-assessment.md](./rc3-operational-readiness-assessment.md)
- [rc3-alert-production-confidence.md](./rc3-alert-production-confidence.md)
