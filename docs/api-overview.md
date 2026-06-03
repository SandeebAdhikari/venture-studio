# API Overview

REST API reference for AI Venture Studio. All endpoints under `/api/v1` require the `X-API-Key` header unless noted.

Interactive docs: `GET /docs` (local/staging only — disabled when `ENVIRONMENT=production`).

List endpoints support `limit` (1–100) and `offset` pagination unless otherwise noted.

---

## Authentication

```
X-API-Key: <API_KEY>
```

Single shared key configured via `API_KEY` environment variable (minimum 16 characters).

---

## Health (Public)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness — `{ "status": "ok" }` |
| GET | `/health/ready` | Readiness — PostgreSQL + Redis connectivity |

---

## Sources and Collection

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/sources` | List sources (filter: `enabled`, `source_type`) |
| GET | `/api/v1/sources/{id}` | Get source |
| POST | `/api/v1/sources` | Create source |
| PATCH | `/api/v1/sources/{id}` | Update source |
| DELETE | `/api/v1/sources/{id}` | Delete source (local/staging guard) |

**Source types with collectors:** `reddit`, `rss`  
**Enum only (no collector):** `hn_algolia`

### RSS Feeds

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/rss-feeds` | List RSS feeds |
| POST | `/api/v1/rss-feeds` | Create RSS feed (auto-creates source) |
| DELETE | `/api/v1/rss-feeds/{feed_id}` | Delete feed |

---

## Taxonomy and Complaints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/categories` | List categories (filter: `kind`, `code`) |
| GET | `/api/v1/categories/{id}` | Get category |
| POST | `/api/v1/categories` | Create category |
| PATCH | `/api/v1/categories/{id}` | Update category |
| GET | `/api/v1/complaints` | List complaints (filter: category, domain, persona, severity) |
| GET | `/api/v1/complaints/{id}` | Get complaint |
| POST | `/api/v1/complaints` | Create complaint |
| PATCH | `/api/v1/complaints/{id}` | Update complaint |
| DELETE | `/api/v1/complaints/{id}` | Delete complaint |

---

## Opportunities

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/opportunities` | List (filter: `review_status`, `min_confidence`) |
| GET | `/api/v1/opportunities/{id}` | Detail with evidence complaint IDs |
| POST | `/api/v1/opportunities` | Create opportunity |
| PATCH | `/api/v1/opportunities/{id}` | Update opportunity |
| POST | `/api/v1/opportunities/{id}/review` | Set review status |
| POST | `/api/v1/opportunities/{id}/link-complaints` | Link evidence complaints |
| POST | `/api/v1/opportunities/{id}/score` | Score single opportunity |

---

## Reports

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/reports` | List reports (filter: `opportunity_id`, `report_type`, `status`) |
| GET | `/api/v1/reports/{id}` | Get report |
| POST | `/api/v1/reports` | Create report |
| PATCH | `/api/v1/reports/{id}` | Update report |
| DELETE | `/api/v1/reports/{id}` | Delete report |
| POST | `/api/v1/reports/{id}/publish` | Publish report |
| POST | `/api/v1/reports/top-opportunities/generate` | Generate Top Opportunities markdown report |
| GET | `/api/v1/reports/{id}/markdown` | Get report markdown body |

### Executive Venture Reports

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/executive-reports/generate` | Generate venture recommendation report |
| GET | `/api/v1/executive-reports/latest` | Latest venture report |
| GET | `/api/v1/executive-reports/{id}` | Get venture report |
| GET | `/api/v1/executive-reports/{id}/markdown` | Venture report markdown |
| GET | `/api/v1/executive-reports/{id}/download` | Download as `.md` file |

---

## Research Agents

Each agent exposes a consistent REST pattern:

| Method | Path pattern | Description |
|--------|--------------|-------------|
| GET | `/{prefix}` | List evaluations/briefs |
| POST | `/{prefix}/generate` | Batch generate |
| GET | `/{prefix}/opportunities/{opportunity_id}/current` | Current evaluation |
| GET | `/{prefix}/opportunities/{opportunity_id}/history` | History |
| POST | `/{prefix}/opportunities/{opportunity_id}/generate` | Single opportunity |
| GET | `/{prefix}/{id}` | Get by ID |

### Prefixes

| Agent | Prefix |
|-------|--------|
| Market Research | `/api/v1/market-research` |
| Competitor Intelligence | `/api/v1/competitor-intelligence` |
| Customer Research | `/api/v1/customer-research` |
| Revenue Validation | `/api/v1/revenue-validation` |
| Product Strategy | `/api/v1/product-strategy` |
| Go-To-Market | `/api/v1/go-to-market` |
| Growth Strategy | `/api/v1/growth-strategy` |
| Human Proxy | `/api/v1/human-proxy` |

### Human Proxy — Founder Profiles

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/human-proxy/founder-profiles` | List profiles |
| POST | `/api/v1/human-proxy/founder-profiles` | Create profile |
| GET | `/api/v1/human-proxy/founder-profiles/{id}` | Get profile |

---

## Executive Ranking

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/executive-ranking/generate` | Generate ranking |
| GET | `/api/v1/executive-ranking/current` | Current ranking |
| GET | `/api/v1/executive-ranking/history` | Ranking history |
| GET | `/api/v1/executive-ranking/{run_id}` | Get ranking run detail |

---

## Pipeline and Jobs

### Pipeline Orchestrator

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/pipeline/run` | Run full 14-stage pipeline (201 sync, 202 with `?background=true`) |
| GET | `/api/v1/pipeline/runs` | List pipeline runs |
| GET | `/api/v1/pipeline/runs/{run_id}` | Run detail with stage runs |

### Background Jobs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/jobs` | List recent jobs |
| GET | `/api/v1/jobs/{job_id}` | Job status |
| POST | `/api/v1/jobs/run-pipeline` | Enqueue full pipeline (202) |
| POST | `/api/v1/jobs/{job_name}` | Enqueue stage job (202) |

**Valid job names:** `collect`, `classify`, `generate_opportunities`, `score`, `market_research`, `competitor_analysis`, `customer_research`, `revenue_validation`, `product_strategy`, `go_to_market`, `growth_strategy`, `human_proxy`, `executive_ranking`, `venture_report`

---

## Scheduler

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/scheduler/jobs` | List cron jobs with last run and failure count |
| PATCH | `/api/v1/scheduler/jobs/{job_name}` | Enable/disable job |
| POST | `/api/v1/scheduler/run/{job_name}` | Manual trigger (202) |

**Scheduler job names:** `collect`, `classify`, `generate_opportunities`, `research_agents`, `executive_ranking`, `venture_report`

---

## Dashboard

Optimized endpoints for the Next.js founder dashboard:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/dashboard/summary` | Overview: ingestion, pipeline, ranking, agents, jobs |
| GET | `/api/v1/dashboard/opportunities` | Top ranked opportunities (`top_n` query param) |
| GET | `/api/v1/dashboard/pipeline` | Pipeline runs with optional stage detail |
| GET | `/api/v1/dashboard/reports` | Report lists by type |

---

## Approvals

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/approvals` | List approval requests (filter: `status`, `subject_type`) |
| POST | `/api/v1/approvals/{id}/approve` | Approve ranking or venture report |
| POST | `/api/v1/approvals/{id}/reject` | Reject |
| POST | `/api/v1/approvals/{id}/research` | Request additional research (comment required) |

---

## Budget

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/budget` | Current daily spend, warnings, per-agent breakdown |
| GET | `/api/v1/budget/history` | Daily rollup (`days` query param, 1–90) |

---

## Triggering Pipeline Stages

There is no dedicated `/classify` or `/collect` REST route. Use:

```bash
# Single stage
curl -X POST http://localhost:8000/api/v1/jobs/classify -H "X-API-Key: $API_KEY"

# Full pipeline
curl -X POST http://localhost:8000/api/v1/pipeline/run -H "X-API-Key: $API_KEY"
```

Or use scheduler manual triggers: `POST /api/v1/scheduler/run/{job_name}`

---

## Related Documentation

- [architecture.md](./architecture.md) — system design
- [pipeline.md](./pipeline.md) — stage definitions
- [agents.md](./agents.md) — agent details
- [api/README.md](../api/README.md) — backend development guide
