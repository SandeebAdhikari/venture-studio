# V2 Final Stabilization Sprint

**Goal:** Close the operational gap from ~82/100 to **88–91** production readiness without new agents, V3, or architecture redesign.

## Implementation summary

| Audit finding | Action taken | Evidence |
|---------------|--------------|----------|
| **1. Production alert configuration** | Alert rules unchanged (#11); consolidated into production validator; documented in `production-deployment.md` + `.env.production.example` | `production_validation.py` includes `validate_alert_config` errors; bootstrap `enforce_alert_config` (exit 14) + `enforce_production_settings` (exit 15) |
| **2. Production environment defaults** | Added `.env.production.example`; local vs production table in `docs/production-deployment.md` | Defaults remain dev-friendly in `config.py`; enforcement only when `ENVIRONMENT=production` |
| **3. Worker readiness** | **Required in production** via validation error if `WORKER_READINESS_REQUIRED=false` | `production_validation.py`; docs updated |
| **4. API authorization** | Constant-time key compare; production rejects weak/example keys; Tier 1/2 guide | `deps.py`, `api-authorization-production.md` |
| **5. Founder approval policy** | **Model A retained** — `require_founder_approval=true` default; warning if disabled in production | No behavior change; documented in sprint + autonomy recommendation |
| **6. Documentation cleanup** | `production-deployment.md`, API auth guide, deployment.md cross-links | Drift reduced for prod env table |

### Code files touched

- `api/app/deployment/production_validation.py` (new)
- `api/app/deployment/bootstrap.py`
- `api/app/core/lifespan.py`
- `api/app/api/deps.py`
- `api/tests/deployment/test_production_validation.py` (new)
- `.env.production.example` (new)
- `docs/production-deployment.md`, `docs/api-authorization-production.md` (new)
- `docs/deployment.md` (production table updates)

## Remaining blockers (after sprint)

| # | Blocker | Owner | Notes |
|---|---------|-------|-------|
| 1 | Production secrets not in repo | Ops | Must fill `.env` from `.env.production.example` |
| 2 | Web not in Compose | Ops | Separate Next.js deploy with `AUTH_SECRET` / `DASHBOARD_USERS` |
| 3 | Model A publication gate | Product | Nightly run ≠ published venture until founder approves (by design) |
| 4 | No pending-approval alert | Engineering (optional) | Metrics exist; no `alerting` check type yet |
| 5 | Multi-replica APScheduler | Ops | Run one scheduler-enabled API replica |
| 6 | Tier 2 API keys | Engineering | Only if API is public-facing |

## Risk assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Deploy with `ENVIRONMENT=local` in prod by mistake | High | Use `.env.production.example`; checklist in `production-deployment.md` |
| Weak API key | Medium | Startup exit 15 in production |
| API exposed publicly with single key | High | Tier 1: private network + BFF-only pattern |
| Worker down, API “ready” | Low | `WORKER_READINESS_REQUIRED=true` enforced in production |
| Alert misconfig | Low | Exit 14/15 on bootstrap |
| Founder approval SLA miss | Medium | Operational process; optional future alert |

## Updated readiness estimate

| State | Score | Notes |
|-------|-------|-------|
| **Before sprint** | **82/100** | Audit baseline |
| **After code + docs (prod env configured)** | **88–90/100** | Enforcement + docs; autonomy still Model A |
| **After ops (secrets, web, alerts live, approval SLA)** | **90–91/100** | Full stack running with production `.env` |

### Score deltas (approximate)

| Pillar | Δ | Reason |
|--------|---|--------|
| Operations / config | +4 | Production validator, `.env.production.example`, deployment guide |
| Security | +2 | API key validation + constant-time compare |
| Alerting | +1 | Documented + enforced path clear |
| Autonomy | 0 | Model A unchanged (correct for product) |

## Founder approval decision

**Keep Model A** (`REQUIRE_FOUNDER_APPROVAL=true`). Aligns with `config.py` default, `ApprovalService`, dashboard E2E, and [autonomy-policy-recommendation.md](./autonomy-policy-recommendation.md). Model B is not recommended without publication alerts and retract flows.

## V2 stabilized?

**Approaching yes for private founder production** once production `.env` is applied and web is deployed. **No** for fully autonomous unattended publication (intentional).

## Next step

**Continue A. V2 Stabilization** — ops apply production profile; optional small follow-up: pending-approval alert. **Do not start V3.**
