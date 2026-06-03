"""Validation for customer research LLM output."""

from app.agents.customer_research.metrics import SENTIMENT_LABEL_RANGES
from app.agents.customer_research.schemas import (
    CustomerResearchLLMOutput,
    OpportunityCustomerContext,
)


class CustomerResearchValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class CustomerResearchValidator:
    """Ensures customer research output is grounded in provided evidence."""

    def validate(
        self,
        output: CustomerResearchLLMOutput,
        *,
        context: OpportunityCustomerContext,
    ) -> CustomerResearchLLMOutput:
        errors: list[str] = []
        max_index = len(context.complaint_evidence) - 1

        if len(output.executive_summary.strip()) < 30:
            errors.append("executive_summary is too short")

        if not output.representative_complaints:
            errors.append("representative_complaints must not be empty")

        if not output.supporting_evidence:
            errors.append("supporting_evidence must not be empty")

        label_range = SENTIMENT_LABEL_RANGES.get(output.customer_sentiment)
        if label_range is not None:
            low, high = label_range
            if not (low <= output.sentiment_score <= high):
                errors.append(
                    "sentiment_score inconsistent with customer_sentiment label"
                )

        if output.cares_verdict == "yes" and output.pain_score < 40:
            errors.append("cares_verdict=yes requires pain_score >= 40")

        if output.cares_verdict == "no" and output.pain_score > 60:
            errors.append("cares_verdict=no requires pain_score <= 60")

        for index, complaint in enumerate(output.representative_complaints, start=1):
            if complaint.complaint_index is not None:
                if complaint.complaint_index < 0 or complaint.complaint_index > max_index:
                    errors.append(
                        f"representative_complaints[{index}].complaint_index out of range"
                    )
                else:
                    evidence = context.complaint_evidence[complaint.complaint_index]
                    if complaint.verbatim_quote.lower() not in evidence.verbatim_quote.lower():
                        if evidence.verbatim_quote.lower() not in complaint.verbatim_quote.lower():
                            errors.append(
                                f"representative_complaints[{index}] quote not grounded "
                                "in complaint evidence"
                            )

        for index, item in enumerate(output.supporting_evidence, start=1):
            if len(item.excerpt.strip()) < 10:
                errors.append(f"supporting_evidence[{index}].excerpt is too short")
            if item.complaint_index is not None:
                if item.complaint_index < 0 or item.complaint_index > max_index:
                    errors.append(
                        f"supporting_evidence[{index}].complaint_index out of range"
                    )

        if not context.complaint_evidence and output.cares_verdict != "no":
            errors.append("cannot conclude customers care without complaint evidence")

        if errors:
            raise CustomerResearchValidationError(errors)

        return output
