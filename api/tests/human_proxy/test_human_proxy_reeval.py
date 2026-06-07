"""Tests for HP-REEVAL-1 legacy human proxy re-evaluation."""

from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.human_proxy.mock_client import (
    MockHumanProxyLLMClient,
    default_mock_human_proxy_output,
)
from app.agents.human_proxy.service import HumanProxyService
from app.config import Settings
from app.db.models.human_proxy_evaluation import HumanProxyEvaluation
from app.repositories import get_repositories
from app.schemas.human_proxy_evaluation import (
    SCALE_VERSION_CENTURY_V1,
    SCALE_VERSION_LEGACY,
    HumanProxyEvaluationCreate,
)
from tests.human_proxy.test_human_proxy_service import (
    _create_opportunity,
    human_proxy_settings,
)

pytest_plugins = ["tests.human_proxy.test_human_proxy_service"]


@pytest.fixture
async def default_founder_profile(db_session: AsyncSession):
    from app.db.models.founder_profile import FounderProfile

    profile = await db_session.scalar(
        select(FounderProfile).where(FounderProfile.is_default.is_(True))
    )
    assert profile is not None
    return profile


async def _seed_legacy_evaluation(
    repos,
    *,
    opportunity_id: UUID,
    founder_profile_id: UUID,
) -> HumanProxyEvaluation:
    return await repos.human_proxy_evaluations.create(
        HumanProxyEvaluationCreate(
            opportunity_id=opportunity_id,
            founder_profile_id=founder_profile_id,
            founder_fit_score=8,
            feasibility_score=7,
            recommendation="explore",
            evaluation_metrics={"ranking_score": 24},
            llm_model="mock-human-proxy",
            scale_version=SCALE_VERSION_LEGACY,
            scale_metadata={},
        )
    )


@pytest.mark.asyncio
async def test_reevaluate_current_creates_century_v1_and_preserves_history(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    default_founder_profile,
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    legacy = await _seed_legacy_evaluation(
        repos,
        opportunity_id=opportunity.id,
        founder_profile_id=default_founder_profile.id,
    )

    mock = MockHumanProxyLLMClient([default_mock_human_proxy_output()])
    service = HumanProxyService(repos, human_proxy_settings, llm_client=mock)
    result = await service.reevaluate_current(
        legacy_only=True,
        opportunity_ids=[opportunity.id],
    )

    assert result.targets_identified == 1
    assert result.completed == 1
    assert result.failed == 0

    await db_session.refresh(legacy)
    assert legacy.is_current is False
    assert legacy.scale_version == SCALE_VERSION_LEGACY

    current = await repos.human_proxy_evaluations.get_current_for_opportunity(
        opportunity.id,
        founder_profile_id=default_founder_profile.id,
    )
    assert current is not None
    assert current.id != legacy.id
    assert current.is_current is True
    assert current.version == 2
    assert current.scale_version == SCALE_VERSION_CENTURY_V1
    assert current.scale_metadata["scale_detected"] in {"century", "zero_to_ten"}
    assert current.founder_fit_score >= 60
    assert current.proxy_metadata["reeval"] == "hp_reeval_1"
    assert current.proxy_metadata["supersedes_evaluation_id"] == str(legacy.id)

    total = await db_session.scalar(
        select(func.count())
        .select_from(HumanProxyEvaluation)
        .where(HumanProxyEvaluation.opportunity_id == opportunity.id)
    )
    assert total == 2


@pytest.mark.asyncio
async def test_reevaluate_current_skips_century_v1_when_legacy_only(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    default_founder_profile,
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockHumanProxyLLMClient([default_mock_human_proxy_output()])
    service = HumanProxyService(repos, human_proxy_settings, llm_client=mock)

    await service.evaluate_opportunity(opportunity.id)

    result = await service.reevaluate_current(
        legacy_only=True,
        opportunity_ids=[opportunity.id],
    )

    assert result.targets_identified == 0
    assert result.skipped_century_v1 == 1
    assert result.completed == 0

    total = await db_session.scalar(
        select(func.count())
        .select_from(HumanProxyEvaluation)
        .where(HumanProxyEvaluation.opportunity_id == opportunity.id)
    )
    assert total == 1


@pytest.mark.asyncio
async def test_reevaluate_current_dry_run_does_not_create_rows(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    default_founder_profile,
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    await _seed_legacy_evaluation(
        repos,
        opportunity_id=opportunity.id,
        founder_profile_id=default_founder_profile.id,
    )

    service = HumanProxyService(
        repos,
        human_proxy_settings,
        llm_client=MockHumanProxyLLMClient([]),
    )
    result = await service.reevaluate_current(
        dry_run=True,
        opportunity_ids=[opportunity.id],
    )

    assert result.dry_run is True
    assert result.targets_identified == 1
    assert result.skipped == 1
    assert result.completed == 0

    total = await db_session.scalar(
        select(func.count())
        .select_from(HumanProxyEvaluation)
        .where(HumanProxyEvaluation.opportunity_id == opportunity.id)
    )
    assert total == 1
