"""Provider registry implementation for managing search providers."""

from typing import Sequence

from .exceptions import ProviderNotFoundError
from .interfaces import ProviderRegistry, SearchProvider
from .models import ProviderHealth, ProviderState


class ProviderRegistryImpl(ProviderRegistry):
    """Implementation of provider registry for managing provider instances.

    This registry manages the lifecycle of search providers including
    registration, unregistration, and health-based retrieval.
    """

    def __init__(self) -> None:
        """Initialize the provider registry."""
        self._providers: dict[str, SearchProvider] = {}

    def register(self, provider: SearchProvider) -> None:
        """Register a provider.

        Args:
            provider: Provider to register.

        Raises:
            ProviderNotFoundError: If provider name is invalid.
        """
        if not provider.name:
            raise ProviderNotFoundError("Provider name cannot be empty")
        self._providers[provider.name] = provider

    def unregister(self, name: str) -> None:
        """Unregister a provider.

        Args:
            name: Provider name to remove.

        Raises:
            ProviderNotFoundError: If provider not found.
        """
        if name not in self._providers:
            raise ProviderNotFoundError(f"Provider '{name}' not found")
        del self._providers[name]

    def get_provider(self, name: str) -> SearchProvider | None:
        """Get provider by name.

        Args:
            name: Provider name.

        Returns:
            Provider if found, None otherwise.
        """
        return self._providers.get(name)

    def get_providers(self, enabled_only: bool = True) -> Sequence[SearchProvider]:
        """Get all providers.

        Args:
            enabled_only: Filter to enabled providers only.

        Returns:
            Sequence of providers.
        """
        providers = list(self._providers.values())
        if enabled_only:
            providers = [p for p in providers if p.config.enabled]
        return providers

    def get_healthy_providers(self) -> Sequence[SearchProvider]:
        """Get all healthy providers sorted by priority.

        Returns:
            Sequence of healthy providers sorted by priority (descending).
        """
        healthy = [
            p for p in self._providers.values()
            if p.config.enabled and p.is_healthy()
        ]
        # Sort by priority (higher first)
        return sorted(healthy, key=lambda p: p.priority, reverse=True)

    def list_providers(self) -> list[str]:
        """List all registered provider names.

        Returns:
            List of provider names.
        """
        return list(self._providers.keys())

    def clear(self) -> None:
        """Clear all registered providers."""
        self._providers.clear()

    def count(self) -> int:
        """Get the number of registered providers.

        Returns:
            Number of providers.
        """
        return len(self._providers)
