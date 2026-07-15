"""Protocol interfaces for the Search Engine.

This module contains only Protocol and ABC interface definitions.
No implementation should be placed here.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Sequence

from .models import (
    PaginationState,
    ProviderConfig,
    ProviderHealth,
    ProviderState,
    RateLimitInfo,
    RetryConfig,
    SearchConfig,
    SearchQuery,
    SearchResult,
    SearchResultSet,
)


class SearchProvider(Protocol):
    """Protocol for search provider implementations.

    Providers are responsible for executing search queries against
    specific search backends (APIs, services, etc.).
    """

    @property
    def name(self) -> str:
        """Provider identifier."""
        ...

    @property
    def priority(self) -> int:
        """Provider priority (higher = more preferred)."""
        ...

    @property
    def config(self) -> ProviderConfig:
        """Provider configuration."""
        ...

    async def search(
        self,
        query: SearchQuery,
        timeout: float,
    ) -> Sequence[SearchResult]:
        """Execute a search query.

        Args:
            query: The search query to execute.
            timeout: Maximum time in seconds to wait.

        Returns:
            Sequence of search results.

        Raises:
            SearchError: If search execution fails.
        """
        ...

    def is_healthy(self) -> bool:
        """Check if provider is healthy.

        Returns:
            True if provider can accept requests.
        """
        ...

    def get_health(self) -> ProviderHealth:
        """Get current health state.

        Returns:
            ProviderHealth with current metrics.
        """
        ...

    def get_rate_limit_info(self) -> RateLimitInfo:
        """Get current rate limit state.

        Returns:
            RateLimitInfo with current state.
        """
        ...

    def update_health(self, state: ProviderState) -> None:
        """Update provider health state.

        Args:
            state: New health state.
        """
        ...


class RateLimiter(Protocol):
    """Protocol for rate limiting strategies."""

    async def acquire(self, provider: str) -> bool:
        """Acquire permission to make a request.

        Args:
            provider: Provider identifier.

        Returns:
            True if permission granted, False otherwise.
        """
        ...

    def release(self, provider: str) -> None:
        """Release rate limit token.

        Args:
            provider: Provider identifier.
        """
        ...

    def get_wait_time(self, provider: str) -> float:
        """Get estimated wait time in seconds.

        Args:
            provider: Provider identifier.

        Returns:
            Seconds to wait before next request.
        """
        ...

    def is_limited(self, provider: str) -> bool:
        """Check if provider is rate limited.

        Args:
            provider: Provider identifier.

        Returns:
            True if rate limited.
        """
        ...


class RetryStrategy(Protocol):
    """Protocol for retry behavior."""

    def should_retry(
        self,
        attempt: int,
        error: Exception,
    ) -> bool:
        """Determine if request should be retried.

        Args:
            attempt: Current attempt number (1-based).
            error: The exception that occurred.

        Returns:
            True if should retry.
        """
        ...

    def get_backoff_delay(self, attempt: int) -> float:
        """Calculate backoff delay in seconds.

        Args:
            attempt: Current attempt number (1-based).

        Returns:
            Delay in seconds before next attempt.
        """
        ...

    def get_config(self) -> RetryConfig:
        """Get retry configuration.

        Returns:
            RetryConfig being used.
        """
        ...


class ResultNormalizer(Protocol):
    """Protocol for result format normalization."""

    def normalize(
        self,
        results: Sequence[SearchResult],
        provider: str,
    ) -> Sequence[SearchResult]:
        """Normalize search results.

        Args:
            results: Raw results from provider.
            provider: Source provider name.

        Returns:
            Normalized results.
        """
        ...

    def calculate_confidence(
        self,
        result: SearchResult,
        keywords: Sequence[str],
    ) -> float:
        """Calculate confidence score for result.

        Args:
            result: Search result to score.
            keywords: Keywords that matched.

        Returns:
            Confidence score between 0 and 1.
        """
        ...


class QueryBuilder(Protocol):
    """Protocol for building queries from keywords."""

    def build_query(
        self,
        keywords: Sequence[str],
        template: str | None = None,
    ) -> SearchQuery:
        """Build a search query from keywords.

        Args:
            keywords: Keywords to search for.
            template: Optional query template.

        Returns:
            SearchQuery ready for execution.
        """
        ...

    def build_batch_queries(
        self,
        keywords: Sequence[str],
        batch_size: int,
        template: str | None = None,
    ) -> Sequence[Sequence[SearchQuery]]:
        """Build batch queries from keywords.

        Args:
            keywords: Keywords to search for.
            batch_size: Number of queries per batch.
            template: Optional query template.

        Returns:
            Batches of SearchQuery objects.
        """
        ...


class ProviderRegistry(Protocol):
    """Protocol for managing provider instances."""

    def register(
        self,
        provider: SearchProvider,
    ) -> None:
        """Register a provider.

        Args:
            provider: Provider to register.
        """
        ...

    def unregister(self, name: str) -> None:
        """Unregister a provider.

        Args:
            name: Provider name to remove.
        """
        ...

    def get_provider(self, name: str) -> SearchProvider | None:
        """Get provider by name.

        Args:
            name: Provider name.

        Returns:
            Provider if found, None otherwise.
        """
        ...

    def get_providers(
        self,
        enabled_only: bool = True,
    ) -> Sequence[SearchProvider]:
        """Get all providers.

        Args:
            enabled_only: Filter to enabled providers only.

        Returns:
            Sequence of providers.
        """
        ...

    def get_healthy_providers(self) -> Sequence[SearchProvider]:
        """Get all healthy providers sorted by priority.

        Returns:
            Sequence of healthy providers.
        """
        ...


class HealthChecker(Protocol):
    """Protocol for provider health checking."""

    def check_health(
        self,
        provider: SearchProvider,
    ) -> ProviderHealth:
        """Check provider health.

        Args:
            provider: Provider to check.

        Returns:
            Updated ProviderHealth.
        """
        ...

    def check_all(
        self,
        providers: Sequence[SearchProvider],
    ) -> dict[str, ProviderHealth]:
        """Check health of all providers.

        Args:
            providers: Providers to check.

        Returns:
            Map of provider name to health.
        """
        ...


class SearchEngine(ABC):
    """Abstract base class for search orchestration.

    This is the main interface for executing searches
    across multiple providers.
    """

    @abstractmethod
    async def search(
        self,
        keywords: Sequence[str],
        config: SearchConfig,
    ) -> SearchResultSet:
        """Execute search for keywords across providers.

        Args:
            keywords: Keywords to search for.
            config: Search configuration.

        Returns:
            SearchResultSet with aggregated results.
        """
        ...

    @abstractmethod
    async def search_batch(
        self,
        keywords: Sequence[str],
        config: SearchConfig,
    ) -> Sequence[SearchResultSet]:
        """Execute batch search for multiple keywords.

        Args:
            keywords: Keywords to search for.
            config: Search configuration.

        Returns:
            Sequence of SearchResultSet, one per keyword batch.
        """
        ...

    @abstractmethod
    def get_provider_registry(self) -> ProviderRegistry:
        """Get the provider registry.

        Returns:
            ProviderRegistry instance.
        """
        ...

    @abstractmethod
    def get_health_status(self) -> dict[str, ProviderHealth]:
        """Get health status of all providers.

        Returns:
            Map of provider name to health.
        """
        ...


class DeduplicationStrategy(Protocol):
    """Protocol for result deduplication."""

    def is_duplicate(
        self,
        result: SearchResult,
        existing: Sequence[SearchResult],
    ) -> bool:
        """Check if result is a duplicate.

        Args:
            result: Result to check.
            existing: Existing results to compare.

        Returns:
            True if duplicate.
        """
        ...

    def deduplicate(
        self,
        results: Sequence[SearchResult],
    ) -> tuple[Sequence[SearchResult], int]:
        """Deduplicate results.

        Args:
            results: Results to deduplicate.

        Returns:
            Tuple of (unique_results, duplicate_count).
        """
        ...


class PaginationHandler(Protocol):
    """Protocol for handling pagination."""

    def get_next_page(
        self,
        current_state: PaginationState,
        results_count: int,
    ) -> PaginationState:
        """Get next pagination state.

        Args:
            current_state: Current pagination state.
            results_count: Number of results returned.

        Returns:
            Next PaginationState.
        """
        ...

    def has_more_pages(
        self,
        state: PaginationState,
    ) -> bool:
        """Check if more pages are available.

        Args:
            state: Current pagination state.

        Returns:
            True if more pages available.
        """
        ...
