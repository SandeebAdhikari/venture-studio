# Alert operational impact assessment

Remediation **#11** — impact of enforcing production alert routing.

## Before

| Aspect | State |
|--------|--------|
| Default providers | `logging` only |
| Production misconfig | Warning only; API started |
| On-call signal | Logs unless operators changed env manually |
| Readiness `alerting` | `warn` for config errors |

## After

| Aspect | State |
|--------|--------|
| Production requirement | At least one of Slack or webhook with valid URLs |
| Misconfigured production deploy | API **does not start** (bootstrap exit 14, lifespan `RuntimeError`) |
| `ALERT_VALIDATION_STRICT=true` | Same fail-fast in any environment |
| Readiness | `alerting` status `error` when startup would fail |

## Operational benefits

- Failed deploys surface immediately in CI/CD or container restart loops instead of silent log-only alerting
- Dual delivery (`slack,webhook,logging`) supports chat + ticketing without architecture changes
- Documented matrix, examples, and runbook reduce mean time to configure new environments

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Deploy blocked without secrets | Document production profile in `.env.example`; use secret manager in prod |
| Staging uses `ENVIRONMENT=production` without URLs | Use `local`/`staging` or set URLs; or enable strict only in true prod |
| Alert storm | Per-type cooldowns unchanged; Redis-backed in production |
| False positive worker offline | Tune monitor interval; see [alert-runbook.md](./alert-runbook.md) |

## No architecture change

Engine, provider interfaces, monitor triggers, and domain helpers are unchanged. Only validation strictness, documentation, and tests were extended.
