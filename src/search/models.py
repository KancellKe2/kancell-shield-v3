"""Data models for the Search Engine.

This module contains only dataclasses, enums, and immutable models.
No algorithms or business logic should be placed here.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import FrozenSet


class ProviderState(Enum):
    """Health states for search providers."""

    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    DISABLED = auto()
    RATE_LIMITED = auto()


class PaginationType(Enum):
    """Types of pagination supported."""

    OFFSET = auto()
    CURSOR = auto()
    PAGE = auto()


class RetryMode(Enum):
    """Retry behavior modes."""

    FIXED = auto()
    LINEAR = auto()
    EXPONENTIAL = auto()
    JITTERED = auto()


@dataclass(frozen=True)
class SearchQuery:
    """Represents a single search query with metadata.

    This is an immutable data class.
    """

    query: str
    keywords: FrozenSet[str] = field(default_factory=frozenset)
    language: str = "en"
    region: str = "US"
    safe_search: bool = True
    custom_params: FrozenSet[tuple[str, str]] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate query data after initialization."""
        if not self.query:
            raise ValueError("Query text cannot be empty")


@dataclass(frozen=True)
class SearchResult:
    """Represents a search result with URL, title, and snippet.

    This is an immutable data class.
    """

    url: str
    title: str
    snippet: str
    provider: str
    confidence: float = 0.5
    keywords: tuple[str, ...] = field(default_factory=tuple)
    discovered_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    position: int = 0
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate result data after initialization."""
        if not self.url:
            raise ValueError("Result URL cannot be empty")
        if not self.title:
            raise ValueError("Result title cannot be empty")
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class SearchResultSet:
    """A collection of search results with metadata.

    This is an immutable data class.
    """

    results: tuple[SearchResult, ...]
    total_count: int
    unique_count: int
    provider_counts: dict[str, int] = field(default_factory=dict)
    query: str = ""
    execution_time_ms: float = 0.0
    providers_used: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate result set after initialization."""
        if self.total_count < 0:
            raise ValueError("total_count cannot be negative")
        if self.unique_count < 0:
            raise ValueError("unique_count cannot be negative")

    def filter_by_provider(self, provider: str) -> "SearchResultSet":
        """Return a new SearchResultSet filtered by provider."""
        filtered = tuple(r for r in self.results if r.provider == provider)
        return self._create_filtered_set(filtered, provider)

    def filter_by_confidence(self, min_confidence: float) -> "SearchResultSet":
        """Return a new SearchResultSet filtered by minimum confidence."""
        filtered = tuple(
            r for r in self.results if r.confidence >= min_confidence
        )
        return SearchResultSet(
            results=filtered,
            total_count=len(filtered),
            unique_count=len(set(r.url for r in filtered)),
            provider_counts=self._count_providers(filtered),
            query=self.query,
            execution_time_ms=self.execution_time_ms,
            providers_used=self.providers_used,
            errors=self.errors,
            metadata=self.metadata,
        )

    def _create_filtered_set(
        self, results: tuple[SearchResult, ...], provider: str
    ) -> "SearchResultSet":
        """Helper to create a filtered set."""
        return SearchResultSet(
            results=results,
            total_count=len(results),
            unique_count=len(set(r.url for r in results)),
            provider_counts={provider: len(results)},
            query=self.query,
            execution_time_ms=self.execution_time_ms,
            providers_used=(provider,),
            errors=self.errors,
            metadata=self.metadata,
        )

    def _count_providers(self, results: tuple[SearchResult, ...]) -> dict[str, int]:
        """Count results per provider."""
        counts: dict[str, int] = {}
        for result in results:
            counts[result.provider] = counts.get(result.provider, 0) + 1
        return counts


@dataclass(frozen=True)
class RateLimitConfig:
    """Configuration for rate limiting.

    This is an immutable data class.
    """

    requests_per_window: int = 10
    window_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 300.0

    def __post_init__(self) -> None:
        """Validate rate limit config."""
        if self.requests_per_window < 1:
            raise ValueError("requests_per_window must be at least 1")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass(frozen=True)
class RateLimitInfo:
    """Current rate limiting state for a provider.

    This is an immutable data class.
    """

    provider_name: str
    requests_remaining: int
    reset_at: datetime
    backoff_until: datetime | None = None
    current_backoff: float = 0.0

    def is_limited(self) -> bool:
        """Check if currently rate limited."""
        if self.backoff_until is None:
            return False
        return datetime.now(timezone.utc) < self.backoff_until


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior.

    This is an immutable data class.
    """

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    mode: RetryMode = RetryMode.EXPONENTIAL

    def __post_init__(self) -> None:
        """Validate retry config."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_delay <= 0:
            raise ValueError("initial_delay must be positive")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")


@dataclass(frozen=True)
class ProviderHealth:
    """Health state and metrics for a provider.

    This is an immutable data class.
    """

    provider_name: str
    state: ProviderState
    success_rate: float = 1.0
    avg_response_time_ms: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    last_check: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_success: datetime | None = None
    last_failure: datetime | None = None

    def __post_init__(self) -> None:
        """Validate health data."""
        if self.success_rate < 0.0 or self.success_rate > 1.0:
            raise ValueError("success_rate must be between 0.0 and 1.0")


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a search provider.

    This is an immutable data class.
    """

    name: str
    priority: int = 1
    enabled: bool = True
    timeout: float | None = None
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    weight: float = 1.0
    custom_settings: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate provider config."""
        if not self.name:
            raise ValueError("Provider name cannot be empty")
        if self.priority < 0:
            raise ValueError("Priority cannot be negative")
        if self.weight < 0.0 or self.weight > 1.0:
            raise ValueError("Weight must be between 0.0 and 1.0")


@dataclass(frozen=True)
class SearchConfig:
    """Global search engine configuration.

    This is an immutable data class.
    """

    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    max_results_per_query: int = 100
    provider_timeout: dict[str, float] = field(default_factory=dict)
    rate_limit_requests: int = 10
    rate_limit_window: float = 60.0
    batch_size: int = 10
    enable_deduplication: bool = True
    confidence_threshold: float = 0.5
    providers: tuple[ProviderConfig, ...] = field(default_factory=tuple)
    global_rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    global_retry: RetryConfig = field(default_factory=RetryConfig)

    def __post_init__(self) -> None:
        """Validate search config."""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if self.confidence_threshold < 0.0 or self.confidence_threshold > 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")


@dataclass(frozen=True)
class PaginationState:
    """Pagination tracking for result sets.

    This is an immutable data class.
    """

    pagination_type: PaginationType = PaginationType.OFFSET
    offset: int = 0
    cursor: str | None = None
    page: int = 1
    page_size: int = 20
    total_results: int | None = None
    has_more: bool = True

    def __post_init__(self) -> None:
        """Validate pagination state."""
        if self.offset < 0:
            raise ValueError("offset cannot be negative")
        if self.page < 1:
            raise ValueError("page must be at least 1")
        if self.page_size < 1:
            raise ValueError("page_size must be at least 1")

    def next_offset(self, count: int) -> "PaginationState":
        """Create state for next offset-based page."""
        return PaginationState(
            pagination_type=self.pagination_type,
            offset=self.offset + count,
            cursor=self.cursor,
            page=self.page,
            page_size=self.page_size,
            total_results=self.total_results,
            has_more=self.has_more,
        )

    def next_page(self) -> "PaginationState":
        """Create state for next page-based navigation."""
        return PaginationState(
            pagination_type=self.pagination_type,
            offset=self.offset,
            cursor=self.cursor,
            page=self.page + 1,
            page_size=self.page_size,
            total_results=self.total_results,
            has_more=self.has_more,
        )


@dataclass(frozen=True)
class ProviderMetrics:
    """Aggregated metrics for provider performance.

    This is an immutable data class.
    """

    provider_name: str
    total_queries: int = 0
    total_results: int = 0
    avg_confidence: float = 0.0
    avg_response_time_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0
    rate_limit_count: int = 0
    timeout_count: int = 0
    period_start: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    period_end: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_queries == 0:
            return 0.0
        return self.success_count / self.total_queries
