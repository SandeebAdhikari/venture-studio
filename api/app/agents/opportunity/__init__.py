"""Opportunity generation agent."""

from app.agents.opportunity.graph import GRAPH_NAME, OpportunityGeneratorAgent
from app.agents.opportunity.schemas import (
    ComplaintPattern,
    GenerationBatchResult,
    OpportunityGenerationResult,
)

__all__ = [
    "GRAPH_NAME",
    "ComplaintPattern",
    "GenerationBatchResult",
    "OpportunityGenerationResult",
    "OpportunityGeneratorAgent",
    "OpportunityGeneratorService",
]


def __getattr__(name: str):
    if name == "OpportunityGeneratorService":
        from app.agents.opportunity.service import OpportunityGeneratorService

        return OpportunityGeneratorService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
