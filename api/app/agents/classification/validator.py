"""Validation for LLM classification output."""

from app.agents.classification.schemas import ClassificationLLMOutput
from app.agents.classification.taxonomy import CUSTOMER_TYPES, INDUSTRIES, PROBLEM_CATEGORIES


class ClassificationValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class ClassificationValidator:
    def validate(
        self,
        output: ClassificationLLMOutput,
        *,
        source_text: str,
    ) -> ClassificationLLMOutput:
        errors: list[str] = []

        if output.problem_category not in PROBLEM_CATEGORIES:
            errors.append(f"invalid problem_category: {output.problem_category}")

        if output.industry not in INDUSTRIES:
            errors.append(f"invalid industry: {output.industry}")

        if output.customer_type not in CUSTOMER_TYPES:
            errors.append(f"invalid customer_type: {output.customer_type}")

        if output.is_complaint:
            quote = output.verbatim_quote.strip()
            if not quote:
                errors.append("verbatim_quote is required for complaints")
            elif quote not in source_text and quote.lower() not in source_text.lower():
                errors.append("verbatim_quote must appear in source text")

            if len(output.summary.strip()) < 10:
                errors.append("summary is too short")

        if errors:
            raise ClassificationValidationError(errors)

        return output
