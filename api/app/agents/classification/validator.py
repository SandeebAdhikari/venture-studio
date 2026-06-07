"""Validation for LLM classification output."""

from app.agents.classification.founder_signal_pairs import validate_bf_jtbd_pair
from app.agents.classification.founder_signals import validate_founder_signal_codes
from app.agents.classification.problem_category_alignment import normalize_problem_category
from app.agents.classification.schemas import ClassificationLLMOutput
from app.agents.classification.source_text import verbatim_quote_in_source
from app.agents.classification.taxonomy import CUSTOMER_TYPES, INDUSTRIES, PROBLEM_CATEGORIES
from app.logging import get_logger

logger = get_logger(__name__)


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

        normalized_category = normalize_problem_category(
            output.problem_category,
            summary=output.summary,
            verbatim_quote=output.verbatim_quote,
        )
        if normalized_category != output.problem_category:
            output = output.model_copy(update={"problem_category": normalized_category})

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

            validated_signals = validate_founder_signal_codes(
                business_function_code=output.business_function_code,
                jtbd_code=output.jtbd_code,
                consequence_code=output.consequence_code,
            )
            if validated_signals is None:
                errors.append(
                    "invalid founder signal codes: "
                    f"business_function_code={output.business_function_code}, "
                    f"jtbd_code={output.jtbd_code}, "
                    f"consequence_code={output.consequence_code}"
                )
            elif not validate_bf_jtbd_pair(
                validated_signals[0],
                validated_signals[1],
            ):
                logger.warning(
                    "incoherent_bf_jtbd_pair",
                    extra={
                        "business_function_code": validated_signals[0],
                        "jtbd_code": validated_signals[1],
                    },
                )

        if errors:
            raise ClassificationValidationError(errors)

        return output
