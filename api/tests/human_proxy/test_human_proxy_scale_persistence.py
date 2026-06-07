"""Tests for human proxy scale provenance persistence."""

from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytest_plugins = ["tests.human_proxy.test_human_proxy_service"]

from app.agents.human_proxy.mock_client import (
    MockHumanProxyLLMClient,
    default_mock_human_proxy_output,
)
from app.agents.human_proxy.schemas import (
    CapitalRequirementsOutput,
    ExecutionComplexityOutput,
    FounderFitAnalysisOutput,
    HumanProxyLLMOutput,
    ImplementationFeasibilityOutput,
    LearningCurveOutput,
    ProxyEvidenceOutput,
)
from app.agents.human_proxy.service import HumanProxyService
from app.config import Settings
from app.db.enums import HumanProxyEvaluationStatus
from app.db.models.founder_profile import FounderProfile
from app.repositories import get_repositories
from app.schemas.filters import HumanProxyEvaluationListFilter
from app.schemas.human_proxy_evaluation import (
    SCALE_VERSION_CENTURY_V1,
    SCALE_VERSION_LEGACY,
    HumanProxyEvaluationCreate,
    HumanProxyEvaluationRead,
)
from app.schemas.pagination import PaginationParams
from tests.human_proxy.test_human_proxy_service import _create_opportunity


def _zero_to_ten_output() -> HumanProxyLLMOutput:
    return HumanProxyLLMOutput(
        founder_fit_score=8,
        feasibility_score=7,
        recommendation="explore",
        founder_fit_analysis=FounderFitAnalysisOutput(
            score=8,
            skill_matches=["Python"],
            skill_gaps=["Mobile"],
            rationale="Moderate fit on a zero-to-ten scale.",
        ),
        implementation_feasibility=ImplementationFeasibilityOutput(
            score=7,
            build_complexity="medium",
            rationale="Buildable with familiar tooling.",
            blockers=["Compliance review"],
        ),
        learning_curve=LearningCurveOutput(
            score=4,
            difficulty="medium",
            new_skills_required=["Domain expertise"],
            rationale="Some new skills required.",
        ),
        execution_complexity=ExecutionComplexityOutput(
            score=5,
            complexity_level="medium",
            operational_burden="Moderate support load",
            rationale="Operational burden is manageable.",
        ),
        capital_requirements=CapitalRequirementsOutput(
            score=7,
            estimated_monthly_usd="$100-$300",
            bootstrap_friendly=True,
            rationale="Bootstrap-friendly spend profile.",
        ),
        supporting_evidence=[
            ProxyEvidenceOutput(
                evidence_type="skill_signal",
                excerpt="Founder skills align with the core web stack.",
                source_reference="Founder profile",
                supports_conclusion="founder_fit",
                confidence="high",
            )
        ],
        executive_summary=(
            "Moderate founder fit on a zero-to-ten scale with manageable feasibility "
            "and execution complexity for a solo technical founder."
        ),
    )


@pytest.fixture
async def default_founder_profile(db_session) -> FounderProfile:
    from sqlalchemy import select

    profile = await db_session.scalar(
        select(FounderProfile).where(FounderProfile.is_default.is_(True))
    )
    assert profile is not None
    return profile


@pytest.mark.asyncio
async def test_service_persists_century_v1_for_normalized_evaluation(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockHumanProxyLLMClient([default_mock_human_proxy_output()])
    service = HumanProxyService(repos, human_proxy_settings, llm_client=mock)

    result = await service.evaluate_opportunity(opportunity.id)

    assert result.status == "completed"
    evaluation = await repos.human_proxy_evaluations.get_by_id_with_evidence(
        result.human_proxy_evaluation_id
    )
    assert evaluation is not None
    assert evaluation.scale_version == SCALE_VERSION_CENTURY_V1
    assert evaluation.scale_metadata == {
        "scale_detected": "century",
        "scale_factor": 1,
    }
    assert "scale_metadata" not in evaluation.proxy_metadata


@pytest.mark.asyncio
async def test_service_persists_zero_to_ten_scale_metadata(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockHumanProxyLLMClient([_zero_to_ten_output()])
    service = HumanProxyService(repos, human_proxy_settings, llm_client=mock)

    result = await service.evaluate_opportunity(opportunity.id)

    assert result.status == "completed"
    evaluation = await repos.human_proxy_evaluations.get_by_id_with_evidence(
        result.human_proxy_evaluation_id
    )
    assert evaluation is not None
    assert evaluation.scale_version == SCALE_VERSION_CENTURY_V1
    assert evaluation.scale_metadata["scale_detected"] == "zero_to_ten"
    assert evaluation.scale_metadata["scale_factor"] == 10
    assert evaluation.founder_fit_score == 80
    assert evaluation.feasibility_score == 70


@pytest.mark.asyncio
async def test_repository_defaults_legacy_scale_version(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    default_founder_profile: FounderProfile,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)

    entity = await repos.human_proxy_evaluations.create(
        HumanProxyEvaluationCreate(
            opportunity_id=opportunity.id,
            founder_profile_id=default_founder_profile.id,
            status=HumanProxyEvaluationStatus.COMPLETED,
            founder_fit_score=72,
            feasibility_score=68,
            recommendation="explore",
            evaluation_metrics={"ranking_score": 70},
            llm_model="mock-human-proxy",
        )
    )

    assert entity.scale_version == SCALE_VERSION_LEGACY
    assert entity.scale_metadata == {}


@pytest.mark.asyncio
async def test_scale_metadata_round_trips_through_read_schema(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    default_founder_profile: FounderProfile,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    metadata = {
        "scale_detected": "zero_to_ten",
        "scale_factor": 10,
        "fields_corrected": ["founder_fit_score", "feasibility_score"],
    }

    entity = await repos.human_proxy_evaluations.create(
        HumanProxyEvaluationCreate(
            opportunity_id=opportunity.id,
            founder_profile_id=default_founder_profile.id,
            status=HumanProxyEvaluationStatus.COMPLETED,
            founder_fit_score=80,
            feasibility_score=70,
            recommendation="explore",
            evaluation_metrics={"ranking_score": 75},
            llm_model="mock-human-proxy",
            scale_version=SCALE_VERSION_CENTURY_V1,
            scale_metadata=metadata,
        )
    )

    read = HumanProxyEvaluationRead.from_entity(entity)
    assert read.scale_version == SCALE_VERSION_CENTURY_V1
    assert read.scale_metadata == metadata

    loaded = await repos.human_proxy_evaluations.get_by_id_with_evidence(entity.id)
    assert loaded is not None
    assert loaded.scale_version == SCALE_VERSION_CENTURY_V1
    assert loaded.scale_metadata == metadata


@pytest.mark.asyncio
async def test_existing_list_filters_continue_working(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockHumanProxyLLMClient([default_mock_human_proxy_output()])
    service = HumanProxyService(repos, human_proxy_settings, llm_client=mock)
    await service.evaluate_opportunity(opportunity.id)

    filters = HumanProxyEvaluationListFilter(
        opportunity_id=opportunity.id,
        min_founder_fit_score=80,
        min_feasibility_score=70,
        min_ranking_score=1,
        is_current=True,
    )
    items = await repos.human_proxy_evaluations.list_filtered(filters, limit=10, offset=0)
    total = await repos.human_proxy_evaluations.count_filtered(filters)

    assert total == 1
    assert len(items) == 1
    assert items[0].scale_version == SCALE_VERSION_CENTURY_V1

    page = await service.list_evaluations(filters, PaginationParams(limit=10, offset=0))
    assert page.total == 1
    assert page.items[0].scale_version == SCALE_VERSION_CENTURY_V1
