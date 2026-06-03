# AI Venture Studio — Pipeline Design (V1)

## Overview

The V1 pipeline is a **sequential batch workflow** with four stages:

```
┌──────────┐    ┌───────────┐    ┌──────────┐    ┌───────────┐
│ COLLECT  │───►│ CLASSIFY  │───►│ CLUSTER  │───►│ GENERATE  │
└──────────┘    └───────────┘    └──────────┘    └───────────┘
     │                │                │                 │
     ▼                ▼                ▼                 ▼
  signals         complaints      clusters         opportunities
```

Each full execution creates one `pipeline_runs` record and four `pipeline_stage_runs` children. Stages can also run **independently** (e.g., classify-only to clear backlog).

**Orchestration:** FastAPI triggers → Redis job queue (ARQ recommended) → worker processes execute stages → LangGraph handles LLM subgraphs within classify and generate stages.

---

## Triggers

| Trigger | Mechanism | Default schedule |
|---------|-----------|------------------|
| Scheduled | Cron → `POST /api/v1/pipeline/run` | `0 */6 * * *` (every 6 hours) |
| Manual (UI) | Dashboard button → same endpoint | On demand |
| Manual (CLI) | `curl` with API key | On demand |
| Stage-only | `POST /api/v1/pipeline/run/{stage}` | On demand |

**Concurrency rule:** Only one full pipeline run at a time. Redis lock `lock:pipeline:run` with 1-hour TTL. Stage-only runs may execute in parallel except `cluster` + `generate` which require exclusive access to cluster tables.

---

## Stage 1: COLLECT (Complaint Collection)

### Purpose
Fetch new content from enabled sources and insert deduplicated `signals` rows with `processing_status = 'pending'`.

### Input
- `sources` where `enabled = true`

### Output
- New `signals` rows
- Updated `sources.last_collected_at`
- `pipeline_stage_runs.items_out` = count of new signals

### Per-Source Collectors

#### Reddit Collector
1. Load source config: subreddit, sort, limit, time_filter
2. Call Reddit JSON API: `https://www.reddit.com/r/{subreddit}/{sort}.json`
3. Map each post → signal:
   - `external_id`: Reddit post fullname (`t3_xxx`)
   - `body`: selftext (skip if empty and no title complaint signal — still ingest title-only if keyword match optional in V1.1)
   - `metadata`: `{ "score": N, "num_comments": N, "subreddit": "..." }`
4. Upsert: on conflict `(source_id, external_id)` do nothing
5. Rate limit: max 1 req/sec per source via Redis

#### HN Algolia Collector
1. Query HN Algolia API with config query string and date filter
2. `external_id`: HN item ID
3. `body`: comment text or story text concatenated
4. Same upsert semantics

#### RSS Collector
1. Parse feed with `feedparser`
2. `external_id`: entry GUID or link hash
3. `body`: summary or content
4. Same upsert semantics

### Filters (Pre-LLM, In Collector)
Skip insertion if:
- Body + title combined length < 50 characters
- Body is entirely URL with no user text
- Exact duplicate URL already exists globally (optional secondary dedup)

### Error Handling
| Error | Action |
|-------|--------|
| HTTP 429 | Exponential backoff, retry 3x, then mark source `last_error` |
| HTTP 5xx | Retry 3x, skip source for this run |
| Parse error | Log, continue next item |
| Source disabled mid-run | Skip |

### Idempotency
Re-running collect produces zero duplicate signals. Existing signals are never updated (immutable content).

---

## Stage 2: CLASSIFY (Complaint Classification)

### Purpose
Transform pending signals into structured `complaints` or mark signals as `skipped` / `failed`.

### Input
- `signals` WHERE `processing_status = 'pending'`
- Batch size: 50 (configurable via `CLASSIFY_BATCH_SIZE`)

### Output
- `complaints` rows (0 or 1 per signal)
- Signal status → `classified`, `skipped`, or `failed`
- `llm_calls` audit rows

### Processing Flow

```
For each signal batch:
  1. SET processing_status = 'processing' (SKIP LOCKED)
  2. Invoke LangGraph: classify_complaint
  3. If is_complaint == false:
       SET signal skipped + skip_reason
  4. Else:
       INSERT complaint
       SET signal classified
  5. Enqueue complaint.id for embedding job (async sub-step)
  6. On LLM/validation error:
       SET signal failed (retry up to 3 times across runs)
```

### LangGraph: `classify_complaint`

**Nodes:**

| Node | Responsibility |
|------|----------------|
| `extract` | LLM structured output: is_complaint, summary, quote, category, domain, persona, severity, product_mentions |
| `validate` | Pydantic validation; enum check against taxonomy tables |
| `persist` | Write complaint + update signal (if run synchronously) or return state for worker |

**State schema:**
```python
{
  "signal_id": UUID,
  "title": str,
  "body": str,
  "url": str,
  "is_complaint": bool | None,
  "complaint": ComplaintDraft | None,
  "skip_reason": str | None,
  "error": str | None,
}
```

**LLM prompt constraints:**
- Must cite verbatim quote from source text (validated: substring check)
- If ambiguous, prefer `is_complaint = false`
- Category/domain/persona must be from allowed enums (reject and retry once on violation)

### Embedding Sub-Step
After complaint insert, worker generates embedding on `summary + " " + verbatim_quote` via OpenAI embeddings API, updates `complaints.embedding`.

Can run inline or as micro-batch every 10 complaints. Clustering stage requires embeddings complete — pipeline waits or runs embed sweep before cluster.

### Skip Reasons (Examples)
- `not_a_complaint` — general discussion, news, promotion
- `insufficient_context` — too vague to extract
- `duplicate_intent` — near-duplicate of existing complaint from same author (V1.1)

### Metrics
- `items_in`: batch size picked up
- `items_out`: complaints created
- `items_failed`: signals marked failed

---

## Stage 3: CLUSTER

### Purpose
Group complaints from the rolling window into `pain_point_clusters` for opportunity synthesis.

### Input
- `complaints` WHERE `cluster_id IS NULL` AND `embedding IS NOT NULL`
- Window: `published_at` or `created_at` within last 30 days (config: `CLUSTER_WINDOW_DAYS`)

### Output
- New/updated `pain_point_clusters`
- `complaints.cluster_id` assigned
- Clusters with `< MIN_CLUSTER_SIZE` complaints remain unclustered (orphans wait for more data)

### Algorithm (V1)

1. **Fetch** all unclustered complaints in window (~500–2000 at V1 scale)
2. **Optional pre-filter:** same domain buckets to reduce cross-domain merges
3. **Cluster:** HDBSCAN on embedding vectors
   - `min_cluster_size = 3` (config: `MIN_CLUSTER_SIZE`)
   - `min_samples = 2`
   - metric: cosine
4. **For each cluster ≥ min size:**
   - Compute centroid embedding (mean of members)
   - LLM call: generate `label` + `description` from top 5 complaint summaries
   - INSERT `pain_point_clusters`, UPDATE member complaints
5. **Noise points** (label -1): leave `cluster_id NULL`

### Re-Clustering Policy
- Full re-cluster weekly (Sunday 00:00 UTC) on active window
- Incremental cluster assignment daily: new complaints assigned to nearest existing centroid if cosine similarity ≥ 0.85, else held for weekly HDBSCAN
- V1 simplification acceptable: **daily full re-cluster** if complaint count < 2000 (solo founder scale)

### Deduplication vs Existing Clusters
Before insert, check cosine similarity of new centroid to existing open clusters in same domain. If ≥ 0.90, merge into existing cluster instead of creating duplicate.

---

## Stage 4: GENERATE (Opportunity Generation)

### Purpose
Create one `opportunities` record per eligible cluster with evidence links.

### Input
- `pain_point_clusters` WHERE `status = 'open'` AND `complaint_count >= MIN_CLUSTER_SIZE`

### Output
- `opportunities` rows
- `opportunity_complaints` junction rows
- Cluster `status → 'opportunity_created'`

### Eligibility Gates
Skip cluster if:
- Already has an opportunity (`cluster_id` unique on opportunities)
- Complaint count < 3
- Top complaint severities average < 2.0 (config: `MIN_AVG_SEVERITY`)
- Generated opportunity confidence < 0.4 (after LLM, discard)

### LangGraph: `generate_opportunity`

**Nodes:**

| Node | Responsibility |
|------|----------------|
| `gather_evidence` | Load all complaints in cluster + source URLs |
| `synthesize` | LLM produces opportunity brief fields (template from mvp.md) |
| `ground_check` | Verify existing_alternatives only mentions products from evidence text |
| `score` | LLM self-assessed confidence 0–1 |
| `dedupe_check` | Compare embedding of title+problem to existing opportunities; skip if ≥ 0.92 similar |
| `persist` | Insert opportunity + junction rows |

**Ground check rule:** Extract product names from `existing_alternatives` field; each must appear in at least one complaint's `product_mentions` or source body. Fail → retry synthesize once with stricter prompt.

### Post-Generate
- Opportunity `review_status = 'new'` → appears in dashboard inbox
- No automatic approval

---

## End-to-End Pipeline Run Sequence

```
1. Acquire lock:pipeline:run
2. INSERT pipeline_runs (status=running)
3. STAGE collect
   - For each enabled source: run collector
   - INSERT pipeline_stage_runs
4. STAGE classify
   - Loop batches until no pending signals
   - Wait for embedding queue drain (timeout 10 min)
5. STAGE cluster
   - Run clustering algorithm
6. STAGE generate
   - For each eligible open cluster: run generate_opportunity graph
7. UPDATE pipeline_runs (status=completed|partial|failed)
8. Release lock
```

**Partial completion:** If classify succeeds but generate fails, status = `partial`. Next run skips collect if last run < 1 hour ago (configurable) or always runs collect ( simpler for V1: **always run all stages**).

---

## Schedules (Recommended V1)

| Job | Cron | Notes |
|-----|------|-------|
| Full pipeline | `0 */6 * * *` | 00:00, 06:00, 12:00, 18:00 UTC |
| Embedding sweep | `*/15 * * * *` | Catch embed failures |
| Weekly deep cluster | `0 3 * * 0` | Optional full HDBSCAN rebuild |

---

## Retry and Dead Letter Policy

| Stage | Max retries | Backoff | Dead letter |
|-------|-------------|---------|-------------|
| Collect (per source) | 3 | 2^n seconds | `sources.last_error` |
| Classify (per signal) | 3 | next pipeline run | `processing_status = 'failed'` |
| Embed (per complaint) | 5 | 1 min | log alert, manual requeue |
| Cluster | 1 | — | stage error on pipeline_run |
| Generate (per cluster) | 2 | inline | skip cluster, log |

**Manual recovery:**
- `POST /api/v1/signals/{id}/reclassify` — reset to pending
- `POST /api/v1/pipeline/retry-failed` — requeue all failed signals

---

## Observability

### Pipeline Run Dashboard Fields
- Run ID, trigger, status, duration
- Per-stage: in/out/failed counts
- Error detail expandable

### Logs (Structured JSON)
```json
{
  "event": "stage_complete",
  "pipeline_run_id": "...",
  "stage": "classify",
  "items_in": 50,
  "items_out": 38,
  "items_failed": 1,
  "duration_ms": 124000
}
```

### Alerts (V1 — Manual)
Check daily:
- `pipeline_runs` with `status = 'failed'` in last 24h
- `sources.last_error IS NOT NULL`
- LLM daily cost > budget env var

---

## Configuration Reference

| Env Var | Default | Description |
|---------|---------|-------------|
| `CLASSIFY_BATCH_SIZE` | 50 | Signals per classify batch |
| `CLUSTER_WINDOW_DAYS` | 30 | Rolling window |
| `MIN_CLUSTER_SIZE` | 3 | Min complaints per cluster |
| `MIN_AVG_SEVERITY` | 2.0 | Generate gate |
| `CLUSTER_SIMILARITY_MERGE` | 0.90 | Merge threshold |
| `OPPORTUNITY_DEDUPE_THRESHOLD` | 0.92 | Skip similar opportunities |
| `LLM_DAILY_BUDGET_USD` | 2.00 | Hard stop |
| `PIPELINE_LOCK_TTL_SEC` | 3600 | Redis lock |

---

## Future Pipeline Stages (Not V1)

These stages will insert after GENERATE when built:

| Stage | Input | Output |
|-------|-------|--------|
| `research_market` | approved opportunities | market_briefs |
| `analyze_competitors` | approved opportunities | competitor_profiles |
| `validate_revenue` | opportunities + market data | revenue_assessments |
| `plan_mvp` | high-ranked opportunities | mvp_plans |
| `plan_gtm` | mvp_plans | gtm_plans |
| `rank` | all assessments | ranked_recommendations |

V1 schema reserves `pipeline_stage_runs.stage` as VARCHAR(50) to accommodate these without migration.

---

## Example Timeline (Single Run)

| Time | Event |
|------|-------|
| T+0s | Cron hits API, lock acquired |
| T+5s | Collect: 3 sources → 42 new signals |
| T+30s | Classify batch 1: 42 signals → 31 complaints |
| T+2m | Embeddings complete |
| T+3m | Cluster: 2 new clusters (8 + 4 complaints) |
| T+4m | Generate: 2 opportunities created |
| T+4m30s | Pipeline completed, lock released |

Total wall clock ~5 min for typical V1 load.
