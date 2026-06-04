# RC2 deployment confidence assessment

Companion to [rc2-validation-report.md](./rc2-validation-report.md).

## Confidence levels

| Layer | Confidence | Rationale |
|-------|------------|-----------|
| Production config validation (exit 14/15, lifespan) | **High (95%)** | 53 automated tests; explicit code paths; smoke exit 14 verified |
| Dependency wait (PG/Redis exit 11) | **High (90%)** | Sync connection tests; bootstrap logic straightforward |
| Worker readiness at runtime | **Medium–high (80%)** | Tests for optional vs required; Compose healthcheck aligned; bootstrap gap documented |
| Full Docker prod-profile E2E | **Medium (65%)** | Not run in RC2 with real secrets; recommended once before go-live |
| Web + dashboard prod deploy | **Medium (60%)** | Out of Compose; documented separately; depends on ops |
| Remote CI reflecting production | **Low for prod rules (N/A)** | By design — local CI env; mitigated by test suite |

**Overall deployment confidence for API + worker:** **~82%** (code-ready; ops proof pending).

## What increases confidence to ~90%+

1. One recorded `docker compose up` with production `.env` (redacted log): bootstrap success, `/health/ready` 200 with worker up.
2. Push `main` to remote and run existing CI green on commit including RC2 tests.
3. Staging environment with real Slack/webhook receiving a test alert.
4. Run `api/scripts/verify-deployment.sh` against staging URL.

## Remaining production risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **17 commits unpushed** to `origin/main` | High (process) | Push when ready; tag RC2 |
| No live prod Compose validation in RC2 | Medium | Execute runbook §3–4 in staging |
| Bootstrap does not verify worker before exit 12 | Medium | Rely on `/health/ready` + Compose `start_period`; or run `bootstrap --mode verify` after worker healthy |
| Flat `API_KEY` (no per-user rotation) | Medium | Network isolation, BFF-only for web; future auth hardening |
| Alerting `error` on `/health/ready` does not fail probe | Low | Startup exit 14 prevents misconfig in prod |
| `REQUIRE_FOUNDER_APPROVAL=false` allowed with warning only | Medium (policy) | Keep `true` (Model A); monitor warnings in logs |
| Web not in Compose | Medium (ops) | Separate deploy checklist |
| No alert on pending founder approval | Low–medium | Operational process / future alerting rule |
| LLM budget & OpenAI outages | Medium | Budget env vars; monitoring |
| pgvector / DB backup / DR | Medium | Ops outside repo |

## Recommendation

- **Ship config enforcement to production:** Yes — behavior is correct and tested.
- **Declare V2 operationally stabilized:** **Conditional YES** after one successful staging deploy using `.env.production.example` profile and green `/health/ready` with worker.
- **Continue V2 stabilization** (not V3): push branch, staging proof, web prod deploy, founder-approval ops.

## Artifacts index

- Checklist: [production-readiness-checklist.md](./production-readiness-checklist.md)
- Runbook: [production-deployment-runbook.md](./production-deployment-runbook.md)
- Failure matrix: [production-failure-matrix.md](./production-failure-matrix.md)
- Tests: `api/tests/deployment/test_production_behavior_rc2.py`
