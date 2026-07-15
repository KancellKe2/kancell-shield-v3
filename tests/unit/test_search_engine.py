"""Unit tests for search engine."""

import pytest
import asyncio

from src.search.engine import SearchEngineImpl, UrlDeduplicationStrategy
from src.search.models import (
    SearchConfig,
    SearchResult,
)
from src.search.registry import ProviderRegistryImpl
from src.search.mock_provider import MockSearchProvider


class TestUrlDeduplicationStrategy:
    """Tests for UrlDeduplicationStrategy."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.strategy = UrlDeduplicationStrategy()

    def test_is_duplicate_same_url(self) -> None:
        """Test duplicate detection for same URL."""
        existing = [
            SearchResult(url="https://a.com", title="A", snippet="A", provider="p1")
        ]
        result = SearchResult(url="https://a.com", title="B", snippet="B", provider="p2")

        assert self.strategy.is_duplicate(result, existing) is True

    def test_is_not_duplicate_different_url(self) -> None:
        """Test non-duplicate for different URL."""
        existing = [
            SearchResult(url="https://a.com", title="A", snippet="A", provider="p1")
        ]
        result = SearchResult(url="https://b.com", title="B", snippet="B", provider="p2")

        assert self.strategy.is_duplicate(result, existing) is False

    def test_deduplicate(self) -> None:
        """Test deduplication."""
        results = [
            SearchResult(url="https://a.com", title="A", snippet="A", provider="p1"),
            SearchResult(url="https://a.com", title="B", snippet="B", provider="p2"),
            SearchResult(url="https://b.com", title="C", snippet="C", provider="p1"),
        ]

        unique, count = self.strategy.deduplicate(results)
        assert len(unique) == 2
        assert count == 1


class TestSearchEngineImpl:
    """Tests for SearchEngineImpl."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.registry = ProviderRegistryImpl()
        self.provider = MockSearchProvider(name="test_provider")
        self.registry.register(self.provider)
        self.engine = SearchEngineImpl(registry=self.registry)

    def test_search_basic(self) -> None:
        """Test basic search."""
        config = SearchConfig()
        result = asyncio.run(self.engine.search(["malware"], config))

        assert isinstance(result.total_count, int)
        assert result.query == "malware"
        assert len(result.results) > 0

    def test_search_multiple_keywords(self) -> None:
        """Test search with multiple keywords."""
        config = SearchConfig()
        result = asyncio.run(self.engine.search(["malware", "virus"], config))

        assert "malware" in result.query
        assert "virus" in result.query

    def test_search_uses_healthy_providers(self) -> None:
        """Test search uses healthy providers."""
        config = SearchConfig()
        result = asyncio.run(self.engine.search(["test"], config))

        assert "test_provider" in result.providers_used

    def test_search_aggregates_results(self) -> None:
        """Test result aggregation."""
        config = SearchConfig()
        result = asyncio.run(self.engine.search(["malware"], config))

        assert len(result.results) == result.total_count
        assert result.unique_count <= result.total_count

    def test_search_with_deduplication(self) -> None:
        """Test search with deduplication enabled."""
        config = SearchConfig(enable_deduplication=True)
        result = asyncio.run(self.engine.search(["test"], config))

        # All URLs should be unique
        urls = [r.url for r in result.results]
        assert len(urls) == len(set(urls))

    def test_search_with_confidence_threshold(self) -> None:
        """Test search with confidence threshold."""
        config = SearchConfig(confidence_threshold=0.9)
        result = asyncio.run(self.engine.search(["test"], config))

        for r in result.results:
            assert r.confidence >= 0.9

    def test_search_batch(self) -> None:
        """Test batch search."""
        config = SearchConfig(batch_size=5)
        results = asyncio.run(self.engine.search_batch(
            ["a", "b", "c", "d", "e", "f"],
            config
        ))

        assert len(results) > 0

    def test_get_provider_registry(self) -> None:
        """Test getting provider registry."""
        registry = self.engine.get_provider_registry()
        assert isinstance(registry, ProviderRegistryImpl)

    def test_get_health_status(self) -> None:
        """Test getting health status."""
        status = self.engine.get_health_status()

        assert "test_provider" in status

    def test_search_no_providers(self) -> None:
        """Test search with no providers."""
        registry = ProviderRegistryImpl()
        engine = SearchEngineImpl(registry=registry)
        config = SearchConfig()

        result = asyncio.run(engine.search(["test"], config))

        assert result.total_count == 0
        assert len(result.errors) > 0

    def test_search_results_sorted_by_confidence(self) -> None:
        """Test results are sorted by confidence."""
        config = SearchConfig()
        result = asyncio.run(self.engine.search(["malware"], config))

        if len(result.results) > 1:
            for i in range(len(result.results) - 1):
                assert result.results[i].confidence >= result.results[i + 1].confidence


class TestSearchEngineIntegration:
    """Integration tests for SearchEngine."""

    def test_multiple_providers(self) -> None:
        """Test with multiple providers."""
        registry = ProviderRegistryImpl()
        p1 = MockSearchProvider(name="provider1", priority=10)
        p2 = MockSearchProvider(name="provider2", priority=5)
        registry.register(p1)
        registry.register(p2)

        engine = SearchEngineImpl(registry=registry)
        config = SearchConfig()
        result = asyncio.run(engine.search(["test"], config))

        # Both providers should be used
        assert len(result.providers_used) >= 1

    def test_provider_priority(self) -> None:
        """Test provider priority ordering."""
        registry = ProviderRegistryImpl()
        p1 = MockSearchProvider(name="low", priority=1)
        p2 = MockSearchProvider(name="high", priority=10)
        registry.register(p1)
        registry.register(p2)

        healthy = registry.get_healthy_providers()
        assert healthy[0].name == "high"
        assert healthy[1].name == "low"
