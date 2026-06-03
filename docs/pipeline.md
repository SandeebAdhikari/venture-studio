# AI Venture Studio — Pipeline Stages

## Overview

The Venture Studio pipeline is a **14-stage sequential workflow** defined in `app/pipeline/constants.py`:

```
COLLECT → CLASSIFY → GENERATE_OPPORTUNITIES → SCORE_OPPORTUNITIES
  → MARKET_RESEARCH → COMPETITOR_ANALYSIS → CUSTOMER_RESEARCH
  → REVENUE_VALIDATION → PRODUCT_STRATEGY → GO_TO_MARKET
  → GROWTH_STRATEGY → HUMAN_PROXY → EXECUTIVE_RANKING → VENTURE_REPORT
```

Each full execution creates one `pipeline_runs` record and up to 14 `pipeline_stage_runs` children. Stages can also run **independently** via `POST /api/v1/jobs/{job_name}`.

**Orchestration:** `PipelineOrchestrator` (sync or background) or discrete scheduler cron slots → ARQ workers → `PipelineStageExecutor` → service layer.

See [pipeline-orchestration.md](./pipeline-orchestration.md) for orchestrator, worker, and scheduler details.

---

## Triggers

| Trigger | Mechanism |
|---------|-----------|
| Full pipeline (sync) | `POST /api/v1/pipeline/run` → 201 |
| Full pipeline (background) | `POST /api/v1/pipeline/run?background=true` → 202 |
| Full pipeline (job) | `POST /api/v1/jobs/run-pipeline` → 202 |
| Single stage | `POST /api/v1/jobs/{job_name}` → 202 |
| Scheduled | APScheduler daily cron → ARQ (see [scheduler.md](./scheduler.md)) |

**Concurrency:** Only one full pipeline run at a time. Redis lock `lock:pipeline:run` + DB running-state check.

---

## Stage 1: COLLECT

### Purpose
Fetch new content from enabled sources and insert deduplicated `signals` with `processing_status = pending`.

### Implementation
- Service: `ComplaintCollectionService` (`app/collection/service.py`)
- Collectors: Reddit (`app/collectors/reddit/`), RSS (`app/collectors/rss/`)
- Registry: `app/collection/collectors/registry.py`

### Collectors

#### Reddit
- Public JSON API (`https://www.reddit.com/r/{subreddit}/{sort}.json`)
- Config: subreddit(s), sort, limit, keyword filter, include comments
- Rate limit: Redis key `ratelimit:reddit:{scope}`
- Dedup: `(source_id, external_id)`, URL, content hash

#### RSS
- Feedparser-based fetch via `RssFeedCollector`
- Managed feeds in `rss_feeds` table
- Rate limit: Redis key `ratelimit:rss:{scope}`

#### Not implemented
- **HN Algolia** — `SourceType.HN_ALGOLIA` exists in enums but no collector is registered in `lifespan.py`

### Output
- New `signals` rows
- Updated `sources.last_collected_at`
- Stage metrics: sources processed, inserted, duplicates, failures

---

## Stage 2: CLASSIFY

### Purpose
Transform pending signals into structured `complaints` or mark signals as `skipped` / `failed`.

### Implementation
- Service: `ComplaintClassificationService` (`app/agents/classification/service.py`)
- Graph: LangGraph `classify_complaint` (`app/agents/classification/graph.py`)
- Model: `CLASSIFICATION_MODEL` (default `gpt-4o-mini`)
- Budget: `LLMBudgetService.try_prepare_call()` before LLM invocation

### Processing flow
1. Fetch pending signals (batch size: `CLASSIFY_BATCH_SIZE`, default 50)
2. Set `processing_status = processing`
3. Invoke LangGraph: extract → validate → persist
4. If not a complaint: mark signal `skipped` with reason
5. Else: insert complaint linked to category/domain/persona FKs
6. Log LLM call to `llm_calls`

### LangGraph nodes
| Node | Responsibility |
|------|----------------|
| extract | LLM structured output: is_complaint, summary, quote, taxonomy, severity |
| validate | Pydantic + verbatim quote substring check |
| persist | Write complaint + update signal status |

---

## Stage 3: GENERATE_OPPORTUNITIES

### Purpose
Detect recurring complaint patterns and synthesize opportunity briefs with evidence links.

### Implementation
- Service: `OpportunityGeneratorService` (`app/agents/opportunity/service.py`)
- Pattern detection: `TopicPatternDetector` (in-memory phrase clustering, **not** pgvector HDBSCAN)
- Graph: LangGraph `generate_opportunity`
- Gates: `MIN_CLUSTER_SIZE` (default 3), `MIN_AVG_SEVERITY` (default 2.0), `MIN_OPPORTUNITY_CONFIDENCE` (default 0.4)

### Output
- `opportunities` rows with `review_status = new`
- `opportunity_complaints` junction rows
- Initial score may be computed inline during generation

**There is no separate CLUSTER pipeline stage.** Pattern grouping happens inside this stage.

---

## Stage 4: SCORE_OPPORTUNITIES

### Purpose
Compute deterministic 0–100 scores for opportunities from complaint evidence.

### Implementation
- Service: `OpportunityScoringService` (`app/scoring/service.py`)
- Engine: `OpportunityScoringEngine` — **no LLM**
- Dimensions: volume, severity, market_indicators, implementation_ease, founder_fit
- Persists to `opportunity_scores` with `is_current` flag and full history

### Scheduler note
The `score` stage is **not** in the default APScheduler cron. Trigger manually via `POST /api/v1/jobs/score` or run the full pipeline orchestrator.

---

## Stages 5–12: Research Agents

Each agent follows the same pattern: service → LangGraph → LLM client → validator → evidence persistence.

| Stage | Service | Output table |
|-------|---------|--------------|
| MARKET_RESEARCH | `MarketResearchService` | `market_briefs` |
| COMPETITOR_ANALYSIS | `CompetitorIntelligenceService` | `competitor_analyses` |
| CUSTOMER_RESEARCH | `CustomerResearchService` | `customer_research` |
| REVENUE_VALIDATION | `RevenueValidationService` | `revenue_validations` |
| PRODUCT_STRATEGY | `ProductStrategyService` | `product_strategies` |
| GO_TO_MARKET | `GoToMarketService` | `gtm_plans` |
| GROWTH_STRATEGY | `GrowthStrategyService` | `growth_evaluations` |
| HUMAN_PROXY | `HumanProxyService` | `human_proxy_evaluations` |

All agents enforce LLM budget before calls. Batch processing respects per-agent `*_batch_size` settings.

See [agents.md](./agents.md) for graph details and API endpoints.

---

## Stage 13: EXECUTIVE_RANKING

### Purpose
Rank all opportunities using composite scores from prior agent outputs.

### Implementation
- Service: `ExecutiveRankingService` (`app/ranking/service.py`)
- Engine: `ExecutiveRankingEngine` — **deterministic, no LLM**
- Components: pain, market, revenue, competition, growth, founder_fit
- Output: `executive_ranking_runs` + `executive_ranking_entries`
- Creates `approval_requests` when `REQUIRE_FOUNDER_APPROVAL=true`

---

## Stage 14: VENTURE_REPORT

### Purpose
Generate executive venture recommendation markdown report from top-ranked opportunities.

### Implementation
- Service: `VentureReportService` (`app/reports/venture/service.py`)
- Output: `reports` row with `report_type = venture_recommendation`
- Creates approval request for founder review when approval enabled
- Published only after approval (status transitions via approval workflow)

---

## End-to-End Run Sequence

```
1. Acquire lock:pipeline:run
2. INSERT pipeline_runs (status=running)
3. For each stage in PIPELINE_STAGE_ORDER:
   a. INSERT pipeline_stage_runs (status=running)
   b. Execute via PipelineStageExecutor (with retries)
   c. UPDATE stage metrics (items_in/out/failed)
4. UPDATE pipeline_runs (status=completed|partial|failed)
5. Release lock
```

Stage retries: `PIPELINE_MAX_RETRIES` (default 3) with backoff.

---

## Configuration Reference

| Env Var | Default | Description |
|---------|---------|-------------|
| `CLASSIFY_BATCH_SIZE` | 50 | Signals per classify batch |
| `PIPELINE_CLASSIFY_MAX_BATCHES` | 100 | Max classify loops per run |
| `MIN_CLUSTER_SIZE` | 3 | Min complaints per pattern |
| `CLUSTER_WINDOW_DAYS` | 30 | Complaint lookback window |
| `MIN_AVG_SEVERITY` | 2.0 | Generation gate |
| `MIN_OPPORTUNITY_CONFIDENCE` | 0.4 | Generation gate |
| `GENERATION_BATCH_SIZE` | 500 | Max complaints scanned |
| `PIPELINE_SCORE_LIMIT` | 1000 | Max opportunities scored per run |
| `LLM_DAILY_BUDGET_USD` | 2.00 | Daily LLM spend cap |
| `PIPELINE_LOCK_TTL_SEC` | 3600 | Redis lock TTL |
| `PIPELINE_MAX_RETRIES` | 3 | Per-stage retry count |
| `REQUIRE_FOUNDER_APPROVAL` | true | Gate rankings and venture reports |

---

## Observability

### Structured logs
JSON logging via `app/logging.py`. Pipeline and job events include `pipeline_run_id`, `stage`, counts, duration.

### Health probes
- `GET /health` — liveness
- `GET /health/ready` — PostgreSQL + Redis connectivity

### Dashboard
- `GET /api/v1/dashboard/pipeline` — run history with stage details
- `GET /api/v1/pipeline/runs` — paginated run list

No Prometheus metrics or external APM integration is implemented.

---

## Related Documentation

- [pipeline-orchestration.md](./pipeline-orchestration.md) — orchestrator, workers, scheduler
- [workers.md](./workers.md) — ARQ job reference
- [scheduler.md](./scheduler.md) — daily cron schedule
- [agents.md](./agents.md) — LangGraph agent details
