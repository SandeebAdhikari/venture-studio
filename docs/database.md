# AI Venture Studio — Database Design

## Overview

PostgreSQL 16 is the **system of record**. All entities, pipeline state, agent outputs, LLM audit trails, scheduler history, and approval decisions live here. Redis is ephemeral (queues, locks, job status).

**Extensions** (migration `001_enable_extensions.py`):

- `pgvector` — complaint embeddings (1536 dimensions)
- `uuid-ossp` / `gen_random_uuid()` for primary keys

**Naming conventions:**

- Tables: plural snake_case
- Primary keys: `id UUID DEFAULT gen_random_uuid()`
- Timestamps: `created_at`, `updated_at` (trigger-maintained on core tables)

**Migrations:** 19 revisions in `api/alembic/versions/` (001–019), single linear chain.

---

## Entity Relationship Diagram

```
sources ─────────────┐
                     │ 1:N
                     ▼
                  signals ─────────────┐
                     │ 1:0..1         │
                     ▼                │
                 complaints ──────────┤
                     │                │
                     │ M:N            │
                     ▼                │
               opportunities ◄───────┘
                     │
        ┌────────────┼────────────┬──────────────┐
        ▼            ▼            ▼              ▼
 opportunity_scores  market_briefs  competitor_analyses  … (agent tables)
        │            │            │
        └────────────┴────────────┴──► executive_ranking_runs
                                          │
                                          ▼
                                    executive_ranking_entries
                                          │
                                          ▼
                                       reports
                                          │
                                          ▼
                                  approval_requests
                                          │
                                          ▼
                                  approval_decisions

pipeline_runs ──► pipeline_stage_runs
scheduler_jobs ──► scheduler_runs
llm_calls (audit)
llm_budget_alerts
rss_feeds ──► sources
founder_profiles ──► human_proxy_evaluations
```

There is **no** `pain_point_clusters` table. Complaint grouping for opportunity generation happens in-memory via `TopicPatternDetector`.

---

## Core Tables

### `sources`

Configured ingestion endpoints.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| name | VARCHAR(100) | Human label |
| source_type | VARCHAR(30) | `reddit`, `hn_algolia`, `rss` |
| config | JSONB | Type-specific params |
| enabled | BOOLEAN | Default true |
| last_collected_at | TIMESTAMPTZ | |
| last_error | TEXT | |
| created_at, updated_at | TIMESTAMPTZ | |

**Collectors registered at runtime:** `reddit`, `rss` only.

### `rss_feeds`

Dedicated RSS feed registry (migration `016_rss_feeds.py`).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| source_id | UUID FK → sources | Auto-created source row |
| feed_url | TEXT UNIQUE | |
| category | VARCHAR(30) | business, tech, startup, etc. |
| enabled | BOOLEAN | |
| polling_interval_sec | INT | Min 60 |
| entry_limit | INT | |
| last_polled_at | TIMESTAMPTZ | |

### `signals`

Raw ingested content.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| source_id | UUID FK | |
| external_id | VARCHAR(255) | Platform-native ID |
| url | TEXT | Canonical link |
| title, body | TEXT | |
| author | VARCHAR(255) | |
| published_at | TIMESTAMPTZ | |
| metadata | JSONB | Score, subreddit, collector version |
| content_hash | VARCHAR(64) | Dedup layer (migration 003) |
| processing_status | VARCHAR(30) | pending → classified \| skipped \| failed |
| skip_reason | TEXT | |
| collected_at | TIMESTAMPTZ | |

**Unique:** `(source_id, external_id)`

### `categories`

Unified taxonomy table (replaces separate `taxonomy_*` tables).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| code | VARCHAR(50) UNIQUE | e.g. `pricing`, `saas_b2b` |
| label | VARCHAR(100) | |
| description | TEXT | |
| kind | VARCHAR(30) | `complaint_category`, `domain`, `persona` |

### `complaints`

Structured extraction from signals. **1:1** with signal (`signal_id UNIQUE`).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| signal_id | UUID FK UNIQUE | |
| category_id, domain_id, persona_id | UUID FK → categories | |
| summary, verbatim_quote | TEXT | |
| severity | INT CHECK 1–5 | |
| product_mentions | TEXT[] | |
| embedding | vector(1536) | Optional pgvector |
| llm_model | VARCHAR(50) | |
| llm_confidence | REAL | |

### `opportunities`

Synthesized business hypotheses.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| title | VARCHAR(200) | |
| problem_statement, target_user | TEXT | |
| frequency_signal | TEXT | |
| existing_alternatives, gap | TEXT | |
| confidence_score | REAL CHECK 0–1 | |
| review_status | VARCHAR(30) | new, approved, rejected, deferred |
| reviewed_at, review_notes | | |
| llm_model | VARCHAR(50) | |

Linked to complaints via `opportunity_complaints` (M:N junction).

### `opportunity_scores`

Scoring history (migration `005_opportunity_score_dimensions.py`).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| opportunity_id | UUID FK | |
| score | INT 0–100 | |
| is_current | BOOLEAN | One current row per opportunity |
| volume_score, severity_score, … | REAL | Dimension breakdown |
| scoring_model | VARCHAR(50) | `scoring_engine_v1` |
| scoring_notes | TEXT | |

---

## Agent Output Tables

Each research agent persists structured output plus evidence junction tables:

| Agent | Main table | Evidence table | Migration |
|-------|------------|----------------|-----------|
| Market Research | `market_briefs` | — | 006 |
| Competitor Intelligence | `competitor_analyses`, `competitor_profiles` | — | 007 |
| Customer Research | `customer_research` | `customer_research_evidence` | 008 |
| Revenue Validation | `revenue_validations` | `revenue_validation_evidence` | 009 |
| Product Strategy | `product_strategies` | `product_strategy_evidence` | 010 |
| Go-To-Market | `gtm_plans` | `gtm_plan_evidence` | 011 |
| Growth Strategy | `growth_evaluations` | `growth_evaluation_evidence` | 012 |
| Human Proxy | `human_proxy_evaluations` | `human_proxy_evaluation_evidence` | 013 |
| Founder profiles | `founder_profiles` | — | 013 |

Common patterns: `opportunity_id` FK, `is_current` flag, `status` enum, `llm_model`, agent-specific score fields.

---

## Ranking and Reports

### `executive_ranking_runs` / `executive_ranking_entries`

Migration `014_executive_ranking.py`. Stores deterministic ranking runs with component scores (pain, market, revenue, competition, growth, founder_fit).

### `reports`

Markdown and structured report content. Types include `top_opportunities`, `venture_recommendation`, `pipeline_summary`, `daily_digest`.

---

## Pipeline and Operations Tables

### `pipeline_runs`

| Column | Description |
|--------|-------------|
| trigger | scheduled, manual, api, worker |
| status | running, completed, failed, partial, cancelled |
| started_at, finished_at | |
| config_snapshot | JSONB thresholds used |
| error_summary | TEXT |

### `pipeline_stage_runs`

Per-stage metrics within a run. Stage values match `PipelineStage` enum (14 stages — see [pipeline.md](./pipeline.md)).

### `scheduler_jobs` / `scheduler_runs`

Migration `017_scheduler.py`. Cron configuration and execution audit trail with linked `arq_job_ids`.

### `llm_calls`

LLM audit log (migration `004_llm_calls.py`).

| Column | Description |
|--------|-------------|
| entity_type, entity_id | Polymorphic reference |
| graph_name | e.g. `classify_complaint` |
| model, prompt_tokens, completion_tokens | |
| estimated_cost_usd | Migration `019_llm_budget.py` |
| latency_ms | |

### `llm_budget_alerts`

Daily threshold warnings (50/75/90%). Migration `019_llm_budget.py`.

### `approval_requests` / `approval_decisions`

Founder approval workflow. Migration `018_approval_workflow.py`. Subjects: executive ranking runs, venture reports.

---

## Key Queries

### Worker: pending signals for classification

```sql
SELECT id, title, body, url
FROM signals
WHERE processing_status = 'pending'
ORDER BY collected_at ASC
LIMIT 50;
```

### Dashboard: new opportunities

```sql
SELECT o.*, os.score
FROM opportunities o
LEFT JOIN opportunity_scores os ON os.opportunity_id = o.id AND os.is_current = true
WHERE o.review_status = 'new'
ORDER BY os.score DESC NULLS LAST, o.confidence_score DESC;
```

### Daily LLM spend

```sql
SELECT DATE(created_at AT TIME ZONE 'UTC'), SUM(estimated_cost_usd)
FROM llm_calls
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY 1;
```

---

## Migration Strategy

- **Tool:** Alembic (`api/alembic/`)
- **Driver:** `postgresql+psycopg` (sync) for migrations; `postgresql+asyncpg` at runtime
- **CI validation:** single head check, `upgrade head`, `alembic check`
- **Local reset:** `alembic downgrade base && alembic upgrade head`

### Migration index

| Revision | File | Purpose |
|----------|------|---------|
| 001 | enable_extensions | pgvector |
| 002 | core_persistence | sources, signals, complaints, opportunities, categories |
| 003 | signal_content_hash | content hash dedup |
| 004 | llm_calls | LLM audit |
| 005 | opportunity_score_dimensions | scoring |
| 006–013 | agent tables | V2 research agents |
| 014 | executive_ranking | ranking runs |
| 015 | pipeline | pipeline_runs, pipeline_stage_runs |
| 016 | rss_feeds | RSS registry |
| 017 | scheduler | scheduler_jobs, scheduler_runs |
| 018 | approval_workflow | approvals |
| 019 | llm_budget | cost tracking, alerts |

---

## Redis Keys (Not PostgreSQL)

| Key Pattern | Purpose |
|-------------|---------|
| `lock:pipeline:run` | Full pipeline concurrency lock |
| `lock:job:{name}:{key}` | Idempotent job dedup |
| `job:status:{job_id}` | ARQ job monitoring (7-day TTL) |
| `jobs:recent` | Recent job ID sorted set |
| `ratelimit:reddit:{scope}` | Reddit collector rate limit |
| `ratelimit:rss:{scope}` | RSS collector rate limit |
| `arq:queue` | ARQ default queue |

PostgreSQL remains authoritative; Redis loss means job retry, not data loss.

---

## Integrity Rules

1. Signal → complaint is 1:0..1; deleting signal cascades to complaint
2. Complaint → opportunity is M:N via `opportunity_complaints`
3. One `is_current=true` opportunity_score per opportunity (application enforced)
4. Approval decisions append-only on `approval_decisions`
5. Review status changes on opportunities persist via service layer
