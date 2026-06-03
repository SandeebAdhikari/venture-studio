# AI Venture Studio — System Architecture

## Overview

AI Venture Studio is a **monorepo** with a FastAPI backend, ARQ workers, APScheduler, and a Next.js founder dashboard. PostgreSQL stores all persistent state; Redis handles job queues, locks, and rate limiting; OpenAI powers LangGraph agents.

```
┌─────────────────────────────────────────────────────────────────┐
│                        SOLO FOUNDER                             │
│              Browser — Founder Dashboard (web/)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS → /api/v1/* (BFF proxy)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Next.js 15 (web/)                                              │
│  BFF: app/api/v1/[...path]/route.ts injects X-API-Key           │
│  Pages: dashboard, opportunities, pipeline, reports,            │
│         approvals, budget, agents                               │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST /api/v1/*
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI (api/)                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ REST routers │  │ APScheduler  │  │ PipelineOrchestrator   │ │
│  │ (25 modules) │  │ (lifespan)   │  │ + PipelineStageExecutor│ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘ │
│         │                 │ enqueue               │             │
│         ▼                 ▼                       ▼             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Services     │  │ ARQ enqueue  │  │ LangGraph agents (10)  │ │
│  │ + repos      │  │              │  │ + ranking/scoring eng. │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
│  ┌──────────────┐                                               │
│  │ Collectors   │  Reddit, RSS (registry pattern)                │
│  └──────────────┘                                               │
└───────┬─────────────────────┬───────────────────────────────────┘
        │                     │
        ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────────┐
│  PostgreSQL   │     │  Redis        │     │  OpenAI API       │
│  + pgvector   │     │  ARQ + locks  │     │  (LLM + embed)    │
└───────────────┘     └───────────────┘     └───────────────────┘
        ▲
        │ async SQLAlchemy
┌───────┴───────┐
│  ARQ Worker   │  arq app.workers.worker.WorkerSettings
│  (separate    │  15 job functions
│   process)    │
└───────────────┘
```

---

## Repository Layout

```
agent/
├── docker-compose.yml       # postgres, redis, api, worker
├── .env.example
├── README.md                # Project overview (this repo)
├── docs/                    # Documentation set
├── web/                     # Next.js 15 founder dashboard
│   ├── src/app/
│   │   ├── (founder)/       # 7 dashboard pages
│   │   └── api/v1/[...path]/  # BFF proxy
│   ├── src/components/
│   ├── src/hooks/
│   ├── src/lib/api/
│   └── src/types/api.ts
└── api/                     # FastAPI + workers
    ├── app/
    │   ├── main.py
    │   ├── config.py
    │   ├── core/lifespan.py       # Scheduler + collector registration
    │   ├── db/models/             # SQLAlchemy 2.0 ORM (36 models)
    │   ├── api/v1/                # 25 router modules
    │   ├── agents/                # LangGraph agents (classification, opportunity, 8 research)
    │   ├── collectors/            # reddit/, rss/
    │   ├── collection/            # ComplaintCollectionService
    │   ├── pipeline/              # orchestrator, executor, constants
    │   ├── ranking/               # ExecutiveRankingEngine (deterministic)
    │   ├── scoring/               # OpportunityScoringEngine (deterministic)
    │   ├── reports/               # Executive + venture report generators
    │   ├── services/              # Service layer + container
    │   ├── repositories/          # Data access layer
    │   ├── workers/               # ARQ jobs, enqueue, monitoring
    │   └── scheduler/             # APScheduler definitions
    ├── alembic/versions/          # 19 migrations
    ├── tests/                     # 230 pytest functions
    ├── pyproject.toml
    └── Dockerfile
```

---

## Service Boundaries

### Next.js (`web/`)

**Responsibilities:**
- Render founder dashboard UI
- Proxy all API calls through BFF (`/api/v1/[...path]`)
- Poll backend via SWR (10–30s intervals)
- No direct database or LLM access

**Auth:** Single shared `API_KEY` injected server-side by BFF. No user accounts or OAuth.

**Pages:**

| Route | Purpose |
|-------|---------|
| `/dashboard` | Overview metrics, top opportunities |
| `/opportunities` | Ranked opportunity inventory |
| `/pipeline` | Pipeline run history and stage timeline |
| `/reports` | Venture and executive reports |
| `/approvals` | Founder approve/reject/research actions |
| `/budget` | Daily LLM spend and warnings |
| `/agents` | Agent activity summary |

See [dashboard.md](./dashboard.md).

### FastAPI (`api/`)

**Responsibilities:**
- REST API (25 router modules under `/api/v1`)
- Pipeline orchestration (sync + enqueue)
- APScheduler lifecycle (when `SCHEDULER_ENABLED=true`)
- Service layer business logic
- LangGraph agent invocation
- Collector execution

**Process model:**

| Process | Command | Role |
|---------|---------|------|
| API | `uvicorn app.main:app` | HTTP + scheduler |
| Worker | `arq app.workers.worker.WorkerSettings` | Background jobs |

Both share codebase and environment. Long-running pipeline work runs in the worker, not in request handlers (except sync `POST /pipeline/run`).

---

## API Surface Summary

Base path: `/api/v1`  
Auth: `X-API-Key: {API_KEY}` on all protected routes  
Public: `GET /health`, `GET /health/ready`

Full reference: [api-overview.md](./api-overview.md)

| Area | Router module | Prefix |
|------|---------------|--------|
| Health | `health.py` | `/health` |
| Sources | `sources.py` | `/sources` |
| RSS feeds | `rss_feeds.py` | `/rss-feeds` |
| Categories | `categories.py` | `/categories` |
| Complaints | `complaints.py` | `/complaints` |
| Opportunities | `opportunities.py` | `/opportunities` |
| Reports | `reports.py` | `/reports` |
| Market research | `market_research.py` | `/market-research` |
| Competitor intelligence | `competitor_intelligence.py` | `/competitor-intelligence` |
| Customer research | `customer_research.py` | `/customer-research` |
| Revenue validation | `revenue_validation.py` | `/revenue-validation` |
| Product strategy | `product_strategy.py` | `/product-strategy` |
| Go-to-market | `go_to_market.py` | `/go-to-market` |
| Growth strategy | `growth_strategy.py` | `/growth-strategy` |
| Human proxy | `human_proxy.py` | `/human-proxy` |
| Executive ranking | `executive_ranking.py` | `/executive-ranking` |
| Executive reports | `executive_reports.py` | `/executive-reports` |
| Pipeline | `pipeline.py` | `/pipeline` |
| Jobs | `jobs.py` | `/jobs` |
| Scheduler | `scheduler.py` | `/scheduler` |
| Dashboard | `dashboard.py` | `/dashboard` |
| Approvals | `approvals.py` | `/approvals` |
| Budget | `budget.py` | `/budget` |

OpenAPI UI: `GET /docs` (local/staging only — disabled in production).

---

## LangGraph Integration

| Decision | Choice |
|----------|--------|
| Graph location | `app/agents/{agent}/graph.py` |
| Invocation | Sync within service/ARQ task |
| Structured output | OpenAI JSON mode + Pydantic validation |
| Budget guard | `LLMBudgetService.try_prepare_call()` in every graph |
| LLM audit | `llm_calls` table via `eval_logging` helper |

**LLM graphs (10):** classification, opportunity generation, market_research, competitor_intelligence, customer_research, revenue_validation, product_strategy, go_to_market, growth_strategy, human_proxy

**Deterministic engines (2):** opportunity scoring (`app/scoring/`), executive ranking (`app/ranking/`)

See [agents.md](./agents.md).

---

## Background Job Architecture

ARQ workers process 15 registered jobs. See [workers.md](./workers.md).

Pipeline orchestrator can run synchronously in API/worker or enqueue via `background=true`.

Scheduler enqueues discrete stage jobs on daily cron — **not** a single chained `run_pipeline`. See [scheduler.md](./scheduler.md).

---

## Collector Architecture

```python
# app/collection/collectors/registry.py
def register_collector(source_type: str, collector: SourceCollector) -> None: ...
def get_collector(source_type: str) -> SourceCollector | None: ...
```

Registered at startup in `app/core/lifespan.py` and worker startup in `app/workers/context.py`:

- `reddit` → `RedditCollectorService`
- `rss` → `RssCollectorService`

Collectors are pure HTTP/parsing — no LLM.

---

## Data Flow

### Dashboard read
```
Browser → Next.js BFF → FastAPI GET → PostgreSQL → JSON → SWR cache
```

### Pipeline write (background)
```
Trigger → POST /pipeline/run?background=true → ARQ enqueue run_pipeline
  → Worker: PipelineOrchestrator.run_pipeline()
    → 14 stages via PipelineStageExecutor
  → PostgreSQL updated
  → Dashboard polls /dashboard/pipeline
```

### Scheduled automation
```
APScheduler cron → scheduler/jobs.py → enqueue_stage() → ARQ → Worker → stage execution
```

---

## Configuration

`api/app/config.py` — Pydantic `BaseSettings` from `.env`:

Key variables: `DATABASE_URL` (computed), `REDIS_URL`, `OPENAI_API_KEY`, `API_KEY`, `LLM_DAILY_BUDGET_USD`, `SCHEDULER_ENABLED`, `REQUIRE_FOUNDER_APPROVAL`, agent model settings, ARQ settings.

Next.js env (`web/.env.local`):

```
API_URL=http://localhost:8000
API_KEY=...          # Server-side only
```

---

## Docker Compose (Local Dev)

```yaml
services:
  postgres:   # pgvector/pgvector:pg16
  redis:      # redis:7-alpine
  api:        # FastAPI on :8000
  worker:     # ARQ worker
```

Web runs separately: `cd web && npm run dev` on port 3000.

See [deployment.md](./deployment.md).

---

## Security

| Concern | Mitigation |
|---------|------------|
| API key | Server-side BFF injection; never `NEXT_PUBLIC_` |
| OpenAI key | API/worker env only |
| SQL injection | SQLAlchemy parameterized queries |
| SSRF (RSS) | HTTP/HTTPS only; collector validation |
| Rate limits | Redis-backed per collector |
| Production docs | `/docs` disabled when `ENVIRONMENT=production` |
| CORS | Configured in `main.py` |

No multi-user RBAC. Single shared API key for solo-founder deployment.

---

## Testing

| Layer | Location | Count |
|-------|----------|-------|
| API integration | `api/tests/test_api.py` | |
| Pipeline | `api/tests/pipeline/` | |
| Workers | `api/tests/workers/` | |
| Agents | `api/tests/{agent}/` | |
| Collectors | `api/tests/collectors/` | |
| Dashboard, approval, budget, scheduler | respective dirs | |
| **Total** | `api/tests/` | **230 tests** |

No automated tests under `web/`. CI runs backend tests only.

---

## Extension Points

| Hook | Location | Use |
|------|----------|-----|
| Collector registry | `collection/collectors/registry.py` | Add HN or new sources |
| Pipeline stages | `db/enums.py` PipelineStage | New stages |
| ARQ jobs | `workers/jobs.py` STAGE_JOB_MAP | Register stage workers |
| LangGraph agents | `app/agents/` | New research agents |
| Scheduler jobs | `scheduler/definitions.py` | New cron slots |

---

## Related Documentation

- [pipeline.md](./pipeline.md) — stage definitions
- [pipeline-orchestration.md](./pipeline-orchestration.md) — orchestrator details
- [database.md](./database.md) — schema
- [deployment.md](./deployment.md) — production deployment
- [ci.md](./ci.md) — GitHub Actions
