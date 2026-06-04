"""Shared fixtures for pipeline integration tests."""

from __future__ import annotations

import pytest

from app.exceptions import ConflictError
from app.pipeline.orchestrator import PipelineOrchestrator


@pytest.fixture(autouse=True)
def _mock_pipeline_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _acquire_lock(self) -> str:
        running = await self._repos.pipelines.get_running()
        if running is not None:
            raise ConflictError(
                f"Pipeline run '{running.id}' is already in progress"
            )
        return "test-pipeline-lock-token"

    async def _release_lock(self, _token: str | None) -> None:
        return None

    monkeypatch.setattr(PipelineOrchestrator, "_acquire_lock", _acquire_lock)
    monkeypatch.setattr(PipelineOrchestrator, "_release_lock", _release_lock)


@pytest.fixture(autouse=True)
def _mock_pipeline_failure_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_alert(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(
        "app.observability.alerting.checks.alert_pipeline_failure",
        _noop_alert,
    )
