"""Validation for synthesized opportunity briefs."""

from __future__ import annotations

import re
from typing import Literal

from app.agents.opportunity.schemas import ComplaintEvidence, OpportunityLLMOutput

PatternSource = Literal[
    "phrase_clustering",
    "token_clustering",
    "founder_signal_clustering",
    "taxonomy_fallback",
]
FOUNDER_SIGNAL_PATTERN_SOURCE: PatternSource = "founder_signal_clustering"

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

IGNORED_PRODUCT_CANDIDATES = frozenset({"None", "N/A", "NA"})


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
        anchor_phrase: str | None = None,
        domain_code: str | None = None,
        category_code: str | None = None,
        pattern_source: PatternSource | None = None,
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

        if pattern_source != FOUNDER_SIGNAL_PATTERN_SOURCE and not self._topic_reflected_in_output(
            topic=topic,
            anchor_phrase=anchor_phrase,
            domain_code=domain_code,
            category_code=category_code,
            evidence_text=evidence_text,
            title=output.title,
        ):
            errors.append("topic not reflected in evidence or title")

        if errors:
            raise OpportunityValidationError(errors)

        return output

    @staticmethod
    def _topic_reflected_in_output(
        *,
        topic: str,
        anchor_phrase: str | None,
        domain_code: str | None,
        category_code: str | None,
        evidence_text: str,
        title: str,
    ) -> bool:
        """B2: Match display topic, anchor phrase, or taxonomy labels — not cosmetic M4 tokens only."""
        title_lower = title.lower()
        references: list[str] = []

        if topic.strip():
            references.append(topic.lower())
        if anchor_phrase and anchor_phrase.strip():
            references.append(anchor_phrase.lower())
        if domain_code:
            references.append(domain_code.replace("_", " ").lower())
            references.append(domain_code.lower())
        if category_code:
            references.append(category_code.replace("_", " ").lower())
            references.append(category_code.lower())

        for reference in references:
            if not reference:
                continue
            if reference in evidence_text or reference in title_lower:
                return True

        return False

    @staticmethod
    def _extract_product_candidates(text: str) -> list[str]:
        if re.search(r"\bno\s+named\s+products\b", text, flags=re.IGNORECASE):
            return []
        if re.search(r"\bnone\s+mentioned\b", text, flags=re.IGNORECASE):
            return []

        candidates = re.findall(r"\b[A-Z][A-Za-z0-9+\-_.]{3,}\b", text)
        return [
            candidate
            for candidate in candidates
            if candidate not in COMMON_WORDS and candidate not in IGNORED_PRODUCT_CANDIDATES
        ]
