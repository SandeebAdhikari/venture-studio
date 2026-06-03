"""Integration tests for the pipeline orchestrator."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.collection.collectors.registry import clear_collectors, register_collector
from app.collection.schemas import RawComplaintInput
from app.config import Settings
from app.db.enums import PipelineRunStatus, PipelineStage, PipelineStageStatus, SourceType
from app.db.models.pipeline_run import PipelineRun
from app.db.models.source import Source
from app.exceptions import ConflictError
from app.pipeline.orchestrator import PipelineOrchestrator
from app.repositories import get_repositories
from app.schemas.pipeline import PipelineRunOptions
from app.services.container import ServiceContainer


class _StaticCollector:
    def __init__(self, items: list[RawComplaintInput]) -> None:
        self._items = items

    async def fetch(self, _source: Source) -> list[RawComplaintInput]:
        return self._items


@pytest.fixture(autouse=True)
def _reset_collectors():
    clear_collectors()
    yield
    clear_collectors()


@pytest.fixture
def pipeline_settings() -> Settings:
    return Settings(
        api_key="test-pipeline-api-key",
        pipeline_max_retries=2,
        pipeline_retry_backoff_sec=0.01,
        pipeline_classify_max_batches=5,
    )


@pytest.fixture
async def enabled_source(db_session: AsyncSession) -> Source:
    source = Source(
        name=f"pipeline-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()
    return source


def _build_orchestrator(db_session: AsyncSession, settings: Settings) -> PipelineOrchestrator:
    repos = get_repositories(db_session)
    services = ServiceContainer(repos)
    services.classification = services.classification  # ensure wired
    return PipelineOrchestrator(repos, services, settings)


async def test_collect_stage_with_registered_collector(
    db_session: AsyncSession,
    enabled_source: Source,
    pipeline_settings: Settings,
):
    register_collector(
        SourceType.REDDIT.value,
        _StaticCollector(
            [
                RawComplaintInput(
                    external_id=f"ext-{uuid4()}",
                    url=f"https://example.com/{uuid4()}",
                    title="Tool is too expensive",
                    body="We cannot afford this SaaS product at our stage. It blocks our workflow daily.",
                )
            ]
        ),
    )

    orchestrator = _build_orchestrator(db_session, pipeline_settings)
    result = await orchestrator.run_pipeline(
        options=PipelineRunOptions(stages_only=[PipelineStage.COLLECT]),
    )

    assert result.status == PipelineRunStatus.COMPLETED
    assert result.stages_completed == 1

    detail = await orchestrator.get_run(result.pipeline_run_id)
    collect_stage = detail.stage_runs[0]
    assert collect_stage.stage == PipelineStage.COLLECT
    assert collect_stage.status == PipelineStageStatus.COMPLETED
    assert collect_stage.items_out == 1


async def test_skip_stages_marks_skipped(
    db_session: AsyncSession,
    pipeline_settings: Settings,
):
    orchestrator = _build_orchestrator(db_session, pipeline_settings)
    skip = [stage for stage in PipelineStage if stage != PipelineStage.COLLECT]
    result = await orchestrator.run_pipeline(
        options=PipelineRunOptions(
            stages_only=[PipelineStage.COLLECT],
            skip_stages=skip,
        ),
    )

    assert result.stages_skipped == 0
    assert result.stages_completed == 1

    detail = await orchestrator.get_run(result.pipeline_run_id)
    assert len(detail.stage_runs) == 1


async def test_running_pipeline_blocks_concurrent_run(
    db_session: AsyncSession,
    pipeline_settings: Settings,
):
    running = PipelineRun(
        trigger="api",
        status=PipelineRunStatus.RUNNING.value,
    )
    db_session.add(running)
    await db_session.flush()

    orchestrator = _build_orchestrator(db_session, pipeline_settings)
    with pytest.raises(ConflictError):
        await orchestrator.run_pipeline(
            options=PipelineRunOptions(stages_only=[PipelineStage.COLLECT]),
        )


async def test_stage_retry_then_success(
    db_session: AsyncSession,
    pipeline_settings: Settings,
    monkeypatch,
):
    orchestrator = _build_orchestrator(db_session, pipeline_settings)
    attempts = {"count": 0}

    async def flaky_execute(stage, opts):
        from app.pipeline.schemas import StageExecutionResult

        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient failure")
        return StageExecutionResult(items_out=1, records_processed=1)

    monkeypatch.setattr(orchestrator._executor, "execute", flaky_execute)

    result = await orchestrator.run_pipeline(
        options=PipelineRunOptions(stages_only=[PipelineStage.COLLECT]),
    )

    assert result.status == PipelineRunStatus.COMPLETED
    assert attempts["count"] == 2

    detail = await orchestrator.get_run(result.pipeline_run_id)
    assert detail.stage_runs[0].attempt == 2
    assert any(entry["event"] == "stage_retry" for entry in detail.audit_trail)


async def test_stop_on_failure_produces_partial_run(
    db_session: AsyncSession,
    pipeline_settings: Settings,
    monkeypatch,
):
    orchestrator = _build_orchestrator(db_session, pipeline_settings)

    async def failing_execute(stage, opts):
        from app.pipeline.schemas import StageExecutionResult

        if stage == PipelineStage.CLASSIFY:
            return StageExecutionResult(failed=True, error="classify boom")
        return StageExecutionResult(items_out=0)

    monkeypatch.setattr(orchestrator._executor, "execute", failing_execute)

    result = await orchestrator.run_pipeline(
        options=PipelineRunOptions(
            stages_only=[
                PipelineStage.COLLECT,
                PipelineStage.CLASSIFY,
                PipelineStage.GENERATE_OPPORTUNITIES,
            ],
            stop_on_failure=True,
        ),
    )

    assert result.status == PipelineRunStatus.PARTIAL
    assert result.stages_failed == 1
    assert result.stages_skipped >= 1

    detail = await orchestrator.get_run(result.pipeline_run_id)
    assert any(entry["event"] == "stage_failed" for entry in detail.audit_trail)


async def test_list_and_get_pipeline_runs(
    db_session: AsyncSession,
    pipeline_settings: Settings,
):
    from app.schemas.pagination import PaginationParams

    orchestrator = _build_orchestrator(db_session, pipeline_settings)
    run = await orchestrator.run_pipeline(
        options=PipelineRunOptions(stages_only=[PipelineStage.COLLECT]),
    )

    listing = await orchestrator.list_runs(PaginationParams(limit=10, offset=0))
    assert listing.total >= 1
    assert any(item.id == run.pipeline_run_id for item in listing.items)

    detail = await orchestrator.get_run(run.pipeline_run_id)
    assert detail.id == run.pipeline_run_id
    assert len(detail.stage_runs) == 1
