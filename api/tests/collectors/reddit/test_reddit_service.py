"""Tests for Reddit keyword filtering and service mapping."""

from uuid import uuid4

from app.collectors.reddit.models import RedditContentKind, RedditSourceConfig
from app.collectors.reddit.service import KeywordFilter, RedditCollectorService


def test_keyword_filter_matches_pain_point_language():
    filt = KeywordFilter(["frustrating", "too expensive"])
    assert filt.matches("Billing tool", "Pricing is too expensive for our startup team")
    assert filt.matched_keywords("Billing", "too expensive monthly") == ["too expensive"]


def test_keyword_filter_rejects_neutral_content():
    filt = KeywordFilter(["frustrating", "too expensive"])
    assert not filt.matches("Weekly discussion", "What are you building this week?")


def test_build_metadata_includes_source_attribution():
    service = RedditCollectorService()
    source_id = uuid4()
    metadata = service._build_metadata(
        kind=RedditContentKind.POST,
        source_id=source_id,
        source_name="reddit-saas",
        subreddit="SaaS",
        post_id="abc123",
        matched_keywords=["frustrating"],
        score=10,
        num_comments=2,
    )
    assert metadata["reddit"]["collector"] == "reddit"
    assert metadata["reddit"]["source_name"] == "reddit-saas"
    assert metadata["reddit"]["source_id"] == str(source_id)
    assert metadata["reddit"]["matched_keywords"] == ["frustrating"]


def test_source_config_keyword_override():
    config = RedditSourceConfig(keywords=["custom pain"])
    assert config.resolved_keywords() == ["custom pain"]
