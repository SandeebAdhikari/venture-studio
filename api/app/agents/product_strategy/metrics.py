"""Deterministic roadmap generation and planning metrics."""

from app.agents.product_strategy.schemas import (
    DevelopmentPhaseOutput,
    EstimatedTimelineOutput,
    ProductStrategyLLMOutput,
)


def generate_roadmap(
    phases: list[DevelopmentPhaseOutput],
    timeline: EstimatedTimelineOutput,
) -> list[dict[str, object]]:
    """Build a sequential roadmap from development phases and timeline."""
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
                "deliverables": phase.deliverables,
                "milestones": phase.milestones,
            }
        )
        start_week = end_week + 1

    return items


def compute_planning_metrics(
    output: ProductStrategyLLMOutput,
    *,
    roadmap: list[dict[str, object]],
) -> dict[str, float | int]:
    p0_count = sum(1 for item in output.feature_priorities if item.priority == "P0")
    high_risk_count = sum(1 for item in output.technical_risks if item.severity == "high")
    phase_weeks = sum(phase.duration_weeks for phase in output.development_phases)

    planning_readiness = min(
        100,
        int(
            min(len(output.core_features), 8) * 6
            + min(len(output.feature_priorities), 10) * 4
            + min(len(output.development_phases), 4) * 8
            + min(len(output.technical_risks), 6) * 3
            + min(len(output.supporting_evidence), 6) * 2
        ),
    )

    return {
        "core_feature_count": len(output.core_features),
        "feature_priority_count": len(output.feature_priorities),
        "p0_feature_count": p0_count,
        "development_phase_count": len(output.development_phases),
        "technical_risk_count": len(output.technical_risks),
        "high_risk_count": high_risk_count,
        "roadmap_item_count": len(roadmap),
        "total_weeks": output.estimated_timeline.total_weeks,
        "mvp_weeks": output.estimated_timeline.mvp_weeks,
        "phase_weeks_sum": phase_weeks,
        "planning_readiness_score": planning_readiness,
    }
