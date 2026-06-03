"""Tests for Reddit API collector with mocked HTTP responses."""

from uuid import uuid4

import httpx
import pytest

from app.collectors.reddit.collector import RedditApiCollector, RedditRateLimiter
from app.collectors.reddit.models import RedditCollectorSettings, RedditSourceConfig


def _post_listing(subreddit: str = "SaaS") -> dict:
    return {
        "kind": "Listing",
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": "abc123",
                        "name": "t3_abc123",
                        "title": "Billing exports are broken",
                        "selftext": (
                            "Our team is frustrated because pricing is too expensive "
                            "and exports fail daily."
                        ),
                        "author": "founder1",
                        "created_utc": 1_700_000_000,
                        "permalink": f"/r/{subreddit}/comments/abc123/billing/",
                        "score": 10,
                        "num_comments": 1,
                        "subreddit": subreddit,
                    },
                },
                {
                    "kind": "t3",
                    "data": {
                        "id": "neutral1",
                        "name": "t3_neutral1",
                        "title": "Weekly thread",
                        "selftext": (
                            "Share what you are building this week "
                            "in our community discussion thread."
                        ),
                        "author": "mod_user",
                        "created_utc": 1_700_000_100,
                        "permalink": f"/r/{subreddit}/comments/neutral1/weekly/",
                        "score": 50,
                        "num_comments": 20,
                        "subreddit": subreddit,
                    },
                },
            ]
        },
    }


def _comment_listing(subreddit: str = "SaaS") -> list:
    return [
        _post_listing(subreddit),
        {
            "kind": "Listing",
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "id": "cmt1",
                            "name": "t1_cmt1",
                            "body": "We have the same problem and wish there was an alternative.",
                            "author": "commenter",
                            "created_utc": 1_700_000_200,
                            "permalink": f"/r/{subreddit}/comments/abc123/billing/cmt1/",
                            "score": 2,
                            "parent_id": "t3_abc123",
                        },
                    }
                ]
            },
        },
    ]


@pytest.mark.asyncio
async def test_fetch_posts_and_comments_with_mock_transport():
    source_id = uuid4()
    config = RedditSourceConfig(subreddit="SaaS", limit=25, include_comments=True)

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/SaaS/new.json"):
            return httpx.Response(200, json=_post_listing("SaaS"))
        if "/comments/abc123.json" in request.url.path:
            return httpx.Response(200, json=_comment_listing("SaaS"))
        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://www.reddit.com",
        headers={"User-Agent": "test"},
    ) as client:
        async with RedditApiCollector(
            settings=RedditCollectorSettings(rate_limit_interval_sec=0),
            rate_limiter=RedditRateLimiter(min_interval_sec=0),
            client=client,
        ) as api:
            posts = await api.fetch_posts(config, subreddit="SaaS", source_id=source_id)
            assert len(posts) == 2
            comments = await api.fetch_comments(
                config,
                subreddit="SaaS",
                post=posts[0],
                source_id=source_id,
            )
            assert len(comments) == 1
            assert comments[0].external_id == "t1_cmt1"
