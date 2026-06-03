"""Unit tests for collection filters."""

from app.collection.filters import CollectionFilter
from app.collection.normalizer import TextNormalizer
from app.collection.settings import CollectionSettings


def test_rejects_short_text() -> None:
    normalizer = TextNormalizer()
    normalized = normalizer.normalize(title=None, body="Too short")
    filter_ = CollectionFilter(CollectionSettings(min_text_length=50))
    reason = filter_.rejection_reason(normalized, url="https://example.com/1")
    assert reason == "text_too_short: minimum 50 characters required"


def test_rejects_url_only_body() -> None:
    normalizer = TextNormalizer()
    normalized = normalizer.normalize(title=None, body="https://example.com/post")
    filter_ = CollectionFilter()
    reason = filter_.rejection_reason(normalized, url="https://example.com/post")
    assert reason == "url_only_body"


def test_accepts_valid_complaint_text() -> None:
    normalizer = TextNormalizer()
    normalized = normalizer.normalize(
        title="Billing pain",
        body="We cannot afford this pricing model for our small team at all.",
    )
    filter_ = CollectionFilter()
    assert filter_.rejection_reason(normalized, url="https://example.com/post") is None
