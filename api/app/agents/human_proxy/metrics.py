"""Evaluation metrics for human proxy rankings."""

from app.agents.human_proxy.schemas import HumanProxyLLMOutput


def compute_evaluation_metrics(output: HumanProxyLLMOutput) -> dict[str, float | int | str]:
    ranking_score = min(
        100,
        int(
            output.founder_fit_score * 0.45
            + output.feasibility_score * 0.35
            + (100 - output.execution_complexity.score) * 0.10
            + (100 - output.learning_curve.score) * 0.10
        ),
    )

    return {
        "founder_fit_score": output.founder_fit_score,
        "feasibility_score": output.feasibility_score,
        "recommendation": output.recommendation,
        "founder_fit_analysis_score": output.founder_fit_analysis.score,
        "implementation_feasibility_score": output.implementation_feasibility.score,
        "learning_curve_score": output.learning_curve.score,
        "execution_complexity_score": output.execution_complexity.score,
        "capital_requirements_score": output.capital_requirements.score,
        "skill_match_count": len(output.founder_fit_analysis.skill_matches),
        "skill_gap_count": len(output.founder_fit_analysis.skill_gaps),
        "new_skills_required_count": len(output.learning_curve.new_skills_required),
        "bootstrap_friendly": output.capital_requirements.bootstrap_friendly,
        "ranking_score": ranking_score,
    }
