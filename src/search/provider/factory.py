"""Provider factory implementation.

This module provides the ProviderFactoryImpl class that creates
and configures provider instances.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .context import ProviderContext
from .exceptions import ConfigurationError, ProviderError, ProviderAlreadyRegisteredError
from .interfaces import Provider, ProviderFactory, ProviderRegistry
from .models import (
    AuthMethod,
    HealthStatus,
    ProviderAuthentication,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderFeatureFlags,
    ProviderHealthStatus,
    ProviderInfo,
    ProviderRequest,
    ProviderResponse,
    ProviderStatistics,
    ProviderVersion,
    RateLimitInfo,
)


@dataclass
class MockProvider(Provider):
    """Mock implementation of Provider for testing.

    This provides a simple mock that can be configured with
    test responses and behaviors.
    """

    _info: ProviderInfo
    _capabilities: ProviderCapabilities
    _version: ProviderVersion
    _config: ProviderConfiguration | None = None
    _auth: ProviderAuthentication | None = None
    _health: ProviderHealthStatus | None = None
    _rate_limit: RateLimitInfo | None = None
    _stats: ProviderStatistics | None = None
    _is_healthy_result: bool = True
    _search_results: tuple[dict[str, object], ...] = ()
    _search_total_count: int = 0
    _validate_config_result: bool = True

    @property
    def info(self) -> ProviderInfo:
        """Get provider information."""
        return self._info

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        return self._capabilities

    @property
    def version(self) -> ProviderVersion:
        """Get provider version."""
        return self._version

    async def search(
        self,
        request: ProviderRequest,
        config: ProviderConfiguration,
    ) -> ProviderResponse:
        """Execute a mock search."""
        from .models import ProviderResponse
        return ProviderResponse(
            results=self._search_results,
            total_count=self._search_total_count,
            provider_name=self._info.name,
            request=request,
        )

    async def authenticate(
        self,
        credentials: ProviderAuthentication,
    ) -> ProviderAuthentication:
        """Mock authentication."""
        return ProviderAuthentication(
            method=credentials.method,
            credentials=credentials.credentials,
            token=credentials.credentials.get("token", "mock-token"),
            token_expires_at=credentials.token_expires_at,
            is_authenticated=True,
            last_auth_attempt=credentials.last_auth_attempt,
        )

    async def refresh_auth(
        self,
        credentials: ProviderAuthentication,
    ) -> ProviderAuthentication:
        """Mock auth refresh."""
        return credentials

    def get_rate_limit_info(self) -> RateLimitInfo:
        """Get rate limit info."""
        return self._rate_limit or RateLimitInfo(
            requests_remaining=100,
            requests_limit=100,
            reset_at=datetime.now(timezone.utc),
        )

    def get_health_status(self) -> ProviderHealthStatus:
        """Get health status."""
        return self._health or ProviderHealthStatus(
            provider_name=self._info.name,
            status=HealthStatus.HEALTHY,
        )

    def get_statistics(self) -> ProviderStatistics:
        """Get statistics."""
        return self._stats or ProviderStatistics(provider_name=self._info.name)

    async def health_check(self) -> bool:
        """Mock health check."""
        return self._is_healthy_result

    def validate_config(self, config: ProviderConfiguration) -> bool:
        """Mock config validation."""
        return self._validate_config_result

    def get_auth_headers(
        self,
        credentials: ProviderAuthentication,
    ) -> dict[str, str]:
        """Get auth headers."""
        headers: dict[str, str] = {}
        value = credentials.get_header_value()
        if value:
            if credentials.method == AuthMethod.API_KEY:
                headers["X-API-Key"] = value
            elif credentials.method == AuthMethod.BEARER:
                headers["Authorization"] = f"Bearer {value}"
            elif credentials.method == AuthMethod.BASIC:
                headers["Authorization"] = f"Basic {value}"
        return headers

    def supports_feature(self, feature: str) -> bool:
        """Check if feature is supported."""
        return False

    def set_search_results(
        self,
        results: tuple[dict[str, object], ...],
        total_count: int,
    ) -> None:
        """Configure mock search results."""
        self._search_results = results
        self._search_total_count = total_count

    def set_health_result(self, is_healthy: bool) -> None:
        """Configure mock health check result."""
        self._is_healthy_result = is_healthy

    def is_healthy(self) -> bool:
        """Check if provider is healthy."""
        return self._is_healthy_result


class ProviderFactoryImpl(ProviderFactory):
    """Implementation of ProviderFactory.

    This factory creates provider instances with the given
    configuration and credentials.
    """

    def __init__(self) -> None:
        """Initialize the factory."""
        self._providers: dict[str, type[Provider]] = {}

    def register(self, name: str, provider_class: type[Provider]) -> None:
        """Register a provider class.

        Args:
            name: Provider name to register.
            provider_class: Provider class to use for creation.
        """
        self._providers[name] = provider_class

    def unregister(self, name: str) -> None:
        """Unregister a provider.

        Args:
            name: Provider name to remove.
        """
        self._providers.pop(name, None)

    def create(
        self,
        config: ProviderConfiguration,
        credentials: ProviderAuthentication | None = None,
    ) -> Provider:
        """Create a provider instance.

        Args:
            config: Provider configuration.
            credentials: Optional authentication credentials.

        Returns:
            Configured Provider instance.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        provider_class = self._providers.get(config.provider_name)

        if provider_class is None:
            provider_class = MockProvider

        try:
            provider = self._create_provider(
                provider_class,
                config,
                credentials,
            )
            return provider
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create provider: {e}",
                provider_name=config.provider_name,
            ) from e

    def _create_provider(
        self,
        provider_class: type[Provider],
        config: ProviderConfiguration,
        credentials: ProviderAuthentication | None,
    ) -> Provider:
        """Internal method to create provider instance.

        Args:
            provider_class: Class to instantiate.
            config: Configuration to use.
            credentials: Credentials to use.

        Returns:
            Provider instance.
        """
        if provider_class is MockProvider:
            info = ProviderInfo(
                name=config.provider_name,
                display_name=config.provider_name.title(),
                version=ProviderVersion(1, 0, 0, "v1"),
                description=f"Mock provider: {config.provider_name}",
            )
            capabilities = ProviderCapabilities()

            return MockProvider(
                _info=info,
                _capabilities=capabilities,
                _version=info.version,
                _config=config,
                _auth=credentials,
            )

        return provider_class()

    def supports(self, provider_name: str) -> bool:
        """Check if this factory supports a provider.

        Args:
            provider_name: Name of provider to check.

        Returns:
            True if this factory creates the named provider.
        """
        return provider_name in self._providers

    def get_supported_providers(self) -> tuple[str, ...]:
        """Get names of providers this factory supports.

        Returns:
            Tuple of supported provider names.
        """
        return tuple(self._providers.keys())


class ProviderRegistryImpl(ProviderRegistry):
    """Implementation of ProviderRegistry.

    This registry manages provider instances and provides
    lookup and discovery capabilities.
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._providers: dict[str, Provider] = {}
        self._configs: dict[str, ProviderConfiguration] = {}
        self._factories: dict[str, ProviderFactory] = {}

    def register(
        self,
        provider: Provider,
        config: ProviderConfiguration,
    ) -> None:
        """Register a provider.

        Args:
            provider: Provider instance to register.
            config: Provider configuration.

        Raises:
            ProviderAlreadyRegisteredError: If provider already exists.
        """
        if config.provider_name in self._providers:
            raise ProviderAlreadyRegisteredError(
                f"Provider '{config.provider_name}' is already registered",
                provider_name=config.provider_name,
            )

        self._providers[config.provider_name] = provider
        self._configs[config.provider_name] = config

    def unregister(self, provider_name: str) -> None:
        """Unregister a provider.

        Args:
            provider_name: Name of provider to remove.
        """
        self._providers.pop(provider_name, None)
        self._configs.pop(provider_name, None)

    def get(self, provider_name: str) -> Provider | None:
        """Get a registered provider.

        Args:
            provider_name: Name of provider to get.

        Returns:
            Provider if registered, None otherwise.
        """
        return self._providers.get(provider_name)

    def list_providers(self) -> tuple[str, ...]:
        """List all registered provider names.

        Returns:
            Tuple of provider names.
        """
        return tuple(self._providers.keys())

    def get_by_capability(self, capability: str) -> tuple[Provider, ...]:
        """Get providers supporting a capability.

        Args:
            capability: Capability name to filter by.

        Returns:
            Sequence of matching providers.
        """
        results: list[Provider] = []
        for provider in self._providers.values():
            if self._has_capability(provider, capability):
                results.append(provider)
        return tuple(results)

    def _has_capability(self, provider: Provider, capability: str) -> bool:
        """Check if provider has a specific capability.

        Args:
            provider: Provider to check.
            capability: Capability to look for.

        Returns:
            True if provider has the capability.
        """
        caps = provider.capabilities

        capability_lower = capability.lower()
        if capability_lower == "search":
            return caps.supports_search
        if capability_lower == "pagination":
            return caps.supports_pagination is not None
        if capability_lower == "filtering":
            return caps.supports_filtering
        if capability_lower == "language_filter":
            return caps.supports_language_filter
        if capability_lower == "region_filter":
            return caps.supports_region_filter
        if capability_lower == "date_filter":
            return caps.supports_date_filter
        if capability_lower == "safe_search":
            return caps.supports_safe_search
        if capability_lower == "autocomplete":
            return caps.supports_autocomplete
        if capability_lower == "suggestions":
            return caps.supports_suggestions
        if capability_lower == "batch_search":
            return caps.supports_batch_search

        if capability in caps.custom_capabilities:
            return caps.custom_capabilities[capability]

        return False

    def get_healthy(self) -> tuple[Provider, ...]:
        """Get all healthy providers.

        Returns:
            Sequence of healthy providers.
        """
        results: list[Provider] = []
        for provider in self._providers.values():
            if provider.is_healthy():
                results.append(provider)
        return tuple(results)

    def get_by_version(self, api_version: str) -> tuple[Provider, ...]:
        """Get providers supporting a specific API version.

        Args:
            api_version: API version to filter by.

        Returns:
            Sequence of matching providers.
        """
        results: list[Provider] = []
        for provider in self._providers.values():
            if provider.version.api_version == api_version:
                results.append(provider)
        return tuple(results)

    def get_config(self, provider_name: str) -> ProviderConfiguration | None:
        """Get configuration for a provider.

        Args:
            provider_name: Name of provider.

        Returns:
            Configuration if registered, None otherwise.
        """
        return self._configs.get(provider_name)

    def clear(self) -> None:
        """Clear all registered providers."""
        self._providers.clear()
        self._configs.clear()

    def __len__(self) -> int:
        """Get number of registered providers."""
        return len(self._providers)

    def __contains__(self, name: str) -> bool:
        """Check if provider is registered."""
        return name in self._providers
