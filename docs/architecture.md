# AI Venture Studio — System Architecture (V1)

## Overview

V1 is a **two-service monorepo** optimized for a solo founder: a Next.js dashboard and a FastAPI backend that owns ingestion, LLM orchestration (LangGraph), background workers, and the pipeline API.

```
┌─────────────────────────────────────────────────────────────────┐
│                         SOLO FOUNDER                            │
│                    (Browser — 30 min/day)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Next.js (web/)          App Router, Server Components          │
│  - Dashboard, inbox, source config, pipeline logs               │
│  - Server Actions / fetch → FastAPI                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST /api/v1/*
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI (api/)                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ REST routes │  │ ARQ worker   │  │ LangGraph graphs        │ │
│  │             │──│ (async jobs) │──│ classify_complaint      │ │
│  │             │  │              │  │ generate_opportunity    │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
│  ┌─────────────┐  ┌──────────────┐                                │
│  │ Collectors  │  │ Cluster svc  │                                │
│  │ reddit/hn/  │  │ HDBSCAN +    │                                │
│  │ rss         │  │ pgvector     │                                │
│  └─────────────┘  └──────────────┘                                │
└───────┬─────────────────────┬───────────────────────────────────┘
        │                     │
        ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────────┐
│  PostgreSQL   │     │  Redis        │     │  OpenAI API       │
│  + pgvector   │     │  queues/locks │     │  (LLM + embed)    │
└───────────────┘     └───────────────┘     └───────────────────┘
```

---

## Repository Layout

```
ai-venture-studio/
├── docker-compose.yml          # postgres, redis, api, worker (optional web)
├── .env.example
├── docs/                       # This documentation set
├── web/                        # Next.js 14+ App Router
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx            # Redirect → /opportunities
│   │   ├── opportunities/
│   │   │   ├── page.tsx        # Inbox
│   │   │   └── [id]/page.tsx   # Detail + evidence
│   │   ├── signals/page.tsx
│   │   ├── sources/page.tsx
│   │   └── pipeline/page.tsx
│   ├── components/
│   ├── lib/api-client.ts       # Typed fetch wrapper
│   └── package.json
└── api/                        # FastAPI + workers
    ├── app/
    │   ├── main.py
    │   ├── config.py           # Pydantic Settings
    │   ├── db/
    │   │   ├── session.py
    │   │   └── models/         # SQLAlchemy 2.0 models
    │   ├── api/v1/
    │   │   ├── router.py
    │   │   ├── opportunities.py
    │   │   ├── signals.py
    │   │   ├── sources.py
    │   │   └── pipeline.py
    │   ├── collectors/
    │   │   ├── base.py
    │   │   ├── reddit.py
    │   │   ├── hn_algolia.py
    │   │   └── rss.py
    │   ├── pipeline/
    │   │   ├── orchestrator.py
    │   │   ├── stages/
    │   │   │   ├── collect.py
    │   │   │   ├── classify.py
    │   │   │   ├── cluster.py
    │   │   │   └── generate.py
    │   │   └── locks.py
    │   ├── graphs/
    │   │   ├── classify_complaint.py
    │   │   └── generate_opportunity.py
    │   ├── services/
    │   │   ├── embedding.py
    │   │   ├── clustering.py
    │   │   └── llm_budget.py
    │   └── workers/
    │       ├── settings.py     # ARQ config
    │       └── tasks.py
    ├── alembic/
    ├── pyproject.toml
    └── Dockerfile
```

---

## Service Boundaries

### Next.js (`web/`)

**Responsibilities:**
- Render UI only; no direct DB access
- Call FastAPI for all mutations and queries
- No LLM calls from browser (keys stay server-side)

**Auth (V1):** Single shared API key in env (`API_KEY`) passed from Next.js server components via header. No user accounts. Acceptable for solo founder local + single VPS deploy.

**Key pages:**

| Route | Purpose |
|-------|---------|
| `/opportunities` | Inbox: filter by review_status, sort by confidence |
| `/opportunities/[id]` | Brief + evidence complaints + source links |
| `/signals` | Raw signal browser with processing status |
| `/sources` | CRUD for ingestion sources |
| `/pipeline` | Run history and manual trigger |

### FastAPI (`api/`)

**Responsibilities:**
- REST API for dashboard
- Pipeline orchestration entrypoints
- Enqueue background jobs
- LangGraph invocation
- Collector execution

**Process model (production VPS):**
1. `uvicorn app.main:app` — 1 worker (API)
2. `arq app.workers.tasks.WorkerSettings` — 1 worker process (jobs)

Both share codebase and env. Do not run pipeline synchronously in API request handlers beyond enqueue.

---

## API Surface (V1)

Base path: `/api/v1`  
Auth: `X-API-Key: {API_KEY}`

### Opportunities

| Method | Path | Description |
|--------|------|-------------|
| GET | `/opportunities` | List with filters: `review_status`, `limit`, `offset` |
| GET | `/opportunities/{id}` | Detail with nested complaints + signal URLs |
| PATCH | `/opportunities/{id}` | Update `review_status`, `review_notes` |

### Signals

| Method | Path | Description |
|--------|------|-------------|
| GET | `/signals` | List with filters: `processing_status`, `source_id` |
| GET | `/signals/{id}` | Detail |
| POST | `/signals/{id}/reclassify` | Reset to `pending` |

### Sources

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sources` | List all |
| POST | `/sources` | Create |
| PATCH | `/sources/{id}` | Update config, enabled |
| DELETE | `/sources/{id}` | Hard delete (dev only guard) |

### Pipeline

| Method | Path | Description |
|--------|------|-------------|
| POST | `/pipeline/run` | Enqueue full pipeline |
| POST | `/pipeline/run/{stage}` | Enqueue single stage: collect, classify, cluster, generate |
| GET | `/pipeline/runs` | List recent runs |
| GET | `/pipeline/runs/{id}` | Run detail + stage runs |
| POST | `/pipeline/retry-failed` | Requeue failed signals |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | `{ "status": "ok" }` |
| GET | `/health/ready` | DB + Redis connectivity |

---

## LangGraph Integration

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Checkpointing | PostgreSQL via LangGraph checkpointer | Resume failed LLM steps; audit trail |
| Graph invocation | Sync within ARQ task | Simpler than separate graph service |
| Structured output | OpenAI JSON mode + Pydantic | Reliable enum validation |
| Graph count (V1) | 2 | classify_complaint, generate_opportunity |

### Graph: `classify_complaint`

```
START → extract → validate ─┬─► persist → END
                            │
                            └─► (invalid) → extract (max 1 retry)
```

- **extract:** Calls LLM with signal text + taxonomy enums
- **validate:** Pydantic model + verbatim quote substring check
- **persist:** Returns draft; worker writes to DB (keeps graph stateless for testability)

### Graph: `generate_opportunity`

```
START → gather_evidence → synthesize → ground_check ─┬─► dedupe_check → persist → END
                                                      │
                                                      └─► synthesize (retry 1)
```

- **dedupe_check:** pgvector similarity against existing opportunity titles
- **persist:** Worker inserts rows

### LLM Budget Guard

`services/llm_budget.py` queries `llm_calls` sum for current UTC day before each LLM node. If over `LLM_DAILY_BUDGET_USD`, raise `BudgetExceededError` → stage marks partial, pipeline continues non-LLM stages.

---

## Background Job Architecture (ARQ)

| Task | Queue | Trigger |
|------|-------|---------|
| `run_pipeline` | default | Cron, manual |
| `run_stage` | default | Manual |
| `classify_batch` | classify | Pipeline classify stage |
| `embed_complaints` | embed | After classify |
| `collect_source` | collect | Pipeline collect stage (parallel per source) |

**Worker settings:**
- `max_jobs = 5`
- `job_timeout = 600` (10 min)
- Redis connection from `REDIS_URL`

Pipeline orchestrator enqueues `collect_source` for each enabled source in parallel, awaits completion via job IDs stored in Redis hash `pipeline:{run_id}:collect_jobs`, then proceeds to classify.

---

## Collector Architecture

```python
# collectors/base.py (conceptual interface)
class BaseCollector(ABC):
    source_type: str

    async def collect(self, source: Source, db: AsyncSession) -> CollectResult:
        ...

class CollectResult:
    new_count: int
    skipped_count: int
    errors: list[str]
```

Each collector:
1. Fetches remote data
2. Normalizes to `SignalCreate` DTOs
3. Bulk inserts with `ON CONFLICT DO NOTHING`
4. Returns counts

Collectors are **pure HTTP/parsing** — no LLM. Keeps collection fast and cheap.

---

## Clustering Service

`services/clustering.py`:

1. Load unclustered complaints as numpy matrix (via `pgvector` query)
2. Run `hdbscan.HDBSCAN(metric='euclidean', min_cluster_size=N)` on L2-normalized vectors (equivalent to cosine)
3. Return cluster assignments
4. LLM labels cluster from representative complaints (medoids)

**Dependency:** `hdbscan`, `numpy`, `scikit-learn` (optional for medoid)

At <500 complaints, brute-force cosine nearest-centroid for incremental assignment is acceptable without HDBSCAN.

---

## Data Flow (Request Path vs Pipeline Path)

### Dashboard Read (Low Latency)
```
Browser → Next.js RSC → FastAPI GET → PostgreSQL → JSON
```
No Redis, no worker. Read replicas not needed at V1 scale.

### Pipeline Write (Async)
```
Cron → FastAPI POST /pipeline/run → ARQ enqueue run_pipeline
  → Worker: orchestrator.run()
    → collect (parallel ARQ jobs)
    → classify (LangGraph batches)
    → embed (micro-batches)
    → cluster (in-process Python)
    → generate (LangGraph per cluster)
  → PostgreSQL updated
  → Founder refreshes dashboard
```

---

## Configuration Management

`api/app/config.py` — Pydantic `BaseSettings`:

```python
DATABASE_URL: str
REDIS_URL: str
OPENAI_API_KEY: str
API_KEY: str                    # Dashboard ↔ API auth
LLM_DAILY_BUDGET_USD: float = 2.0
CLASSIFY_BATCH_SIZE: int = 50
MIN_CLUSTER_SIZE: int = 3
CLUSTER_WINDOW_DAYS: int = 30
ENVIRONMENT: Literal["local", "production"] = "local"
```

Next.js env:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
API_KEY=...                     # Server-side only, not NEXT_PUBLIC
```

---

## Docker Compose (Local Dev)

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  api:
    build: ./api
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, redis]

  worker:
    build: ./api
    command: arq app.workers.tasks.WorkerSettings
    env_file: .env
    depends_on: [postgres, redis]
```

Web runs via `npm run dev` on host for fast HMR, or add `web` service optionally.

---

## Production Deployment

### Option A — Split (Recommended)
- **Vercel:** Next.js (`web/`)
- **Hetzner CX22:** FastAPI + ARQ worker (Docker)
- **Neon:** PostgreSQL with pgvector
- **Upstash:** Redis

### Option B — Single VPS
- Caddy reverse proxy → Uvicorn (API) + PM2 (Next.js standalone build)
- Managed PG + Redis still preferred over self-hosted for solo founder reliability

### Cron
VPS crontab:
```bash
0 */6 * * * curl -sf -X POST -H "X-API-Key: $API_KEY" https://api.example.com/api/v1/pipeline/run
```

Or GitHub Actions scheduled workflow if API is not publicly exposed (uses SSH tunnel or Tailscale).

---

## Security (V1)

| Concern | Mitigation |
|---------|------------|
| API key leakage | Server-side only in Next.js; never `NEXT_PUBLIC_` |
| OpenAI key | API/worker env only |
| SQL injection | SQLAlchemy parameterized queries |
| SSRF in RSS collector | Block private IP ranges; allowlist http/https only |
| Reddit/HN abuse | Rate limits via Redis; User-Agent string with contact |
| Public API exposure | Optional IP allowlist on VPS firewall |

No PII storage beyond public post author handles. GDPR deletion not prioritized for V1 public data.

---

## Testing Strategy (V1)

| Layer | Approach |
|-------|----------|
| Collectors | VCR.py recorded HTTP fixtures |
| LangGraph nodes | Mock LLM responses; test validate/ground_check logic |
| Pipeline stages | Integration test against test DB with 10 fixture signals |
| API | pytest + httpx AsyncClient |
| E2E | Manual weekly; Playwright optional in M4 |

**Fixture corpus:** Maintain `api/tests/fixtures/signals.jsonl` with 20 hand-labeled examples for classification regression.

---

## Extension Points (Future Agents)

V1 architecture intentionally leaves hooks for later stages without refactoring core:

| Hook | Location | Future Use |
|------|----------|------------|
| `pipeline_stage_runs.stage` | VARCHAR(50) | Add research, competitor, etc. |
| `opportunities.review_status = 'approved'` | DB enum | Triggers V2 research pipeline |
| LangGraph `graphs/` directory | New files | One graph per future agent |
| ARQ task registry | `workers/tasks.py` | Register new stage tasks |
| Next.js `/opportunities/[id]` tabs | UI | Market, Competitors, MVP tabs when data exists |

**V2 entry condition:** Founder approves ≥10 opportunities in V1; manually validate that briefs are useful before automating research.

---

## Failure Modes and Recovery

| Failure | System Behavior | Recovery |
|---------|-----------------|----------|
| OpenAI outage | Classify/generate fail; signals stay pending/failed | Auto-retry next run |
| Redis down | API `/health/ready` fails; jobs not enqueued | Fix Redis; manual pipeline trigger |
| Postgres down | Full stop | Restore from backup |
| Worker crash mid-pipeline | Lock TTL expires after 1h; next run may overlap | Inspect `pipeline_runs`; manual cleanup |
| Bad LLM output | validate node retries once; then signal failed | `/reclassify` or `/retry-failed` |
| Disk full | Postgres write fails | Monitor VPS disk |

---

## Technology Versions (Recommended)

| Package | Version |
|---------|---------|
| Python | 3.12 |
| FastAPI | ≥0.110 |
| SQLAlchemy | 2.0 |
| LangGraph | ≥0.2 |
| ARQ | ≥0.26 |
| Next.js | 14+ (App Router) |
| PostgreSQL | 16 + pgvector 0.7 |
| Redis | 7 |

---

## Summary

V1 architecture prioritizes **simplicity, observability, and evidence lineage** over scale. Two LangGraph workflows, four pipeline stages, one PostgreSQL schema, and one Redis instance give a solo founder a complete loop from internet signal to reviewable opportunity brief — with clear seams to add research, competitor, and planning agents later without redesign.
