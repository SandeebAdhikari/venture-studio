"""Validation for human proxy LLM output."""

from app.agents.human_proxy.schemas import HumanProxyLLMOutput, OpportunityProxyContext


class HumanProxyValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class HumanProxyValidator:
    """Ensures human proxy output is complete and consistent."""

    def validate(
        self,
        output: HumanProxyLLMOutput,
        *,
        context: OpportunityProxyContext,
    ) -> HumanProxyLLMOutput:
        errors: list[str] = []
        max_complaint_index = len(context.complaint_evidence) - 1

        if len(output.executive_summary.strip()) < 40:
            errors.append("executive_summary is too short")

        if output.recommendation == "pursue" and output.founder_fit_score < 60:
            errors.append("pursue recommendation requires founder_fit_score >= 60")

        if output.recommendation == "pursue" and output.feasibility_score < 55:
            errors.append("pursue recommendation requires feasibility_score >= 55")

        if output.recommendation == "pass" and output.founder_fit_score > 70:
            errors.append("pass recommendation is inconsistent with high founder_fit_score")

        if output.founder_fit_analysis.score > output.founder_fit_score + 15:
            errors.append("founder_fit_analysis.score exceeds founder_fit_score by too much")

        for index, item in enumerate(output.supporting_evidence, start=1):
            if len(item.excerpt.strip()) < 10:
                errors.append(f"supporting_evidence[{index}].excerpt is too short")
            if item.complaint_index is not None:
                if item.complaint_index < 0 or item.complaint_index > max_complaint_index:
                    errors.append(f"supporting_evidence[{index}].complaint_index out of range")

        if errors:
            raise HumanProxyValidationError(errors)

        return output
