"""Tests for EXEC-RANK-REGEN-1 executive ranking regeneration."""

from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.executive_ranking_run import ExecutiveRankingRun
from app.ranking.service import ExecutiveRankingService
from app.repositories import get_repositories
from app.schemas.human_proxy_evaluation import SCALE_VERSION_CENTURY_V1
from tests.ranking.test_executive_ranking_service import (
    AgentScoreProfile,
    _create_opportunity,
    _seed_agent_outputs,
)

pytest_plugins = ["tests.ranking.test_executive_ranking_service"]


async def _seed_century_v1_hp(
    repos,
    opportunity_id: UUID,
    founder_profile_id: UUID,
    profile: AgentScoreProfile,
) -> None:
    from app.db.enums import HumanProxyEvaluationStatus
    from app.schemas.human_proxy_evaluation import HumanProxyEvaluationCreate

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


@pytest.mark.asyncio
async def test_regenerate_current_rankings_dry_run_does_not_create_run(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity = await _create_opportunity(db_session, taxonomy_ids, title="Dry Run Opportunity")
    await _seed_agent_outputs(
        repos,
        opportunity.id,
        default_profile.id,
        AgentScoreProfile(founder_fit=82, feasibility=78),
    )
    await _seed_century_v1_hp(repos, opportunity.id, default_profile.id, AgentScoreProfile())

    service = ExecutiveRankingService(repos)
    await service.generate_ranking(top_n=5)

    before = await db_session.scalar(select(func.count()).select_from(ExecutiveRankingRun))
    result = await service.regenerate_current_rankings(dry_run=True)

    after = await db_session.scalar(select(func.count()).select_from(ExecutiveRankingRun))
    assert after == before
    assert result.dry_run is True
    assert result.rankable_opportunity_count >= 1
    assert result.century_v1_hp_count >= 1
    assert result.ranking_run_id is None
    assert result.superseded_run_id is not None


@pytest.mark.asyncio
async def test_regenerate_current_rankings_creates_version_and_preserves_history(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity = await _create_opportunity(db_session, taxonomy_ids, title="Regen Opportunity")
    profile = AgentScoreProfile(founder_fit=85, feasibility=80)
    await _seed_agent_outputs(repos, opportunity.id, default_profile.id, profile)
    await _seed_century_v1_hp(repos, opportunity.id, default_profile.id, profile)

    service = ExecutiveRankingService(repos)
    first = await service.generate_ranking(top_n=5)

    first_run = await repos.executive_rankings.get_by_id_with_entries(first.ranking_run_id)
    assert first_run is not None
    for entry in first_run.entries:
        if entry.opportunity_id == opportunity.id:
            entry.ranking_details = {"opportunity_title": "Regen Opportunity"}
    await db_session.flush()

    runs_before = await db_session.scalar(select(func.count()).select_from(ExecutiveRankingRun))
    result = await service.regenerate_current_rankings(top_n=5)

    assert result.ranking_run_id is not None
    assert result.version is not None
    assert result.version > first.version
    assert result.stale_entry_count >= 1

    new_run = await repos.executive_rankings.get_by_id_with_entries(result.ranking_run_id)
    old_run = await repos.executive_rankings.get_by_id_with_entries(first.ranking_run_id)
    assert new_run is not None and old_run is not None
    assert new_run.is_current is True
    assert old_run.is_current is False
    assert new_run.ranking_metadata["regen"] == "exec_rank_regen_1"
    assert new_run.ranking_metadata["supersedes_ranking_run_id"] == str(first.ranking_run_id)

    runs_after = await db_session.scalar(select(func.count()).select_from(ExecutiveRankingRun))
    assert runs_after == runs_before + 1

    our_entries = [
        item for item in result.top_opportunities if item.opportunity_id == opportunity.id
    ]
    assert len(our_entries) == 1
    details = our_entries[0].ranking_details
    assert details["founder_fit_source"] == "human_proxy_v1"
    assert details["founder_fit_score"] == 85
    assert details["feasibility_score"] == 80
    assert details["executive_founder_fit"] == round(85 * 0.70 + 80 * 0.30)


@pytest.mark.asyncio
async def test_regenerate_current_rankings_is_idempotent_via_versioning(
    db_session: AsyncSession,
    taxonomy_ids: tuple[UUID, UUID, UUID],
) -> None:
    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    opportunity = await _create_opportunity(db_session, taxonomy_ids, title="Idempotent Opportunity")
    profile = AgentScoreProfile()
    await _seed_agent_outputs(repos, opportunity.id, default_profile.id, profile)
    await _seed_century_v1_hp(repos, opportunity.id, default_profile.id, profile)

    service = ExecutiveRankingService(repos)
    runs_before = await db_session.scalar(select(func.count()).select_from(ExecutiveRankingRun))
    await service.generate_ranking(top_n=5)
    first_regen = await service.regenerate_current_rankings(top_n=5)
    second_regen = await service.regenerate_current_rankings(top_n=5)
    runs_after = await db_session.scalar(select(func.count()).select_from(ExecutiveRankingRun))

    assert second_regen.version is not None
    assert first_regen.version is not None
    assert second_regen.version > first_regen.version
    assert runs_after == runs_before + 3
