# RC3 — Alert production confidence report

**Date:** 2026-06-03  
**Sprint:** V2 Release Candidate #3

## Confidence summary

| Layer | Confidence | Notes |
|-------|------------|-------|
| Alert type coverage (7/7) | **92%** | All helpers + monitor/wiring tests |
| Deduplication / cooldown | **90%** | In-memory + Redis store; per-type TTL from config |
| Multi-provider delivery | **88%** | HTTP mocked; order and failover verified |
| Background monitor | **85%** | Cycle logic tested; full loop timing not load-tested |
| Live external delivery | **60%** | Requires human `alerts/test` in target env |
| Cross-process dedup (Redis) | **80%** | `RedisCooldownStore` logic tested; not testcontainers E2E |

**Overall alerting production confidence: ~84%** (up from ~70% pre-RC3 for “operational delivery validated”).

## What RC3 proved

1. Each audited scenario maps to a **concrete code path** with automated verification where feasible.
2. **Duplicate suppression** works for global and per-entity dedup keys.
3. **Slack, webhook, and logging** participate in routing; logging catches failover.
4. **Deployment validation** still blocks production misconfiguration (exit 14).

## Residual risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| No automated live Slack/webhook | Medium | Post-deploy test alert |
| Worker heartbeat vs monitor timing | Low | Align TTL/interval; start worker before API health passes |
| Queue alert needs 2 cycles (~60s+) | Low | Document in runbook |
| Multiple RUNNING pipelines | Low | `scalar_one_or_none` may error — ops should avoid concurrent runs |
| Email provider stub | Low | Do not list `email` expecting delivery |
| Pipeline failure E2E | Low | Orchestrator branch reviewed; helper + dedup tested |

## Recommendation

- **Accept alerting for V2 RC** from a **code and test** perspective.
- **Gate production go-live** on one successful live `alerts/test` per environment.
- Include RC3 docs in release notes for on-call.

## Test evidence

```bash
cd api && PYTHONPATH=. API_KEY=ci-github-actions-api-key \
  pytest tests/observability/test_alerting*.py -q
# 55 passed (13 RC3-specific in test_alerting_rc3_validation.py)
```

## Document index

| Deliverable | File |
|-------------|------|
| Alert validation report | [rc3-alert-validation-report.md](./rc3-alert-validation-report.md) |
| Operational readiness | [rc3-operational-readiness-assessment.md](./rc3-operational-readiness-assessment.md) |
| Alert matrix | [alert-matrix.md](./alert-matrix.md) |
| Response guide | [rc3-alert-operational-response-guide.md](./rc3-alert-operational-response-guide.md) |
| This report | `rc3-alert-production-confidence.md` |
