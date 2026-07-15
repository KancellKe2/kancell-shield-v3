"""Unit tests for mock search providers."""

import pytest
import asyncio

from src.search.models import ProviderState, SearchQuery
from src.search.mock_provider import (
    FailingMockProvider,
    MockSearchProvider,
    RateLimitedMockProvider,
    SlowMockProvider,
)


class TestMockSearchProvider:
    """Tests for MockSearchProvider."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.provider = MockSearchProvider(
            name="test_provider",
            priority=5,
        )

    def test_name_property(self) -> None:
        """Test name property."""
        assert self.provider.name == "test_provider"

    def test_priority_property(self) -> None:
        """Test priority property."""
        assert self.provider.priority == 5

    def test_config_property(self) -> None:
        """Test config property."""
        config = self.provider.config
        assert config.name == "test_provider"
        assert config.priority == 5
        assert config.enabled is True

    def test_is_healthy(self) -> None:
        """Test health check."""
        assert self.provider.is_healthy() is True

    def test_search_returns_results(self) -> None:
        """Test search returns results."""
        query = SearchQuery(query="malware test")
        results = asyncio.run(self.provider.search(query, 30.0))

        assert len(results) > 0
        assert all(r.provider == "test_provider" for r in results)

    def test_search_updates_health(self) -> None:
        """Test search updates health metrics."""
        query = SearchQuery(query="test")
        asyncio.run(self.provider.search(query, 30.0))

        health = self.provider.get_health()
        assert health.total_requests == 1
        assert health.last_success is not None

    def test_set_health_state(self) -> None:
        """Test setting health state."""
        self.provider.set_health_state(ProviderState.UNHEALTHY)
        assert self.provider.is_healthy() is False

    def test_set_results(self) -> None:
        """Test setting custom results."""
        from src.search.models import SearchResult
        custom_results = [
            SearchResult(
                url="https://custom.com",
                title="Custom",
                snippet="Custom result",
                provider="test",
            )
        ]
        self.provider.set_results(custom_results)

        query = SearchQuery(query="test")
        results = asyncio.run(self.provider.search(query, 30.0))

        assert len(results) == 1
        assert results[0].url == "https://custom.com"

    def test_clear_results(self) -> None:
        """Test clearing custom results."""
        self.provider.set_results([])
        self.provider.clear_results()

        query = SearchQuery(query="test")
        results = asyncio.run(self.provider.search(query, 30.0))

        # Should generate default results
        assert len(results) > 0

    def test_disabled_provider(self) -> None:
        """Test disabled provider."""
        disabled = MockSearchProvider(name="disabled", enabled=False)
        config = disabled.config
        assert config.enabled is False


class TestFailingMockProvider:
    """Tests for FailingMockProvider."""

    def test_fails_after_attempts(self) -> None:
        """Test failure after configured attempts."""
        provider = FailingMockProvider(
            name="failing",
            attempts_before_failure=2,
        )

        query = SearchQuery(query="test")

        # First two should succeed
        asyncio.run(provider.search(query, 30.0))
        asyncio.run(provider.search(query, 30.0))

        # Third should fail
        with pytest.raises(RuntimeError, match="has failed"):
            asyncio.run(provider.search(query, 30.0))


class TestRateLimitedMockProvider:
    """Tests for RateLimitedMockProvider."""

    def test_rate_limits_after_attempts(self) -> None:
        """Test rate limiting after configured requests."""
        provider = RateLimitedMockProvider(
            name="rate_limited",
            requests_before_limit=1,  # Set to 1 since MockProvider also counts
        )

        query = SearchQuery(query="test")

        # First should succeed
        asyncio.run(provider.search(query, 30.0))

        # Second should fail
        with pytest.raises(RuntimeError, match="rate limited"):
            asyncio.run(provider.search(query, 30.0))

    def test_health_state_after_limit(self) -> None:
        """Test health state after rate limit."""
        provider = RateLimitedMockProvider(
            name="rate_limited",
            requests_before_limit=1,
        )

        query = SearchQuery(query="test")
        asyncio.run(provider.search(query, 30.0))

        with pytest.raises(RuntimeError):
            asyncio.run(provider.search(query, 30.0))

        assert provider.is_healthy() is False
        health = provider.get_health()
        assert health.state == ProviderState.RATE_LIMITED


class TestSlowMockProvider:
    """Tests for SlowMockProvider."""

    def test_adds_latency(self) -> None:
        """Test simulated latency."""
        import time
        provider = SlowMockProvider(name="slow", latency_ms=50)

        query = SearchQuery(query="test")

        start = time.time()
        asyncio.run(provider.search(query, 30.0))
        elapsed = time.time() - start

        # Should have added at least 50ms latency
        assert elapsed >= 0.05
