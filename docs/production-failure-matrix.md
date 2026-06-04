# Production failure matrix (RC2)

Maps misconfiguration or missing dependencies to **symptom**, **where it is detected**, and **exit / HTTP behavior**. Code paths verified against `api/app/deployment/bootstrap.py`, `production_validation.py`, `observability/alerting/validation.py`, `observability/readiness.py`, and `api/app/core/lifespan.py`.

## Configuration validation (before dependencies)

| Scenario | Detection | Bootstrap (`python -m app.deployment.bootstrap`) | API lifespan (uvicorn) | Automated test |
|----------|-----------|---------------------------------------------------|------------------------|----------------|
| `ENVIRONMENT=production` + `ALERT_PROVIDERS=logging` only | `validate_alert_config` | Exit **14** (`enforce_alert_config`) | `RuntimeError` | `test_production_behavior_rc2`, `test_alerting_delivery` |
| `slack` in providers, empty `ALERT_SLACK_WEBHOOK_URL` | Alert validation | Exit **14** | `RuntimeError` | `test_production_behavior_rc2` (parametrize) |
| `webhook` in providers, empty `ALERT_WEBHOOK_URL` | Alert validation | Exit **14** | `RuntimeError` | `test_production_behavior_rc2` |
| `API_KEY` &lt; 32 chars | Production validation | Exit **15** | `RuntimeError` | `test_production_validation` |
| `API_KEY` = CI/example placeholder | Production validation | Exit **15** | `RuntimeError` | `test_production_validation` |
| `WORKER_READINESS_REQUIRED=false` | Production validation | Exit **15** | `RuntimeError` | `test_production_behavior_rc2` |
| Missing / empty `OPENAI_API_KEY` | Production validation | Exit **15** | `RuntimeError` | `test_production_behavior_rc2` |
| Valid production profile (slack + URLs, strong key, worker flag) | Both validators | Success (after deps) | Starts | `test_production_valid_config_passes_validation` |
| `ENVIRONMENT=local` + logging-only alerts | Skipped / non-strict | Success | Starts | `test_local_default_skips_production_rules` |

**Order in bootstrap `verify_in_process_readiness`:** `enforce_alert_config` (14) runs before `enforce_production_settings` (15). Alert errors duplicated in `validate_production_settings` still surface as 15 if alert enforcement were disabled — in production, 14 always fires first when alerting is enabled.

## Infrastructure dependencies

| Scenario | Detection | Bootstrap | Lifespan | `/health/ready` |
|----------|-----------|-----------|----------|-----------------|
| PostgreSQL unreachable during bootstrap wait | `wait_for_dependencies` → `check_postgresql_sync` | Exit **11** (timeout, default 120s) | May fail on DB init | `postgresql` check → **503** |
| Redis unreachable during bootstrap wait | `wait_for_dependencies` → `check_redis_sync` | Exit **11** | May fail on Redis init | `redis` check → **503** |
| PG/Redis down after API up | Readiness checks | N/A | N/A | **503** |
| Alembic migration failure | `run_alembic_upgrade` | Exit **10** | N/A | N/A |

## Worker and HTTP readiness

| Scenario | Detection | Bootstrap `verify` | `/health/ready` | Compose |
|----------|-----------|-------------------|-----------------|---------|
| Worker not running, `WORKER_READINESS_REQUIRED=true` | `check_worker_availability` | **Not checked** (bootstrap only verifies PG + Redis) | `worker` → **503** | API healthcheck may fail after start_period |
| Worker not running, `WORKER_READINESS_REQUIRED=false` | Worker check | Passes bootstrap | `worker` → ok (`not required`) | Allowed in dev only; **rejected at config** in production |
| `bootstrap --mode verify` while worker down | HTTP poll | Exit **13** if `/health/ready` ≠ 200 | — | Use after worker is up |

## Alerting at runtime (informational)

| Scenario | `/health/ready` |
|----------|-----------------|
| Alert misconfiguration | `alerting` check may be `error`; **does not fail** overall readiness (`health.py` treats alerting as informational) |

Startup still blocks misconfigured alerts in production via exit **14** / lifespan `RuntimeError`.

## Exit code reference

| Code | Constant | Meaning |
|------|----------|---------|
| 10 | `STARTUP_EXIT_MIGRATION_FAILED` | Alembic upgrade failed |
| 11 | `STARTUP_EXIT_DEPS_TIMEOUT` | PostgreSQL and/or Redis not reachable in time |
| 12 | `STARTUP_EXIT_READINESS_FAILED` | In-process PG/Redis readiness failed after migrate |
| 13 | `STARTUP_EXIT_VERIFY_FAILED` | HTTP readiness URL not 200 in time |
| 14 | `STARTUP_EXIT_ALERT_CONFIG_INVALID` | Alert config invalid when enforcement applies |
| 15 | `STARTUP_EXIT_PRODUCTION_CONFIG_INVALID` | Production profile invalid |

## Defaults that are unsafe for production (local dev)

From `api/app/config.py`:

- `environment="local"`
- `alert_providers="logging"`
- `worker_readiness_required=False`

Production behavior requires explicit `ENVIRONMENT=production` and values from `.env.production.example`.
