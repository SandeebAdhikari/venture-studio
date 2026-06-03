# Observability documentation

Production observability for the AI Venture Studio API covers metrics, tracing, error tracking, and expanded health checks. Alerting is intentionally out of scope for this layer.

## Architecture

```
HTTP request
  └─ ObservabilityMiddleware (trace ID, HTTP metrics)
       └─ FastAPI routes / pipeline / workers
            └─ MetricsRecorder (Prometheus counters, gauges, histograms)
            └─ TracingProvider (logging or OpenTelemetry)
            └─ ErrorTracker (noop, Sentry, or OpenTelemetry)
```

## Metrics

Prometheus metrics are exposed at **`GET /metrics`** (no authentication; intended for scrape targets inside the cluster).

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `avs_pipeline_runs_total` | Counter | `status`, `trigger` | Pipeline orchestrator |
| `avs_pipeline_failures_total` | Counter | `trigger` | Failed/partial pipeline runs |
| `avs_pipeline_stage_duration_seconds` | Histogram | `stage`, `status` | Stage completion |
| `avs_pipeline_running` | Gauge | — | Active pipeline lock |
| `avs_worker_jobs_total` | Counter | `job_name`, `status` | ARQ job wrapper |
| `avs_worker_failures_total` | Counter | `job_name` | Failed ARQ jobs |
| `avs_collector_runs_total` | Counter | `source_type`, `status` | Collection service |
| `avs_collector_items_total` | Counter | `source_type`, `result` | Inserted/duplicate/skipped |
| `avs_llm_requests_total` | Counter | `graph_name`, `status` | Agent eval logging |
| `avs_llm_cost_usd_total` | Counter | `graph_name` | Agent eval logging |
| `avs_approval_requests_created_total` | Counter | `subject_type` | Approval service |
| `avs_approval_decisions_total` | Counter | `decision_type` | Approval actions |
| `avs_approval_pending_total` | Gauge | — | Synced from DB |
| `avs_approval_requests_by_status` | Gauge | `status` | Synced from DB |
| `avs_http_requests_total` | Counter | `method`, `path_template`, `status_code` | HTTP middleware |
| `avs_http_request_duration_seconds` | Histogram | `method`, `path_template` | HTTP middleware |

### Dashboard snapshot

Authenticated clients can read a JSON snapshot at **`GET /api/v1/dashboard/metrics`** for the Next.js dashboard. This aggregates pipeline run counts, worker heartbeats, scheduler state, LLM totals, and approval queue metrics.

## Tracing

Request tracing is enabled via **`ObservabilityMiddleware`**:

- Accepts incoming **`X-Trace-Id`** or generates a UUID.
- Echoes **`X-Trace-Id`** on every response.
- Emits **`http.request`** spans and structured log events.

Pipeline tracing emits:

- **`pipeline.run`** — full orchestrator execution
- **`pipeline.stage`** — each stage with retries

### Providers

| `OBSERVABILITY_TRACING_PROVIDER` | Behavior |
|----------------------------------|----------|
| `logging` (default) | Structured span start/finish logs |
| `opentelemetry` | OTLP export when optional packages are installed |

Install OpenTelemetry extras:

```bash
pip install '.[observability-opentelemetry]'
```

Configure:

```env
OBSERVABILITY_TRACING_ENABLED=true
OBSERVABILITY_TRACING_PROVIDER=opentelemetry
OTEL_EXPORTER_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAME=ai-venture-studio-api
```

## Error tracking

The **`ErrorTracker`** abstraction supports:

| `OBSERVABILITY_ERROR_TRACKING_PROVIDER` | Behavior |
|----------------------------------------|----------|
| `noop` (default) | No external reporting |
| `sentry` | Requires `sentry-sdk` and `SENTRY_DSN` |
| `opentelemetry` | Records exceptions on active OTEL spans |

Install Sentry:

```bash
pip install '.[observability-sentry]'
```

```env
OBSERVABILITY_ERROR_TRACKING_PROVIDER=sentry
SENTRY_DSN=https://example@sentry.io/123
SENTRY_TRACES_SAMPLE_RATE=0.1
```

Unhandled **`AppError`** and response validation failures are forwarded to the configured tracker.

## Health checks

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness — process is up |
| `GET /health/ready` | Readiness — dependencies available |

Readiness checks:

| Check | Pass condition |
|-------|----------------|
| `postgresql` | `SELECT 1` succeeds |
| `redis` | `PING` returns true |
| `worker` | At least one heartbeat when `WORKER_READINESS_REQUIRED=true`; otherwise optional |
| `scheduler` | Running when `SCHEDULER_ENABLED=true`; otherwise reports `disabled` |

### Worker heartbeats

ARQ workers refresh Redis keys at `observability:worker:{worker_id}` with TTL **`WORKER_HEARTBEAT_TTL_SEC`** (default 90s). Readiness uses these keys when worker availability is required.

## Configuration reference

```env
# Metrics
OBSERVABILITY_METRICS_ENABLED=true

# Tracing
OBSERVABILITY_TRACING_ENABLED=true
OBSERVABILITY_TRACING_PROVIDER=logging

# Error tracking
OBSERVABILITY_ERROR_TRACKING_PROVIDER=noop

# Readiness
WORKER_READINESS_REQUIRED=false
WORKER_HEARTBEAT_TTL_SEC=90
SCHEDULER_ENABLED=true
```

## Prometheus scrape example

```yaml
scrape_configs:
  - job_name: avs-api
    metrics_path: /metrics
    static_configs:
      - targets: ['api:8000']
```

## Testing

Observability tests live under `api/tests/observability/`:

- Metrics recording
- Tracing context
- Error tracker noop behavior
- `/metrics`, `/health/ready`, and `/api/v1/dashboard/metrics` endpoints

Run:

```bash
cd api && pytest tests/observability -q
```

## Out of scope

- Alerting rules and notification routing (PagerDuty, Slack, etc.)
- Grafana dashboard JSON (use Prometheus + dashboard metrics API as inputs)
- Log aggregation backend setup (logs remain JSON via existing logging config)
