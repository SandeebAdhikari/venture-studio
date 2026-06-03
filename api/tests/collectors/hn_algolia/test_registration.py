"""Tests for HN Algolia collector registration."""

from app.collection.collectors.registry import clear_collectors, get_collector
from app.collectors.hn_algolia import register_hn_algolia_collector
from app.collectors.hn_algolia.service import HnAlgoliaCollectorService
from app.db.enums import SourceType


def test_register_hn_algolia_collector():
    clear_collectors()
    try:
        service = register_hn_algolia_collector()
        assert isinstance(service, HnAlgoliaCollectorService)
        collector = get_collector(SourceType.HN_ALGOLIA.value)
        assert collector is service
    finally:
        clear_collectors()
