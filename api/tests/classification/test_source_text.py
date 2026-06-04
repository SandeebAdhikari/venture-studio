"""Tests for classification source text normalization and quote grounding."""

import pytest

from app.agents.classification.source_text import (
    build_classification_source_text,
    normalize_for_verbatim_grounding,
    verbatim_quote_in_source,
)


def test_decode_hex_apostrophe_entity() -> None:
    source = build_classification_source_text(
        title=None,
        body="We can&#x27;t ship until dependencies install.",
    )
    assert "can't" in source
    assert "&#x27;" not in source


def test_decode_slash_entity() -> None:
    source = build_classification_source_text(
        title=None,
        body="See path foo&#x2F;bar in config.",
    )
    assert "foo/bar" in source


def test_strip_html_tags() -> None:
    source = build_classification_source_text(
        title="Ask HN",
        body="<i>Frustrated</i> with <p>deploy</p> complexity.",
    )
    assert "<i>" not in source
    assert "Frustrated" in source
    assert "deploy" in source


def test_mixed_casing_grounding() -> None:
    raw = "The Pricing IS Too Expensive for us."
    source = build_classification_source_text(title=None, body=raw)
    assert verbatim_quote_in_source(quote="pricing is too expensive", source_text=source)


def test_rejects_hallucinated_quote_after_normalization() -> None:
    source = build_classification_source_text(
        title=None,
        body="We can&#x27;t deploy without fixing libraries.",
    )
    assert not verbatim_quote_in_source(
        quote="this text never appeared in the thread",
        source_text=source,
    )


def test_quote_with_entities_matches_decoded_source() -> None:
    body = "I can&#x27;t get <b>npm</b> working."
    source = build_classification_source_text(title=None, body=body)
    assert verbatim_quote_in_source(quote="I can't get npm working.", source_text=source)


def test_normalize_is_idempotent() -> None:
    once = normalize_for_verbatim_grounding("Hello &#x27; world")
    twice = normalize_for_verbatim_grounding(once)
    assert once == twice
