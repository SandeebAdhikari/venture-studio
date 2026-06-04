# V2 RC5 — Production confidence score (pipeline operations)

Companion to [rc5-full-pipeline-validation-report.md](./rc5-full-pipeline-validation-report.md).

## Score summary

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Orchestration & stage lifecycle | **90%** | 25% | 22.5 |
| Retries, skip-on-failure, audit trail | **92%** | 15% | 13.8 |
| Metrics & observability hooks | **88%** | 15% | 13.2 |
| Tracing (logging provider) | **85%** | 10% | 8.5 |
| Full 14-stage successful run | **25%** | 25% | 6.25 |
| Rankings / reports / approvals E2E | **80%** | 10% | 8.0 |

**Overall pipeline production confidence: ~72%** (weighted).

Prior RC scores (~82–84) assumed config enforcement; RC5 lowers **operational proof** until a green nightly run is recorded.

---

## What RC5 proved

1. **Live API path works** — run persisted, queryable, audit trail complete.
2. **Failure handling is correct** — partial status, 11 skips, retry events, `avs_pipeline_failures_total` incremented.
3. **Fast stages are sub-second** with empty inputs.
4. **Downstream artifacts** (ranking, draft reports, approvals) verified via controlled seed.

---

## What RC5 did not prove

| Gap | Impact on go-live |
|-----|-------------------|
| No completed 14-stage run | Cannot quote end-to-end SLA |
| No LLM stages exercised in orchestrator | Latency/budget unknown in prod |
| No background worker run | Queue/backpressure not observed |
| No live alert delivery | Ops notification path unverified in this run |
| GENERATE logging defect | **Blocks** any real data pipeline |

---

## Confidence by deployment model

| Model | Pipeline confidence | Notes |
|-------|---------------------|-------|
| **Private founder (sync API)** | **65%** | Use background + worker; fix logging first |
| **Nightly scheduled (worker)** | **75%** after fix + OpenAI + sources | Matches intended V2 ops |
| **High-volume signals** | **60%** until budget/timeout tuning measured | CLASSIFY may dominate |

---

## Path to ≥85% (ops + one defect fix)

| Step | Δ score |
|------|---------|
| Fix LogRecord `created` logging key | +8 |
| One green `background=true` run with sources + OpenAI | +12 |
| Record stage histograms for all 14 stages | +5 |
| Live `pipeline_failure` alert received | +3 |

---

## Recommendation

- **Do not treat V2 as operationally proven for nightly venture publication** until one documented **completed** (or acceptable `partial` with founder sign-off) **14-stage** run in staging.
- **Do treat orchestration and observability as RC-ready** — metrics, partial/failed semantics, and approval/report wiring are sound.
- **Prioritize** the GENERATE logging fix in the next code sprint (minimal; not a redesign).

---

## Audit score impact (informal)

| Area | Before RC5 | After RC5 |
|------|------------|-------------|
| Unit/integration/E2E tests | High | Unchanged |
| Operational reality | Low–medium | **Documented** with evidence |
| Production readiness (pipeline) | ~82 | **~72–78** until green run; honesty improves audit credibility |
