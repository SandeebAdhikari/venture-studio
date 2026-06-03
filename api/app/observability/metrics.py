"""Prometheus metrics definitions and recording helpers."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

from app.config import Settings

_metrics_enabled = True

PIPELINE_RUNS = Counter(
    "avs_pipeline_runs_total",
    "Total pipeline runs",
    ["status", "trigger"],
)
PIPELINE_FAILURES = Counter(
    "avs_pipeline_failures_total",
    "Pipeline runs that ended with failures",
    ["trigger"],
)
STAGE_DURATION = Histogram(
    "avs_pipeline_stage_duration_seconds",
    "Pipeline stage execution duration",
    ["stage", "status"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, float("inf")),
)
PIPELINE_RUNNING = Gauge(
    "avs_pipeline_running",
    "Whether a pipeline run is currently in progress (1=yes, 0=no)",
)
WORKER_JOBS = Counter(
    "avs_worker_jobs_total",
    "Background worker job executions",
    ["job_name", "status"],
)
WORKER_FAILURES = Counter(
    "avs_worker_failures_total",
    "Background worker job failures",
    ["job_name"],
)
COLLECTOR_RUNS = Counter(
    "avs_collector_runs_total",
    "Collector execution outcomes per source type",
    ["source_type", "status"],
)
COLLECTOR_ITEMS = Counter(
    "avs_collector_items_total",
    "Items processed during collection",
    ["source_type", "result"],
)
LLM_REQUESTS = Counter(
    "avs_llm_requests_total",
    "LLM API requests",
    ["graph_name", "status"],
)
LLM_COST_USD = Counter(
    "avs_llm_cost_usd_total",
    "Estimated LLM spend in USD",
    ["graph_name"],
)
APPROVAL_CREATED = Counter(
    "avs_approval_requests_created_total",
    "Approval requests created",
    ["subject_type"],
)
APPROVAL_DECISIONS = Counter(
    "avs_approval_decisions_total",
    "Approval decisions recorded",
    ["decision_type"],
)
APPROVAL_PENDING = Gauge(
    "avs_approval_pending_total",
    "Approval requests awaiting founder action",
)
APPROVAL_BY_STATUS = Gauge(
    "avs_approval_requests_by_status",
    "Approval requests grouped by status",
    ["status"],
)
HTTP_REQUESTS = Counter(
    "avs_http_requests_total",
    "HTTP requests handled by the API",
    ["method", "path_template", "status_code"],
)
HTTP_REQUEST_DURATION = Histogram(
    "avs_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path_template"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
)


def metrics_enabled() -> bool:
    return _metrics_enabled


def configure_metrics(settings: Settings) -> None:
    global _metrics_enabled
    _metrics_enabled = settings.observability_metrics_enabled


class MetricsRecorder:
    """Thin facade over Prometheus counters, gauges, and histograms."""

    def record_pipeline_run(self, *, status: str, trigger: str) -> None:
        if not _metrics_enabled:
            return
        PIPELINE_RUNS.labels(status=status, trigger=trigger).inc()
        if status in {"failed", "partial"}:
            PIPELINE_FAILURES.labels(trigger=trigger).inc()

    def set_pipeline_running(self, running: bool) -> None:
        if not _metrics_enabled:
            return
        PIPELINE_RUNNING.set(1 if running else 0)

    def record_stage_duration(self, *, stage: str, status: str, duration_ms: int | None) -> None:
        if not _metrics_enabled or duration_ms is None:
            return
        STAGE_DURATION.labels(stage=stage, status=status).observe(duration_ms / 1000.0)

    def record_worker_job(self, *, job_name: str, status: str) -> None:
        if not _metrics_enabled:
            return
        WORKER_JOBS.labels(job_name=job_name, status=status).inc()
        if status == "failed":
            WORKER_FAILURES.labels(job_name=job_name).inc()

    def record_collector_run(self, *, source_type: str, status: str) -> None:
        if not _metrics_enabled:
            return
        COLLECTOR_RUNS.labels(source_type=source_type, status=status).inc()

    def record_collector_items(
        self,
        *,
        source_type: str,
        inserted: int = 0,
        duplicates: int = 0,
        skipped: int = 0,
    ) -> None:
        if not _metrics_enabled:
            return
        if inserted:
            COLLECTOR_ITEMS.labels(source_type=source_type, result="inserted").inc(inserted)
        if duplicates:
            COLLECTOR_ITEMS.labels(source_type=source_type, result="duplicate").inc(duplicates)
        if skipped:
            COLLECTOR_ITEMS.labels(source_type=source_type, result="skipped").inc(skipped)

    def record_llm_request(
        self,
        *,
        graph_name: str,
        status: str,
        cost_usd: float | None = None,
    ) -> None:
        if not _metrics_enabled:
            return
        LLM_REQUESTS.labels(graph_name=graph_name, status=status).inc()
        if cost_usd:
            LLM_COST_USD.labels(graph_name=graph_name).inc(cost_usd)

    def record_approval_created(self, *, subject_type: str) -> None:
        if not _metrics_enabled:
            return
        APPROVAL_CREATED.labels(subject_type=subject_type).inc()

    def record_approval_decision(self, *, decision_type: str) -> None:
        if not _metrics_enabled:
            return
        APPROVAL_DECISIONS.labels(decision_type=decision_type).inc()

    def sync_approval_gauges(self, counts_by_status: dict[str, int]) -> None:
        if not _metrics_enabled:
            return
        pending = counts_by_status.get("pending", 0) + counts_by_status.get(
            "research_requested", 0
        )
        APPROVAL_PENDING.set(pending)
        for status, count in counts_by_status.items():
            APPROVAL_BY_STATUS.labels(status=status).set(count)

    def record_http_request(
        self,
        *,
        method: str,
        path_template: str,
        status_code: int,
        duration_sec: float,
    ) -> None:
        if not _metrics_enabled:
            return
        HTTP_REQUESTS.labels(
            method=method,
            path_template=path_template,
            status_code=str(status_code),
        ).inc()
        HTTP_REQUEST_DURATION.labels(method=method, path_template=path_template).observe(
            duration_sec
        )


_recorder = MetricsRecorder()


def record_metrics() -> MetricsRecorder:
    return _recorder
