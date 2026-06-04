"""OpenAI strict JSON-schema compatibility helpers for structured outputs."""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel

_COMPOSITION_KEYS = frozenset({"allOf", "anyOf", "oneOf"})
_DEFS_KEYS = frozenset({"$defs", "definitions"})


def openai_strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Build a Pydantic JSON schema compatible with OpenAI ``strict`` response_format."""
    schema = model.model_json_schema()
    return prepare_openai_strict_schema(schema)


def prepare_openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of *schema* prepared for OpenAI ``strict`` response_format."""
    prepared = copy.deepcopy(schema)
    _enforce_additional_properties_false(prepared)
    _enforce_strict_required_fields(prepared)
    return prepared


def _enforce_additional_properties_false(node: Any) -> None:
    if isinstance(node, dict):
        _patch_object_node(node)
        for key in _DEFS_KEYS:
            defs = node.get(key)
            if isinstance(defs, dict):
                for subschema in defs.values():
                    _enforce_additional_properties_false(subschema)
        properties = node.get("properties")
        if isinstance(properties, dict):
            for subschema in properties.values():
                _enforce_additional_properties_false(subschema)
        pattern_properties = node.get("patternProperties")
        if isinstance(pattern_properties, dict):
            for subschema in pattern_properties.values():
                _enforce_additional_properties_false(subschema)
        items = node.get("items")
        if items is not None:
            if isinstance(items, list):
                for subschema in items:
                    _enforce_additional_properties_false(subschema)
            else:
                _enforce_additional_properties_false(items)
        prefix_items = node.get("prefixItems")
        if isinstance(prefix_items, list):
            for subschema in prefix_items:
                _enforce_additional_properties_false(subschema)
        for key in _COMPOSITION_KEYS:
            variants = node.get(key)
            if isinstance(variants, list):
                for subschema in variants:
                    _enforce_additional_properties_false(subschema)
        not_schema = node.get("not")
        if isinstance(not_schema, dict):
            _enforce_additional_properties_false(not_schema)
        if_schema = node.get("if")
        if isinstance(if_schema, dict):
            _enforce_additional_properties_false(if_schema)
        then_schema = node.get("then")
        if isinstance(then_schema, dict):
            _enforce_additional_properties_false(then_schema)
        else_schema = node.get("else")
        if isinstance(else_schema, dict):
            _enforce_additional_properties_false(else_schema)
    elif isinstance(node, list):
        for item in node:
            _enforce_additional_properties_false(item)


def _patch_object_node(node: dict[str, Any]) -> None:
    if node.get("type") == "object" or "properties" in node or "patternProperties" in node:
        node["additionalProperties"] = False


def _enforce_strict_required_fields(node: Any) -> None:
    if isinstance(node, dict):
        _patch_required_fields(node)
        for key in _DEFS_KEYS:
            defs = node.get(key)
            if isinstance(defs, dict):
                for subschema in defs.values():
                    _enforce_strict_required_fields(subschema)
        properties = node.get("properties")
        if isinstance(properties, dict):
            for subschema in properties.values():
                _enforce_strict_required_fields(subschema)
        pattern_properties = node.get("patternProperties")
        if isinstance(pattern_properties, dict):
            for subschema in pattern_properties.values():
                _enforce_strict_required_fields(subschema)
        items = node.get("items")
        if items is not None:
            if isinstance(items, list):
                for subschema in items:
                    _enforce_strict_required_fields(subschema)
            else:
                _enforce_strict_required_fields(items)
        prefix_items = node.get("prefixItems")
        if isinstance(prefix_items, list):
            for subschema in prefix_items:
                _enforce_strict_required_fields(subschema)
        for key in _COMPOSITION_KEYS:
            variants = node.get(key)
            if isinstance(variants, list):
                for subschema in variants:
                    _enforce_strict_required_fields(subschema)
        for key in ("not", "if", "then", "else"):
            subschema = node.get(key)
            if isinstance(subschema, dict):
                _enforce_strict_required_fields(subschema)
    elif isinstance(node, list):
        for item in node:
            _enforce_strict_required_fields(item)


def _patch_required_fields(node: dict[str, Any]) -> None:
    properties = node.get("properties")
    if not isinstance(properties, dict) or not properties:
        return
    node["required"] = sorted(properties.keys())


def find_object_nodes_missing_additional_properties_false(
    schema: dict[str, Any],
    *,
    path: str = "root",
) -> list[str]:
    """Return paths of object nodes that do not set additionalProperties to false."""
    missing: list[str] = []

    def visit(node: Any, current_path: str) -> None:
        if not isinstance(node, dict):
            return
        is_object = (
            node.get("type") == "object"
            or "properties" in node
            or "patternProperties" in node
        )
        if is_object and node.get("additionalProperties") is not False:
            missing.append(current_path)
        for key in _DEFS_KEYS:
            defs = node.get(key)
            if isinstance(defs, dict):
                for name, subschema in defs.items():
                    visit(subschema, f"{current_path}/$defs/{name}")
        properties = node.get("properties")
        if isinstance(properties, dict):
            for name, subschema in properties.items():
                visit(subschema, f"{current_path}.{name}")
        pattern_properties = node.get("patternProperties")
        if isinstance(pattern_properties, dict):
            for name, subschema in pattern_properties.items():
                visit(subschema, f"{current_path}[pattern:{name}]")
        items = node.get("items")
        if items is not None:
            if isinstance(items, list):
                for index, subschema in enumerate(items):
                    visit(subschema, f"{current_path}[{index}]")
            else:
                visit(items, f"{current_path}[]")
        prefix_items = node.get("prefixItems")
        if isinstance(prefix_items, list):
            for index, subschema in enumerate(prefix_items):
                visit(subschema, f"{current_path}[prefix:{index}]")
        for key in _COMPOSITION_KEYS:
            variants = node.get(key)
            if isinstance(variants, list):
                for index, subschema in enumerate(variants):
                    visit(subschema, f"{current_path}/{key}[{index}]")
        for key in ("not", "if", "then", "else"):
            subschema = node.get(key)
            if isinstance(subschema, dict):
                visit(subschema, f"{current_path}/{key}")

    visit(schema, path)
    return missing
