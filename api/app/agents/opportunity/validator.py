"""Validation for synthesized opportunity briefs."""

import re

from app.agents.opportunity.schemas import ComplaintEvidence, OpportunityLLMOutput

COMMON_WORDS = frozenset(
    {
        "Teams",
        "They",
        "The",
        "Our",
        "No",
        "Yes",
        "And",
        "But",
        "For",
        "With",
        "Use",
        "Today",
        "Manual",
        "When",
        "What",
        "This",
        "That",
        "From",
        "Into",
    }
)


class OpportunityValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class OpportunityValidator:
    """Ensures LLM output stays grounded in complaint evidence."""

    def validate(
        self,
        output: OpportunityLLMOutput,
        *,
        evidence: list[ComplaintEvidence],
        topic: str,
    ) -> OpportunityLLMOutput:
        errors: list[str] = []

        if len(output.title.strip()) < 5:
            errors.append("title is too short")

        if len(output.explanation.strip()) < 20:
            errors.append("explanation is too short")

        if len(output.problem_statement.strip()) < 20:
            errors.append("problem_statement is too short")

        evidence_text = " ".join(
            f"{complaint.summary} {complaint.verbatim_quote} "
            f"{' '.join(complaint.product_mentions)}"
            for complaint in evidence
        ).lower()

        mentioned_products = self._extract_product_candidates(output.existing_alternatives)
        known_products = {
            product.lower()
            for complaint in evidence
            for product in complaint.product_mentions
            if product.strip()
        }

        for product in mentioned_products:
            product_lower = product.lower()
            if product_lower in evidence_text:
                continue
            if product_lower in known_products:
                continue
            errors.append(f"existing_alternatives mentions ungrounded product: {product}")

        if topic.lower() not in evidence_text and topic.lower() not in output.title.lower():
            errors.append("topic not reflected in evidence or title")

        if errors:
            raise OpportunityValidationError(errors)

        return output

    @staticmethod
    def _extract_product_candidates(text: str) -> list[str]:
        candidates = re.findall(r"\b[A-Z][A-Za-z0-9+\-_.]{3,}\b", text)
        return [candidate for candidate in candidates if candidate not in COMMON_WORDS]
