"""Unit tests for Reddit collector models."""

from app.collectors.reddit.models import (
    DEFAULT_SUBREDDITS,
    RedditComment,
    RedditPost,
    RedditSourceConfig,
)


def test_source_config_resolves_single_subreddit():
    config = RedditSourceConfig(subreddit="SaaS")
    assert config.resolved_subreddits() == ["SaaS"]


def test_source_config_resolves_multiple_subreddits():
    config = RedditSourceConfig(subreddits=["entrepreneur", "startups"])
    assert config.resolved_subreddits() == ["entrepreneur", "startups"]


def test_source_config_defaults_to_standard_subreddits():
    config = RedditSourceConfig()
    assert config.resolved_subreddits() == list(DEFAULT_SUBREDDITS)


def test_post_from_listing_parses_submission():
    post = RedditPost.from_listing(
        {
            "kind": "t3",
            "data": {
                "id": "abc123",
                "name": "t3_abc123",
                "title": "Billing tool is frustrating",
                "selftext": "Pricing is too expensive and exports are broken for our team.",
                "author": "founder1",
                "created_utc": 1_700_000_000,
                "permalink": "/r/SaaS/comments/abc123/billing/",
                "score": 15,
                "num_comments": 4,
                "subreddit": "SaaS",
            },
        }
    )
    assert post is not None
    assert post.external_id == "t3_abc123"
    assert post.subreddit == "SaaS"
    assert post.url.endswith("/r/SaaS/comments/abc123/billing/")


def test_comment_from_listing_parses_comment():
    post = RedditPost.from_listing(
        {
            "kind": "t3",
            "data": {
                "id": "abc123",
                "name": "t3_abc123",
                "title": "Need a tool for invoicing",
                "selftext": "Looking for alternatives because our current workflow is a nightmare.",
                "author": "founder1",
                "created_utc": 1_700_000_000,
                "permalink": "/r/SaaS/comments/abc123/invoicing/",
                "score": 8,
                "num_comments": 2,
                "subreddit": "SaaS",
            },
        }
    )
    assert post is not None

    comment = RedditComment.from_listing(
        {
            "kind": "t1",
            "data": {
                "id": "cmt1",
                "name": "t1_cmt1",
                "body": "Same issue here — wish there was a better alternative.",
                "author": "user2",
                "created_utc": 1_700_000_100,
                "permalink": "/r/SaaS/comments/abc123/invoicing/cmt1/",
                "score": 3,
                "parent_id": "t3_abc123",
            },
        },
        post=post,
    )
    assert comment is not None
    assert comment.external_id == "t1_cmt1"
    assert comment.post_id == "abc123"
