"""Risk and recommendation logic for venture reports."""

from app.reports.venture.schemas import RiskItem, VentureOpportunityReport

RECOMMEND_PURSUE = "Pursue — strong composite score with validated demand and founder fit."
RECOMMEND_EXPLORE = "Explore — promising signal; run focused validation before committing."
RECOMMEND_MONITOR = "Monitor — mixed signals; gather more evidence before investing time."
RECOMMEND_PASS = "Pass — weak fit or insufficient signal for a solo founder right now."


def build_risk_items(
    *,
    growth_risk_score: int | None,
    technical_risks: list[dict],
    execution_complexity: dict | None,
    capital_requirements: dict | None,
    competitor_threat_level: str | None,
    revenue_confidence_score: int | None,
) -> list[RiskItem]:
    items: list[RiskItem] = []

    if growth_risk_score is not None and growth_risk_score >= 60:
        severity = "high" if growth_risk_score >= 75 else "medium"
        items.append(
            RiskItem(
                category="growth",
                severity=severity,
                description=f"Growth risk score is {growth_risk_score}/100 — scaling may be harder than expected.",
            )
        )

    if competitor_threat_level in {"high", "medium"}:
        items.append(
            RiskItem(
                category="competition",
                severity=competitor_threat_level,
                description=f"Competitive threat assessed as {competitor_threat_level}.",
            )
        )

    for risk in technical_risks[:3]:
        name = risk.get("risk") or risk.get("name") or "Technical risk"
        level = str(risk.get("severity") or risk.get("level") or "medium").lower()
        items.append(
            RiskItem(
                category="product",
                severity=level if level in {"low", "medium", "high"} else "medium",
                description=str(name),
            )
        )

    if execution_complexity:
        level = str(execution_complexity.get("complexity_level") or "medium")
        burden = execution_complexity.get("operational_burden")
        description = execution_complexity.get("rationale") or f"Execution complexity: {level}."
        if burden:
            description = f"{description} Operational burden: {burden}."
        items.append(
            RiskItem(
                category="execution",
                severity=level if level in {"low", "medium", "high"} else "medium",
                description=description,
            )
        )

    if capital_requirements and not capital_requirements.get("bootstrap_friendly", True):
        items.append(
            RiskItem(
                category="capital",
                severity="medium",
                description=(
                    capital_requirements.get("rationale")
                    or "Capital requirements may exceed a limited bootstrap budget."
                ),
            )
        )

    if revenue_confidence_score is not None and revenue_confidence_score < 50:
        items.append(
            RiskItem(
                category="revenue",
                severity="medium",
                description=f"Revenue confidence is low ({revenue_confidence_score}/100).",
            )
        )

    if not items:
        items.append(
            RiskItem(
                category="general",
                severity="low",
                description="No major risks flagged from current agent outputs; continue validation.",
            )
        )

    return items


def build_recommendation(
    *,
    final_score: int,
    human_proxy_recommendation: str | None,
    pain_score: int | None,
    founder_fit_score: int | None,
    rank: int,
) -> str:
    if human_proxy_recommendation == "pass":
        return f"Pass — human proxy analysis recommends passing despite rank #{rank}."

    if human_proxy_recommendation == "defer":
        base = RECOMMEND_MONITOR
    elif final_score >= 75 and (founder_fit_score or 0) >= 65:
        base = RECOMMEND_PURSUE
    elif final_score >= 55:
        base = RECOMMEND_EXPLORE
    elif final_score >= 40:
        base = RECOMMEND_MONITOR
    else:
        base = RECOMMEND_PASS

    parts = [base, f"Ranked #{rank} with composite score {final_score}/100."]
    if pain_score is not None:
        parts.append(f"Customer pain score: {pain_score}/100.")
    if founder_fit_score is not None:
        parts.append(f"Founder fit score: {founder_fit_score}/100.")
    if human_proxy_recommendation:
        parts.append(f"Human proxy recommendation: {human_proxy_recommendation}.")

    return " ".join(parts)


def format_risk_analysis_markdown(risks: list[RiskItem]) -> str:
    lines = []
    for risk in risks:
        lines.append(f"- **{risk.category.title()} ({risk.severity})** — {risk.description}")
    return "\n".join(lines)
