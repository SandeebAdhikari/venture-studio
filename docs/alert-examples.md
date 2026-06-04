# Example alert payloads

Webhook delivery uses JSON from `Alert.to_payload()`. Slack uses a formatted `text` field derived from the same alert.

Fields: `alert_type`, `severity`, `title`, `message`, `dedup_key`, `fired_at` (ISO-8601 UTC), `context`.

## worker_offline

```json
{
  "alert_type": "worker_offline",
  "severity": "critical",
  "title": "Worker offline",
  "message": "No active ARQ worker heartbeats detected",
  "dedup_key": "global",
  "fired_at": "2026-06-03T14:00:00+00:00",
  "context": {"component": "worker"}
}
```

## scheduler_offline

```json
{
  "alert_type": "scheduler_offline",
  "severity": "critical",
  "title": "Scheduler offline",
  "message": "APScheduler is enabled but not running",
  "dedup_key": "global",
  "fired_at": "2026-06-03T14:00:00+00:00",
  "context": {"component": "scheduler"}
}
```

## pipeline_failure

```json
{
  "alert_type": "pipeline_failure",
  "severity": "critical",
  "title": "Pipeline failed",
  "message": "classify stage error",
  "dedup_key": "550e8400-e29b-41d4-a716-446655440000",
  "fired_at": "2026-06-03T14:00:00+00:00",
  "context": {
    "pipeline_run_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "failed",
    "trigger": "scheduler"
  }
}
```

## pipeline_stall

```json
{
  "alert_type": "pipeline_stall",
  "severity": "warning",
  "title": "Pipeline stall detected",
  "message": "Pipeline run 550e8400-e29b-41d4-a716-446655440000 has been running for at least 3600s (started 2026-06-03T12:00:00+00:00)",
  "dedup_key": "550e8400-e29b-41d4-a716-446655440000",
  "fired_at": "2026-06-03T14:00:00+00:00",
  "context": {
    "pipeline_run_id": "550e8400-e29b-41d4-a716-446655440000",
    "stall_sec": 3600,
    "started_at": "2026-06-03T12:00:00+00:00"
  }
}
```

## queue_backlog_growth

```json
{
  "alert_type": "queue_backlog_growth",
  "severity": "warning",
  "title": "ARQ queue backlog growing",
  "message": "Queue depth 20 increased by 10 (previous 10)",
  "dedup_key": "global",
  "fired_at": "2026-06-03T14:00:00+00:00",
  "context": {"queue_depth": 20, "previous_depth": 10, "delta": 10}
}
```

## collector_repeated_failure

```json
{
  "alert_type": "collector_repeated_failure",
  "severity": "warning",
  "title": "Repeated collector failures",
  "message": "Source 'HN Front Page' (hn_algolia) failed 3 times in a row: timeout",
  "dedup_key": "660e8400-e29b-41d4-a716-446655440001",
  "fired_at": "2026-06-03T14:00:00+00:00",
  "context": {
    "source_id": "660e8400-e29b-41d4-a716-446655440001",
    "source_name": "HN Front Page",
    "source_type": "hn_algolia",
    "failure_count": 3,
    "last_error": "timeout"
  }
}
```

## llm_budget_exhausted

Threshold (75%):

```json
{
  "alert_type": "llm_budget_exhausted",
  "severity": "warning",
  "title": "LLM budget at 75%",
  "message": "Daily LLM spend $1.5000 reached 75% of budget $2.00",
  "dedup_key": "threshold:75",
  "fired_at": "2026-06-03T14:00:00+00:00",
  "context": {"spent_usd": 1.5, "budget_usd": 2.0, "threshold_pct": 75}
}
```

Exhausted:

```json
{
  "alert_type": "llm_budget_exhausted",
  "severity": "critical",
  "title": "LLM budget exhausted",
  "message": "Daily LLM budget exceeded: spent $2.1000 of $2.00",
  "dedup_key": "exhausted",
  "fired_at": "2026-06-03T14:00:00+00:00",
  "context": {"spent_usd": 2.1, "budget_usd": 2.0}
}
```

## Test delivery

`POST /api/v1/observability/alerts/test` sends an INFO-level test using type `worker_offline` with `context.test=true` and bypasses cooldown.
