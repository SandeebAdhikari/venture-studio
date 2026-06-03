"""Roadmap generation and ranking metrics for go-to-market plans."""

from app.agents.go_to_market.schemas import AcquisitionPhaseOutput, GoToMarketLLMOutput


def generate_acquisition_roadmap(
    phases: list[AcquisitionPhaseOutput],
) -> list[dict[str, object]]:
    """Build a sequential acquisition roadmap from GTM phases."""
    items: list[dict[str, object]] = []
    start_week = 1
    for index, phase in enumerate(phases, start=1):
        end_week = start_week + phase.duration_weeks - 1
        items.append(
            {
                "phase_number": index,
                "phase_name": phase.phase_name,
                "start_week": start_week,
                "end_week": end_week,
                "duration_weeks": phase.duration_weeks,
                "focus": phase.focus,
                "channels": phase.channels,
                "targets": phase.targets,
                "milestones": phase.milestones,
            }
        )
        start_week = end_week + 1
    return items


def compute_ranking_metrics(
    output: GoToMarketLLMOutput,
    *,
    acquisition_roadmap: list[dict[str, object]],
) -> dict[str, float | int]:
    primary_channels = sum(
        1 for channel in output.acquisition_channels if channel.priority == "primary"
    )
    high_seo = sum(1 for item in output.seo_opportunities if item.priority == "high")
    high_partnerships = sum(1 for item in output.partnerships if item.priority == "high")
    roadmap_weeks = sum(phase.duration_weeks for phase in output.acquisition_phases)

    gtm_readiness = min(
        100,
        int(
            output.confidence_score * 0.35
            + min(len(output.acquisition_channels), 6) * 6
            + min(len(output.customer_personas), 4) * 5
            + min(len(output.seo_opportunities), 6) * 3
            + min(len(output.partnerships), 4) * 4
            + min(len(output.supporting_evidence), 6) * 2
        ),
    )

    channel_cac_values = [
        channel.estimated_cac_usd
        for channel in output.acquisition_channels
        if channel.estimated_cac_usd >= 0
    ]
    avg_channel_cac = (
        sum(channel_cac_values) / len(channel_cac_values) if channel_cac_values else 0.0
    )

    return {
        "confidence_score": output.confidence_score,
        "estimated_cac_usd": output.estimated_cac_usd,
        "gtm_readiness_score": gtm_readiness,
        "persona_count": len(output.customer_personas),
        "acquisition_channel_count": len(output.acquisition_channels),
        "primary_channel_count": primary_channels,
        "seo_opportunity_count": len(output.seo_opportunities),
        "high_priority_seo_count": high_seo,
        "partnership_count": len(output.partnerships),
        "high_priority_partnership_count": high_partnerships,
        "roadmap_item_count": len(acquisition_roadmap),
        "acquisition_roadmap_weeks": roadmap_weeks,
        "avg_channel_cac_usd": round(avg_channel_cac, 2),
    }
