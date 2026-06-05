"""Validation for LLM classification output."""

from app.agents.classification.founder_signals import validate_founder_signal_codes
from app.agents.classification.schemas import ClassificationLLMOutput
from app.agents.classification.source_text import verbatim_quote_in_source
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
            elif not verbatim_quote_in_source(quote=quote, source_text=source_text):
                errors.append("verbatim_quote must appear in source text")

            if len(output.summary.strip()) < 10:
                errors.append("summary is too short")

            if validate_founder_signal_codes(
                business_function_code=output.business_function_code,
                jtbd_code=output.jtbd_code,
                consequence_code=output.consequence_code,
            ) is None:
                errors.append(
                    "invalid founder signal codes: "
                    f"business_function_code={output.business_function_code}, "
                    f"jtbd_code={output.jtbd_code}, "
                    f"consequence_code={output.consequence_code}"
                )

        if errors:
            raise ClassificationValidationError(errors)

        return output
