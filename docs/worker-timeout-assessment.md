# Worker timeout assessment (`run_pipeline`)

Production Readiness Remediation **#12** — whether `arq_job_timeout_sec = 600` is appropriate for the 14-stage orchestrated pipeline.

## Execution model

| Property | Value |
|----------|--------|
| ARQ job | `run_pipeline` (single job per nightly / manual full run) |
| In-process work | `PipelineOrchestrator.run_pipeline()` — 14 sequential stages |
| Stage retries | Up to `pipeline_max_retries + 1` attempts per stage (default 4) with exponential backoff |
| ARQ retries | `arq_max_tries` (default 3) on worker crash / timeout |
| Lock TTL | `pipeline_lock_ttl_sec` = **3600** |
| Stall alert | `alert_pipeline_stall_sec` = **3600** |

## Duration evidence (code-based)

No production `pipeline_runs.duration_ms` samples are checked into the repo. Assessment uses **stage composition** and **configured upper bounds**:

| Stage | Dominant cost driver | Upper-bound signal |
|-------|----------------------|-------------------|
| `collect` | External APIs (Reddit, RSS, HN) | Minutes under rate limits |
| `classify` | LLM batches | Up to `pipeline_classify_max_batches` (100) × `classify_batch_size` (50) pending signals |
| `generate_opportunities` | LLM / clustering | Variable |
| `score_opportunities` | Scoring engine | Up to `pipeline_score_limit` (1000) records |
| `market_research` … `venture_report` (10 stages) | Agent batch LLM per opportunity | Often largest share of wall time |
| Retries | Per-stage | × up to 4 attempts with backoff |

**Conservative wall-clock estimate (full data, retries):** often **30–120+ minutes**, potentially beyond 60 minutes when classify and agent stages process large backlogs.

### Contradiction at 600 seconds

- **600 s (10 min)** is less than **one** heavy stage under load.
- **3600 s** matches `PIPELINE_LOCK_TTL_SEC` and `ALERT_PIPELINE_STALL_SEC` — the system already assumes runs may last up to an hour before stall semantics apply.
- ARQ killing `run_pipeline` at 600 s while the lock remains for 3600 s leaves a **stuck lock** and a **partial** `pipeline_runs` row until TTL expires.

## Recommendation

| Option | Verdict | Rationale |
|--------|---------|-----------|
| **Keep 600** | **Reject** | Inconsistent with lock/stall; high risk of mid-pipeline ARQ timeout on real workloads |
| **Increase** | **Accept** | Align job timeout with orchestration and observability assumptions |
| **Redesign** | **Defer** | Not justified without measured prod traces; split-stage scheduling was intentionally removed |

### Implemented default

- Code default: `arq_job_timeout_sec` **3600** (1 hour)
- Production profile in `api/.env.example`: **7200** (2 hours) when backlog / LLM volume is high

After deploy, compare `pipeline_runs.duration_ms` and ARQ `JobMonitor` durations for `run_pipeline`; raise toward 7200+ if timeouts persist.

## Heartbeats during long jobs

Worker heartbeats refresh on a background asyncio loop (`worker_heartbeat_ttl_sec // 3`, min 10 s) for the lifetime of the ARQ process. Long `run_pipeline` jobs do **not** block heartbeats unless the event loop is starved (not observed in current async stage code).

## Related

- [worker-reliability-report.md](./worker-reliability-report.md)
- [scheduler-orchestrator.md](./scheduler-orchestrator.md)
