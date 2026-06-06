"""Grounding helpers for revenue validation evidence indices."""

from __future__ import annotations

from app.agents.revenue_validation.schemas import (
    OpportunityRevenueContext,
    RevenueValidationLLMOutput,
)


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
    output: RevenueValidationLLMOutput,
    context: OpportunityRevenueContext,
) -> RevenueValidationLLMOutput:
    """Coerce invalid complaint/competitor indices for singleton contexts only."""
    complaint_singleton = len(context.complaint_evidence) == 1
    competitor_singleton = len(context.competitor_pricing) == 1
    max_complaint_index = len(context.complaint_evidence) - 1
    max_competitor_index = len(context.competitor_pricing) - 1

    supporting = []
    for item in output.supporting_evidence:
        complaint_index = item.complaint_index
        competitor_index = item.competitor_index
        if complaint_singleton:
            complaint_index = _coerce_singleton_index(
                complaint_index,
                max_index=max_complaint_index,
            )
        if competitor_singleton:
            competitor_index = _coerce_singleton_index(
                competitor_index,
                max_index=max_competitor_index,
            )
        supporting.append(
            item.model_copy(
                update={
                    "complaint_index": complaint_index,
                    "competitor_index": competitor_index,
                }
            )
        )

    return output.model_copy(update={"supporting_evidence": supporting})
