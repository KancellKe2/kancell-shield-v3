"""Search Engine for Kancell Shield v3.

This module provides search capabilities for querying multiple
search providers and aggregating results.
"""

from .models import (
    PaginationState,
    PaginationType,
    ProviderConfig,
    ProviderHealth,
    ProviderMetrics,
    ProviderState,
    RateLimitConfig,
    RateLimitInfo,
    RetryConfig,
    RetryMode,
    SearchConfig,
    SearchQuery,
    SearchResult,
    SearchResultSet,
)

from .interfaces import (
    DeduplicationStrategy,
    HealthChecker,
    PaginationHandler,
    ProviderRegistry,
    QueryBuilder,
    RateLimiter,
    ResultNormalizer,
    RetryStrategy,
    SearchEngine,
    SearchProvider,
)

__all__ = [
    # Models
    "PaginationState",
    "PaginationType",
    "ProviderConfig",
    "ProviderHealth",
    "ProviderMetrics",
    "ProviderState",
    "RateLimitConfig",
    "RateLimitInfo",
    "RetryConfig",
    "RetryMode",
    "SearchConfig",
    "SearchQuery",
    "SearchResult",
    "SearchResultSet",
    # Interfaces
    "DeduplicationStrategy",
    "HealthChecker",
    "PaginationHandler",
    "ProviderRegistry",
    "QueryBuilder",
    "RateLimiter",
    "ResultNormalizer",
    "RetryStrategy",
    "SearchEngine",
    "SearchProvider",
]
