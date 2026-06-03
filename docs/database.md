# AI Venture Studio — Database Design (V1)

## Overview

PostgreSQL is the **system of record**. All entities, pipeline state, LLM audit trails, and human decisions live here. Redis is not persisted to long-term storage except via job metadata mirrors.

**Extensions required:**

- `uuid-ossp` or `gen_random_uuid()` (PG 13+)
- `pgvector` — complaint and cluster embeddings (1536 dims for `text-embedding-3-small`)

**Naming conventions:**

- Tables: plural snake_case (`signals`, `complaints`)
- Primary keys: `id UUID DEFAULT gen_random_uuid()`
- Timestamps: `created_at`, `updated_at` (trigger-maintained)
- Soft deletes: not used in V1 (hard delete via cascade only in dev)

---

## Entity Relationship Diagram

```
sources ─────────────┐
                     │ 1:N
                     ▼
                  signals ─────────────┐
                     │ 1:0..1         │
                     ▼                │
                 complaints ─────────┤
                     │ N:1            │
                     ▼                │
              pain_point_clusters     │
                     │ 1:0..1         │
                     ▼                │
               opportunities ◄───────┘ (via opportunity_complaints M:N)
                     │
                     ▼
            opportunity_reviews (audit)

pipeline_runs ──► pipeline_stage_runs
llm_calls (audit, polymorphic reference)
```

---

## Tables

### `sources`

Configured ingestion endpoints.

| Column            | Type         | Constraints  | Description                      |
| ----------------- | ------------ | ------------ | -------------------------------- |
| id                | UUID         | PK           |                                  |
| name              | VARCHAR(100) | NOT NULL     | Human label, e.g. "r/SaaS"       |
| source_type       | VARCHAR(30)  | NOT NULL     | `reddit`, `hn_algolia`, `rss`    |
| config            | JSONB        | NOT NULL     | Type-specific params (see below) |
| enabled           | BOOLEAN      | DEFAULT true |                                  |
| last_collected_at | TIMESTAMPTZ  | NULL         |                                  |
| last_error        | TEXT         | NULL         |                                  |
| created_at        | TIMESTAMPTZ  | NOT NULL     |                                  |
| updated_at        | TIMESTAMPTZ  | NOT NULL     |                                  |

**`config` examples:**

```json
// reddit
{ "subreddit": "SaaS", "sort": "new", "limit": 50, "time_filter": "day" }

// hn_algolia
{ "query": "wish OR \"someone should build\"", "tags": "story,comment", "days_back": 7 }

// rss
{ "url": "https://www.indiehackers.com/feed", "limit": 30 }
```

**Indexes:**

- `idx_sources_enabled` ON `(enabled)` WHERE `enabled = true`

---

### `signals`

Raw ingested content. Immutable text after insert.

| Column            | Type         | Constraints                | Description                |
| ----------------- | ------------ | -------------------------- | -------------------------- |
| id                | UUID         | PK                         |                            |
| source_id         | UUID         | FK → sources.id            |                            |
| external_id       | VARCHAR(255) | NOT NULL                   | Platform-native ID         |
| url               | TEXT         | NOT NULL                   | Canonical link             |
| title             | TEXT         | NULL                       | Post title if applicable   |
| body              | TEXT         | NOT NULL                   | Full text for LLM          |
| author            | VARCHAR(255) | NULL                       |                            |
| published_at      | TIMESTAMPTZ  | NULL                       | Original post time         |
| metadata          | JSONB        | DEFAULT '{}'               | Score, comment count, etc. |
| processing_status | VARCHAR(30)  | NOT NULL DEFAULT 'pending' | See enum below             |
| skip_reason       | TEXT         | NULL                       | If skipped                 |
| collected_at      | TIMESTAMPTZ  | NOT NULL                   | Ingestion time             |
| created_at        | TIMESTAMPTZ  | NOT NULL                   |                            |
| updated_at        | TIMESTAMPTZ  | NOT NULL                   |                            |

**`processing_status` enum:**
`pending` → `processing` → `classified` | `skipped` | `failed`

**Unique constraint:**

- `uq_signals_source_external` UNIQUE `(source_id, external_id)`

**Indexes:**

- `idx_signals_status_collected` ON `(processing_status, collected_at)` — worker pickup
- `idx_signals_published` ON `(published_at DESC)`

---

### `complaints`

Structured extraction from a signal. V1 enforces **at most one complaint per signal**.

| Column           | Type         | Constraints                       | Description                  |
| ---------------- | ------------ | --------------------------------- | ---------------------------- |
| id               | UUID         | PK                                |                              |
| signal_id        | UUID         | FK → signals.id, UNIQUE           | 1:1 with signal              |
| summary          | TEXT         | NOT NULL                          | 1–2 sentence neutral summary |
| verbatim_quote   | TEXT         | NOT NULL                          | Exact user language          |
| category         | VARCHAR(50)  | NOT NULL                          | Taxonomy enum                |
| domain           | VARCHAR(50)  | NOT NULL                          | Taxonomy enum                |
| persona          | VARCHAR(50)  | NOT NULL                          | Taxonomy enum                |
| severity         | SMALLINT     | NOT NULL CHECK (1–5)              |                              |
| product_mentions | TEXT[]       | DEFAULT '{}'                      | Tools named in text          |
| embedding        | vector(1536) | NULL                              | Set after insert             |
| cluster_id       | UUID         | FK → pain_point_clusters.id, NULL | Assigned during clustering   |
| llm_model        | VARCHAR(50)  | NOT NULL                          | Model used for extraction    |
| llm_confidence   | REAL         | NULL                              | 0.0–1.0                      |
| created_at       | TIMESTAMPTZ  | NOT NULL                          |                              |
| updated_at       | TIMESTAMPTZ  | NOT NULL                          |                              |

**Indexes:**

- `idx_complaints_cluster` ON `(cluster_id)` WHERE `cluster_id IS NOT NULL`
- `idx_complaints_domain_category` ON `(domain, category)`
- `idx_complaints_embedding` USING ivfflat `(embedding vector_cosine_ops)` WITH (lists = 100) — create after ≥1000 rows or use exact search at low volume

---

### `pain_point_clusters`

Groups of similar complaints within a rolling window.

| Column             | Type         | Constraints           | Description                                |
| ------------------ | ------------ | --------------------- | ------------------------------------------ |
| id                 | UUID         | PK                    |                                            |
| label              | VARCHAR(200) | NOT NULL              | LLM-generated cluster name                 |
| description        | TEXT         | NULL                  |                                            |
| domain             | VARCHAR(50)  | NOT NULL              | Majority domain                            |
| complaint_count    | INT          | NOT NULL DEFAULT 0    | Denormalized                               |
| centroid_embedding | vector(1536) | NULL                  | Mean of member embeddings                  |
| window_start       | DATE         | NOT NULL              | Clustering window                          |
| window_end         | DATE         | NOT NULL              |                                            |
| pipeline_run_id    | UUID         | FK → pipeline_runs.id |                                            |
| status             | VARCHAR(30)  | DEFAULT 'open'        | `open`, `opportunity_created`, `dismissed` |
| created_at         | TIMESTAMPTZ  | NOT NULL              |                                            |
| updated_at         | TIMESTAMPTZ  | NOT NULL              |                                            |

**Indexes:**

- `idx_clusters_status_window` ON `(status, window_end DESC)`

---

### `opportunities`

Synthesized business hypotheses from clusters.

| Column                | Type         | Constraints                         | Description                               |
| --------------------- | ------------ | ----------------------------------- | ----------------------------------------- |
| id                    | UUID         | PK                                  |                                           |
| cluster_id            | UUID         | FK → pain_point_clusters.id, UNIQUE | 1:1 per cluster in V1                     |
| title                 | VARCHAR(200) | NOT NULL                            |                                           |
| problem_statement     | TEXT         | NOT NULL                            |                                           |
| target_user           | TEXT         | NOT NULL                            |                                           |
| frequency_signal      | TEXT         | NOT NULL                            |                                           |
| existing_alternatives | TEXT         | NOT NULL                            | Evidence-only                             |
| gap                   | TEXT         | NOT NULL                            |                                           |
| confidence_score      | REAL         | NOT NULL CHECK (0–1)                |                                           |
| review_status         | VARCHAR(30)  | DEFAULT 'new'                       | `new`, `approved`, `rejected`, `deferred` |
| reviewed_at           | TIMESTAMPTZ  | NULL                                |                                           |
| review_notes          | TEXT         | NULL                                | Founder notes                             |
| llm_model             | VARCHAR(50)  | NOT NULL                            |                                           |
| pipeline_run_id       | UUID         | FK → pipeline_runs.id               |                                           |
| created_at            | TIMESTAMPTZ  | NOT NULL                            |                                           |
| updated_at            | TIMESTAMPTZ  | NOT NULL                            |                                           |

**Indexes:**

- `idx_opportunities_review_status` ON `(review_status, created_at DESC)`

---

### `opportunity_complaints`

M:N evidence linkage (denormalized convenience; cluster membership is primary).

| Column         | Type                           | Constraints                             |
| -------------- | ------------------------------ | --------------------------------------- |
| opportunity_id | UUID                           | FK → opportunities.id ON DELETE CASCADE |
| complaint_id   | UUID                           | FK → complaints.id ON DELETE CASCADE    |
| PRIMARY KEY    | (opportunity_id, complaint_id) |                                         |

---

### `opportunity_reviews`

Append-only audit of human decisions.

| Column         | Type        | Constraints           | Description |
| -------------- | ----------- | --------------------- | ----------- |
| id             | UUID        | PK                    |             |
| opportunity_id | UUID        | FK → opportunities.id |             |
| from_status    | VARCHAR(30) | NOT NULL              |             |
| to_status      | VARCHAR(30) | NOT NULL              |             |
| notes          | TEXT        | NULL                  |             |
| created_at     | TIMESTAMPTZ | NOT NULL              |             |

---

### `pipeline_runs`

Top-level pipeline execution record.

| Column          | Type        | Constraints  | Description                                 |
| --------------- | ----------- | ------------ | ------------------------------------------- |
| id              | UUID        | PK           |                                             |
| trigger         | VARCHAR(30) | NOT NULL     | `scheduled`, `manual`, `api`                |
| status          | VARCHAR(30) | NOT NULL     | `running`, `completed`, `failed`, `partial` |
| started_at      | TIMESTAMPTZ | NOT NULL     |                                             |
| finished_at     | TIMESTAMPTZ | NULL         |                                             |
| config_snapshot | JSONB       | DEFAULT '{}' | Thresholds used                             |
| error_summary   | TEXT        | NULL         |                                             |
| created_at      | TIMESTAMPTZ | NOT NULL     |                                             |

---

### `pipeline_stage_runs`

Per-stage metrics within a pipeline run.

| Column          | Type        | Constraints           | Description                                  |
| --------------- | ----------- | --------------------- | -------------------------------------------- |
| id              | UUID        | PK                    |                                              |
| pipeline_run_id | UUID        | FK → pipeline_runs.id |                                              |
| stage           | VARCHAR(50) | NOT NULL              | `collect`, `classify`, `cluster`, `generate` |
| status          | VARCHAR(30) | NOT NULL              |                                              |
| started_at      | TIMESTAMPTZ | NOT NULL              |                                              |
| finished_at     | TIMESTAMPTZ | NULL                  |                                              |
| items_in        | INT         | DEFAULT 0             |                                              |
| items_out       | INT         | DEFAULT 0             |                                              |
| items_failed    | INT         | DEFAULT 0             |                                              |
| error_detail    | TEXT        | NULL                  |                                              |
| created_at      | TIMESTAMPTZ | NOT NULL              |                                              |

**Index:**

- `idx_stage_runs_pipeline` ON `(pipeline_run_id, stage)`

---

### `llm_calls`

Audit log for cost tracking and debugging.

| Column            | Type          | Constraints | Description                        |
| ----------------- | ------------- | ----------- | ---------------------------------- |
| id                | UUID          | PK          |                                    |
| entity_type       | VARCHAR(50)   | NOT NULL    | `signal`, `cluster`, `opportunity` |
| entity_id         | UUID          | NOT NULL    |                                    |
| graph_name        | VARCHAR(100)  | NOT NULL    | e.g.`classify_complaint`           |
| model             | VARCHAR(50)   | NOT NULL    |                                    |
| prompt_tokens     | INT           | NOT NULL    |                                    |
| completion_tokens | INT           | NOT NULL    |                                    |
| cost_usd          | NUMERIC(10,6) | NULL        |                                    |
| latency_ms        | INT           | NULL        |                                    |
| request_hash      | VARCHAR(64)   | NULL        | Dedup/debug                        |
| created_at        | TIMESTAMPTZ   | NOT NULL    |                                    |

**Indexes:**

- `idx_llm_calls_entity` ON `(entity_type, entity_id)`
- `idx_llm_calls_created` ON `(created_at DESC)`

---

## Lookup Tables (Taxonomy)

### `taxonomy_categories`, `taxonomy_domains`, `taxonomy_personas`

| Column      | Type           |
| ----------- | -------------- |
| code        | VARCHAR(50) PK |
| label       | VARCHAR(100)   |
| description | TEXT           |

Seed via migration. Application validates against these codes; LLM prompt includes allowed values.

---

## Key Queries (V1)

### Worker: fetch signals to classify

```sql
SELECT id, title, body, url
FROM signals
WHERE processing_status = 'pending'
ORDER BY collected_at ASC
LIMIT 50
FOR UPDATE SKIP LOCKED;
```

### Dashboard: new opportunities inbox

```sql
SELECT o.*, c.label AS cluster_label, c.complaint_count
FROM opportunities o
JOIN pain_point_clusters c ON c.id = o.cluster_id
WHERE o.review_status = 'new'
ORDER BY o.confidence_score DESC, o.created_at DESC;
```

### Opportunity detail with evidence

```sql
SELECT comp.*
FROM complaints comp
JOIN opportunity_complaints oc ON oc.complaint_id = comp.id
WHERE oc.opportunity_id = $1
ORDER BY comp.severity DESC;
```

### Daily LLM spend

```sql
SELECT DATE(created_at), SUM(cost_usd)
FROM llm_calls
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY 1;
```

---

## Migration Strategy

- **Tool:** Alembic (Python/FastAPI side)
- **Order:** extensions → lookup seeds → core tables → indexes → pgvector index (deferred)
- **Versioning:** Single linear chain; no branch migrations in V1
- **Local reset:** `alembic downgrade base && alembic upgrade head` + seed script

---

## Data Volume Estimates (V1 — 90 days)

| Table         | Rows    | Storage                     |
| ------------- | ------- | --------------------------- |
| signals       | ~25,000 | ~50 MB                      |
| complaints    | ~18,000 | ~30 MB + embeddings ~110 MB |
| clusters      | ~300    | negligible                  |
| opportunities | ~250    | negligible                  |
| llm_calls     | ~20,000 | ~5 MB                       |

Well within single PostgreSQL instance limits. Re-evaluate partitioning at 500K+ signals.

---

## Redis Keys (Not PostgreSQL — Documented for Completeness)

| Key Pattern                    | TTL    | Purpose                                      |
| ------------------------------ | ------ | -------------------------------------------- |
| `queue:classify`               | —      | List of signal IDs (or use ARQ native queue) |
| `queue:embed`                  | —      | Complaint IDs needing embedding              |
| `lock:pipeline:run`            | 3600s  | Prevent concurrent full pipeline runs        |
| `ratelimit:reddit:{source_id}` | 60s    | Collection rate limiting                     |
| `cache:source:{id}:cursor`     | 86400s | Pagination cursor for collectors             |

PostgreSQL remains authoritative; Redis loss means job retry, not data loss.

---

## Integrity Rules

1. Signal → complaint is 1:0..1; deleting signal cascades to complaint
2. Cluster → opportunity is 1:0..1 in V1
3. `complaints.cluster_id` must reference cluster containing that complaint (enforced in application layer during clustering transaction)
4. `opportunity_complaints` must be subset of cluster members
5. `review_status` changes must insert `opportunity_reviews` row in same transaction
