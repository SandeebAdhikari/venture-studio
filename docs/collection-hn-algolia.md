# Hacker News Algolia Collector

Production remediation #2: implements `SourceType.HN_ALGOLIA` collection via the public Algolia search API.

## Architecture

```
Source (config.query) → HnAlgoliaCollectorService → HnAlgoliaApiCollector
  → keyword filter / dedupe → RawComplaintInput → ComplaintCollectionService
```

Registered at API startup (`lifespan.py`) and ARQ worker startup (`workers/context.py`).

## Source configuration

| Field | Default | Description |
|-------|---------|-------------|
| `query` | required | Algolia search query |
| `tags` | `story` | HN tag filter (e.g. `story`, `comment`) |
| `hits_per_page` | 20 | Results per page (1–100) |
| `max_pages` | 3 | Maximum pages to fetch (1–10) |
| `keywords` | pain keywords | Optional override for keyword filter |
| `min_keyword_matches` | 1 | Minimum keyword hits required |
| `min_points` | 0 | Minimum HN points threshold |

Example: `{"query": "wish alternative", "max_pages": 2}`

## Production impact

| Area | Impact |
|------|--------|
| **Collection coverage** | HN_ALGOLIA sources no longer skipped with `no_collector_registered` |
| **Rate limiting** | Redis-backed limiter with in-process fallback (1 req/sec default) |
| **Retries** | Exponential backoff on HTTP/transport errors (3 attempts default) |
| **Deduplication** | In-run external_id dedupe + pipeline content_hash dedupe |
| **Observability** | Collector metadata on each signal; `avs_collector_*` metrics on ingest |
