"""Orchestrates executive ranking across all agent outputs."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.config import Settings, get_settings
from app.db.enums import ExecutiveRankingStatus
from app.exceptions import NotFoundError
from app.logging import get_logger
from app.discovery.validation import is_opportunity_validation_eligible
from app.pipeline.lineage import merge_pipeline_run_lineage
from app.ranking.collector import AgentEvaluationCollector
from app.ranking.constants import MIN_AGENT_COVERAGE, RANKING_ENGINE
from app.ranking.engine import ExecutiveRankingEngine
from app.ranking.schemas import (
    AgentEvaluationInput,
    ExecutiveRankingEntryRead,
    ExecutiveRankingRegenResult,
    ExecutiveRankingResult,
    ExecutiveRankingScore,
)
from app.schemas.human_proxy_evaluation import SCALE_VERSION_CENTURY_V1
from app.repositories import RepositoryContainer
from app.schemas.executive_ranking import (
    ExecutiveRankingEntryCreate,
    ExecutiveRankingRunCreate,
    ExecutiveRankingRunDetail,
    ExecutiveRankingRunRead,
)
from app.schemas.filters import OpportunityListFilter
from app.schemas.pagination import PaginatedResponse, PaginationParams

if TYPE_CHECKING:
    from app.services.approval import ApprovalService

logger = get_logger(__name__)


class ExecutiveRankingService:
    """Ranks opportunities using outputs from all prior agents."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        engine: ExecutiveRankingEngine | None = None,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._engine = engine or ExecutiveRankingEngine()
        self._collector = AgentEvaluationCollector(repos)
        self._approval = approval_service

    async def generate_ranking(
        self,
        *,
        top_n: int | None = None,
        founder_profile_id: UUID | None = None,
        discovery_validation_mode: bool = False,
        pipeline_run_id: UUID | None = None,
        ranking_metadata_extra: dict[str, object] | None = None,
    ) -> ExecutiveRankingResult:
        top_limit = top_n or self._settings.executive_ranking_top_n
        profile = await self._resolve_profile(founder_profile_id)

        opportunities, scored = await self._score_opportunities(
            founder_profile_id=profile.id,
            discovery_validation_mode=discovery_validation_mode,
        )

        entries = self._build_entry_creates(scored, top_limit=top_limit)

        ranking_metadata = merge_pipeline_run_lineage(
            {
                "founder_profile_name": profile.name if profile else None,
                "min_agent_coverage": MIN_AGENT_COVERAGE,
                **({"discovery_validation_mode": True} if discovery_validation_mode else {}),
            },
            pipeline_run_id=pipeline_run_id,
        )
        if ranking_metadata_extra:
            ranking_metadata.update(ranking_metadata_extra)

        run = await self._repos.executive_rankings.create(
            ExecutiveRankingRunCreate(
                status=ExecutiveRankingStatus.COMPLETED,
                founder_profile_id=profile.id if profile else None,
                top_n=top_limit,
                opportunity_count=len(opportunities),
                ranked_opportunity_count=len(entries),
                ranking_engine=RANKING_ENGINE,
                ranking_metadata=ranking_metadata,
                entries=entries,
            )
        )

        loaded = await self._repos.executive_rankings.get_by_id_with_entries(run.id)
        assert loaded is not None

        top_opportunities = self._build_top_entries(loaded, top_limit)

        logger.info(
            "Executive ranking generated",
            extra={
                "ranking_run_id": str(run.id),
                "version": run.version,
                "ranked_opportunity_count": len(entries),
                "top_n": top_limit,
            },
        )

        if self._approval is not None:
            await self._approval.create_for_executive_ranking(
                run_id=loaded.id,
                title=f"Executive Ranking v{loaded.version}",
                version=loaded.version,
            )

        return ExecutiveRankingResult(
            ranking_run_id=run.id,
            version=run.version,
            top_n=top_limit,
            ranked_opportunity_count=len(entries),
            top_opportunities=top_opportunities,
        )

    async def regenerate_current_rankings(
        self,
        *,
        founder_profile_id: UUID | None = None,
        top_n: int | None = None,
        dry_run: bool = False,
    ) -> ExecutiveRankingRegenResult:
        """Regenerate the current executive ranking using fresh agent outputs.

        Creates a new versioned run via ``generate_ranking`` and demotes the prior
        current run. Does not mutate or delete historical ranking rows.
        """
        top_limit = top_n or self._settings.executive_ranking_top_n
        profile = await self._resolve_profile(founder_profile_id)

        current_run = await self._repos.executive_rankings.get_current_with_entries()
        stale_entry_count = self._count_stale_founder_fit_entries(current_run)

        opportunities, scored = await self._score_opportunities(
            founder_profile_id=profile.id,
            discovery_validation_mode=False,
        )
        century_evaluations = (
            await self._repos.human_proxy_evaluations.list_current_evaluations(
                founder_profile_id=profile.id,
                scale_version=SCALE_VERSION_CENTURY_V1,
            )
        )

        result = ExecutiveRankingRegenResult(
            dry_run=dry_run,
            founder_profile_id=profile.id,
            top_n=top_limit,
            opportunity_count=len(opportunities),
            rankable_opportunity_count=len(scored),
            century_v1_hp_count=len(century_evaluations),
            stale_entry_count=stale_entry_count,
            superseded_run_id=current_run.id if current_run is not None else None,
            superseded_version=current_run.version if current_run is not None else None,
        )

        if dry_run:
            logger.info(
                "Executive ranking regeneration dry run",
                extra={
                    "founder_profile_id": str(profile.id),
                    "opportunity_count": result.opportunity_count,
                    "rankable_opportunity_count": result.rankable_opportunity_count,
                    "century_v1_hp_count": result.century_v1_hp_count,
                    "stale_entry_count": result.stale_entry_count,
                    "superseded_run_id": (
                        str(result.superseded_run_id) if result.superseded_run_id else None
                    ),
                },
            )
            return result

        metadata_extra: dict[str, object] = {"regen": "exec_rank_regen_1"}
        if current_run is not None:
            metadata_extra.update(
                {
                    "supersedes_ranking_run_id": str(current_run.id),
                    "supersedes_version": current_run.version,
                    "supersedes_stale_entry_count": stale_entry_count,
                }
            )

        ranking_result = await self.generate_ranking(
            top_n=top_limit,
            founder_profile_id=profile.id,
            ranking_metadata_extra=metadata_extra,
        )

        result.ranking_run_id = ranking_result.ranking_run_id
        result.version = ranking_result.version
        result.ranked_opportunity_count = ranking_result.ranked_opportunity_count
        result.top_opportunities = ranking_result.top_opportunities

        logger.info(
            "Executive ranking regeneration complete",
            extra={
                "ranking_run_id": str(result.ranking_run_id),
                "version": result.version,
                "ranked_opportunity_count": result.ranked_opportunity_count,
                "superseded_run_id": (
                    str(result.superseded_run_id) if result.superseded_run_id else None
                ),
                "stale_entry_count": result.stale_entry_count,
            },
        )
        return result

    async def _score_opportunities(
        self,
        *,
        founder_profile_id: UUID,
        discovery_validation_mode: bool,
    ) -> tuple[list, list[tuple[ExecutiveRankingScore, AgentEvaluationInput]]]:
        opportunities = await self._repos.opportunities.list_filtered(
            OpportunityListFilter(),
            limit=1000,
            offset=0,
        )

        scored: list[tuple[ExecutiveRankingScore, AgentEvaluationInput]] = []
        for opportunity in opportunities:
            if discovery_validation_mode:
                eligible = await is_opportunity_validation_eligible(
                    self._repos,
                    opportunity.id,
                    founder_profile_id=founder_profile_id,
                )
                if not eligible:
                    continue

            agent_input = await self._collector.collect(
                opportunity.id,
                opportunity_title=opportunity.title,
                founder_profile_id=founder_profile_id,
            )
            if agent_input.agent_coverage_count < MIN_AGENT_COVERAGE:
                continue

            ranking_score = self._engine.score(agent_input)
            if ranking_score is None:
                continue
            scored.append((ranking_score, agent_input))

        scored.sort(key=lambda item: item[0].final_opportunity_score, reverse=True)
        return opportunities, scored

    @staticmethod
    def _build_entry_creates(
        scored: list[tuple[ExecutiveRankingScore, AgentEvaluationInput]],
        *,
        top_limit: int,
    ) -> list[ExecutiveRankingEntryCreate]:
        entries: list[ExecutiveRankingEntryCreate] = []
        for index, (ranking_score, _agent_input) in enumerate(scored, start=1):
            entries.append(
                ExecutiveRankingEntryCreate(
                    opportunity_id=ranking_score.opportunity_id,
                    rank=index,
                    final_opportunity_score=ranking_score.final_opportunity_score,
                    pain_score=ranking_score.components.pain_score,
                    market_score=ranking_score.components.market_score,
                    revenue_score=ranking_score.components.revenue_score,
                    competition_score=ranking_score.components.competition_score,
                    growth_score=ranking_score.components.growth_score,
                    founder_fit_score=ranking_score.components.founder_fit_score,
                    agent_coverage_count=ranking_score.agent_coverage_count,
                    is_top_opportunity=index <= top_limit,
                    source_references=ranking_score.source_references.model_dump(mode="json"),
                    ranking_details={
                        **ranking_score.ranking_details,
                        "opportunity_title": ranking_score.opportunity_title,
                    },
                )
            )
        return entries

    @staticmethod
    def _count_stale_founder_fit_entries(current_run) -> int:
        if current_run is None:
            return 0
        stale = 0
        for entry in current_run.entries:
            details = entry.ranking_details or {}
            if details.get("founder_fit_source") != "human_proxy_v1":
                stale += 1
        return stale

    async def get_current_ranking(self) -> ExecutiveRankingRunDetail:
        run = await self._repos.executive_rankings.get_current_with_entries()
        if run is None:
            raise NotFoundError("executive_ranking_run", "current")
        return ExecutiveRankingRunDetail.from_entity(run)

    async def get_ranking(self, run_id: UUID) -> ExecutiveRankingRunDetail:
        run = await self._repos.executive_rankings.get_by_id_with_entries(run_id)
        if run is None:
            raise NotFoundError("executive_ranking_run", run_id)
        return ExecutiveRankingRunDetail.from_entity(run)

    async def list_history(
        self,
        pagination: PaginationParams,
    ) -> PaginatedResponse[ExecutiveRankingRunRead]:
        items = await self._repos.executive_rankings.list_history(
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.executive_rankings.count_history()
        return PaginatedResponse[ExecutiveRankingRunRead](
            items=[ExecutiveRankingRunRead.from_entity(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def _resolve_profile(self, founder_profile_id: UUID | None):
        if founder_profile_id is not None:
            profile = await self._repos.founder_profiles.get_by_id(founder_profile_id)
            if profile is None or not profile.is_active:
                raise NotFoundError("founder_profile", founder_profile_id)
            return profile

        return await self._repos.founder_profiles.get_default()

    @staticmethod
    def _build_top_entries(run, top_n: int) -> list[ExecutiveRankingEntryRead]:
        top_entries = sorted(
            [entry for entry in run.entries if entry.is_top_opportunity],
            key=lambda item: item.rank,
        )[:top_n]

        result: list[ExecutiveRankingEntryRead] = []
        for entry in top_entries:
            details = entry.ranking_details or {}
            result.append(
                ExecutiveRankingEntryRead(
                    id=entry.id,
                    opportunity_id=entry.opportunity_id,
                    opportunity_title=str(details.get("opportunity_title", "Unknown")),
                    rank=entry.rank,
                    final_opportunity_score=entry.final_opportunity_score,
                    pain_score=entry.pain_score,
                    market_score=entry.market_score,
                    revenue_score=entry.revenue_score,
                    competition_score=entry.competition_score,
                    growth_score=entry.growth_score,
                    founder_fit_score=entry.founder_fit_score,
                    agent_coverage_count=entry.agent_coverage_count,
                    is_top_opportunity=entry.is_top_opportunity,
                    source_references=entry.source_references,
                    ranking_details=entry.ranking_details,
                )
            )
        return result
