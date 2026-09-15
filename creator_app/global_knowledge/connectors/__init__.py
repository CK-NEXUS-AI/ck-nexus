"""Connector contracts for global knowledge discovery and crawling."""

from .crawl4ai import (
    Crawl4AIAdapter,
    CrawlRequest,
    CrawlResult,
    CrawlStatus,
)
from .searxng import (
    SearchHit,
    SearxngConfig,
    SearxngDiscoveryAdapter,
    SearxngStatus,
)

__all__ = [
    "Crawl4AIAdapter",
    "CrawlRequest",
    "CrawlResult",
    "CrawlStatus",
    "SearchHit",
    "SearxngConfig",
    "SearxngDiscoveryAdapter",
    "SearxngStatus",
]
