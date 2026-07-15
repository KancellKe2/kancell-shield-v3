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

from .exceptions import (
    ConfigurationError,
    DeduplicationError,
    HealthCheckError,
    ProviderDisabledError,
    ProviderError,
    ProviderNotFoundError,
    ProviderUnhealthyError,
    QueryError,
    RateLimitError,
    ResultError,
    RetryError,
    SearchEngineError,
    TimeoutError,
    ValidationError,
)

from .registry import ProviderRegistryImpl
from .rate_limiter import (
    GlobalRateLimiter,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
)
from .retry import (
    ExponentialBackoffRetry,
    FixedRetryStrategy,
    JitteredRetryStrategy,
    LinearRetryStrategy,
    SelectiveRetryStrategy,
)
from .query_builder import (
    DomainQueryBuilder,
    KeywordQueryBuilder,
    PhraseQueryBuilder,
)
from .normalizer import (
    DeduplicatingNormalizer,
    ResultNormalizerImpl,
    StrictResultNormalizer,
)
from .engine import SearchEngineImpl, UrlDeduplicationStrategy
from .mock_provider import (
    FailingMockProvider,
    MockSearchProvider,
    RateLimitedMockProvider,
    SlowMockProvider,
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
    # Exceptions
    "ConfigurationError",
    "DeduplicationError",
    "HealthCheckError",
    "ProviderDisabledError",
    "ProviderError",
    "ProviderNotFoundError",
    "ProviderUnhealthyError",
    "QueryError",
    "RateLimitError",
    "ResultError",
    "RetryError",
    "SearchEngineError",
    "TimeoutError",
    "ValidationError",
    # Implementations
    "ProviderRegistryImpl",
    "TokenBucketRateLimiter",
    "SlidingWindowRateLimiter",
    "GlobalRateLimiter",
    "ExponentialBackoffRetry",
    "FixedRetryStrategy",
    "LinearRetryStrategy",
    "JitteredRetryStrategy",
    "SelectiveRetryStrategy",
    "KeywordQueryBuilder",
    "PhraseQueryBuilder",
    "DomainQueryBuilder",
    "ResultNormalizerImpl",
    "StrictResultNormalizer",
    "DeduplicatingNormalizer",
    "SearchEngineImpl",
    "UrlDeduplicationStrategy",
    # Mock providers
    "MockSearchProvider",
    "FailingMockProvider",
    "RateLimitedMockProvider",
    "SlowMockProvider",
]
