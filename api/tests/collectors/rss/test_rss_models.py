"""Tests for RSS feed entry mapping."""

from types import SimpleNamespace

from app.collectors.rss.models import RssFeedEntry


def test_from_feedparser_entry_maps_required_fields():
    entry = SimpleNamespace(
        link="https://example.com/article/1",
        title="Startup funding slowdown",
        summary="Industry signals show tightening capital markets.",
        id="article-1",
        author="Editor",
        published_parsed=(2024, 1, 1, 12, 0, 0),
    )
    mapped = RssFeedEntry.from_feedparser_entry(entry, feed_title="Tech News")
    assert mapped is not None
    assert mapped.external_id == "article-1"
    assert mapped.url == "https://example.com/article/1"
    assert mapped.title == "Startup funding slowdown"
    assert mapped.body == "Industry signals show tightening capital markets."
    assert mapped.feed_title == "Tech News"
    assert mapped.published_at is not None


def test_from_feedparser_entry_skips_missing_link():
    entry = SimpleNamespace(title="No link", summary="Body", id="x")
    assert RssFeedEntry.from_feedparser_entry(entry, feed_title=None) is None
