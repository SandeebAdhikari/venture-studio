"""Integration tests for FF-CM-5 capability-match shadow mode."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    HumanProxyEvaluationStatus,
    SourceType,
)
from app.db.models.executive_ranking_entry import ExecutiveRankingEntry
from app.db.models.executive_ranking_run import ExecutiveRankingRun
from app.db.models.signal import Signal
from app.db.models.source import Source
from app.founder_fit.fingerprint_resolution import resolve_dominant_mechanism_fingerprint
from app.founder_fit.shadow import build_capability_match_shadow_details
from app.ranking.collector import AgentEvaluationCollector
from app.ranking.engine import ExecutiveRankingEngine, compute_founder_fit_score
from app.ranking.service import ExecutiveRankingService
from app.reports.venture.analysis import build_recommendation
from app.repositories import get_repositories
from app.schemas.complaint import ComplaintCreate
from app.schemas.human_proxy_evaluation import (
    HumanProxyEvaluationCreate,
    SCALE_VERSION_CENTURY_V1,
)
from app.schemas.opportunity import OpportunityCreate
from app.schemas.pagination import PaginationParams
from tests.ranking.test_executive_ranking_service import (
    AgentScoreProfile,
    _create_opportunity,
    _seed_agent_outputs,
)

pytest_plugins = ["tests.ranking.test_executive_ranking_service"]

AI_EVAL_VERBATIM = (
    "Been trying to build a proper evaluation pipeline for months but every tool we've "
    "tested has significant limitations."
)


async def _create_opportunity_with_complaint_quote(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
    *,
    title: str,
    verbatim_quote: str,
    summary: str,
) -> UUID:
    category_id, domain_id, persona_id = taxonomy_ids
    source = Source(
        name=f"cm-shadow-source-{uuid4()}",
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
        body=verbatim_quote,
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
            summary=summary,
            verbatim_quote=verbatim_quote,
            severity=4,
            product_mentions=[],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )

    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title=title,
            problem_statement="AI eval tooling gap.",
            target_user="ML engineers",
            frequency_signal="Repeated eval pipeline complaints.",
            existing_alternatives="Half-baked tools.",
            gap="No production-grade eval pipeline.",
            confidence_score=0.86,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )
    return opportunity.id


async def _seed_century_v1_hp(
    repos,
    opportunity_id: UUID,
    founder_profile_id: UUID,
    profile: AgentScoreProfile,
) -> None:
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
            scale_version=SCALE_VERSION_CENTURY_V1,
            scale_metadata={"scale_detected": "century"},
        )
    )


def test_build_capability_match_shadow_details_resolved_fingerprint() -> None:
    details = build_capability_match_shadow_details("ai_eval_pipeline_gap")
    assert details["capability_match_shadow"] is True
    assert details["capability_match_score"] == 96
    assert details["capability_match_version"] == "capability_match_v1"
    assert details["dominant_fingerprint"] == "ai_eval_pipeline_gap"
    assert details["family_coverage"]["python_data"] == 1.0
    assert details["critical_gaps"] == []


def test_build_capability_match_shadow_details_null_fingerprint() -> None:
    details = build_capability_match_shadow_details(None)
    assert details == {
        "capability_match_shadow": True,
        "capability_match_score": None,
        "dominant_fingerprint": None,
    }


def test_build_capability_match_shadow_details_is_deterministic() -> None:
    first = build_capability_match_shadow_details("ai_eval_pipeline_gap")
    second = build_capability_match_shadow_details("ai_eval_pipeline_gap")
    assert first == second


def test_resolve_dominant_mechanism_fingerprint_picks_mode() -> None:
    from app.db.models.complaint import Complaint

    complaints = [
        Complaint(
            verbatim_quote=AI_EVAL_VERBATIM,
            summary="Eval pipeline gap.",
        ),
        Complaint(
            verbatim_quote="Scheduling chaos from last-minute shift changes.",
            summary="Scheduling chaos.",
        ),
        Complaint(
            verbatim_quote=AI_EVAL_VERBATIM,
            summary="Another eval complaint.",
        ),
    ]
    assert resolve_dominant_mechanism_fingerprint(complaints) == "ai_eval_pipeline_gap"


def test_resolve_dominant_mechanism_fingerprint_empty_when_unmatched() -> None:
    from app.db.models.complaint import Complaint

    complaints = [
        Complaint(
            verbatim_quote="Scheduling chaos from last-minute shift changes.",
            summary="Scheduling chaos.",
        ),
    ]
    assert resolve_dominant_mechanism_fingerprint(complaints) is None


def test_recommendation_unchanged_by_shadow_metadata() -> None:
    recommendation = build_recommendation(
        final_score=78,
        human_proxy_recommendation="pursue",
        pain_score=82,
        founder_fit_score=60,
        rank=1,
    )
    assert "Pursue" in recommendation or "pursue" in recommendation.lower()
    assert "capability_match" not in recommendation


@pytest.mark.asyncio
async def test_collector_includes_cm_shadow_fields_with_resolved_fingerprint(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity_id = await _create_opportunity_with_complaint_quote(
        db_session,
        taxonomy_ids,
        title="AI Eval Opportunity",
        verbatim_quote=AI_EVAL_VERBATIM,
        summary="Eval pipeline tooling gap.",
    )
    profile = AgentScoreProfile(founder_fit=70, feasibility=60)
    await _seed_agent_outputs(repos, opportunity_id, default_profile.id, profile)
    await _seed_century_v1_hp(repos, opportunity_id, default_profile.id, profile)

    collector = AgentEvaluationCollector(repos)
    evaluation = await collector.collect(
        opportunity_id,
        opportunity_title="AI Eval Opportunity",
        founder_profile_id=default_profile.id,
    )

    details = evaluation.ranking_details
    assert details["founder_fit_source"] == "human_proxy_v1"
    assert details["capability_match_shadow"] is True
    assert details["capability_match_score"] == 96
    assert details["dominant_fingerprint"] == "ai_eval_pipeline_gap"
    assert details["capability_match_version"] == "capability_match_v1"
    assert "family_coverage" in details
    assert details["critical_gaps"] == []


@pytest.mark.asyncio
async def test_collector_null_fingerprint_path(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity = await _create_opportunity(
        db_session,
        taxonomy_ids,
        title="Scheduling Opportunity",
    )
    profile = AgentScoreProfile(founder_fit=70, feasibility=60)
    await _seed_agent_outputs(repos, opportunity.id, default_profile.id, profile)
    await _seed_century_v1_hp(repos, opportunity.id, default_profile.id, profile)

    collector = AgentEvaluationCollector(repos)
    evaluation = await collector.collect(
        opportunity.id,
        opportunity_title="Scheduling Opportunity",
        founder_profile_id=default_profile.id,
    )

    details = evaluation.ranking_details
    assert details["capability_match_shadow"] is True
    assert details["capability_match_score"] is None
    assert details["dominant_fingerprint"] is None
    assert "capability_match_version" not in details
    assert evaluation.founder_fit_score == compute_founder_fit_score(
        founder_fit_score=70,
        feasibility_score=60,
        planning_readiness_score=profile.planning_readiness,
        ranking_score=int(round(70 * 0.7 + 60 * 0.3)),
    )


@pytest.mark.asyncio
async def test_ranking_order_and_scores_unchanged_with_shadow(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    high_id = await _create_opportunity_with_complaint_quote(
        db_session,
        taxonomy_ids,
        title="High Fit Eval",
        verbatim_quote=AI_EVAL_VERBATIM,
        summary="Eval pipeline gap.",
    )
    low_opportunity = await _create_opportunity(
        db_session,
        taxonomy_ids,
        title="Low Fit Scheduling",
    )
    low_id = low_opportunity.id

    high_profile = AgentScoreProfile(
        pain=90,
        revenue_wtp=85,
        growth_readiness=88,
        founder_fit=92,
        feasibility=88,
    )
    low_profile = AgentScoreProfile(
        pain=45,
        revenue_wtp=40,
        growth_readiness=42,
        founder_fit=38,
        feasibility=35,
        competition_diff=0.3,
        competition_threat=0.7,
    )
    await _seed_agent_outputs(repos, high_id, default_profile.id, high_profile)
    await _seed_century_v1_hp(repos, high_id, default_profile.id, high_profile)
    await _seed_agent_outputs(repos, low_id, default_profile.id, low_profile)
    await _seed_century_v1_hp(repos, low_id, default_profile.id, low_profile)

    collector = AgentEvaluationCollector(repos)
    engine = ExecutiveRankingEngine()
    high_eval = await collector.collect(
        high_id,
        opportunity_title="High Fit Eval",
        founder_profile_id=default_profile.id,
    )
    low_eval = await collector.collect(
        low_id,
        opportunity_title="Low Fit Scheduling",
        founder_profile_id=default_profile.id,
    )

    high_score = engine.score(high_eval)
    low_score = engine.score(low_eval)
    assert high_score is not None and low_score is not None
    assert high_score.final_opportunity_score > low_score.final_opportunity_score
    assert high_score.components.founder_fit_score == compute_founder_fit_score(
        founder_fit_score=high_profile.founder_fit,
        feasibility_score=high_profile.feasibility,
        planning_readiness_score=high_profile.planning_readiness,
        ranking_score=int(round(high_profile.founder_fit * 0.7 + high_profile.feasibility * 0.3)),
    )

    service = ExecutiveRankingService(repos)
    result = await service.generate_ranking(top_n=5)

    run = await repos.executive_rankings.get_by_id_with_entries(result.ranking_run_id)
    assert run is not None
    our_entries = [entry for entry in run.entries if entry.opportunity_id in {high_id, low_id}]
    assert len(our_entries) == 2
    high_entry = next(entry for entry in our_entries if entry.opportunity_id == high_id)
    low_entry = next(entry for entry in our_entries if entry.opportunity_id == low_id)
    assert high_entry.final_opportunity_score > low_entry.final_opportunity_score
    assert high_entry.final_opportunity_score == high_score.final_opportunity_score
    assert low_entry.final_opportunity_score == low_score.final_opportunity_score
    assert high_entry.ranking_details["capability_match_score"] == 96
    assert low_entry.ranking_details["capability_match_score"] is None


@pytest.mark.asyncio
async def test_historical_ranking_entries_remain_untouched(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity = await _create_opportunity(db_session, taxonomy_ids, title="Historical Opportunity")
    profile = AgentScoreProfile()
    await _seed_agent_outputs(repos, opportunity.id, default_profile.id, profile)
    await _seed_century_v1_hp(repos, opportunity.id, default_profile.id, profile)

    service = ExecutiveRankingService(repos)
    first = await service.generate_ranking(top_n=5)

    old_run = await repos.executive_rankings.get_by_id_with_entries(first.ranking_run_id)
    assert old_run is not None
    for entry in old_run.entries:
        if entry.opportunity_id == opportunity.id:
            entry.ranking_details = {
                "founder_fit_source": "human_proxy_v1",
                "founder_fit_score": profile.founder_fit,
                "feasibility_score": profile.feasibility,
                "executive_founder_fit": compute_founder_fit_score(
                    founder_fit_score=profile.founder_fit,
                    feasibility_score=profile.feasibility,
                    planning_readiness_score=profile.planning_readiness,
                    ranking_score=int(
                        round(profile.founder_fit * 0.7 + profile.feasibility * 0.3)
                    ),
                ),
            }
    await db_session.flush()

    second = await service.generate_ranking(top_n=5)
    preserved = await db_session.scalar(
        select(ExecutiveRankingEntry).where(
            ExecutiveRankingEntry.executive_ranking_run_id == first.ranking_run_id,
            ExecutiveRankingEntry.opportunity_id == opportunity.id,
        )
    )
    current = await db_session.scalar(
        select(ExecutiveRankingEntry).where(
            ExecutiveRankingEntry.executive_ranking_run_id == second.ranking_run_id,
            ExecutiveRankingEntry.opportunity_id == opportunity.id,
        )
    )
    assert preserved is not None and current is not None
    assert "capability_match_score" not in preserved.ranking_details
    assert current.ranking_details["capability_match_shadow"] is True
    assert "capability_match_score" in current.ranking_details


@pytest.mark.asyncio
async def test_deterministic_rerun_produces_identical_cm_shadow(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity_id = await _create_opportunity_with_complaint_quote(
        db_session,
        taxonomy_ids,
        title="Deterministic Eval",
        verbatim_quote=AI_EVAL_VERBATIM,
        summary="Eval pipeline gap.",
    )
    profile = AgentScoreProfile()
    await _seed_agent_outputs(repos, opportunity_id, default_profile.id, profile)
    await _seed_century_v1_hp(repos, opportunity_id, default_profile.id, profile)

    service = ExecutiveRankingService(repos)
    first = await service.generate_ranking(top_n=5)
    second = await service.generate_ranking(top_n=5)

    first_entry = next(
        item for item in first.top_opportunities if item.opportunity_id == opportunity_id
    )
    second_entry = next(
        item for item in second.top_opportunities if item.opportunity_id == opportunity_id
    )

    cm_keys = {
        "capability_match_shadow",
        "capability_match_score",
        "capability_match_version",
        "dominant_fingerprint",
        "family_coverage",
        "critical_gaps",
    }
    assert {key: first_entry.ranking_details[key] for key in cm_keys} == {
        key: second_entry.ranking_details[key] for key in cm_keys
    }
    assert first_entry.final_opportunity_score == second_entry.final_opportunity_score
    assert first_entry.founder_fit_score == second_entry.founder_fit_score

    runs = await service.list_history(PaginationParams(limit=10, offset=0))
    assert runs.total >= 2
    assert await db_session.scalar(select(func.count()).select_from(ExecutiveRankingRun)) >= 2
