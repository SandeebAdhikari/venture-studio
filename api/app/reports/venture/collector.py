"""Collect agent outputs for venture recommendation reports."""

from __future__ import annotations

from uuid import UUID

from app.reports.venture.analysis import build_recommendation, build_risk_items
from app.reports.venture.schemas import CustomerEvidenceItem, VentureOpportunityReport
from app.repositories import RepositoryContainer
from app.schemas.executive_ranking import ExecutiveRankingEntryRead


def _format_usd(value: float | None) -> str:
    if value is None:
        return "Not estimated"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def _bullet_lines(items: list[str], *, empty: str = "_No data available._") -> str:
    if not items:
        return empty
    return "\n".join(f"- {item}" for item in items)


class VentureReportCollector:
    """Assembles founder-readable sections from all agent outputs."""

    def __init__(self, repos: RepositoryContainer) -> None:
        self._repos = repos

    async def collect_opportunity(
        self,
        entry: ExecutiveRankingEntryRead,
        *,
        founder_profile_id: UUID | None,
    ) -> VentureOpportunityReport:
        opportunity = await self._repos.opportunities.get_by_id_with_relations(entry.opportunity_id)
        if opportunity is None:
            raise ValueError(f"Opportunity {entry.opportunity_id} not found")

        market_brief = await self._repos.market_briefs.get_current_for_opportunity(entry.opportunity_id)
        competitor = await self._repos.competitor_analyses.get_current_for_opportunity(entry.opportunity_id)
        if competitor is not None:
            competitor = await self._repos.competitor_analyses.get_by_id_with_profiles(competitor.id)
        customer_current = await self._repos.customer_research.get_current_for_opportunity(
            entry.opportunity_id
        )
        customer = None
        if customer_current is not None:
            customer = await self._repos.customer_research.get_by_id_with_evidence(
                customer_current.id
            )
        revenue = await self._repos.revenue_validations.get_current_for_opportunity(entry.opportunity_id)
        if revenue is not None:
            revenue = await self._repos.revenue_validations.get_by_id_with_evidence(revenue.id)
        product = await self._repos.product_strategies.get_current_for_opportunity(entry.opportunity_id)
        if product is not None:
            product = await self._repos.product_strategies.get_by_id_with_evidence(product.id)
        gtm = await self._repos.gtm_plans.get_current_for_opportunity(entry.opportunity_id)
        growth = await self._repos.growth_evaluations.get_current_for_opportunity(entry.opportunity_id)
        human_proxy = None
        if founder_profile_id is not None:
            human_proxy = await self._repos.human_proxy_evaluations.get_current_for_opportunity(
                entry.opportunity_id,
                founder_profile_id=founder_profile_id,
            )

        customer_evidence = self._customer_evidence(opportunity, customer)
        competitor_threat = None
        if competitor and competitor.evaluation_metrics:
            competitor_threat = competitor.evaluation_metrics.get("threat_level")

        risks = build_risk_items(
            growth_risk_score=growth.risk_score if growth else None,
            technical_risks=list(product.technical_risks or []) if product else [],
            execution_complexity=human_proxy.execution_complexity if human_proxy else None,
            capital_requirements=human_proxy.capital_requirements if human_proxy else None,
            competitor_threat_level=str(competitor_threat) if competitor_threat else None,
            revenue_confidence_score=revenue.revenue_confidence_score if revenue else None,
        )

        recommendation = build_recommendation(
            final_score=entry.final_opportunity_score,
            human_proxy_recommendation=str(human_proxy.recommendation) if human_proxy else None,
            pain_score=entry.pain_score,
            founder_fit_score=entry.founder_fit_score,
            rank=entry.rank,
        )

        return VentureOpportunityReport(
            rank=entry.rank,
            opportunity_id=entry.opportunity_id,
            title=opportunity.title,
            final_opportunity_score=entry.final_opportunity_score,
            pain_score=entry.pain_score,
            market_score=entry.market_score,
            revenue_score=entry.revenue_score,
            competition_score=entry.competition_score,
            growth_score=entry.growth_score,
            founder_fit_score=entry.founder_fit_score,
            opportunity_summary=self._opportunity_summary(opportunity),
            market_analysis=self._market_analysis(market_brief),
            competitor_analysis=self._competitor_analysis(competitor),
            customer_evidence=customer_evidence,
            revenue_analysis=self._revenue_analysis(revenue),
            mvp_plan=self._mvp_plan(product),
            go_to_market_strategy=self._gtm_strategy(gtm),
            growth_strategy=self._growth_strategy(growth),
            founder_fit_analysis=self._founder_fit_analysis(human_proxy),
            risk_analysis=risks,
            recommendation=recommendation,
        )

    @staticmethod
    def _opportunity_summary(opportunity) -> str:
        return (
            f"**Problem:** {opportunity.problem_statement}\n\n"
            f"**Target user:** {opportunity.target_user}\n\n"
            f"**Frequency signal:** {opportunity.frequency_signal}\n\n"
            f"**Existing alternatives:** {opportunity.existing_alternatives}\n\n"
            f"**Gap:** {opportunity.gap}\n\n"
            f"**Confidence:** {opportunity.confidence_score:.0%}"
        )

    @staticmethod
    def _market_analysis(market_brief) -> str:
        if market_brief is None:
            return "_Market research not yet completed for this opportunity._"

        segments = [
            segment.get("name") or segment.get("segment") or "Segment"
            for segment in (market_brief.customer_segments or [])[:5]
        ]
        trends = [
            trend.get("trend") or trend.get("title") or str(trend)
            for trend in (market_brief.industry_trends or [])[:5]
        ]

        lines = [
            market_brief.executive_summary or "Market brief available.",
            "",
            f"- **SAM:** {_format_usd(market_brief.sam_usd)}",
            f"- **TAM:** {_format_usd(market_brief.tam_usd)}",
            f"- **Industry growth:** {market_brief.industry_growth_rate_pct or 'N/A'}%",
            "",
            "**Customer segments**",
            _bullet_lines(segments),
            "",
            "**Industry trends**",
            _bullet_lines(trends),
        ]
        return "\n".join(lines)

    @staticmethod
    def _competitor_analysis(competitor) -> str:
        if competitor is None:
            return "_Competitor analysis not yet completed for this opportunity._"

        metrics = competitor.evaluation_metrics or {}
        profile_lines = []
        for profile in (competitor.profiles or [])[:5]:
            profile_lines.append(
                f"{profile.name}: {profile.positioning} "
                f"(sentiment {profile.sentiment_score:+.2f})"
            )

        gap_lines = [
            gap.get("gap") or gap.get("description") or str(gap)
            for gap in (competitor.competitive_gaps or [])[:5]
        ]

        lines = [
            competitor.executive_summary or "Competitor landscape analyzed.",
            "",
            f"- **Competitors tracked:** {metrics.get('competitor_count', len(competitor.profiles or []))}",
            f"- **Differentiation score:** {metrics.get('differentiation_score', 'N/A')}",
            f"- **Threat level:** {metrics.get('threat_level', 'N/A')}",
            "",
            "**Key competitors**",
            _bullet_lines(profile_lines),
            "",
            "**Competitive gaps**",
            _bullet_lines(gap_lines),
        ]
        return "\n".join(lines)

    @staticmethod
    def _customer_evidence(opportunity, customer) -> list[CustomerEvidenceItem]:
        items: list[CustomerEvidenceItem] = []

        if customer and customer.evidence:
            for evidence in customer.evidence[:5]:
                items.append(
                    CustomerEvidenceItem(
                        summary=evidence.excerpt,
                        verbatim_quote=evidence.excerpt,
                        severity=3,
                        source_url=evidence.url,
                    )
                )

        if not items:
            for complaint in sorted(opportunity.complaints, key=lambda c: c.severity, reverse=True)[:5]:
                source_url = complaint.signal.url if complaint.signal else None
                items.append(
                    CustomerEvidenceItem(
                        summary=complaint.summary,
                        verbatim_quote=complaint.verbatim_quote,
                        severity=complaint.severity,
                        source_url=source_url,
                    )
                )

        return items

    @staticmethod
    def _revenue_analysis(revenue) -> str:
        if revenue is None:
            return "_Revenue validation not yet completed for this opportunity._"

        pricing_lines = []
        for rec in (revenue.pricing_recommendations or [])[:3]:
            price = rec.get("recommended_price_usd") or rec.get("price_usd")
            tier = rec.get("tier") or rec.get("plan_name") or "Tier"
            if price is not None:
                pricing_lines.append(f"{tier}: ${price}/mo")
            else:
                pricing_lines.append(str(tier))

        lines = [
            revenue.executive_summary or "Revenue potential assessed.",
            "",
            f"- **Willingness to pay:** {revenue.willingness_to_pay_score}/100",
            f"- **Revenue confidence:** {revenue.revenue_confidence_score}/100",
            "",
            "**Pricing recommendations**",
            _bullet_lines(pricing_lines, empty="_No pricing tiers recommended yet._"),
        ]
        return "\n".join(lines)

    @staticmethod
    def _mvp_plan(product) -> str:
        if product is None:
            return "_Product strategy not yet completed for this opportunity._"

        feature_lines = [
            feature.get("name") or feature.get("feature") or str(feature)
            for feature in (product.core_features or [])[:5]
        ]
        roadmap_lines = [
            item.get("milestone") or item.get("phase") or item.get("title") or str(item)
            for item in (product.roadmap or [])[:5]
        ]
        timeline = product.estimated_timeline or {}
        mvp_weeks = timeline.get("mvp_weeks") or timeline.get("total_weeks")

        lines = [
            product.executive_summary or product.mvp_definition,
            "",
            f"**MVP definition:** {product.mvp_definition}",
        ]
        if mvp_weeks:
            lines.append(f"**Estimated MVP timeline:** {mvp_weeks} weeks")
        lines.extend(
            [
                "",
                "**Core features**",
                _bullet_lines(feature_lines),
                "",
                "**Roadmap highlights**",
                _bullet_lines(roadmap_lines),
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _gtm_strategy(gtm) -> str:
        if gtm is None:
            return "_Go-to-market plan not yet completed for this opportunity._"

        channel_lines = [
            channel.get("channel") or channel.get("name") or str(channel)
            for channel in (gtm.acquisition_channels or [])[:5]
        ]
        persona_lines = [
            persona.get("name") or persona.get("persona") or str(persona)
            for persona in (gtm.customer_personas or [])[:3]
        ]

        lines = [
            gtm.gtm_report[:500] + ("..." if len(gtm.gtm_report) > 500 else ""),
            "",
            f"- **GTM confidence:** {gtm.confidence_score}/100",
            f"- **Estimated CAC:** ${gtm.estimated_cac_usd:,.0f}",
            "",
            "**Target personas**",
            _bullet_lines(persona_lines),
            "",
            "**Acquisition channels**",
            _bullet_lines(channel_lines),
        ]
        return "\n".join(lines)

    @staticmethod
    def _growth_strategy(growth) -> str:
        if growth is None:
            return "_Growth strategy not yet completed for this opportunity._"

        metrics = growth.evaluation_metrics or {}
        roadmap_lines = [
            item.get("phase") or item.get("title") or str(item)
            for item in (growth.growth_roadmap or [])[:5]
        ]

        lines = [
            growth.executive_summary or "Long-term growth path defined.",
            "",
            f"- **Growth score:** {growth.growth_score}/100",
            f"- **Scalability score:** {growth.scalability_score}/100",
            f"- **Risk score:** {growth.risk_score}/100",
            f"- **Growth readiness:** {metrics.get('growth_readiness_score', 'N/A')}",
            "",
            "**Growth roadmap**",
            _bullet_lines(roadmap_lines),
        ]
        return "\n".join(lines)

    @staticmethod
    def _founder_fit_analysis(human_proxy) -> str:
        if human_proxy is None:
            return "_Founder fit analysis not yet completed for this opportunity._"

        fit = human_proxy.founder_fit_analysis or {}
        feasibility = human_proxy.implementation_feasibility or {}
        learning = human_proxy.learning_curve or {}

        skill_matches = fit.get("skill_matches") or []
        skill_gaps = fit.get("skill_gaps") or []

        lines = [
            human_proxy.executive_summary or fit.get("rationale") or "Founder fit evaluated.",
            "",
            f"- **Founder fit score:** {human_proxy.founder_fit_score}/100",
            f"- **Feasibility score:** {human_proxy.feasibility_score}/100",
            f"- **Recommendation:** {human_proxy.recommendation}",
            f"- **Build complexity:** {feasibility.get('build_complexity', 'N/A')}",
            f"- **Learning curve:** {learning.get('difficulty', 'N/A')}",
            "",
            "**Skill matches**",
            _bullet_lines([str(item) for item in skill_matches]),
            "",
            "**Skill gaps**",
            _bullet_lines([str(item) for item in skill_gaps], empty="_No major skill gaps identified._"),
        ]
        return "\n".join(lines)
