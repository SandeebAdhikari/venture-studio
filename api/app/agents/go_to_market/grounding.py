"""Grounding helpers for go-to-market evidence indices."""

from __future__ import annotations

from app.agents.go_to_market.schemas import GoToMarketLLMOutput, OpportunityGTMContext


def _coerce_singleton_index(index: int | None, *, max_index: int) -> int | None:
    """Map out-of-range indices to 0 when only one valid index exists."""
    if index is None:
        return None
    if 0 <= index <= max_index:
        return index
    if max_index == 0:
        return 0
    return index


def normalize_evidence_indices(
    output: GoToMarketLLMOutput,
    context: OpportunityGTMContext,
) -> GoToMarketLLMOutput:
    """Coerce invalid complaint indices for singleton contexts only."""
    complaint_singleton = len(context.complaint_evidence) == 1
    max_complaint_index = len(context.complaint_evidence) - 1

    supporting = []
    for item in output.supporting_evidence:
        complaint_index = item.complaint_index
        if complaint_singleton:
            complaint_index = _coerce_singleton_index(
                complaint_index,
                max_index=max_complaint_index,
            )
        supporting.append(
            item.model_copy(update={"complaint_index": complaint_index})
        )

    return output.model_copy(update={"supporting_evidence": supporting})
