"""Discovery funnel metrics for empty-outcome venture reports."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.db.enums import PipelineStage
from app.repositories import RepositoryContainer


class VentureDiscoveryFunnel(BaseModel):
    """Pipeline discovery counts surfaced in empty-outcome venture reports."""

    signals_collected: int = 0
    complaints_extracted: int = 0
    patterns_found: int = 0
    opportunities_generated: int = 0
    ranked_opportunity_count: int = 0


def build_empty_discovery_explanation(funnel: VentureDiscoveryFunnel) -> list[str]:
    """Deterministic narrative for why no founder-grade opportunities were found."""
    lines = [
        "No founder-grade opportunities were ranked for this run. Discovery processed "
        "real signal data but did not surface a venture thesis strong enough to research "
        "and rank.",
        "",
        "**Likely reasons:**",
    ]

    if funnel.signals_collected == 0:
        lines.append("- No signals were collected — check source configuration.")
    elif funnel.complaints_extracted == 0:
        lines.append(
            "- Signals were collected but classification produced no usable complaints."
        )
    elif funnel.patterns_found == 0:
        lines.append(
            "- Complaints did not form recurring phrase clusters or taxonomy fallback "
            "patterns that passed coherence gates."
        )
    elif funnel.opportunities_generated == 0:
        lines.append(
            "- Patterns were detected but opportunity synthesis did not produce "
            "persisted opportunities (skipped, failed, or filtered)."
        )
    else:
        lines.append(
            "- Opportunities existed but none met executive ranking coverage thresholds "
            "for a founder-grade recommendation."
        )

    lines.extend(
        [
            "",
            "**Quality bar:** Opportunities require recurring, coherent complaint evidence "
            "before research agents run. An empty outcome is valid when the signal batch "
            "does not meet that bar.",
        ]
    )
    return lines


async def load_discovery_funnel(
    repos: RepositoryContainer,
    *,
    pipeline_run_id: UUID | None,
    ranked_opportunity_count: int = 0,
) -> VentureDiscoveryFunnel:
    """Load funnel counters from pipeline stage runs when available."""
    funnel = VentureDiscoveryFunnel(ranked_opportunity_count=ranked_opportunity_count)
    if pipeline_run_id is None:
        return funnel

    run = await repos.pipelines.get_by_id_with_stages(pipeline_run_id)
    if run is None:
        return funnel

    for stage_run in run.stage_runs:
        stage = stage_run.stage
        if stage == PipelineStage.COLLECT.value:
            funnel.signals_collected = stage_run.items_out
        elif stage == PipelineStage.CLASSIFY.value:
            funnel.complaints_extracted = stage_run.items_out
        elif stage == PipelineStage.GENERATE_OPPORTUNITIES.value:
            funnel.patterns_found = stage_run.items_in
            funnel.opportunities_generated = stage_run.items_out

    return funnel
