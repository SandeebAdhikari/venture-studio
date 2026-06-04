# V2 RC5 — Full pipeline validation report

**Sprint:** Release Candidate #5 — operational reality (live run + verification)  
**Date:** 2026-06-04  
**Environment:** Local stack — API `:8000`, PostgreSQL `:5433`, Redis `:6379`, `ENVIRONMENT=local`  
**Constraint:** Analysis and observation only; no feature development in this sprint.

## Executive summary

A **live synchronous full pipeline** was triggered via `POST /api/v1/pipeline/run`. The orchestrator executed all **14 stages** in sequence but finished **`partial`** after **`generate_opportunities`** failed. Downstream stages were skipped per `stop_on_failure=true`.

| Result | Value |
|--------|-------|
| Run ID | `680aba8b-9c08-4bb5-a599-8bad5f782d4e` |
| Wall time | **3.83 s** (API); `duration_ms=3825` |
| Stages completed | 2 (COLLECT, CLASSIFY) |
| Stages failed | 1 (GENERATE_OPPORTUNITIES) |
| Stages skipped | 11 |
| Retries observed | 3 on GENERATE (attempts 2–4) |
| Queue depth (ARQ) | 0 (sync run; no background enqueue) |
| Approvals from this run | **0** (ranking never ran) |

**Verdict:** Pipeline **orchestration, metrics, tracing hooks, retries, and skip-on-failure** behave correctly. A **production-style end-to-end success** was **not achieved** in this environment due to **empty data plane** (no sources/signals) and a **logging defect** in opportunity generation (see §Failures).

Secondary verification: E2E seed script confirmed **rankings**, **venture reports (draft)**, and **approval requests** when downstream services run outside the failed orchestrator path.

---

## Stage map (canonical order)

Code: `api/app/pipeline/constants.py` — `PIPELINE_STAGE_ORDER` (14 stages).

| # | Product name | Enum | Executor entry |
|---|--------------|------|----------------|
| 1 | COLLECT | `collect` | `services.collection.collect_enabled_sources()` |
| 2 | CLASSIFY | `classify` | `services.classification.classify_pending()` |
| 3 | GENERATE | `generate_opportunities` | `services.generation.generate()` |
| 4 | SCORE | `score_opportunities` | `services.scoring.score_all()` |
| 5 | MARKET_RESEARCH | `market_research` | `market_research.research_pending()` |
| 6 | COMPETITOR_ANALYSIS | `competitor_analysis` | `competitor_intelligence.analyze_pending()` |
| 7 | CUSTOMER_RESEARCH | `customer_research` | `customer_research.research_pending()` |
| 8 | REVENUE_VALIDATION | `revenue_validation` | `validate_pending()` |
| 9 | PRODUCT_STRATEGY | `product_strategy` | `plan_pending()` |
| 10 | GO_TO_MARKET | `go_to_market` | `plan_pending()` |
| 11 | GROWTH_STRATEGY | `growth_strategy` | `evaluate_pending()` |
| 12 | HUMAN_PROXY | `human_proxy` | `evaluate_pending()` |
| 13 | EXECUTIVE_RANKING | `executive_ranking` | `executive_ranking.generate_ranking()` |
| 14 | VENTURE_REPORT | `venture_report` | `venture_reports.generate_venture_report()` |

---

## Live run — execution report

**Trigger:** `POST /api/v1/pipeline/run` with default `PipelineRunRequest` (`stop_on_failure: true`).

### Stage durations (observed)

| Stage | Status | Attempts | duration_ms | Notes |
|-------|--------|----------|-------------|-------|
| collect | completed | 1 | **6** | 0 sources configured |
| classify | completed | 1 | **4** | 0 pending signals |
| generate_opportunities | failed | **4** | **3670** | Retries + backoff; see error |
| score_opportunities | skipped | — | — | `prior_stage_failure` |
| market_research … venture_report | skipped | — | — | Same |

### Retries (audit trail)

| Stage | Retry events |
|-------|----------------|
| generate_opportunities | `stage_retry` at attempts 2, 3, 4 |

Backoff: `pipeline_retry_backoff_sec * 2^(attempt-2)` (default 0.5s → ~0.5s, 1s, 2s between attempts).

### Failures

| Field | Value |
|-------|-------|
| `error_summary` | `"Attempt to overwrite 'created' in LogRecord"` |
| Root cause (code) | `ComplaintClassificationService` / opportunity batch log uses `extra={"created": ...}` — **`created` is reserved** on `logging.LogRecord` (`api/app/agents/opportunity/service.py` ~L101–108) |
| Impact | Stage fails even with zero patterns; blocks entire downstream pipeline |

This is a **defect** blocking operational validation of GENERATE and later stages until fixed (out of RC5 scope per “no feature development”).

### Queue depth

| Check | Result |
|-------|--------|
| Sync `POST /pipeline/run` | Does not enqueue ARQ |
| `GET /api/v1/jobs` after run | Empty |
| Redis `LLEN arq:queue` | 0 |

Background mode (`?background=true` or `POST /jobs/run-pipeline`) would populate the queue; not exercised in this run.

### Alert generation

| Check | Result |
|-------|--------|
| Orchestrator on `partial` | Calls `alert_pipeline_failure` (`orchestrator.py`) |
| `ALERTING_ENABLED` in `.env` | Not set (app defaults apply) |
| `avs_alerts_fired_total` after run | Not observed on `/metrics` scrape |
| Interpretation | Alert path likely not configured for external delivery in local env; failure path in code is wired |

### Approval creation (this run)

| Check | Result |
|-------|--------|
| Approvals after live run | **0** — EXECUTIVE_RANKING / VENTURE_REPORT never executed |

### E2E seed verification (downstream artifacts)

`api/scripts/seed_e2e_fixtures.py` (with `REQUIRE_FOUNDER_APPROVAL=true`):

| Artifact | Verified |
|----------|----------|
| Executive ranking runs | Seeded (`ranking_run_id` in script output) |
| Venture reports | `GET /api/v1/reports` — draft markdown reports present |
| Approval requests | `GET /api/v1/approvals` — **3 pending** (2× ranking, 1× venture_report) |
| Synthetic pipeline run | Completed fixture with COLLECT + VENTURE_REPORT marked done (UI visibility only) |

This confirms **approval creation**, **ranking**, and **report** subsystems work when invoked; it is **not** a substitute for a single orchestrated 14-stage live run.

---

## Verification matrix

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Metrics — pipeline runs | **PASS** | `avs_pipeline_runs_total{status="partial",trigger="api"}`, `avs_pipeline_failures_total` |
| Metrics — stage duration | **PASS** | `avs_pipeline_stage_duration_seconds` for collect, classify, generate_opportunities (failed) |
| Tracing | **PASS** (logging) | `trace_span("pipeline.run")`, `trace_span("pipeline.stage")` in orchestrator; structured span start/end in logs |
| Reports | **PASS** (seed) | Venture recommendation reports in DB/API |
| Rankings | **PASS** (seed) | Ranking runs created by seed |
| Approvals | **PASS** (seed) | Pending approval requests with audit trail |
| Full 14-stage success | **FAIL** | Blocked at GENERATE (logging bug + no input data) |
| OpenAPI / production profile | N/A | Local run |

---

## Bottleneck analysis

### Observed (this run)

| Bottleneck | Detail |
|------------|--------|
| Early exit | 96% of wall time in **generate_opportunities** retries (3.67s of 3.82s) |
| Empty inputs | COLLECT/CLASSIFY trivial without sources/signals |
| Sequential stages | Orchestrator runs stages one-by-one; no parallelism across agents |

### Expected (production with data + OpenAI)

| Stage group | Expected dominance |
|-------------|-------------------|
| COLLECT | Network I/O to Reddit/RSS/HN; scales with source count |
| CLASSIFY | LLM per signal batch; `CLASSIFY_BATCH_SIZE` × pending signals |
| GENERATE → HUMAN_PROXY | LLM-heavy; **largest cumulative time** for typical nightly volume |
| SCORE | CPU/DB; comparatively cheap |
| EXECUTIVE_RANKING + VENTURE_REPORT | LLM + aggregation; second peak |

**Primary production bottleneck:** **LLM throughput and daily budget** (`LLM_DAILY_BUDGET_USD`), not Redis or PostgreSQL for typical loads.

---

## Timeout analysis

| Layer | Setting | Default | Implication |
|-------|---------|---------|-------------|
| ARQ job | `ARQ_JOB_TIMEOUT_SEC` | 3600 | Background pipeline/stage jobs killed after 1h |
| Pipeline lock | `PIPELINE_LOCK_TTL_SEC` | 3600 | Stale lock expires |
| Stage retries | `pipeline_max_retries` | 3 (+1 initial = 4 attempts) | Matches observed 4 attempts |
| Retry backoff | `pipeline_retry_backoff_sec` | 0.5s exponential | Short local retries; not a substitute for LLM timeouts |
| Stall alert | `ALERT_PIPELINE_STALL_SEC` | 3600 | Monitor alerts if run stays RUNNING > 1h |
| Sync HTTP `POST /pipeline/run` | No dedicated HTTP timeout | Client/proxy must allow **hours** for full prod run |
| OpenAI clients | Per-agent HTTP timeouts | Agent-specific | Failures surface as stage retries/failures |

**Risk:** A full production sync run via API may exceed reverse-proxy timeouts (60–120s) while stages 5–14 run. **Recommendation:** use `background=true` or `POST /jobs/run-pipeline` for nightly execution.

---

## Operational recommendations

### Before next production-style validation

1. **Fix LogRecord `created` extra key** in opportunity generation logging (unblocks GENERATE stage).
2. **Configure `OPENAI_API_KEY`** and raise `LLM_DAILY_BUDGET_USD` for full agent chain (production example: ≥10).
3. **Enable at least one collector source** (Reddit/RSS/HN) so COLLECT → CLASSIFY have work.
4. **Set `REQUIRE_FOUNDER_APPROVAL=true`** and confirm approvals after ranking/report stages.
5. **Enable alerting** with external webhook/Slack for `pipeline_failure` on partial/failed runs.
6. **Run via worker:** `POST /api/v1/pipeline/run?background=true` with worker healthy; monitor `GET /jobs` and `/metrics`.

### Runbook command (repeatable)

```bash
API_KEY="<from .env>"
curl -sS -X POST "http://localhost:8000/api/v1/pipeline/run" \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d '{}'
# Poll:
curl -sS -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/api/v1/pipeline/runs/<run_id>"
curl -sS http://localhost:8000/metrics | grep avs_pipeline
```

### Production deployment

| Item | Action |
|------|--------|
| Nightly trigger | Scheduler → `run_pipeline` job on worker, not sync API |
| HTTP timeout | LB timeout ≥ `ARQ_JOB_TIMEOUT_SEC` or use async only |
| Observability | Scrape `/metrics`; alert on `avs_pipeline_failures_total` |
| Founder gate | Review `/approvals` after run; reports stay draft until approve |

---

## Preconditions for “green” 14/14 run

| Prerequisite | Current local |
|--------------|---------------|
| PostgreSQL + Redis | OK |
| API healthy | OK (`/health/ready` ok) |
| Worker (background) | Optional; not required for sync |
| `OPENAI_API_KEY` | **Missing** in `.env` |
| Enabled sources | **0** |
| LogRecord fix | **Required** |
| LLM budget | $2/day local — likely insufficient for full chain |

---

## Related deliverable

- [rc5-production-confidence-score.md](./rc5-production-confidence-score.md)
