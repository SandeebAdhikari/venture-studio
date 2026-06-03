"""Collector registry package."""

from app.collection.collectors.registry import (
    SourceCollector,
    clear_collectors,
    get_collector,
    register_collector,
)

__all__ = [
    "SourceCollector",
    "clear_collectors",
    "get_collector",
    "register_collector",
]
