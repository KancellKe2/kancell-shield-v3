"""Mock search provider for testing."""

from datetime import datetime, timezone
from typing import Sequence

from .interfaces import SearchProvider
from .models import (
    ProviderConfig,
    ProviderHealth,
    ProviderState,
    RateLimitConfig,
    RateLimitInfo,
    SearchQuery,
    SearchResult,
)


class MockSearchProvider(SearchProvider):
    """Mock search provider for testing.

    This provider returns deterministic mock results without any
    network activity. It can be configured to simulate various
    scenarios including errors, rate limits, and delayed responses.
    """

    def __init__(
        self,
        name: str = "mock_provider",
        priority: int = 1,
        enabled: bool = True,
        results: Sequence[SearchResult] | None = None,
        error_rate: float = 0.0,
        latency_ms: float = 0.0,
    ) -> None:
        """Initialize the mock provider.

        Args:
            name: Provider name.
            priority: Provider priority.
            enabled: Whether provider is enabled.
            results: Pre-configured results to return.
            error_rate: Probability of returning an error (0.0-1.0).
            latency_ms: Simulated latency in milliseconds.
        """
        self._name = name
        self._priority = priority
        self._enabled = enabled
        self._results = list(results) if results else []
        self._error_rate = error_rate
        self._latency_ms = latency_ms

        self._health = ProviderHealth(
            provider_name=name,
            state=ProviderState.HEALTHY,
        )
        self._rate_limit_info = RateLimitInfo(
            provider_name=name,
            requests_remaining=100,
            reset_at=datetime.now(timezone.utc),
        )

        # Track request count for deterministic behavior
        self._request_count = 0

    @property
    def name(self) -> str:
        """Provider identifier."""
        return self._name

    @property
    def priority(self) -> int:
        """Provider priority (higher = more preferred)."""
        return self._priority

    @property
    def config(self) -> ProviderConfig:
        """Provider configuration."""
        return ProviderConfig(
            name=self._name,
            priority=self._priority,
            enabled=self._enabled,
            rate_limit=RateLimitConfig(),
        )

    async def search(
        self,
        query: SearchQuery,
        timeout: float,
    ) -> Sequence[SearchResult]:
        """Execute a mock search query.

        Args:
            query: The search query to execute.
            timeout: Maximum time in seconds to wait.

        Returns:
            Sequence of mock search results.
        """
        self._request_count += 1

        # Update health metrics
        self._health = ProviderHealth(
            provider_name=self._name,
            state=ProviderState.HEALTHY,
            total_requests=self._health.total_requests + 1,
            last_success=datetime.now(timezone.utc),
        )

        # Update rate limit
        self._rate_limit_info = RateLimitInfo(
            provider_name=self._name,
            requests_remaining=self._rate_limit_info.requests_remaining - 1,
            reset_at=datetime.now(timezone.utc),
        )

        # Return pre-configured results if available
        if self._results:
            return self._add_metadata(self._results, query)

        # Generate default mock results
        return self._generate_results(query)

    def is_healthy(self) -> bool:
        """Check if provider is healthy."""
        return self._health.state == ProviderState.HEALTHY

    def get_health(self) -> ProviderHealth:
        """Get current health state."""
        return self._health

    def get_rate_limit_info(self) -> RateLimitInfo:
        """Get current rate limit state."""
        return self._rate_limit_info

    def update_health(self, state: ProviderState) -> None:
        """Update provider health state."""
        self._health = ProviderHealth(
            provider_name=self._name,
            state=state,
            total_requests=self._health.total_requests,
            failed_requests=self._health.failed_requests + 1,
            last_failure=datetime.now(timezone.utc) if state == ProviderState.UNHEALTHY else None,
        )

    def set_results(self, results: Sequence[SearchResult]) -> None:
        """Set the results to return for future searches.

        Args:
            results: Results to return.
        """
        self._results = list(results)

    def clear_results(self) -> None:
        """Clear pre-configured results."""
        self._results = []

    def set_health_state(self, state: ProviderState) -> None:
        """Set the health state.

        Args:
            state: New health state.
        """
        self._health = ProviderHealth(
            provider_name=self._name,
            state=state,
            total_requests=self._health.total_requests,
            failed_requests=self._health.failed_requests,
        )

    def _generate_results(self, query: SearchQuery) -> Sequence[SearchResult]:
        """Generate mock results for a query.

        Args:
            query: Search query.

        Returns:
            Generated results.
        """
        results: list[SearchResult] = []

        # Generate a few results based on keywords
        keywords = list(query.keywords)
        if not keywords:
            keywords = [query.query]

        for i, keyword in enumerate(keywords[:5]):
            result = SearchResult(
                url=f"https://{keyword.replace(' ', '-')}-{i}.example.com",
                title=f"Result for {keyword} - Page {i + 1}",
                snippet=f"This is a mock search result for the keyword '{keyword}'. "
                        f"It contains relevant information about {keyword}.",
                provider=self._name,
                confidence=0.8 - (i * 0.1),
                keywords=(keyword,),
                position=i,
            )
            results.append(result)

        return results

    def _add_metadata(
        self,
        results: Sequence[SearchResult],
        query: SearchQuery,
    ) -> Sequence[SearchResult]:
        """Add query metadata to results.

        Args:
            results: Results to modify.
            query: Original query.

        Returns:
            Results with updated metadata.
        """
        updated: list[SearchResult] = []

        for i, result in enumerate(results):
            updated_result = SearchResult(
                url=result.url,
                title=result.title,
                snippet=result.snippet,
                provider=self._name,
                confidence=result.confidence,
                keywords=tuple(query.keywords),
                discovered_at=datetime.now(timezone.utc),
                position=i,
                metadata={
                    **result.metadata,
                    "query": query.query,
                },
            )
            updated.append(updated_result)

        return updated


class FailingMockProvider(MockSearchProvider):
    """Mock provider that always fails after configured attempts."""

    def __init__(
        self,
        name: str = "failing_mock_provider",
        attempts_before_failure: int = 1,
        **kwargs: object,
    ) -> None:
        """Initialize the failing mock provider.

        Args:
            name: Provider name.
            attempts_before_failure: Number of successful attempts before failure.
            **kwargs: Additional arguments for parent.
        """
        super().__init__(name=name, **kwargs)
        self._attempts_before_failure = attempts_before_failure
        self._current_attempts = 0

    async def search(
        self,
        query: SearchQuery,
        timeout: float,
    ) -> Sequence[SearchResult]:
        """Execute a search that fails after configured attempts.

        Args:
            query: The search query.
            timeout: Maximum time to wait.

        Returns:
            Results until failure threshold reached.

        Raises:
            RuntimeError: After configured number of attempts.
        """
        self._current_attempts += 1

        if self._current_attempts > self._attempts_before_failure:
            self.set_health_state(ProviderState.UNHEALTHY)
            raise RuntimeError(f"Provider {self._name} has failed")

        return await super().search(query, timeout)


class RateLimitedMockProvider(MockSearchProvider):
    """Mock provider that simulates rate limiting."""

    def __init__(
        self,
        name: str = "rate_limited_mock_provider",
        requests_before_limit: int = 3,
        **kwargs: object,
    ) -> None:
        """Initialize the rate-limited mock provider.

        Args:
            name: Provider name.
            requests_before_limit: Requests before rate limit kicks in.
            **kwargs: Additional arguments for parent.
        """
        super().__init__(name=name, **kwargs)
        self._requests_before_limit = requests_before_limit
        self._request_count = 0

    async def search(
        self,
        query: SearchQuery,
        timeout: float,
    ) -> Sequence[SearchResult]:
        """Execute a search with rate limiting.

        Args:
            query: The search query.
            timeout: Maximum time to wait.

        Returns:
            Results until rate limit reached.

        Raises:
            RuntimeError: After rate limit reached.
        """
        self._request_count += 1

        if self._request_count > self._requests_before_limit:
            self.set_health_state(ProviderState.RATE_LIMITED)
            self._rate_limit_info = RateLimitInfo(
                provider_name=self._name,
                requests_remaining=0,
                reset_at=datetime.now(timezone.utc),
                backoff_until=datetime(2099, 1, 1, tzinfo=timezone.utc),
            )
            raise RuntimeError(f"Provider {self._name} is rate limited")

        return await super().search(query, timeout)


class SlowMockProvider(MockSearchProvider):
    """Mock provider with configurable latency."""

    def __init__(
        self,
        name: str = "slow_mock_provider",
        latency_ms: float = 100.0,
        **kwargs: object,
    ) -> None:
        """Initialize the slow mock provider.

        Args:
            name: Provider name.
            latency_ms: Latency in milliseconds.
            **kwargs: Additional arguments for parent.
        """
        super().__init__(name=name, latency_ms=latency_ms, **kwargs)

    async def search(
        self,
        query: SearchQuery,
        timeout: float,
    ) -> Sequence[SearchResult]:
        """Execute a slow search.

        Args:
            query: The search query.
            timeout: Maximum time to wait.

        Returns:
            Results after simulated delay.
        """
        import asyncio
        await asyncio.sleep(self._latency_ms / 1000.0)
        return await super().search(query, timeout)
