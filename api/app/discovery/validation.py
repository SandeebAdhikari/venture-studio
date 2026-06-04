"""Discovery validation run mode: preflight checks and eligibility filters."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import func, or_, select, text

from app.config import Settings
from app.db.models.competitor_analysis import CompetitorAnalysis
from app.db.models.customer_research import CustomerResearch
from app.db.models.growth_evaluation import GrowthEvaluation
from app.db.models.gtm_plan import GTMPlan
from app.db.models.human_proxy_evaluation import HumanProxyEvaluation
from app.db.models.market_brief import MarketBrief
from app.db.models.opportunity import Opportunity
from app.db.models.product_strategy import ProductStrategy
from app.db.models.revenue_validation import RevenueValidation
from app.exceptions import ValidationError
from app.repositories import RepositoryContainer
from app.schemas.pipeline import PipelineRunOptions

MOCK_LLM_PREFIX = "mock-"
E2E_MARKER_KEY = "e2e_marker"

_AGENT_MODEL_CHECKS: tuple[tuple[str, type], ...] = (
    ("market_briefs", MarketBrief),
    ("competitor_analyses", CompetitorAnalysis),
    ("customer_research", CustomerResearch),
    ("revenue_validations", RevenueValidation),
    ("product_strategies", ProductStrategy),
    ("gtm_plans", GTMPlan),
    ("growth_evaluations", GrowthEvaluation),
    ("human_proxy_evaluations", HumanProxyEvaluation),
)


@dataclass(frozen=True)
class DiscoveryValidationPreflightResult:
    passed: bool
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def detail(self) -> str:
        return "; ".join(self.errors)


def resolve_pipeline_options(
    options: PipelineRunOptions | None,
    settings: Settings,
) -> PipelineRunOptions:
    """Apply global settings and validation-run defaults (force, stop_on_failure)."""
    opts = options or PipelineRunOptions()
    validation_mode = opts.discovery_validation_mode or settings.discovery_validation_mode
    if not validation_mode:
        return opts
    return opts.model_copy(
        update={
            "discovery_validation_mode": True,
            "force": True,
            "stop_on_failure": True,
        }
    )


def is_mock_llm_model(model: str | None) -> bool:
    return bool(model and model.startswith(MOCK_LLM_PREFIX))


def is_e2e_opportunity_title(title: str) -> bool:
    return "E2E" in title.upper()


class DiscoveryValidationPreflight:
    """Preflight checks before a discovery validation pipeline run."""

    def __init__(self, repos: RepositoryContainer) -> None:
        self._repos = repos

    async def check(self) -> DiscoveryValidationPreflightResult:
        errors: list[str] = []

        mock_opps = await self._count(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.llm_model.like(f"{MOCK_LLM_PREFIX}%"))
        )
        if mock_opps:
            errors.append(f"{mock_opps} opportunit(ies) with mock-* llm_model")

        e2e_opps = await self._count(
            select(func.count())
            .select_from(Opportunity)
            .where(
                or_(
                    Opportunity.title.ilike("%E2E%"),
                    Opportunity.llm_model.like(f"{MOCK_LLM_PREFIX}%"),
                )
            )
        )
        if e2e_opps:
            errors.append(f"{e2e_opps} E2E or mock-tagged opportunit(ies)")

        for table_name, model in _AGENT_MODEL_CHECKS:
            mock_rows = await self._count(
                select(func.count())
                .select_from(model)
                .where(
                    model.is_current.is_(True),
                    model.llm_model.like(f"{MOCK_LLM_PREFIX}%"),
                )
            )
            if mock_rows:
                errors.append(f"{mock_rows} current mock-* row(s) in {table_name}")

        e2e_runs = (
            await self._repos.session.execute(
                text(
                    "SELECT count(*)::int FROM pipeline_runs "
                    "WHERE config_snapshot->>'e2e_marker' IS NOT NULL"
                )
            )
        ).scalar_one()
        if e2e_runs:
            errors.append(f"{e2e_runs} pipeline run(s) with e2e_marker")

        return DiscoveryValidationPreflightResult(
            passed=len(errors) == 0,
            errors=tuple(errors),
        )

    async def _count(self, stmt) -> int:
        result = await self._repos.session.execute(stmt)
        return int(result.scalar_one() or 0)


async def is_opportunity_validation_eligible(
    repos: RepositoryContainer,
    opportunity_id: UUID,
    *,
    founder_profile_id: UUID | None,
) -> bool:
    """True when opportunity and all current research artifacts are non-mock."""
    opportunity = await repos.opportunities.get_by_id(opportunity_id)
    if opportunity is None:
        return False
    if is_mock_llm_model(opportunity.llm_model) or is_e2e_opportunity_title(opportunity.title):
        return False

    market_brief = await repos.market_briefs.get_current_for_opportunity(opportunity_id)
    competitor = await repos.competitor_analyses.get_current_for_opportunity(opportunity_id)
    customer = await repos.customer_research.get_current_for_opportunity(opportunity_id)
    revenue = await repos.revenue_validations.get_current_for_opportunity(opportunity_id)
    product = await repos.product_strategies.get_current_for_opportunity(opportunity_id)
    gtm = await repos.gtm_plans.get_current_for_opportunity(opportunity_id)
    growth = await repos.growth_evaluations.get_current_for_opportunity(opportunity_id)
    human_proxy = None
    if founder_profile_id is not None:
        human_proxy = await repos.human_proxy_evaluations.get_current_for_opportunity(
            opportunity_id,
            founder_profile_id=founder_profile_id,
        )

    artifacts = (
        market_brief,
        competitor,
        customer,
        revenue,
        product,
        gtm,
        growth,
        human_proxy,
    )
    for artifact in artifacts:
        if artifact is None:
            continue
        if is_mock_llm_model(artifact.llm_model):
            return False
    return True


def assert_ranking_bound_to_pipeline_run(
    *,
    ranking_metadata: dict,
    pipeline_run_id: UUID | None,
) -> None:
    """Reject stale rankings not tagged with this validation pipeline run."""
    if pipeline_run_id is None:
        raise ValidationError("Validation run requires pipeline_run_id context for ranking")
    bound_run = ranking_metadata.get("pipeline_run_id")
    if bound_run is None:
        raise ValidationError(
            "Executive ranking was not produced by this validation pipeline run"
        )
    if str(bound_run) != str(pipeline_run_id):
        raise ValidationError(
            "Executive ranking belongs to a different pipeline run (stale ranking)"
        )


def assert_report_uses_validation_ranking(
    *,
    report_metadata: dict,
    ranking_run_id: UUID,
    pipeline_run_id: UUID | None,
) -> None:
    """Reject venture reports that reference a different ranking run."""
    report_ranking = report_metadata.get("executive_ranking_run_id")
    if report_ranking is None or str(report_ranking) != str(ranking_run_id):
        raise ValidationError(
            "Venture report executive_ranking_run_id does not match validation ranking"
        )
    if pipeline_run_id is not None:
        report_run = report_metadata.get("pipeline_run_id")
        if report_run is not None and str(report_run) != str(pipeline_run_id):
            raise ValidationError(
                "Venture report belongs to a different pipeline run (stale report)"
            )
