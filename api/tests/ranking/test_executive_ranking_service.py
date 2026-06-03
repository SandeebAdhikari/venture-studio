"""Integration tests for executive ranking service."""

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.db.models.executive_ranking_run import ExecutiveRankingRun
from app.db.models.opportunity import Opportunity
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.ranking.service import ExecutiveRankingService
from app.repositories import get_repositories
from app.schemas.competitor_analysis import CompetitorAnalysisCreate
from app.schemas.customer_research import CustomerResearchCreate
from app.schemas.growth_evaluation import GrowthEvaluationCreate
from app.schemas.gtm_plan import GTMPlanCreate
from app.schemas.human_proxy_evaluation import HumanProxyEvaluationCreate
from app.schemas.market_brief import MarketBriefCreate
from app.schemas.opportunity import OpportunityCreate
from app.schemas.pagination import PaginationParams
from app.schemas.product_strategy import ProductStrategyCreate
from app.schemas.revenue_validation import RevenueValidationCreate


@dataclass
class AgentScoreProfile:
    pain: int = 70
    market_sam: float = 25_000_000
    market_growth: float = 10
    revenue_wtp: int = 72
    revenue_confidence: int = 68
    competition_diff: float = 0.7
    competition_threat: float = 0.3
    growth_readiness: int = 74
    gtm_readiness: int = 70
    founder_fit: int = 80
    feasibility: int = 76
    planning_readiness: int = 71


@pytest.fixture
async def taxonomy_ids(db_session: AsyncSession) -> tuple[UUID, UUID, UUID]:
    from app.db.models.category import Category

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
    *,
    title: str,
) -> Opportunity:
    from app.schemas.complaint import ComplaintCreate

    category_id, domain_id, persona_id = taxonomy_ids
    source = Source(
        name=f"ranking-source-{uuid4()}",
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
        title=title,
        body="Scheduling pain for hourly teams.",
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
            summary="Scheduling chaos from last-minute shift changes.",
            verbatim_quote="Scheduling chaos from last-minute shift changes.",
            severity=4,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )

    return await repos.opportunities.create(
        OpportunityCreate(
            title=title,
            problem_statement="Ops teams struggle with hourly staff scheduling.",
            target_user="Ops admins",
            frequency_signal="Repeated scheduling complaints.",
            existing_alternatives="ShiftApp and spreadsheets.",
            gap="No lightweight scheduling workflow.",
            confidence_score=0.86,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )


async def _seed_agent_outputs(
    repos,
    opportunity_id: UUID,
    founder_profile_id: UUID,
    profile: AgentScoreProfile,
) -> None:
    await repos.market_briefs.create(
        MarketBriefCreate(
            opportunity_id=opportunity_id,
            status=MarketResearchStatus.COMPLETED,
            sam_usd=profile.market_sam,
            tam_usd=profile.market_sam * 4,
            industry_growth_rate_pct=profile.market_growth,
            customer_segments=[{"name": "SMB"}, {"name": "Mid-market"}],
            executive_summary="Large addressable market with steady growth.",
            llm_model="mock-market",
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
            executive_summary="Differentiation opportunity exists.",
            llm_model="mock-competitor",
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
            executive_summary="Strong pain signal.",
            llm_model="mock-customer",
        )
    )
    await repos.revenue_validations.create(
        RevenueValidationCreate(
            opportunity_id=opportunity_id,
            status=RevenueValidationStatus.COMPLETED,
            willingness_to_pay_score=profile.revenue_wtp,
            revenue_confidence_score=profile.revenue_confidence,
            evaluation_metrics={
                "evaluation_readiness_score": int(
                    round(profile.revenue_wtp * 0.65 + profile.revenue_confidence * 0.35)
                )
            },
            executive_summary="Buyers show willingness to pay.",
            llm_model="mock-revenue",
        )
    )
    await repos.product_strategies.create(
        ProductStrategyCreate(
            opportunity_id=opportunity_id,
            status=ProductStrategyStatus.COMPLETED,
            mvp_definition="Scheduling MVP for hourly teams.",
            planning_metrics={"planning_readiness_score": profile.planning_readiness},
            executive_summary="Achievable MVP roadmap.",
            llm_model="mock-product",
        )
    )
    await repos.gtm_plans.create(
        GTMPlanCreate(
            opportunity_id=opportunity_id,
            status=GTMPlanStatus.COMPLETED,
            gtm_report="Founder-led outbound and SEO wedge.",
            estimated_cac_usd=120.0,
            confidence_score=profile.gtm_readiness,
            ranking_metrics={"gtm_readiness_score": profile.gtm_readiness},
            llm_model="mock-gtm",
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
            executive_summary="Solid long-term growth potential.",
            llm_model="mock-growth",
        )
    )
    await repos.human_proxy_evaluations.create(
        HumanProxyEvaluationCreate(
            opportunity_id=opportunity_id,
            founder_profile_id=founder_profile_id,
            status=HumanProxyEvaluationStatus.COMPLETED,
            founder_fit_score=profile.founder_fit,
            feasibility_score=profile.feasibility,
            recommendation="pursue",
            evaluation_metrics={
                "ranking_score": int(round(profile.founder_fit * 0.7 + profile.feasibility * 0.3))
            },
            llm_model="mock-human-proxy",
        )
    )


@pytest.mark.asyncio
async def test_generate_ranking_returns_top_opportunities(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    high = await _create_opportunity(db_session, taxonomy_ids, title="High Fit Scheduling SaaS")
    low = await _create_opportunity(db_session, taxonomy_ids, title="Low Fit Scheduling SaaS")

    await _seed_agent_outputs(
        repos,
        high.id,
        default_profile.id,
        AgentScoreProfile(
            pain=90,
            revenue_wtp=85,
            growth_readiness=88,
            founder_fit=92,
            feasibility=88,
            competition_diff=0.85,
        ),
    )
    await _seed_agent_outputs(
        repos,
        low.id,
        default_profile.id,
        AgentScoreProfile(
            pain=45,
            revenue_wtp=40,
            growth_readiness=42,
            founder_fit=38,
            feasibility=35,
            competition_diff=0.3,
            competition_threat=0.7,
        ),
    )

    service = ExecutiveRankingService(repos)
    result = await service.generate_ranking(top_n=5)

    assert result.ranked_opportunity_count == 2
    assert len(result.top_opportunities) == 2
    assert (
        result.top_opportunities[0].final_opportunity_score
        > result.top_opportunities[1].final_opportunity_score
    )
    assert result.top_opportunities[0].opportunity_id == high.id
    assert result.top_opportunities[0].pain_score is not None
    assert result.top_opportunities[0].founder_fit_score is not None


@pytest.mark.asyncio
async def test_generate_ranking_stores_versioned_history(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity = await _create_opportunity(db_session, taxonomy_ids, title="Ranked Opportunity")
    await _seed_agent_outputs(repos, opportunity.id, default_profile.id, AgentScoreProfile())

    service = ExecutiveRankingService(repos)
    first = await service.generate_ranking(top_n=5)
    second = await service.generate_ranking(top_n=5)

    assert second.version > first.version

    current = await service.get_current_ranking()
    assert current.is_current is True
    assert current.version == second.version
    assert len(current.top_opportunities) == 1

    history = await service.list_history(PaginationParams(limit=10, offset=0))
    assert history.total == 2


@pytest.mark.asyncio
async def test_generate_ranking_limits_top_five(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    for index in range(7):
        opportunity = await _create_opportunity(
            db_session,
            taxonomy_ids,
            title=f"Opportunity {index}",
        )
        await _seed_agent_outputs(
            repos,
            opportunity.id,
            default_profile.id,
            AgentScoreProfile(pain=50 + index * 5, founder_fit=50 + index * 5),
        )

    service = ExecutiveRankingService(repos)
    result = await service.generate_ranking(top_n=5)

    assert result.ranked_opportunity_count == 7
    assert len(result.top_opportunities) == 5

    run = await db_session.scalar(
        select(ExecutiveRankingRun).where(ExecutiveRankingRun.id == result.ranking_run_id)
    )
    assert run is not None
    assert run.top_n == 5
