# AI Venture Studio — MVP (Version 1)

## Scope Statement

Version 1 delivers three capabilities end-to-end:

1. **Complaint Collection** — Scheduled ingestion from configured sources into raw signals
2. **Complaint Classification** — LLM extraction and tagging of complaints from signals
3. **Opportunity Generation** — Cluster similar complaints and synthesize opportunity briefs

Everything else in the vision doc is **deferred**. V1 optimizes for a solo founder who wants a daily digest of evidence-backed opportunities, not a fully autonomous venture machine.

---

## In Scope

| Feature | Description |
|---------|-------------|
| Source configuration | YAML/DB-backed list of Reddit subreddits, HN keyword searches, RSS feeds |
| Scheduled collection | Cron-triggered jobs every 6 hours (configurable) |
| Deduplication | Skip signals already ingested by `(source, external_id)` |
| Complaint extraction | LLM parses signal text → structured complaint fields |
| Taxonomy tagging | Category, domain, persona, severity, product-type hints |
| Embedding + clustering | Group complaints within rolling 30-day window |
| Opportunity synthesis | One brief per cluster meeting minimum size threshold |
| Review dashboard | List opportunities with linked evidence; approve/reject/defer |
| Pipeline monitoring | Run history, stage counts, last error per stage |
| Manual re-run | Trigger single stage or full pipeline from UI |

---

## Out of Scope (V1)

| Feature | Target Version |
|---------|----------------|
| Market sizing (TAM/SAM) | V2 |
| Competitor scraping and analysis | V2 |
| Revenue validation / pricing research | V2 |
| MVP plan generation | V3 |
| GTM plan generation | V3 |
| Multi-user auth / teams | V2+ |
| Public API / webhooks | V2+ |
| Twitter/X, LinkedIn scraping | V2 (API cost + ToS complexity) |
| Email/Slack notifications | V1.1 (nice-to-have) |
| Fine-tuned classification models | V2 |

---

## User Stories

### US-1: Configure sources
**As a** founder  
**I want to** add Reddit subreddits and HN search terms  
**So that** the system collects relevant signals without code changes

**Acceptance:**
- Add/edit/disable sources from dashboard or config file
- Each source has: type, identifier, enabled flag, last_collected_at

### US-2: Automatic collection
**As a** founder  
**I want** collection to run on a schedule  
**So that** I wake up to fresh signals

**Acceptance:**
- Default schedule: every 6 hours UTC
- Failed source does not block other sources
- Collection run recorded with per-source counts

### US-3: Complaint classification
**As a** founder  
**I want** raw posts converted to structured complaints  
**So that** I can filter and cluster consistently

**Acceptance:**
- Each signal processed within 1 hour of ingestion (batch worker)
- Complaints store: summary, verbatim quote, category, domain, persona, severity (1–5)
- Signals with no complaint intent marked `skipped` with reason

### US-4: Opportunity generation
**As a** founder  
**I want** recurring pain surfaced as opportunity briefs  
**So that** I focus on patterns, not one-off rants

**Acceptance:**
- Clusters require ≥3 complaints in 30 days (configurable)
- Each opportunity includes: title, problem statement, target user, why now, evidence links, confidence score
- Duplicate opportunities (high embedding similarity to existing) flagged not created

### US-5: Review queue
**As a** founder  
**I want** a single inbox of new opportunities  
**So that** I can triage in one session

**Acceptance:**
- Filter by status: new, approved, rejected, deferred
- Drill down to source complaints and original URLs
- Status change persists with timestamp

---

## V1 Source List (Recommended Start)

Start narrow. Expand after pipeline stability.

| Source | Type | Identifier | Rationale |
|--------|------|------------|-----------|
| r/SaaS | Reddit (JSON API) | `SaaS` | Founders discussing tools and gaps |
| r/Entrepreneur | Reddit | `Entrepreneur` | Broad pain points |
| r/smallbusiness | Reddit | `smallbusiness` | SMB software gaps |
| r/sysadmin | Reddit | `sysadmin` | IT pain, B2B ops tools |
| HN — "wish" | HN Algolia API | `wish OR "I wish" OR "someone should build"` | Explicit build requests |
| HN — "frustrating" | HN Algolia API | `frustrating OR "hate using" OR workaround` | Implicit complaints |
| Indie Hackers RSS | RSS | `https://www.indiehackers.com/feed` | Builder community signals |

**Rate limits:** Respect Reddit (60 req/min unauthenticated), HN Algolia (reasonable backoff). Store API credentials in env vars, never in repo.

---

## LLM Usage Budget (V1)

Designed for ~200 signals/week, ~150 complaints/week, ~10 clusters/week.

| Stage | Model (suggested) | Calls/week | Est. tokens/call | Weekly cost @ GPT-4o-mini |
|-------|-------------------|------------|------------------|---------------------------|
| Complaint extraction | `gpt-4o-mini` | 200 | ~2K in / 500 out | ~$0.15 |
| Classification refine | `gpt-4o-mini` | 150 | ~1K in / 300 out | ~$0.05 |
| Cluster labeling | `gpt-4o-mini` | 10 | ~3K in / 800 out | ~$0.02 |
| Opportunity synthesis | `gpt-4o` | 10 | ~4K in / 1.5K out | ~$0.50 |
| Embeddings | `text-embedding-3-small` | 150 | ~500 tokens | ~$0.01 |

**Estimated total:** $1–5/week at V1 volume. Hard cap: env var `LLM_DAILY_BUDGET_USD=2.00` enforced in worker.

---

## Milestones

### M0 — Foundation (Week 1)
- Monorepo or two-repo layout: `web/` (Next.js), `api/` (FastAPI)
- PostgreSQL + Redis via Docker Compose locally
- Alembic migrations for core tables
- Health check endpoints

**Done when:** `docker compose up` yields healthy API and empty dashboard.

### M1 — Collection (Week 2)
- Reddit collector (subreddit new/hot posts, last 24h)
- HN Algolia collector (keyword search, last 7 days)
- RSS collector (generic parser)
- `signals` table populated; dedup verified

**Done when:** Manual trigger ingests ≥50 signals from 3 sources without duplicates on re-run.

### M2 — Classification (Week 3)
- LangGraph `classify_complaint` graph
- Batch worker: `pending` signals → complaints or `skipped`
- Classification taxonomy v1 (see below)
- Dashboard: signal list with classification status

**Done when:** ≥80% of test corpus (20 hand-labeled signals) classified acceptably.

### M3 — Clustering + Opportunities (Week 4)
- Embedding generation on complaint summaries
- HDBSCAN or pgvector cosine clustering (min cluster size 3)
- LangGraph `generate_opportunity` graph
- Opportunities linked to clusters and complaints

**Done when:** 5+ opportunities generated from real data with traceable evidence.

### M4 — Review UX + Hardening (Week 5)
- Opportunity inbox with approve/reject/defer
- Pipeline run log page
- Scheduled cron (GitHub Actions or server cron hitting API)
- Error alerting via log inspection (email deferred to V1.1)

**Done when:** Founder runs system unattended for 7 days; reviews daily inbox only.

---

## Classification Taxonomy (V1)

Fixed enum sets stored in PostgreSQL lookup tables for consistency.

### Categories
`pricing`, `integration`, `ux_ui`, `performance`, `support`, `missing_feature`, `workflow`, `data_export`, `onboarding`, `security`, `other`

### Domains
`saas_b2b`, `saas_b2c`, `ecommerce`, `devtools`, `fintech`, `healthcare`, `education`, `hr_recruiting`, `marketing`, `ops_it`, `creator_economy`, `other`

### Personas
`founder`, `developer`, `product_manager`, `ops_admin`, `marketer`, `sales`, `support_agent`, `consumer`, `other`

### Severity
1 = mild annoyance, 3 = meaningful friction, 5 = blocker / actively seeking alternative

---

## Opportunity Brief Template (V1 Output)

Each generated opportunity must populate:

```yaml
title: string                    # ≤80 chars, specific wedge
problem_statement: string        # 2–3 sentences
target_user: string              # persona + context
frequency_signal: string         # why this looks recurring (N complaints, date range)
existing_alternatives: string    # what users mention today (from evidence only)
gap: string                      # what's missing in current solutions
confidence_score: float          # 0.0–1.0, model-estimated
evidence_complaint_ids: uuid[]   # linked complaints
status: enum                       # new | approved | rejected | deferred
```

No fabricated market size or competitor names not present in source text.

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Local dev startup | < 2 min via Docker Compose |
| API p95 latency (read) | < 300ms |
| Single pipeline run (200 signals) | < 45 min wall clock |
| Data retention | Signals forever; embeddings recomputed on demand |
| Backup | Daily pg_dump to object storage (manual script OK for V1) |
| Secrets | `.env` locally; production env vars only |

---

## Deployment (V1 — Solo Founder)

**Recommended:** Single VPS (Hetzner CX22 or similar) + managed PostgreSQL (Neon/Supabase free tier) + Upstash Redis free tier.

| Component | Deployment |
|-----------|------------|
| Next.js | Vercel free tier OR same VPS via PM2 |
| FastAPI | VPS, 1 Uvicorn worker + background worker process |
| Workers | Same VPS: `arq` or `celery` consumer reading Redis queue |
| Cron | VPS crontab → `POST /api/v1/pipeline/run` with API key |
| LangGraph | In-process within FastAPI worker (no separate service) |

Total estimated cost: **$15–40/month** excluding LLM.

---

## Definition of Done (V1 Release)

- [ ] 3+ sources collecting on schedule for 7 consecutive days
- [ ] Classification pipeline clears backlog within 2 hours of ingestion
- [ ] ≥5 opportunity briefs generated with ≥3 evidence complaints each
- [ ] Founder can triage all new opportunities from dashboard
- [ ] README with setup, env vars, and runbook for failed pipeline stages
- [ ] No P0 bugs in collection dedup or opportunity evidence linkage
