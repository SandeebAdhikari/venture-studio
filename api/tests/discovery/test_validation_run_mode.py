"""Integration tests for discovery validation run mode (Phase 1)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.enums import (
    CategoryKind,
    CompetitorAnalysisStatus,
    CustomerResearchStatus,
    GrowthEvaluationStatus,
    GTMPlanStatus,
    HumanProxyEvaluationStatus,
    MarketResearchStatus,
    ProductStrategyStatus,
    RevenueValidationStatus,
    SourceType,
)
from app.db.models.category import Category
from app.db.models.opportunity import Opportunity
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.discovery.validation import (
    DiscoveryValidationPreflight,
    is_opportunity_validation_eligible,
    resolve_pipeline_options,
)
from app.exceptions import ValidationError
from app.pipeline.orchestrator import PipelineOrchestrator
from app.ranking.service import ExecutiveRankingService
from app.reports.venture.service import VentureReportService
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.competitor_analysis import CompetitorAnalysisCreate
from app.schemas.customer_research import CustomerResearchCreate
from app.schemas.executive_ranking import ExecutiveRankingRunCreate
from app.schemas.growth_evaluation import GrowthEvaluationCreate
from app.schemas.gtm_plan import GTMPlanCreate
from app.schemas.human_proxy_evaluation import HumanProxyEvaluationCreate
from app.schemas.market_brief import MarketBriefCreate
from app.schemas.opportunity import OpportunityCreate
from app.schemas.pipeline import PipelineRunOptions
from app.schemas.product_strategy import ProductStrategyCreate
from app.schemas.revenue_validation import RevenueValidationCreate
from app.services.container import ServiceContainer
from tests.ranking.test_executive_ranking_service import AgentScoreProfile, _seed_agent_outputs


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


async def _create_live_opportunity(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    *,
    title: str,
    llm_model: str = "gpt-4o-mini",
) -> Opportunity:
    category_id, domain_id, persona_id = taxonomy_ids
    repos = get_repositories(db_session)
    source = Source(
        name=f"validation-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url=f"https://news.ycombinator.com/item?id={abs(hash(uuid4())) % 99999999}",
        title=title,
        body="Frustrated with workflow tooling.",
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category_id,
            domain_id=domain_id,
            persona_id=persona_id,
            summary="Workflow pain.",
            verbatim_quote="Workflow pain.",
            severity=4,
            product_mentions=["ToolX"],
            llm_model="gpt-4o-mini",
            llm_confidence=0.9,
        )
    )
    return await repos.opportunities.create(
        OpportunityCreate(
            title=title,
            problem_statement="Teams struggle with workflow.",
            target_user="Ops admins",
            frequency_signal="Repeated complaints.",
            existing_alternatives="ToolX",
            gap="No lightweight workflow.",
            confidence_score=0.86,
            llm_model=llm_model,
            complaint_ids=[complaint.id],
        )
    )


async def _seed_live_agents(
    repos,
    opportunity_id: UUID,
    founder_profile_id: UUID,
    profile: AgentScoreProfile,
) -> None:
    """Same shape as test helpers but with non-mock llm_model values."""
    live = "gpt-4o-mini"
    await repos.market_briefs.create(
        MarketBriefCreate(
            opportunity_id=opportunity_id,
            status=MarketResearchStatus.COMPLETED,
            sam_usd=profile.market_sam,
            tam_usd=profile.market_sam * 4,
            industry_growth_rate_pct=profile.market_growth,
            customer_segments=[{"name": "SMB"}],
            executive_summary="Market summary.",
            llm_model=live,
        )
    )
    await repos.competitor_analyses.create(
        CompetitorAnalysisCreate(
            opportunity_id=opportunity_id,
            status=CompetitorAnalysisStatus.COMPLETED,
            evaluation_metrics={
                "differentiation_score": profile.competition_diff,
                "threat_score": profile.competition_threat,
            },
            executive_summary="Competition summary.",
            llm_model=live,
        )
    )
    await repos.customer_research.create(
        CustomerResearchCreate(
            opportunity_id=opportunity_id,
            status=CustomerResearchStatus.COMPLETED,
            pain_score=profile.pain,
            urgency_score=profile.pain,
            frequency_score=profile.pain,
            customer_sentiment="negative",
            sentiment_score=-0.4,
            cares_verdict="yes",
            validation_metrics={"validation_readiness_score": profile.pain},
            executive_summary="Customer summary.",
            llm_model=live,
        )
    )
    await repos.revenue_validations.create(
        RevenueValidationCreate(
            opportunity_id=opportunity_id,
            status=RevenueValidationStatus.COMPLETED,
            willingness_to_pay_score=profile.revenue_wtp,
            revenue_confidence_score=profile.revenue_confidence,
            evaluation_metrics={"evaluation_readiness_score": 70},
            executive_summary="Revenue summary.",
            llm_model=live,
        )
    )
    await repos.product_strategies.create(
        ProductStrategyCreate(
            opportunity_id=opportunity_id,
            status=ProductStrategyStatus.COMPLETED,
            mvp_definition="Workflow MVP for ops teams.",
            planning_metrics={"planning_readiness_score": profile.planning_readiness},
            executive_summary="Product summary.",
            llm_model=live,
        )
    )
    await repos.gtm_plans.create(
        GTMPlanCreate(
            opportunity_id=opportunity_id,
            status=GTMPlanStatus.COMPLETED,
            gtm_report="Founder-led outbound.",
            estimated_cac_usd=120.0,
            confidence_score=profile.gtm_readiness,
            ranking_metrics={"gtm_readiness_score": profile.gtm_readiness},
            executive_summary="GTM summary.",
            llm_model=live,
        )
    )
    await repos.growth_evaluations.create(
        GrowthEvaluationCreate(
            opportunity_id=opportunity_id,
            status=GrowthEvaluationStatus.COMPLETED,
            growth_score=profile.growth_readiness,
            scalability_score=profile.growth_readiness - 5,
            risk_score=40,
            evaluation_metrics={"growth_readiness_score": profile.growth_readiness},
            executive_summary="Growth summary.",
            llm_model=live,
        )
    )
    await repos.human_proxy_evaluations.create(
        HumanProxyEvaluationCreate(
            opportunity_id=opportunity_id,
            founder_profile_id=founder_profile_id,
            status=HumanProxyEvaluationStatus.COMPLETED,
            founder_fit_score=profile.founder_fit,
            feasibility_score=profile.feasibility,
            recommendation="explore",
            evaluation_metrics={
                "ranking_score": int(round(profile.founder_fit * 0.7 + profile.feasibility * 0.3))
            },
            executive_summary="Founder fit summary.",
            llm_model=live,
        )
    )


@pytest.mark.asyncio
async def test_preflight_fails_on_contaminated_db(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    await _create_live_opportunity(
        db_session,
        taxonomy_ids,
        title="E2E Approval Workflow SaaS",
        llm_model="mock-generator",
    )
    result = await DiscoveryValidationPreflight(get_repositories(db_session)).check()
    assert not result.passed
    assert any("mock" in err.lower() or "e2e" in err.lower() for err in result.errors)


@pytest.mark.asyncio
async def test_preflight_passes_on_clean_db(db_session: AsyncSession) -> None:
    mock_tables = (
        "market_briefs",
        "competitor_analyses",
        "customer_research",
        "revenue_validations",
        "product_strategies",
        "gtm_plans",
        "growth_evaluations",
        "human_proxy_evaluations",
    )
    for table in mock_tables:
        await db_session.execute(
            text(f"DELETE FROM {table} WHERE llm_model LIKE 'mock-%'")  # noqa: S608
        )
    await db_session.execute(
        text("DELETE FROM pipeline_runs WHERE config_snapshot->>'e2e_marker' IS NOT NULL")
    )
    await db_session.execute(
        text("DELETE FROM opportunities WHERE llm_model LIKE 'mock-%' OR title ILIKE '%E2E%'")
    )
    await db_session.commit()

    result = await DiscoveryValidationPreflight(get_repositories(db_session)).check()
    assert result.passed
    assert result.errors == ()


@pytest.mark.asyncio
async def test_resolve_pipeline_options_applies_validation_defaults() -> None:
    settings = Settings(api_key="test-validation-mode-key", discovery_validation_mode=False)
    opts = resolve_pipeline_options(
        PipelineRunOptions(discovery_validation_mode=True, force=False, stop_on_failure=False),
        settings,
    )
    assert opts.discovery_validation_mode is True
    assert opts.force is True
    assert opts.stop_on_failure is True


@pytest.mark.asyncio
async def test_orchestrator_preflight_raises_on_contamination(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    await _create_live_opportunity(
        db_session,
        taxonomy_ids,
        title="Mock Venture",
        llm_model="mock-generator",
    )
    repos = get_repositories(db_session)
    services = ServiceContainer(repos)
    settings = Settings(
        api_key="test-validation-mode-key",
        require_founder_approval=False,
        pipeline_max_retries=0,
    )
    orchestrator = PipelineOrchestrator(repos, services, settings)

    with pytest.raises(ValidationError, match="preflight failed"):
        await orchestrator.run_pipeline(
            options=PipelineRunOptions(
                discovery_validation_mode=True,
                stages_only=[],
            ),
        )


@pytest.mark.asyncio
async def test_ranking_excludes_mock_opportunities(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    profile = await repos.founder_profiles.get_default()
    assert profile is not None

    mock_opp = await _create_live_opportunity(
        db_session,
        taxonomy_ids,
        title="Mock Opp",
        llm_model="mock-generator",
    )
    live_opp = await _create_live_opportunity(
        db_session,
        taxonomy_ids,
        title="Live Workflow Venture",
        llm_model="gpt-4o-mini",
    )
    await _seed_agent_outputs(repos, mock_opp.id, profile.id, AgentScoreProfile())
    await _seed_live_agents(repos, live_opp.id, profile.id, AgentScoreProfile())

    pipeline_run_id = uuid4()
    settings = Settings(api_key="test-validation-mode-key", require_founder_approval=False)
    ranking_service = ExecutiveRankingService(repos, settings)
    result = await ranking_service.generate_ranking(
        discovery_validation_mode=True,
        pipeline_run_id=pipeline_run_id,
        founder_profile_id=profile.id,
    )

    ranked_ids = {entry.opportunity_id for entry in result.top_opportunities}
    assert mock_opp.id not in ranked_ids
    assert live_opp.id in ranked_ids

    loaded = await repos.executive_rankings.get_by_id_with_entries(result.ranking_run_id)
    assert loaded is not None
    assert loaded.ranking_metadata.get("pipeline_run_id") == str(pipeline_run_id)


@pytest.mark.asyncio
async def test_venture_report_rejects_stale_ranking_in_validation_mode(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    profile = await repos.founder_profiles.get_default()
    assert profile is not None

    opportunity = await _create_live_opportunity(
        db_session,
        taxonomy_ids,
        title="Live Only Venture",
    )
    await _seed_live_agents(repos, opportunity.id, profile.id, AgentScoreProfile())

    stale_run = await repos.executive_rankings.create(
        ExecutiveRankingRunCreate(
            status="completed",
            founder_profile_id=profile.id,
            top_n=5,
            opportunity_count=1,
            ranked_opportunity_count=1,
            ranking_engine="executive_ranking_v1",
            ranking_metadata={"founder_profile_name": profile.name},
            entries=[],
        )
    )

    settings = Settings(api_key="test-validation-mode-key", require_founder_approval=False)
    venture_service = VentureReportService(repos, settings)

    with pytest.raises(ValidationError, match="validation pipeline run"):
        await venture_service.generate_venture_report(
            ranking_run_id=stale_run.id,
            discovery_validation_mode=True,
            pipeline_run_id=uuid4(),
            generate_ranking_if_missing=False,
            publish=False,
        )


@pytest.mark.asyncio
async def test_venture_report_rejects_current_ranking_in_validation_mode(
    db_session: AsyncSession,
) -> None:
    repos = get_repositories(db_session)
    settings = Settings(api_key="test-validation-mode-key", require_founder_approval=False)
    venture_service = VentureReportService(repos, settings)

    with pytest.raises(ValidationError, match="stale"):
        await venture_service.generate_venture_report(
            discovery_validation_mode=True,
            pipeline_run_id=uuid4(),
            generate_ranking_if_missing=False,
            publish=False,
        )


@pytest.mark.asyncio
async def test_is_opportunity_validation_eligible_rejects_mock_artifacts(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    profile = await repos.founder_profiles.get_default()
    assert profile is not None

    opp = await _create_live_opportunity(
        db_session,
        taxonomy_ids,
        title="Looks Live",
        llm_model="gpt-4o-mini",
    )
    await _seed_agent_outputs(repos, opp.id, profile.id, AgentScoreProfile())

    assert not await is_opportunity_validation_eligible(
        repos,
        opp.id,
        founder_profile_id=profile.id,
    )
