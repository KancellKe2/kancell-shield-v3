"""Provider registry for managing search providers.

This module provides a registry for managing multiple search
providers and their configurations.
"""

from typing import Sequence

from .models import DiscoverySource, SourceType
from .provider_adapter import ProviderAdapter, MockSearchProviderAdapter


class ProviderRegistry:
    """Registry for managing search providers.

    Providers are registered by name and can be enabled/disabled.
    """

    def __init__(self) -> None:
        """Initialize provider registry."""
        self._providers: dict[str, ProviderAdapter] = {}
        self._enabled: set[str] = set()
        self._priorities: dict[str, int] = {}

    def register(
        self,
        provider: ProviderAdapter,
        enabled: bool = True,
        priority: int = 50,
    ) -> None:
        """Register a provider.

        Args:
            provider: Provider adapter to register.
            enabled: Whether provider is enabled.
            priority: Provider priority (higher = preferred).
        """
        name = provider.provider_name
        self._providers[name] = provider
        self._priorities[name] = priority

        if enabled:
            self._enabled.add(name)

    def unregister(self, name: str) -> bool:
        """Unregister a provider.

        Args:
            name: Provider name.

        Returns:
            True if provider was unregistered.
        """
        if name not in self._providers:
            return False

        del self._providers[name]
        self._enabled.discard(name)
        self._priorities.pop(name, None)
        return True

    def get(self, name: str) -> ProviderAdapter | None:
        """Get a provider by name.

        Args:
            name: Provider name.

        Returns:
            Provider adapter or None.
        """
        return self._providers.get(name)

    def get_enabled(self) -> list[ProviderAdapter]:
        """Get all enabled providers.

        Returns:
            List of enabled providers.
        """
        return [
            self._providers[name]
            for name in self._enabled
            if name in self._providers
        ]

    def get_disabled(self) -> list[ProviderAdapter]:
        """Get all disabled providers.

        Returns:
            List of disabled providers.
        """
        return [
            self._providers[name]
            for name in self._providers
            if name not in self._enabled
        ]

    def get_all(self) -> list[ProviderAdapter]:
        """Get all registered providers.

        Returns:
            List of all providers.
        """
        return list(self._providers.values())

    def enable(self, name: str) -> bool:
        """Enable a provider.

        Args:
            name: Provider name.

        Returns:
            True if provider was enabled.
        """
        if name not in self._providers:
            return False
        self._enabled.add(name)
        return True

    def disable(self, name: str) -> bool:
        """Disable a provider.

        Args:
            name: Provider name.

        Returns:
            True if provider was disabled.
        """
        if name not in self._providers:
            return False
        self._enabled.discard(name)
        return True

    def is_enabled(self, name: str) -> bool:
        """Check if a provider is enabled.

        Args:
            name: Provider name.

        Returns:
            True if provider is enabled.
        """
        return name in self._enabled

    def set_priority(self, name: str, priority: int) -> bool:
        """Set provider priority.

        Args:
            name: Provider name.
            priority: Priority value.

        Returns:
            True if priority was set.
        """
        if name not in self._providers:
            return False
        self._priorities[name] = priority
        return True

    def get_priority(self, name: str) -> int:
        """Get provider priority.

        Args:
            name: Provider name.

        Returns:
            Priority value or 0 if not found.
        """
        return self._priorities.get(name, 0)

    def get_sorted_by_priority(self) -> list[ProviderAdapter]:
        """Get enabled providers sorted by priority.

        Returns:
            List of enabled providers sorted by priority.
        """
        enabled = self.get_enabled()
        return sorted(
            enabled,
            key=lambda p: self._priorities.get(p.provider_name, 0),
            reverse=True,
        )

    def get_by_type(self, source_type: SourceType) -> list[ProviderAdapter]:
        """Get providers by source type.

        Args:
            source_type: Source type to filter by.

        Returns:
            List of matching providers.
        """
        return [
            p for p in self._providers.values()
            if p.provider_type == source_type
        ]

    def clear(self) -> None:
        """Clear all registered providers."""
        self._providers.clear()
        self._enabled.clear()
        self._priorities.clear()

    def __len__(self) -> int:
        """Get number of registered providers."""
        return len(self._providers)

    def __contains__(self, name: str) -> bool:
        """Check if provider is registered.

        Args:
            name: Provider name.

        Returns:
            True if provider is registered.
        """
        return name in self._providers


class DefaultProviderRegistry(ProviderRegistry):
    """Provider registry with default mock providers.

    Pre-registers common mock providers for testing.
    """

    def __init__(
        self,
        include_mocks: bool = True,
    ) -> None:
        """Initialize default registry.

        Args:
            include_mocks: Whether to include mock providers.
        """
        super().__init__()

        if include_mocks:
            self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default mock providers."""
        # Certificate Transparency mock
        ct_provider = MockSearchProviderAdapter(
            provider_name="ct",
            mock_domains=[
                "cert-transparency-example.com",
            ],
        )
        self.register(ct_provider, priority=100)

        # Passive DNS mock
        pdns_provider = MockSearchProviderAdapter(
            provider_name="passive_dns",
            mock_domains=[
                "passive-dns-example.com",
            ],
        )
        self.register(pdns_provider, priority=80)

        # DNS Cache mock
        dns_provider = MockSearchProviderAdapter(
            provider_name="dns_cache",
            mock_domains=[
                "dns-cache-example.com",
            ],
        )
        self.register(dns_provider, priority=60)


class ProviderConfig:
    """Configuration for a provider."""

    def __init__(
        self,
        name: str,
        enabled: bool = True,
        priority: int = 50,
        max_requests_per_minute: int = 60,
        timeout_seconds: float = 30.0,
        retry_count: int = 3,
        source_type: SourceType = SourceType.CUSTOM,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Initialize provider config.

        Args:
            name: Provider name.
            enabled: Whether provider is enabled.
            priority: Provider priority.
            max_requests_per_minute: Rate limit.
            timeout_seconds: Request timeout.
            retry_count: Number of retries.
            source_type: Source type.
            metadata: Additional metadata.
        """
        self.name = name
        self.enabled = enabled
        self.priority = priority
        self.max_requests_per_minute = max_requests_per_minute
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.source_type = source_type
        self.metadata = metadata or {}

    def to_discovery_source(self) -> DiscoverySource:
        """Convert to discovery source.

        Returns:
            DiscoverySource representation.
        """
        return DiscoverySource(
            name=self.name,
            source_type=self.source_type,
            description=self.metadata.get("description"),
            priority=self.priority,
            timeout_seconds=self.timeout_seconds,
            enabled=self.enabled,
            metadata=tuple(self.metadata.items()),
        )


class ProviderRegistryBuilder:
    """Builder for creating provider registries.

    Provides a fluent interface for building registries.
    """

    def __init__(self) -> None:
        """Initialize builder."""
        self._registry = ProviderRegistry()
        self._configs: list[ProviderConfig] = []

    def add_config(self, config: ProviderConfig) -> "ProviderRegistryBuilder":
        """Add a provider configuration.

        Args:
            config: Provider configuration.

        Returns:
            Self for chaining.
        """
        self._configs.append(config)
        return self

    def add_mock(
        self,
        name: str,
        domains: Sequence[str] | None = None,
        priority: int = 50,
        enabled: bool = True,
    ) -> "ProviderRegistryBuilder":
        """Add a mock provider.

        Args:
            name: Provider name.
            domains: Mock domains to return.
            priority: Provider priority.
            enabled: Whether provider is enabled.

        Returns:
            Self for chaining.
        """
        provider = MockSearchProviderAdapter(
            provider_name=name,
            mock_domains=domains or [],
        )
        self._registry.register(provider, enabled=enabled, priority=priority)
        return self

    def build(self) -> ProviderRegistry:
        """Build the registry.

        Returns:
            Configured registry.
        """
        for config in self._configs:
            source = config.to_discovery_source()
            provider = MockSearchProviderAdapter(
                provider_name=config.name,
                mock_domains=[],
            )
            self._registry.register(
                provider,
                enabled=config.enabled,
                priority=config.priority,
            )

        return self._registry
