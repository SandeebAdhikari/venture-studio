"""Tests for OpenAI strict JSON-schema compatibility helpers."""

from __future__ import annotations

import os

import pytest
from pydantic import BaseModel

from app.agents.classification.schemas import ClassificationLLMOutput
from app.agents.competitor_intelligence.schemas import CompetitorAnalysisLLMOutput
from app.agents.customer_research.schemas import CustomerResearchLLMOutput
from app.agents.go_to_market.schemas import GoToMarketLLMOutput
from app.agents.growth_strategy.schemas import GrowthStrategyLLMOutput
from app.agents.human_proxy.schemas import HumanProxyLLMOutput
from app.agents.market_research.schemas import MarketResearchLLMOutput
from app.agents.openai_schema import (
    find_object_nodes_missing_additional_properties_false,
    openai_strict_json_schema,
    prepare_openai_strict_schema,
)
from app.agents.opportunity.schemas import OpportunityLLMOutput
from app.agents.product_strategy.schemas import ProductStrategyLLMOutput
from app.agents.revenue_validation.schemas import RevenueValidationLLMOutput

ALL_LLM_OUTPUT_MODELS: list[tuple[str, type[BaseModel]]] = [
    ("classification", ClassificationLLMOutput),
    ("opportunity", OpportunityLLMOutput),
    ("market_research", MarketResearchLLMOutput),
    ("competitor_intelligence", CompetitorAnalysisLLMOutput),
    ("customer_research", CustomerResearchLLMOutput),
    ("revenue_validation", RevenueValidationLLMOutput),
    ("product_strategy", ProductStrategyLLMOutput),
    ("go_to_market", GoToMarketLLMOutput),
    ("growth_strategy", GrowthStrategyLLMOutput),
    ("human_proxy", HumanProxyLLMOutput),
]


@pytest.mark.parametrize("name,model", ALL_LLM_OUTPUT_MODELS)
def test_raw_pydantic_schema_missing_additional_properties(name: str, model: type[BaseModel]) -> None:
    raw = model.model_json_schema()
    missing = find_object_nodes_missing_additional_properties_false(raw)
    assert missing, f"{name} raw schema should expose missing nodes for regression coverage"


@pytest.mark.parametrize("name,model", ALL_LLM_OUTPUT_MODELS)
def test_openai_strict_schema_sets_additional_properties_false(
    name: str,
    model: type[BaseModel],
) -> None:
    schema = openai_strict_json_schema(model)
    missing = find_object_nodes_missing_additional_properties_false(schema)
    assert missing == [], f"{name} missing additionalProperties=false at: {missing}"


@pytest.mark.parametrize("name,model", ALL_LLM_OUTPUT_MODELS)
def test_openai_strict_schema_required_includes_all_properties(
    name: str,
    model: type[BaseModel],
) -> None:
    schema = openai_strict_json_schema(model)

    def check(node: object, path: str) -> None:
        if not isinstance(node, dict):
            return
        properties = node.get("properties")
        if isinstance(properties, dict) and properties:
            required = node.get("required")
            assert isinstance(required, list), f"{name} {path}: required must be a list"
            assert set(required) == set(properties.keys()), (
                f"{name} {path}: required must include all properties"
            )
        for key in ("$defs", "definitions"):
            defs = node.get(key)
            if isinstance(defs, dict):
                for def_name, subschema in defs.items():
                    check(subschema, f"{path}/$defs/{def_name}")
        if isinstance(properties, dict):
            for prop_name, subschema in properties.items():
                check(subschema, f"{path}.{prop_name}")
        items = node.get("items")
        if isinstance(items, dict):
            check(items, f"{path}[]")
        for key in ("allOf", "anyOf", "oneOf"):
            variants = node.get(key)
            if isinstance(variants, list):
                for index, subschema in enumerate(variants):
                    check(subschema, f"{path}/{key}[{index}]")

    check(schema, "root")


def test_prepare_openai_strict_schema_handles_defs_arrays_and_composition() -> None:
    nested = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {"$ref": "#/$defs/Child"},
            },
            "choice": {
                "anyOf": [
                    {"type": "object", "properties": {"a": {"type": "string"}}},
                    {"$ref": "#/$defs/Child"},
                ],
            },
        },
        "$defs": {
            "Child": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
            }
        },
    }
    prepared = prepare_openai_strict_schema(nested)
    missing = find_object_nodes_missing_additional_properties_false(prepared)
    assert missing == []


def test_openai_strict_schema_does_not_mutate_pydantic_output() -> None:
    raw = ClassificationLLMOutput.model_json_schema()
    before = raw.get("additionalProperties", "unset")
    _ = openai_strict_json_schema(ClassificationLLMOutput)
    after = raw.get("additionalProperties", "unset")
    assert before == after


def _strict_schema_names() -> dict[str, str]:
    return {
        "classification": "complaint_classification",
        "opportunity": "opportunity_brief",
        "market_research": "market_intelligence_brief",
        "competitor_intelligence": "competitor_analysis",
        "customer_research": "customer_research",
        "revenue_validation": "revenue_validation",
        "product_strategy": "product_strategy",
        "go_to_market": "go_to_market_plan",
        "growth_strategy": "growth_strategy",
        "human_proxy": "human_proxy_evaluation",
    }


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY", "").strip(),
    reason="OPENAI_API_KEY required for live OpenAI schema validation",
)
@pytest.mark.parametrize("name,model", ALL_LLM_OUTPUT_MODELS)
async def test_openai_accepts_strict_schema_for_each_llm_output(
    name: str,
    model: type[BaseModel],
) -> None:
    from openai import AsyncOpenAI

    from app.config import get_settings

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key or os.environ["OPENAI_API_KEY"])
    schema_name = _strict_schema_names()[name]
    response = await client.chat.completions.create(
        model=settings.classification_model,
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": openai_strict_json_schema(model),
            },
        },
        messages=[
            {
                "role": "user",
                "content": (
                    f"Return minimal valid JSON for schema {schema_name} about a B2B SaaS "
                    "scheduling pain point."
                ),
            }
        ],
    )
    assert response.choices[0].message.content
