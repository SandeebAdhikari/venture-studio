# AI Venture Studio — Scope and Status

This document describes **what is implemented today**, not the original plan. Use the codebase as the source of truth; this file tracks scope for contributors.

---

## Implemented Capabilities

### V1 — Signal to Opportunity

| Feature | Status | Implementation |
|---------|--------|----------------|
| Source configuration | ✅ | `sources` table + `GET/POST/PATCH/DELETE /api/v1/sources` |
| RSS feed management | ✅ | `rss_feeds` table + `/api/v1/rss-feeds` |
| Reddit collection | ✅ | `app/collectors/reddit/` registered at startup |
| RSS collection | ✅ | `app/collectors/rss/` registered at startup |
| HN Algolia collection | ✅ | `app/collectors/hn_algolia/` registered in `lifespan.py` and worker context |
| Scheduled collection | ✅ | Nightly `nightly_pipeline` @ 02:00 UTC → ARQ `run_pipeline` (includes collect stage) |
| Deduplication | ✅ | `(source_id, external_id)`, URL, content hash |
| Complaint classification | ✅ | LangGraph `classify_complaint` in `app/agents/classification/` |
| Opportunity generation | ✅ | `TopicPatternDetector` + LangGraph in `app/agents/opportunity/` |
| Opportunity scoring | ✅ | Deterministic engine in `app/scoring/` (no LLM) |
| Reporting | ✅ | Top opportunities, venture reports, pipeline summary |
| Review workflow | ✅ | `review_status` on opportunities + `/opportunities/{id}/review` |

**Note:** Opportunity generation uses **in-memory topic pattern detection** (repeated phrases in complaint summaries), not a separate `pain_point_clusters` database table or HDBSCAN/pgvector clustering stage.

### V2 — Research Agents

All eight LLM agents are implemented with LangGraph graphs, services, REST APIs, worker jobs, and tests:

| Agent | Package | API prefix |
|-------|---------|------------|
| Market Research | `app/agents/market_research/` | `/api/v1/market-research` |
| Competitor Intelligence | `app/agents/competitor_intelligence/` | `/api/v1/competitor-intelligence` |
| Customer Research | `app/agents/customer_research/` | `/api/v1/customer-research` |
| Revenue Validation | `app/agents/revenue_validation/` | `/api/v1/revenue-validation` |
| Product Strategy | `app/agents/product_strategy/` | `/api/v1/product-strategy` |
| Go-To-Market | `app/agents/go_to_market/` | `/api/v1/go-to-market` |
| Growth Strategy | `app/agents/growth_strategy/` | `/api/v1/growth-strategy` |
| Human Proxy | `app/agents/human_proxy/` | `/api/v1/human-proxy` |

**Executive Ranking** uses a deterministic engine (`app/ranking/engine.py`), not an LLM graph. It combines agent outputs into composite scores.

### Operations

| Feature | Status | Implementation |
|---------|--------|----------------|
| Pipeline orchestrator | ✅ | 14 stages, `PipelineOrchestrator` |
| ARQ workers | ✅ | 15 registered jobs (14 stages + `run_pipeline`) |
| APScheduler | ✅ | Single `nightly_pipeline` cron @ 02:00 UTC (see [scheduler.md](./scheduler.md)) |
| Observability | ✅ | Prometheus `/metrics`, tracing middleware, expanded readiness |
| Alerting | ✅ | Logging, webhook, Slack backends (`app/observability/alerting/`) |
| Deployment bootstrap | ✅ | Auto-migrations + startup validation (`app/deployment/bootstrap.py`) |
| Dashboard APIs | ✅ | `/api/v1/dashboard/*` |
| Founder dashboard UI | ✅ | Next.js app in `web/` (7 pages) |
| Approval workflow | ✅ | Rankings + venture reports |
| LLM budget | ✅ | Daily cap + warnings + `/api/v1/budget` |
| CI/CD | ✅ | GitHub Actions: quality, test, deployment-check, web-quality, web-deployment-check |

---

## Out of Scope (Not Implemented)

| Feature | Notes |
|---------|-------|
| `pain_point_clusters` table | Replaced by pattern detection at generation time |
| Dedicated `/signals` REST API | Signals accessed via complaints and collection internals |
| Multi-user auth / RBAC | Single shared `X-API-Key`; dashboard BFF has no user auth |
| Additional collectors | Twitter/X and other sources beyond Reddit, RSS, HN Algolia |
| Web service in default docker-compose | API + worker only; web runs separately or via optional compose profile |
| Full-stack E2E tests | Backend pytest + frontend Vitest; no BFF ↔ API integration smoke |
| Sentry / Datadog integrations | Prometheus metrics + structured logs + configurable alerting backends |

---

## Recommended Source Configuration

Start narrow. Expand after pipeline stability.

| Source | Type | Status | Notes |
|--------|------|--------|-------|
| Reddit subreddits | `reddit` | ✅ | Public JSON API; rate-limited via Redis |
| RSS feeds | `rss` | ✅ | Managed via `/api/v1/rss-feeds` |
| HN Algolia | `hn_algolia` | ✅ | Algolia search API; see [collection-hn-algolia.md](./collection-hn-algolia.md) |

Example Reddit source config (JSONB on `sources.config`):

```json
{
  "subreddit": "SaaS",
  "sort": "new",
  "limit": 50,
  "include_comments": true,
  "keyword_filter": ["frustrated", "wish", "workaround"]
}
```

---

## LLM Usage Budget

Configured via `LLM_DAILY_BUDGET_USD` (default `2.00`). Enforced by `LLMBudgetService.try_prepare_call()` before every agent LLM invocation. Warnings at 50%, 75%, and 90% of daily cap.

| Stage | Model (default) | Budget enforced |
|-------|-----------------|-----------------|
| Classification | `gpt-4o-mini` | ✅ |
| Opportunity generation | `gpt-4o-mini` | ✅ |
| All 8 research agents | `gpt-4o-mini` | ✅ |
| Scoring | N/A (deterministic) | — |
| Executive ranking | N/A (deterministic) | — |

See [operations.md](./operations.md) for budget API and monitoring.

---

## Default Scheduler (UTC)

| Time | Scheduler job | ARQ job |
|------|---------------|---------|
| 02:00 | `nightly_pipeline` | `run_pipeline` (full 14-stage orchestrator) |

Manual per-stage execution remains available via `POST /api/v1/jobs/{stage}` for debugging. See [scheduler-orchestrator.md](./scheduler-orchestrator.md).

---

## Classification Taxonomy

Stored in the unified `categories` table with `kind` enum:

- `complaint_category` — pricing, integration, ux_ui, performance, etc.
- `domain` — saas_b2b, devtools, fintech, etc.
- `persona` — founder, developer, product_manager, etc.

Seeded in migration `002_core_persistence.py`.

---

## Opportunity Brief Fields

Each generated opportunity populates:

| Field | Source |
|-------|--------|
| `title` | LLM synthesis |
| `problem_statement` | LLM synthesis |
| `target_user` | LLM synthesis |
| `frequency_signal` | Pattern metadata (complaint count, date range) |
| `existing_alternatives` | Evidence-only from complaints |
| `gap` | LLM synthesis |
| `confidence_score` | LLM self-assessment 0.0–1.0 |
| Evidence | `opportunity_complaints` junction table |

---

## Non-Functional Targets

| Requirement | Target |
|-------------|--------|
| Local dev startup | < 2 min via Docker Compose (postgres + redis + api + worker) |
| Test suite | 250+ pytest functions (backend) + Vitest (frontend) |
| Migrations | 19 Alembic revisions, single linear chain |
| Data retention | Signals and audit tables persisted in PostgreSQL |

---

## Definition of Done (Current Release)

- [x] Reddit + RSS + HN Algolia collectors with deduplication
- [x] Classification pipeline with LangGraph + LLM audit
- [x] Opportunity generation from complaint patterns
- [x] Deterministic scoring engine with history
- [x] Eight research agents + executive ranking
- [x] Pipeline orchestrator (14 stages)
- [x] ARQ workers + orchestrated APScheduler
- [x] Production observability (metrics, tracing, readiness)
- [x] Production alerting (logging/webhook/Slack)
- [x] Deployment bootstrap with auto-migrations
- [x] Founder dashboard (Next.js)
- [x] Approval workflow + LLM budget
- [x] GitHub Actions CI (backend + frontend)
- [ ] Full-stack E2E tests
- [ ] Multi-user dashboard authentication
