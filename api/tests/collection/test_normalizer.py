"""Unit tests for text normalization."""

from app.collection.normalizer import TextNormalizer


def test_normalizes_unicode_and_whitespace() -> None:
    normalizer = TextNormalizer()
    result = normalizer.normalize(
        title="  Pricing   issue  ",
        body="Too\u200b expensive\r\nfor  startups ",
    )
    assert result.title == "Pricing issue"
    assert result.body == "Too expensive for startups"
    assert result.combined_text == "Pricing issue\n\nToo expensive for startups"


def test_content_hash_is_deterministic() -> None:
    normalizer = TextNormalizer()
    first = normalizer.normalize(title="A", body="B")
    second = normalizer.normalize(title="A", body="B")
    assert first.content_hash == second.content_hash
    assert len(first.content_hash) == 64


def test_is_url_only_detects_bare_urls() -> None:
    normalizer = TextNormalizer()
    assert normalizer.is_url_only("https://example.com/post") is True
    assert normalizer.is_url_only("https://example.com and more") is False
