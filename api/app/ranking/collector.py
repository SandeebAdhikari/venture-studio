"""Collect current agent evaluations for executive ranking."""

from uuid import UUID

from app.db.models.competitor_analysis import CompetitorAnalysis
from app.db.models.customer_research import CustomerResearch
from app.db.models.growth_evaluation import GrowthEvaluation
from app.db.models.gtm_plan import GTMPlan
from app.db.models.human_proxy_evaluation import HumanProxyEvaluation
from app.db.models.market_brief import MarketBrief
from app.db.models.product_strategy import ProductStrategy
from app.db.models.revenue_validation import RevenueValidation
from app.ranking.engine import (
    build_founder_fit_ranking_details,
    compute_competition_score,
    compute_founder_fit_score,
    compute_growth_score,
    compute_market_score,
    compute_pain_score,
    compute_revenue_score,
)
from app.ranking.schemas import AgentEvaluationInput, AgentSourceReferences
from app.repositories import RepositoryContainer


class AgentEvaluationCollector:
    """Loads and normalizes current agent outputs for one opportunity."""

    def __init__(self, repos: RepositoryContainer) -> None:
        self._repos = repos

    async def collect(
        self,
        opportunity_id: UUID,
        *,
        opportunity_title: str,
        founder_profile_id: UUID | None,
    ) -> AgentEvaluationInput:
        market_brief = await self._repos.market_briefs.get_current_for_opportunity(opportunity_id)
        competitor_analysis = await self._repos.competitor_analyses.get_current_for_opportunity(
            opportunity_id
        )
        customer_research = await self._repos.customer_research.get_current_for_opportunity(
            opportunity_id
        )
        revenue_validation = await self._repos.revenue_validations.get_current_for_opportunity(
            opportunity_id
        )
        product_strategy = await self._repos.product_strategies.get_current_for_opportunity(
            opportunity_id
        )
        gtm_plan = await self._repos.gtm_plans.get_current_for_opportunity(opportunity_id)
        growth_evaluation = await self._repos.growth_evaluations.get_current_for_opportunity(
            opportunity_id
        )
        human_proxy = None
        if founder_profile_id is not None:
            human_proxy = await self._repos.human_proxy_evaluations.get_current_for_opportunity(
                opportunity_id,
                founder_profile_id=founder_profile_id,
            )

        sources = AgentSourceReferences(
            market_brief_id=market_brief.id if market_brief else None,
            competitor_analysis_id=competitor_analysis.id if competitor_analysis else None,
            customer_research_id=customer_research.id if customer_research else None,
            revenue_validation_id=revenue_validation.id if revenue_validation else None,
            product_strategy_id=product_strategy.id if product_strategy else None,
            gtm_plan_id=gtm_plan.id if gtm_plan else None,
            growth_evaluation_id=growth_evaluation.id if growth_evaluation else None,
            human_proxy_evaluation_id=human_proxy.id if human_proxy else None,
        )

        pain_score = self._pain_score(customer_research)
        market_score = self._market_score(market_brief)
        revenue_score = self._revenue_score(revenue_validation)
        competition_score = self._competition_score(competitor_analysis)
        growth_score = self._growth_score(growth_evaluation, gtm_plan)
        founder_fit_score, founder_fit_details = self._founder_fit_score(
            human_proxy,
            product_strategy,
        )

        component_scores = [
            pain_score,
            market_score,
            revenue_score,
            competition_score,
            growth_score,
            founder_fit_score,
        ]
        agent_coverage_count = sum(
            1 for source_id in sources.model_dump().values() if source_id is not None
        )

        return AgentEvaluationInput(
            opportunity_id=opportunity_id,
            opportunity_title=opportunity_title,
            sources=sources,
            pain_score=pain_score,
            market_score=market_score,
            revenue_score=revenue_score,
            competition_score=competition_score,
            growth_score=growth_score,
            founder_fit_score=founder_fit_score,
            agent_coverage_count=agent_coverage_count,
            ranking_details={
                "available_dimensions": sum(1 for score in component_scores if score is not None),
                **founder_fit_details,
            },
        )

    @staticmethod
    def _pain_score(customer_research: CustomerResearch | None) -> int | None:
        if customer_research is None:
            return None
        metrics = customer_research.validation_metrics or {}
        return compute_pain_score(
            pain_score=customer_research.pain_score,
            urgency_score=customer_research.urgency_score,
            frequency_score=customer_research.frequency_score,
            validation_readiness_score=metrics.get("validation_readiness_score"),
        )

    @staticmethod
    def _market_score(market_brief: MarketBrief | None) -> int | None:
        if market_brief is None:
            return None
        return compute_market_score(
            sam_usd=market_brief.sam_usd,
            tam_usd=market_brief.tam_usd,
            industry_growth_rate_pct=market_brief.industry_growth_rate_pct,
            customer_segment_count=len(market_brief.customer_segments or []),
        )

    @staticmethod
    def _revenue_score(revenue_validation: RevenueValidation | None) -> int | None:
        if revenue_validation is None:
            return None
        metrics = revenue_validation.evaluation_metrics or {}
        return compute_revenue_score(
            willingness_to_pay_score=revenue_validation.willingness_to_pay_score,
            revenue_confidence_score=revenue_validation.revenue_confidence_score,
            evaluation_readiness_score=metrics.get("evaluation_readiness_score"),
        )

    @staticmethod
    def _competition_score(competitor_analysis: CompetitorAnalysis | None) -> int | None:
        if competitor_analysis is None:
            return None
        metrics = competitor_analysis.evaluation_metrics or {}
        return compute_competition_score(
            differentiation_score=metrics.get("differentiation_score"),
            threat_score=metrics.get("threat_score"),
        )

    @staticmethod
    def _growth_score(
        growth_evaluation: GrowthEvaluation | None,
        gtm_plan: GTMPlan | None,
    ) -> int | None:
        growth_metrics = growth_evaluation.evaluation_metrics if growth_evaluation else {}
        gtm_metrics = gtm_plan.ranking_metrics if gtm_plan else {}
        return compute_growth_score(
            growth_readiness_score=(growth_metrics or {}).get("growth_readiness_score"),
            growth_score=growth_evaluation.growth_score if growth_evaluation else None,
            gtm_readiness_score=(gtm_metrics or {}).get("gtm_readiness_score"),
        )

    @staticmethod
    def _founder_fit_score(
        human_proxy: HumanProxyEvaluation | None,
        product_strategy: ProductStrategy | None,
    ) -> tuple[int | None, dict[str, object]]:
        proxy_metrics = human_proxy.evaluation_metrics if human_proxy else {}
        planning_metrics = product_strategy.planning_metrics if product_strategy else {}
        founder_fit_score = human_proxy.founder_fit_score if human_proxy else None
        feasibility_score = human_proxy.feasibility_score if human_proxy else None
        executive_founder_fit = compute_founder_fit_score(
            founder_fit_score=founder_fit_score,
            feasibility_score=feasibility_score,
            planning_readiness_score=(planning_metrics or {}).get("planning_readiness_score"),
            ranking_score=(proxy_metrics or {}).get("ranking_score"),
        )
        founder_fit_details = build_founder_fit_ranking_details(
            founder_fit_score=founder_fit_score,
            feasibility_score=feasibility_score,
            executive_founder_fit=executive_founder_fit,
        )
        return executive_founder_fit, founder_fit_details
