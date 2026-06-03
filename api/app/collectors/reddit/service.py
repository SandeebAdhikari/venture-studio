"""Reddit collector service — maps Reddit content to collection pipeline inputs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from app.collection.schemas import RawComplaintInput
from app.collectors.reddit.collector import RedditApiCollector, RedditRateLimiter
from app.collectors.reddit.models import (
    RedditCollectionStats,
    RedditCollectorSettings,
    RedditComment,
    RedditContentKind,
    RedditFetchStats,
    RedditPost,
    RedditSourceConfig,
)
from app.db.models.source import Source
from app.logging import get_logger

logger = get_logger(__name__)


class KeywordFilter:
    """Filters text for business pain / complaint signals."""

    def __init__(self, keywords: list[str], *, min_matches: int = 1) -> None:
        self._keywords = [keyword.lower() for keyword in keywords]
        self._min_matches = min_matches

    def matched_keywords(self, *parts: str) -> list[str]:
        combined = " ".join(part for part in parts if part).lower()
        return [keyword for keyword in self._keywords if keyword in combined]

    def matches(self, *parts: str) -> bool:
        return len(self.matched_keywords(*parts)) >= self._min_matches


class RedditCollectorService:
    """Collects Reddit posts and comments and adapts them for signal ingestion."""

    def __init__(
        self,
        *,
        settings: RedditCollectorSettings | None = None,
        redis=None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or RedditCollectorSettings()
        self._redis = redis
        self._client = client
        self._rate_limiter = RedditRateLimiter(
            redis=redis,
            min_interval_sec=self._settings.rate_limit_interval_sec,
        )

    async def fetch(self, source: Source) -> list[RawComplaintInput]:
        config = RedditSourceConfig.model_validate(source.config or {})
        stats = RedditCollectionStats()
        seen_external_ids: set[str] = set()
        items: list[RawComplaintInput] = []

        async with RedditApiCollector(
            settings=self._settings,
            rate_limiter=self._rate_limiter,
            client=self._client,
        ) as api:
            for subreddit in config.resolved_subreddits():
                subreddit_stats = RedditFetchStats(subreddit=subreddit)
                posts = await api.fetch_posts(config, subreddit=subreddit, source_id=source.id)
                subreddit_stats.posts_fetched = len(posts)

                keyword_filter = KeywordFilter(
                    config.resolved_keywords(),
                    min_matches=config.min_keyword_matches,
                )

                for post in posts:
                    stats.total_candidates += 1
                    matched = keyword_filter.matched_keywords(post.title, post.body)
                    if not matched:
                        subreddit_stats.keyword_filtered += 1
                        continue

                    item = self._post_to_raw(
                        post,
                        source_id=source.id,
                        source_name=source.name,
                        config=config,
                        stats=subreddit_stats,
                        seen_external_ids=seen_external_ids,
                        matched_keywords=matched,
                    )
                    if item is not None:
                        items.append(item)

                    if config.include_comments:
                        comments = await api.fetch_comments(
                            config,
                            subreddit=subreddit,
                            post=post,
                            source_id=source.id,
                        )
                        subreddit_stats.comments_fetched += len(comments)
                        for comment in comments:
                            stats.total_candidates += 1
                            comment_item = self._comment_to_raw(
                                comment,
                                post=post,
                                source_id=source.id,
                                source_name=source.name,
                                config=config,
                                stats=subreddit_stats,
                                seen_external_ids=seen_external_ids,
                            )
                            if comment_item is not None:
                                items.append(comment_item)

                stats.subreddit_stats.append(subreddit_stats)
                stats.duplicates_skipped += subreddit_stats.duplicates_skipped
                stats.keyword_filtered += subreddit_stats.keyword_filtered

        stats.total_returned = len(items)
        logger.info(
            "Reddit collection complete",
            extra={
                "source_id": str(source.id),
                "source_name": source.name,
                "subreddits": config.resolved_subreddits(),
                "total_candidates": stats.total_candidates,
                "total_returned": stats.total_returned,
                "duplicates_skipped": stats.duplicates_skipped,
                "keyword_filtered": stats.keyword_filtered,
            },
        )
        return items

    def _post_to_raw(
        self,
        post: RedditPost,
        *,
        source_id: UUID,
        source_name: str,
        config: RedditSourceConfig,
        stats: RedditFetchStats,
        seen_external_ids: set[str],
        matched_keywords: list[str],
    ) -> RawComplaintInput | None:
        if post.external_id in seen_external_ids:
            stats.duplicates_skipped += 1
            return None
        seen_external_ids.add(post.external_id)
        stats.keyword_matches += 1

        return RawComplaintInput(
            external_id=post.external_id,
            url=post.url,
            title=post.title,
            body=post.body,
            author=post.author,
            published_at=post.published_at,
            metadata=self._build_metadata(
                kind=RedditContentKind.POST,
                source_id=source_id,
                source_name=source_name,
                subreddit=post.subreddit,
                post_id=post.post_id,
                score=post.score,
                num_comments=post.num_comments,
                matched_keywords=matched_keywords,
            ),
        )

    def _comment_to_raw(
        self,
        comment: RedditComment,
        *,
        post: RedditPost,
        source_id: UUID,
        source_name: str,
        config: RedditSourceConfig,
        stats: RedditFetchStats,
        seen_external_ids: set[str],
    ) -> RawComplaintInput | None:
        keyword_filter = KeywordFilter(
            config.resolved_keywords(),
            min_matches=config.min_keyword_matches,
        )
        matched = keyword_filter.matched_keywords(post.title, comment.body)
        if not matched:
            stats.keyword_filtered += 1
            return None

        if comment.external_id in seen_external_ids:
            stats.duplicates_skipped += 1
            return None
        seen_external_ids.add(comment.external_id)
        stats.keyword_matches += 1

        return RawComplaintInput(
            external_id=comment.external_id,
            url=comment.url,
            title=post.title,
            body=comment.body,
            author=comment.author,
            published_at=comment.published_at,
            metadata=self._build_metadata(
                kind=RedditContentKind.COMMENT,
                source_id=source_id,
                source_name=source_name,
                subreddit=comment.subreddit,
                post_id=post.post_id,
                comment_id=comment.comment_id,
                parent_post_title=post.title,
                score=comment.score,
                matched_keywords=matched,
            ),
        )

    def _build_metadata(
        self,
        *,
        kind: RedditContentKind,
        source_id: UUID,
        source_name: str,
        subreddit: str,
        post_id: str,
        matched_keywords: list[str],
        score: int,
        num_comments: int | None = None,
        comment_id: str | None = None,
        parent_post_title: str | None = None,
    ) -> dict[str, Any]:
        attribution = {
            "collector": "reddit",
            "collector_version": self._settings.collector_version,
            "source_id": str(source_id),
            "source_name": source_name,
            "subreddit": subreddit,
            "kind": kind.value,
            "post_id": post_id,
            "comment_id": comment_id,
            "parent_post_title": parent_post_title,
            "score": score,
            "num_comments": num_comments,
            "matched_keywords": matched_keywords,
        }
        return {
            "reddit": attribution,
            "score": score,
            "subreddit": subreddit,
        }
