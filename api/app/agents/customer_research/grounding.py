"""Grounding helpers for customer research representative quotes."""

from __future__ import annotations

from app.agents.classification.source_text import verbatim_quote_in_source
from app.agents.customer_research.schemas import (
    ComplaintEvidenceItem,
    CustomerResearchLLMOutput,
    OpportunityCustomerContext,
    RepresentativeComplaintOutput,
    SupportingEvidenceOutput,
)


def representative_quote_grounded(*, generated: str, evidence_quote: str) -> bool:
    """True when generated quote matches stored complaint evidence (normalized)."""
    if verbatim_quote_in_source(quote=generated, source_text=evidence_quote):
        return True
    return verbatim_quote_in_source(quote=evidence_quote, source_text=generated)


def normalize_complaint_indices(
    output: CustomerResearchLLMOutput,
    context: OpportunityCustomerContext,
) -> CustomerResearchLLMOutput:
    """Coerce invalid complaint_index values to 0 for singleton opportunities only."""
    if len(context.complaint_evidence) != 1:
        return output

    max_index = 0

    def _coerce(index: int | None) -> int | None:
        if index is None:
            return None
        if 0 <= index <= max_index:
            return index
        return 0

    representative = [
        complaint.model_copy(update={"complaint_index": _coerce(complaint.complaint_index)})
        for complaint in output.representative_complaints
    ]
    supporting = [
        item.model_copy(update={"complaint_index": _coerce(item.complaint_index)})
        for item in output.supporting_evidence
    ]
    return output.model_copy(
        update={
            "representative_complaints": representative,
            "supporting_evidence": supporting,
        }
    )


def canonicalize_representative_complaints(
    output: CustomerResearchLLMOutput,
    context: OpportunityCustomerContext,
) -> CustomerResearchLLMOutput:
    """Replace ungrounded quotes with exact evidence text when complaint_index is valid."""
    if not context.complaint_evidence:
        return output

    max_index = len(context.complaint_evidence) - 1
    updated: list[RepresentativeComplaintOutput] = []

    for complaint in output.representative_complaints:
        idx = complaint.complaint_index
        if idx is not None and 0 <= idx <= max_index:
            evidence = context.complaint_evidence[idx]
            if not representative_quote_grounded(
                generated=complaint.verbatim_quote,
                evidence_quote=evidence.verbatim_quote,
            ):
                complaint = _copy_from_evidence(complaint, evidence)
        updated.append(complaint)

    return output.model_copy(update={"representative_complaints": updated})


def _copy_from_evidence(
    complaint: RepresentativeComplaintOutput,
    evidence: ComplaintEvidenceItem,
) -> RepresentativeComplaintOutput:
    source_type = complaint.source_type
    if evidence.source_type in {
        "complaint",
        "discussion",
        "review",
        "forum",
        "social",
    }:
        source_type = evidence.source_type  # type: ignore[assignment]

    return complaint.model_copy(
        update={
            "verbatim_quote": evidence.verbatim_quote,
            "severity": evidence.severity,
            "source_type": source_type,
        }
    )
