"""Roadmap generation and evaluation metrics for growth strategy."""

from app.agents.growth_strategy.schemas import GrowthPhaseOutput, GrowthStrategyLLMOutput


def generate_growth_roadmap(
    phases: list[GrowthPhaseOutput],
) -> list[dict[str, object]]:
    """Build a sequential growth roadmap from long-term phases."""
    items: list[dict[str, object]] = []
    start_month = 1
    for index, phase in enumerate(phases, start=1):
        end_month = start_month + phase.duration_months - 1
        items.append(
            {
                "phase_number": index,
                "phase_name": phase.phase_name,
                "start_month": start_month,
                "end_month": end_month,
                "duration_months": phase.duration_months,
                "focus": phase.focus,
                "growth_levers": phase.growth_levers,
                "milestones": phase.milestones,
            }
        )
        start_month = end_month + 1
    return items


def compute_evaluation_metrics(
    output: GrowthStrategyLLMOutput,
    *,
    growth_roadmap: list[dict[str, object]],
) -> dict[str, float | int]:
    high_partnerships = sum(
        1 for item in output.partnership_opportunities if item.priority == "high"
    )
    high_expansion = sum(
        1 for item in output.market_expansion_opportunities if item.priority == "high"
    )
    roadmap_months = sum(phase.duration_months for phase in output.growth_phases)

    growth_readiness = min(
        100,
        int(
            output.growth_score * 0.30
            + output.scalability_score * 0.25
            + (100 - output.risk_score) * 0.15
            + min(len(output.partnership_opportunities), 5) * 4
            + min(len(output.market_expansion_opportunities), 5) * 3
            + min(len(output.supporting_evidence), 6) * 2
        ),
    )

    return {
        "growth_score": output.growth_score,
        "scalability_score": output.scalability_score,
        "risk_score": output.risk_score,
        "seo_potential_score": output.seo_potential.score,
        "referral_potential_score": output.referral_potential.score,
        "paid_acquisition_potential_score": output.paid_acquisition_potential.score,
        "partnership_opportunity_count": len(output.partnership_opportunities),
        "high_priority_partnership_count": high_partnerships,
        "market_expansion_count": len(output.market_expansion_opportunities),
        "high_priority_expansion_count": high_expansion,
        "roadmap_item_count": len(growth_roadmap),
        "growth_roadmap_months": roadmap_months,
        "growth_readiness_score": growth_readiness,
    }
