"""Integration tests for human proxy service."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.human_proxy.mock_client import (
    MockHumanProxyLLMClient,
    default_mock_human_proxy_output,
)
from app.agents.human_proxy.service import HumanProxyService
from app.config import Settings
from app.db.enums import CategoryKind, HumanProxyEvaluationStatus, SourceType
from app.db.models.category import Category
from app.db.models.founder_profile import FounderProfile
from app.db.models.human_proxy_evaluation import HumanProxyEvaluation
from app.db.models.human_proxy_evaluation_evidence import HumanProxyEvaluationEvidence
from app.db.models.llm_call import LLMCall
from app.db.models.opportunity import Opportunity
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.founder_profile import FounderProfileCreate
from app.schemas.opportunity import OpportunityCreate

QUOTE = "Staff scheduling breaks every week when employees swap shifts without notice."


@pytest.fixture
def human_proxy_settings() -> Settings:
    return Settings(
        api_key="test-api-key-for-human-proxy",
        human_proxy_model="mock-human-proxy",
        human_proxy_max_retries=2,
    )


@pytest.fixture
async def taxonomy_ids(db_session: AsyncSession) -> tuple[UUID, UUID, UUID]:
    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None
    return category.id, domain.id, persona.id


async def _create_opportunity(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> Opportunity:
    category_id, domain_id, persona_id = taxonomy_ids
    source = Source(
        name=f"human-proxy-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url=f"https://example.com/posts/{uuid4()}",
        title="Scheduling pain",
        body=QUOTE,
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category_id,
            domain_id=domain_id,
            persona_id=persona_id,
            summary="Staff scheduling chaos from last-minute shift changes.",
            verbatim_quote=QUOTE,
            severity=4,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )

    return await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Ops teams struggle with hourly staff scheduling.",
            target_user="Ops admins at multi-location service businesses",
            frequency_signal="Multiple complaints mention scheduling coordination pain.",
            existing_alternatives="Teams mention ShiftApp and spreadsheets.",
            gap="No lightweight scheduling workflow for hourly staff.",
            confidence_score=0.86,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )


@pytest.mark.asyncio
async def test_evaluate_opportunity_persists_scores_and_evidence(
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
    assert result.human_proxy_evaluation_id is not None
    assert result.draft is not None
    assert result.draft.founder_fit_score == 82
    assert result.draft.feasibility_score == 76
    assert result.draft.recommendation == "pursue"
    assert result.draft.evaluation_metrics["ranking_score"] > 0

    evaluation = await repos.human_proxy_evaluations.get_by_id_with_evidence(
        result.human_proxy_evaluation_id
    )
    assert evaluation is not None
    assert evaluation.status == HumanProxyEvaluationStatus.COMPLETED.value
    assert evaluation.is_current is True
    assert len(evaluation.evidence) == 3
    assert evaluation.evidence[1].complaint_id is not None


@pytest.mark.asyncio
async def test_evaluate_opportunity_skips_when_already_evaluated(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockHumanProxyLLMClient([default_mock_human_proxy_output()])
    service = HumanProxyService(repos, human_proxy_settings, llm_client=mock)

    first = await service.evaluate_opportunity(opportunity.id)
    second = await service.evaluate_opportunity(opportunity.id)

    assert first.status == "completed"
    assert second.status == "skipped"
    assert second.skip_reason == "already_evaluated"
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_evaluate_pending_processes_unevaluated_opportunities(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockHumanProxyLLMClient([default_mock_human_proxy_output()])
    service = HumanProxyService(repos, human_proxy_settings, llm_client=mock)

    batch = await service.evaluate_pending(limit=10)

    assert batch.completed >= 1
    assert batch.items[0].opportunity_id == opportunity.id


@pytest.mark.asyncio
async def test_evaluate_logs_llm_calls(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockHumanProxyLLMClient([default_mock_human_proxy_output()])
    service = HumanProxyService(repos, human_proxy_settings, llm_client=mock)

    await service.evaluate_opportunity(opportunity.id)

    count = await db_session.scalar(
        select(func.count())
        .select_from(LLMCall)
        .where(
            LLMCall.entity_id == opportunity.id,
            LLMCall.graph_name == "evaluate_human_proxy",
        )
    )
    assert count == 1


@pytest.mark.asyncio
async def test_evaluate_retries_malformed_response(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockHumanProxyLLMClient([None, default_mock_human_proxy_output()])
    service = HumanProxyService(repos, human_proxy_settings, llm_client=mock)

    result = await service.evaluate_opportunity(opportunity.id)

    assert result.status == "completed"
    assert mock.call_count == 2

    total_evaluations = await db_session.scalar(select(func.count()).select_from(HumanProxyEvaluation))
    total_evidence = await db_session.scalar(
        select(func.count()).select_from(HumanProxyEvaluationEvidence)
    )
    assert total_evaluations == 1
    assert total_evidence == 3


@pytest.mark.asyncio
async def test_create_profile_and_evaluate_with_custom_profile(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockHumanProxyLLMClient([default_mock_human_proxy_output()])
    service = HumanProxyService(repos, human_proxy_settings, llm_client=mock)

    profile = await service.create_profile(
        FounderProfileCreate(
            name="Custom Founder",
            skills=["React", "Node.js"],
            constraints={"team_size": "solo"},
        )
    )

    result = await service.evaluate_opportunity(opportunity.id, founder_profile_id=profile.id)

    assert result.status == "completed"
    assert result.founder_profile_id == profile.id

    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None
    assert default_profile.id != profile.id


@pytest.mark.asyncio
async def test_list_history_returns_versions(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    human_proxy_settings: Settings,
) -> None:
    opportunity = await _create_opportunity(db_session, taxonomy_ids)
    repos = get_repositories(db_session)
    mock = MockHumanProxyLLMClient(
        [default_mock_human_proxy_output(), default_mock_human_proxy_output()]
    )
    service = HumanProxyService(repos, human_proxy_settings, llm_client=mock)

    await service.evaluate_opportunity(opportunity.id)
    await service.evaluate_opportunity(opportunity.id, force=True)

    history = await service.list_history(opportunity.id)
    assert len(history) == 2
    assert history[0].version > history[1].version

    default_profile = await db_session.scalar(
        select(FounderProfile).where(FounderProfile.is_default.is_(True))
    )
    assert default_profile is not None
