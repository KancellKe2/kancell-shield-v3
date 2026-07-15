"""Unit tests for search engine components."""

import pytest

from src.search.models import (
    ProviderConfig,
    ProviderState,
    RateLimitConfig,
    RetryConfig,
    RetryMode,
    SearchConfig,
)
from src.search.interfaces import SearchProvider
from src.search.registry import ProviderRegistryImpl
from src.search.exceptions import ProviderNotFoundError


class TestProviderRegistry:
    """Tests for ProviderRegistryImpl."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.registry = ProviderRegistryImpl()

    def test_register_provider(self) -> None:
        """Test registering a provider."""
        from src.search.mock_provider import MockSearchProvider
        provider = MockSearchProvider(name="test_provider")
        self.registry.register(provider)

        assert "test_provider" in self.registry.list_providers()
        assert self.registry.count() == 1

    def test_unregister_provider(self) -> None:
        """Test unregistering a provider."""
        from src.search.mock_provider import MockSearchProvider
        provider = MockSearchProvider(name="test_provider")
        self.registry.register(provider)
        self.registry.unregister("test_provider")

        assert "test_provider" not in self.registry.list_providers()
        assert self.registry.count() == 0

    def test_get_provider(self) -> None:
        """Test getting a provider."""
        from src.search.mock_provider import MockSearchProvider
        provider = MockSearchProvider(name="test_provider")
        self.registry.register(provider)

        retrieved = self.registry.get_provider("test_provider")
        assert retrieved is not None
        assert retrieved.name == "test_provider"

    def test_get_nonexistent_provider(self) -> None:
        """Test getting a non-existent provider."""
        retrieved = self.registry.get_provider("nonexistent")
        assert retrieved is None

    def test_unregister_nonexistent_raises(self) -> None:
        """Test unregistering non-existent provider raises error."""
        with pytest.raises(ProviderNotFoundError):
            self.registry.unregister("nonexistent")

    def test_register_empty_name_raises(self) -> None:
        """Test registering provider with empty name raises error."""
        from src.search.mock_provider import MockSearchProvider
        provider = MockSearchProvider(name="")
        with pytest.raises(ProviderNotFoundError):
            self.registry.register(provider)

    def test_get_providers_enabled_only(self) -> None:
        """Test getting only enabled providers."""
        from src.search.mock_provider import MockSearchProvider
        p1 = MockSearchProvider(name="enabled", enabled=True)
        p2 = MockSearchProvider(name="disabled", enabled=False)
        self.registry.register(p1)
        self.registry.register(p2)

        providers = self.registry.get_providers(enabled_only=True)
        assert len(providers) == 1
        assert providers[0].name == "enabled"

    def test_get_healthy_providers(self) -> None:
        """Test getting healthy providers."""
        from src.search.mock_provider import MockSearchProvider
        p1 = MockSearchProvider(name="healthy")
        p2 = MockSearchProvider(name="unhealthy")
        p2.set_health_state(ProviderState.UNHEALTHY)
        self.registry.register(p1)
        self.registry.register(p2)

        healthy = self.registry.get_healthy_providers()
        assert len(healthy) == 1
        assert healthy[0].name == "healthy"

    def test_get_healthy_providers_sorted_by_priority(self) -> None:
        """Test healthy providers are sorted by priority."""
        from src.search.mock_provider import MockSearchProvider
        p1 = MockSearchProvider(name="low", priority=1)
        p2 = MockSearchProvider(name="high", priority=10)
        p3 = MockSearchProvider(name="medium", priority=5)
        self.registry.register(p1)
        self.registry.register(p2)
        self.registry.register(p3)

        healthy = self.registry.get_healthy_providers()
        assert healthy[0].name == "high"
        assert healthy[1].name == "medium"
        assert healthy[2].name == "low"

    def test_clear_providers(self) -> None:
        """Test clearing all providers."""
        from src.search.mock_provider import MockSearchProvider
        provider = MockSearchProvider(name="test")
        self.registry.register(provider)
        self.registry.clear()

        assert self.registry.count() == 0

    def test_list_providers(self) -> None:
        """Test listing provider names."""
        from src.search.mock_provider import MockSearchProvider
        p1 = MockSearchProvider(name="a")
        p2 = MockSearchProvider(name="b")
        self.registry.register(p1)
        self.registry.register(p2)

        names = self.registry.list_providers()
        assert "a" in names
        assert "b" in names
