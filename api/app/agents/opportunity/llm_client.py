"""LLM client for opportunity synthesis."""

from __future__ import annotations

import json
import time
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agents.openai_schema import openai_strict_json_schema
from app.agents.opportunity.schemas import (
    ComplaintEvidence,
    ComplaintPattern,
    LLMInvocationResult,
    OpportunityLLMOutput,
)
from app.config import Settings

FOUNDER_THESIS_SYSTEM_PROMPT = """You extract founder venture theses from complaint evidence.

Your job is NOT to summarize a market category, write a market-gap report, or produce an analyst opportunity brief.

Your job IS to:
1. Read all complaints.
2. Select ONE dominant wedge — the single most specific, buildable problem a founder could solve first.
3. Anchor the thesis on the strongest evidence (highest severity; most specific verbatim quote; clearest economic consequence).
4. Name a concrete product mechanism — what the software actually does — not a category label.

Rules:
- Use ONLY provided evidence. Do not invent market size, funding data, TAM, or competitor names not in the evidence.
- If complaints imply multiple different products, pick ONE wedge and state which pain you are NOT solving in this thesis.
- Preserve economic consequence: what the buyer loses (revenue stopped, margin eroded, fraud loss, engineering time, etc.) using evidence and founder signals.
- When founder signal consequence codes are present (revenue_interruption, margin_erosion, fraud_loss, operational_risk, engineering_friction), reflect that economic stake explicitly in the problem_statement — do not replace them with generic phrases like "financial losses" or "significant gap".
- The title must pass the "Monday morning build test": a founder reading only the title should know what to build.

Title constraints (hard):
- DO NOT use: "Solutions for", "Platform for", "Management for", "Tool for", "Enhanced", "Comprehensive", "Alternative X for Y" (category wrapper).
- These patterns are invalid because they name a market category or segment instead of a product mechanism — they fail the build test.
- DO NOT name a market category alone (e.g. "Payment Processing", "Fraud Prevention", "Subscription Management").
- DO name: buyer situation + mechanism, OR mechanism + specific failure mode.
- Prefer verbatim specificity from quotes (e.g. deplatformed from Stripe, chargeback fees despite low rate, usage per subscription, GB metering).

Output fields are thesis components mapped to the JSON schema:
- title: venture thesis headline (wedge-level, not category-level)
- problem_statement: 2-3 sentences on ONE specific pain, anchored on strongest quote; include economic consequence
- target_user: narrow ICP in the wedge (who feels this exact pain today)
- frequency_signal: why THIS wedge recurs in the evidence (not generic category recurrence)
- existing_alternatives: only products named in evidence; what they fail to do FOR THIS WEDGE
- gap: the missing mechanism or capability (not "current solutions are inadequate" alone)
- explanation: why this wedge is buildable now from evidence; cite the dominant complaint
- confidence_score: 0-1 based on evidence specificity and wedge clarity"""

BANNED_TITLE_PATTERNS = (
    "Solutions for",
    "Platform for",
    "Management for",
    "Comprehensive",
    "Enhanced",
    "Alternative X for Y",
)

FOUNDER_CONSEQUENCE_CODES = (
    "revenue_interruption",
    "margin_erosion",
    "fraud_loss",
    "operational_risk",
    "engineering_friction",
)


class OpportunityLLMClient(Protocol):
    async def synthesize(
        self,
        *,
        pattern: ComplaintPattern,
        evidence: list[ComplaintEvidence],
        attempt: int,
        validation_errors: list[str] | None = None,
    ) -> LLMInvocationResult: ...


def _format_founder_signal_value(code: str | None) -> str:
    return code if code else "unknown"


def _format_evidence_complaint(index: int, item: ComplaintEvidence) -> str:
    products = ", ".join(item.product_mentions) if item.product_mentions else "none"
    consequence = _format_founder_signal_value(item.consequence_code)
    return (
        f"{index}. [severity={item.severity} persona={item.persona_code} products={products}]\n"
        f"   quote: {item.verbatim_quote!r}\n"
        f"   economic_consequence: {consequence}\n"
        f"   founder_signals("
        f"business_function={_format_founder_signal_value(item.business_function_code)}, "
        f"jtbd={_format_founder_signal_value(item.jtbd_code)}, "
        f"consequence={consequence})\n"
        f"   summary: {item.summary!r}"
    )


def format_opportunity_evidence(evidence: list[ComplaintEvidence]) -> str:
    """Format complaint evidence for founder-thesis synthesis (quote-first ordering)."""
    lines: list[str] = []
    for index, item in enumerate(evidence[:20], start=1):
        lines.append(_format_evidence_complaint(index, item))
    if len(evidence) > 20:
        lines.append(f"... and {len(evidence) - 20} more complaints")
    return "\n\n".join(lines)


def _build_step2_wedge_selection() -> str:
    return (
        "=== STEP 2: WEDGE SELECTION (required before writing output) ===\n"
        "Internally determine:\n"
        "- dominant_complaint: which single complaint has the strongest, most specific, most buildable pain?\n"
        "  Use highest severity first, then most specific quote, then clearest economic consequence.\n"
        "- dominant_wedge: one sentence describing the product mechanism you would build.\n"
        "- excluded_pains: other complaints in this cluster that you are NOT solving in this thesis.\n"
        "- economic_stake: what the buyer loses if this pain persists (from consequence code + quote).\n"
        "Do NOT merge excluded pains into the title or problem_statement."
    )


def _build_step3_cluster_context(pattern: ComplaintPattern) -> str:
    return (
        "=== STEP 3: CLUSTER CONTEXT (secondary — do not copy labels into title) ===\n"
        f"Pattern topic (internal cluster label only): {pattern.topic}\n"
        f"Anchor phrase (internal): {pattern.anchor_phrase}\n"
        f"Pattern founder signals (supporting hints only): "
        f"business_function={_format_founder_signal_value(pattern.business_function_code)}, "
        f"jtbd={_format_founder_signal_value(pattern.jtbd_code)}, "
        f"consequence={_format_founder_signal_value(pattern.consequence_code)}\n"
        f"Complaint count: {pattern.complaint_count} | Avg severity: {pattern.avg_severity:.1f}\n"
        f"Dominant taxonomy (weak signal only): domain={pattern.domain_code}, "
        f"category={pattern.category_code}, persona={pattern.dominant_persona_code}"
    )


def _build_step4_output(retry_block: str) -> str:
    consequence_list = ", ".join(FOUNDER_CONSEQUENCE_CODES)
    banned_list = "; ".join(f'"{pattern}"' for pattern in BANNED_TITLE_PATTERNS)
    return (
        "=== STEP 4: OUTPUT ===\n"
        "Write the JSON thesis using the field definitions in the system prompt.\n\n"
        "Strongest evidence anchoring (required):\n"
        "- title and problem_statement MUST anchor on the dominant_complaint from Step 2.\n"
        "- Include language from the dominant quote where possible.\n"
        "- State the economic stake explicitly using the consequence code when present "
        f"({consequence_list}).\n\n"
        "Anti-category title rules (hard bans — invalid because they hide the mechanism):\n"
        f"- {banned_list}\n\n"
        "If existing_alternatives has no named products in evidence, write exactly: "
        "'No named products in evidence' (do not use the word None as a product name)."
        f"{retry_block}"
    )


def build_opportunity_user_prompt(
    *,
    pattern: ComplaintPattern,
    evidence: list[ComplaintEvidence],
    attempt: int,
    validation_errors: list[str] | None = None,
) -> str:
    """Build the user prompt for founder-thesis synthesis (also used in tests)."""
    evidence_block = format_opportunity_evidence(evidence)
    retry_block = ""
    if validation_errors:
        retry_block = (
            "\n\nPrevious validation errors (fix these in your response):\n"
            + "\n".join(f"- {err}" for err in validation_errors)
        )
        if any("topic not reflected" in err for err in validation_errors):
            retry_block += (
                "\nIf retrying for abstraction: your previous title sounded like a market category "
                "or merged multiple wedges. Rewrite with ONE mechanism-level thesis anchored on the "
                "dominant complaint."
            )

    return (
        f"Attempt: {attempt}\n\n"
        "=== STEP 1: COMPLAINT EVIDENCE (primary — read first) ===\n"
        "Fields are ranked by importance: quote > economic consequence > founder signals > summary.\n\n"
        f"{evidence_block}\n\n"
        f"{_build_step2_wedge_selection()}\n\n"
        f"{_build_step3_cluster_context(pattern)}\n\n"
        f"{_build_step4_output(retry_block)}"
    )


def build_opportunity_synthesis_messages(
    *,
    pattern: ComplaintPattern,
    evidence: list[ComplaintEvidence],
    attempt: int,
    validation_errors: list[str] | None = None,
) -> list[dict[str, str]]:
    """Return chat messages sent to the model for opportunity synthesis."""
    return [
        {"role": "system", "content": FOUNDER_THESIS_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_opportunity_user_prompt(
                pattern=pattern,
                evidence=evidence,
                attempt=attempt,
                validation_errors=validation_errors,
            ),
        },
    ]


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    if "gpt-4o-mini" in model:
        return (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
    if "gpt-4o" in model:
        return (prompt_tokens * 2.50 + completion_tokens * 10.00) / 1_000_000
    return 0.0


class OpenAIOpportunityClient:
    """Calls OpenAI with JSON schema structured output."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for opportunity generation")
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def synthesize(
        self,
        *,
        pattern: ComplaintPattern,
        evidence: list[ComplaintEvidence],
        attempt: int,
        validation_errors: list[str] | None = None,
    ) -> LLMInvocationResult:
        started = time.perf_counter()
        messages = build_opportunity_synthesis_messages(
            pattern=pattern,
            evidence=evidence,
            attempt=attempt,
            validation_errors=validation_errors,
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._settings.generation_model,
                temperature=self._settings.generation_temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "opportunity_brief",
                        "strict": True,
                        "schema": openai_strict_json_schema(OpportunityLLMOutput),
                    },
                },
                messages=messages,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            raw_text = response.choices[0].message.content or ""
            usage = response.usage

            try:
                parsed = OpportunityLLMOutput.model_validate(json.loads(raw_text))
            except (json.JSONDecodeError, ValidationError) as exc:
                return LLMInvocationResult(
                    parsed=None,
                    raw_text=raw_text,
                    model=self._settings.generation_model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=latency_ms,
                    cost_usd=_estimate_cost_usd(
                        self._settings.generation_model,
                        usage.prompt_tokens if usage else 0,
                        usage.completion_tokens if usage else 0,
                    ),
                    error=f"malformed_response: {exc}",
                )

            return LLMInvocationResult(
                parsed=parsed,
                raw_text=raw_text,
                model=self._settings.generation_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
                cost_usd=_estimate_cost_usd(
                    self._settings.generation_model,
                    usage.prompt_tokens if usage else 0,
                    usage.completion_tokens if usage else 0,
                ),
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return LLMInvocationResult(
                parsed=None,
                raw_text=None,
                model=self._settings.generation_model,
                latency_ms=latency_ms,
                error=f"llm_error: {exc}",
            )

    @staticmethod
    def _format_evidence(evidence: list[ComplaintEvidence]) -> str:
        """Backward-compatible alias for tests and callers."""
        return format_opportunity_evidence(evidence)
