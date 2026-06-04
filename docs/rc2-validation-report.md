# V2 Release Candidate Sprint #2 — Validation report

**Scope:** Production mode behavior (`ENVIRONMENT=production`) — configuration defaults, alert enforcement, production-only validation, worker readiness, Compose alignment. **No feature development.**

**Branch:** `main` at `50f24d3` + uncommitted RC2 tests/docs  
**Date:** 2026-06-03

## Executive summary

Production mode **correctly rejects** weak alert config, weak API keys, disabled worker readiness, and missing OpenAI key **before** serving traffic. Local defaults remain permissive. Automated validation: **53 tests passed** (deployment + alerting + readiness, including new RC2 matrix).

**Gap:** Full Docker bring-up with a real production `.env` was not executed in this sprint (unit/integration tests and sync dependency checks only). Operational confidence for live deploy is **high for config enforcement**, **medium for end-to-end Compose** until one staged prod-profile run is recorded.

## Reviewed artifacts

| Area | Path | Finding |
|------|------|---------|
| Defaults | `api/app/config.py` | `environment=local`, `alert_providers=logging`, `worker_readiness_required=False` — safe for dev |
| Production rules | `api/app/deployment/production_validation.py` | Runs only when `environment=="production"`; merges alert errors; exit **15** |
| Alert enforcement | `api/app/observability/alerting/validation.py` | `should_fail_on_alert_errors()` true for production + alerting; exit **14** |
| Bootstrap | `api/app/deployment/bootstrap.py` | Order: deps (11) → migrate (10) → alert (14) → production (15) → PG/Redis verify (12) |
| Lifespan | `api/app/core/lifespan.py` | Same rules via `RuntimeError` (no process exit code) |
| Readiness | `api/app/observability/readiness.py`, `api/app/api/v1/health.py` | Worker required when flag set; alerting errors informational on `/health/ready` |
| Compose | `docker-compose.yml` | API + worker healthchecks; uses `.env`; no `web` |

## Task 1 — `ENVIRONMENT=production` validation

| Check | Result |
|-------|--------|
| Production validator active | Pass — skipped for `local` |
| Local dev unchanged | Pass — logging-only alerts valid locally |
| Valid minimal prod profile | Pass — `test_production_valid_config_passes_validation` |
| Slack-only external delivery | Pass — webhook URL optional if slack configured |

## Task 2 — Startup success and failure

| Case | Expected | Verified by |
|------|----------|-------------|
| Valid production settings | Validation `valid=True` | RC2 tests + Python smoke |
| Logging-only in production | Fail | Exit **14** smoke: `LOGGING_ONLY_EXIT 14` |
| Insecure / short API key | Fail | Exit **15** tests |
| `WORKER_READINESS_REQUIRED=false` | Fail | Exit **15** tests |
| Lifespan equivalent | `RuntimeError` | Code review `lifespan.py` |
| Missing PostgreSQL | Fail bootstrap wait | `test_postgresql_sync_fails_on_unreachable_host` → would exit **11** in bootstrap |
| Missing Redis | Fail bootstrap wait | `test_redis_sync_fails_on_unreachable_host` → exit **11** |
| In-process readiness after migrate | PG/Redis only in `verify_in_process_readiness` | Code review — worker **not** in bootstrap verify |

## Task 3 — Scenario matrix

| Scenario | Blocks startup (14/15/lifespan) | Blocks `/health/ready` | Test coverage |
|----------|--------------------------------|------------------------|---------------|
| Missing Slack URL (`slack` in providers) | Yes (**14**) | N/A if never starts | RC2 parametrize |
| Missing Webhook URL (`webhook` in providers) | Yes (**14**) | N/A | RC2 parametrize |
| Missing / weak API key | Yes (**15**) | N/A | RC2 + existing validation tests |
| Missing worker (prod flag true) | No at bootstrap verify | Yes (**503** worker check) | `test_readiness.py` patterns; runbook note |
| Missing Redis | Yes (**11**) | Yes | Sync check test + bootstrap |
| Missing PostgreSQL | Yes (**11**) | Yes | Sync check test + bootstrap |
| Logging-only alerts in prod | Yes (**14**) | Informational only if misconfig slipped through | RC2 + alerting delivery tests |

## Task 4 — Deliverables produced

| Deliverable | Document |
|-------------|----------|
| Production readiness checklist | [production-readiness-checklist.md](./production-readiness-checklist.md) |
| Deployment runbook | [production-deployment-runbook.md](./production-deployment-runbook.md) |
| Failure matrix | [production-failure-matrix.md](./production-failure-matrix.md) |
| Validation report | This file |
| Deployment confidence | [rc2-deployment-confidence-assessment.md](./rc2-deployment-confidence-assessment.md) |

## Test execution

```text
cd api && PYTHONPATH=. API_KEY=ci-github-actions-api-key pytest \
  tests/deployment/test_production_behavior_rc2.py \
  tests/deployment/test_production_validation.py \
  tests/observability/test_alerting_delivery.py \
  tests/observability/test_readiness.py -q

53 passed in ~0.8s
```

New file: `api/tests/deployment/test_production_behavior_rc2.py` (parametrized misconfigurations, exit 14/15, unreachable PG/Redis sync).

## Notable design behaviors (not bugs)

1. **Bootstrap verify vs HTTP ready:** Bootstrap in-process verify does not require worker heartbeats; Compose API healthcheck uses `/health/ready`, which **does** when `WORKER_READINESS_REQUIRED=true`. Start worker before or tolerate API healthcheck retries (`start_period: 90s`).
2. **Alerting on readiness endpoint:** Misconfigured alerting reports `error` but does not flip overall readiness to 503 — startup enforcement is the gate.
3. **CI stays local:** GitHub Actions uses permissive env; production rules rely on dedicated tests, not CI `ENVIRONMENT=production`.

## Conclusion

**Production mode behaves correctly** for configuration enforcement and dependency failure detection at the code level. **V2 operationally stabilized** for config/deploy rules: **ready for staged production `.env` trial**; not yet **proven** on a full production Compose run in this sprint.
