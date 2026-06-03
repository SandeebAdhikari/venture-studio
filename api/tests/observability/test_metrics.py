"""Tests for Prometheus metrics recording."""

from prometheus_client import REGISTRY

from app.observability.metrics import MetricsRecorder, configure_metrics
from app.observability.setup import init_observability


def _metric_value(name: str, labels: dict[str, str]) -> float:
    for metric in REGISTRY.collect():
        if metric.name != name:
            continue
        for sample in metric.samples:
            if sample.labels == labels and sample.name.endswith("_total"):
                return sample.value
            if sample.labels == labels and not sample.name.endswith("_created"):
                return sample.value
    return 0.0


def test_record_pipeline_and_worker_metrics() -> None:
    configure_metrics(type("S", (), {"observability_metrics_enabled": True})())
    recorder = MetricsRecorder()

    recorder.record_pipeline_run(status="completed", trigger="api")
    recorder.record_worker_job(job_name="collect", status="completed")
    recorder.record_worker_job(job_name="collect", status="failed")
    recorder.record_llm_request(graph_name="classification", status="success", cost_usd=0.01)

    assert _metric_value("avs_pipeline_runs", {"status": "completed", "trigger": "api"}) >= 1
    assert _metric_value("avs_worker_jobs", {"job_name": "collect", "status": "completed"}) >= 1
    assert _metric_value("avs_worker_failures", {"job_name": "collect"}) >= 1
    assert (
        _metric_value("avs_llm_requests", {"graph_name": "classification", "status": "success"})
        >= 1
    )


def test_init_observability_is_idempotent(monkeypatch) -> None:
    monkeypatch.setenv("OBSERVABILITY_METRICS_ENABLED", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    init_observability(get_settings())
    init_observability(get_settings())
    get_settings.cache_clear()
