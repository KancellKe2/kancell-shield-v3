"""Provider adapter for integrating search providers with discovery.

This module provides adapters that translate between the search provider
SDK and the discovery engine interfaces.
"""

from typing import Sequence

from .models import (
    DiscoveryCandidate,
    DiscoverySource,
    SourceType,
)
from .interfaces import DiscoveryCollector

# Import search provider SDK models
from src.search.provider.models import (
    ProviderRequest,
    ProviderResponse,
    ProviderHealthStatus,
    ProviderCapabilities,
    ProviderFeatureFlags,
    HealthStatus,
)


class ProviderAdapter:
    """Adapter base class for search providers.

    Translates between search provider SDK types and
    discovery engine types.
    """

    def __init__(
        self,
        provider_name: str,
        provider_type: SourceType = SourceType.CUSTOM,
    ) -> None:
        """Initialize provider adapter.

        Args:
            provider_name: Name of the provider.
            provider_type: Type of discovery source.
        """
        self._provider_name = provider_name
        self._provider_type = provider_type

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return self._provider_name

    @property
    def provider_type(self) -> SourceType:
        """Get provider type."""
        return self._provider_type

    def to_discovery_source(self) -> DiscoverySource:
        """Convert to discovery source.

        Returns:
            DiscoverySource representation.
        """
        return DiscoverySource(
            name=self._provider_name,
            source_type=self._provider_type,
            description=f"Search provider: {self._provider_name}",
            priority=50,
        )

    def to_provider_request(
        self,
        domains: Sequence[str],
        **kwargs: object,
    ) -> ProviderRequest:
        """Convert domains to provider request.

        Args:
            domains: Domain strings.
            **kwargs: Additional request parameters.

        Returns:
            ProviderRequest for the search provider.
        """
        query = " ".join(domains)
        return ProviderRequest(
            query=query,
            custom_params=dict(kwargs) if kwargs else None,
        )

    def to_discovery_candidates(
        self,
        response: ProviderResponse,
    ) -> list[DiscoveryCandidate]:
        """Convert provider response to discovery candidates.

        Args:
            response: Provider response.

        Returns:
            List of discovery candidates.
        """
        from .models import Domain

        candidates = []
        for result in response.results:
            # Extract domain from result
            if isinstance(result, dict):
                url = result.get("url", "")
                domain_name = self._extract_domain(url)
            elif isinstance(result, str):
                domain_name = self._extract_domain(result)
            else:
                continue

            if domain_name:
                domain = Domain(name=domain_name)
                candidate = DiscoveryCandidate(
                    domain=domain,
                    source=self._provider_name,
                )
                candidates.append(candidate)

        return candidates

    def _extract_domain(self, url_or_domain: str) -> str | None:
        """Extract domain from URL or domain string.

        Args:
            url_or_domain: URL or domain string.

        Returns:
            Extracted domain or None.
        """
        if not url_or_domain:
            return None

        # Handle URL
        if "://" in url_or_domain:
            # Simple URL parsing
            parts = url_or_domain.split("/")
            if len(parts) >= 3:
                host = parts[2]
                # Remove port
                if ":" in host:
                    host = host.split(":")[0]
                return host.lower()

        # Already a domain
        return url_or_domain.lower()

    def check_health(
        self,
        health_status: ProviderHealthStatus | None,
    ) -> bool:
        """Check if provider is healthy based on health status.

        Args:
            health_status: Provider health status.

        Returns:
            True if provider is healthy.
        """
        if health_status is None:
            return False

        if health_status.status == HealthStatus.HEALTHY:
            return True
        if health_status.status == HealthStatus.DEGRADED:
            return health_status.is_available
        return False

    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities.

        Returns:
            Provider capabilities.
        """
        return ProviderCapabilities()


class MockSearchProviderAdapter(ProviderAdapter):
    """Adapter for mock search providers.

    Provides mock data for testing without network operations.
    """

    def __init__(
        self,
        provider_name: str = "mock",
        mock_domains: Sequence[str] | None = None,
    ) -> None:
        """Initialize mock adapter.

        Args:
            provider_name: Name of the mock provider.
            mock_domains: Domains to return in responses.
        """
        super().__init__(provider_name, SourceType.PASSIVE)
        self._mock_domains = list(mock_domains) if mock_domains else []

    def to_discovery_candidates(
        self,
        response: ProviderResponse,
    ) -> list[DiscoveryCandidate]:
        """Convert mock response to candidates.

        Args:
            response: Provider response.

        Returns:
            List of discovery candidates.
        """
        from .models import Domain

        candidates = []
        for domain_str in self._mock_domains:
            domain = Domain(name=domain_str)
            candidate = DiscoveryCandidate(
                domain=domain,
                source=self._provider_name,
            )
            candidates.append(candidate)

        return candidates

    def create_mock_response(
        self,
        domains: Sequence[str] | None = None,
    ) -> ProviderResponse:
        """Create a mock provider response.

        Args:
            domains: Optional domains to include.

        Returns:
            Mock provider response.
        """
        results = []
        for domain in (domains or self._mock_domains):
            results.append({"url": f"https://{domain}", "domain": domain})

        return ProviderResponse(
            results=tuple(results),
            total_count=len(results),
        )

    def set_mock_domains(self, domains: Sequence[str]) -> None:
        """Set mock domains for testing.

        Args:
            domains: Domains to return.
        """
        self._mock_domains = list(domains)

    def add_mock_domain(self, domain: str) -> None:
        """Add a mock domain.

        Args:
            domain: Domain to add.
        """
        if domain not in self._mock_domains:
            self._mock_domains.append(domain)


class ProviderCapabilityAdapter:
    """Adapter for provider capability matching.

    Matches discovery requirements against provider capabilities.
    """

    def __init__(self) -> None:
        """Initialize capability adapter."""
        self._feature_requirements: dict[str, bool] = {}

    def set_requirement(self, feature: str, required: bool = True) -> None:
        """Set a feature requirement.

        Args:
            feature: Feature name.
            required: Whether feature is required.
        """
        self._feature_requirements[feature] = required

    def clear_requirements(self) -> None:
        """Clear all requirements."""
        self._feature_requirements.clear()

    def get_requirements(self) -> dict[str, bool]:
        """Get current requirements.

        Returns:
            Feature requirements.
        """
        return self._feature_requirements.copy()

    def matches_capabilities(
        self,
        capabilities: ProviderCapabilities,
    ) -> tuple[bool, list[str]]:
        """Check if capabilities match requirements.

        Args:
            capabilities: Provider capabilities to check.

        Returns:
            Tuple of (matches, missing_features).
        """
        missing = []

        for feature, required in self._feature_requirements.items():
            if not required:
                continue

            has_feature = self._check_feature(capabilities, feature)
            if not has_feature:
                missing.append(feature)

        return (len(missing) == 0, missing)

    def _check_feature(
        self,
        capabilities: ProviderCapabilities,
        feature: str,
    ) -> bool:
        """Check if a specific feature is supported.

        Args:
            capabilities: Provider capabilities.
            feature: Feature name.

        Returns:
            True if feature is supported.
        """
        feature_checks = {
            "search": capabilities.supports_search,
            "autocomplete": capabilities.supports_autocomplete,
            "pagination": capabilities.supports_pagination,
            "filtering": capabilities.supports_filtering,
            "safe_search": capabilities.supports_safe_search,
        }

        return feature_checks.get(feature, False)


class ProviderHealthAdapter:
    """Adapter for provider health state management.

    Manages health state transitions and reporting.
    """

    def __init__(self) -> None:
        """Initialize health adapter."""
        self._health_states: dict[str, ProviderHealthStatus] = {}
        self._failure_counts: dict[str, int] = {}
        self._failure_threshold = 3

    def set_health_status(
        self,
        provider_name: str,
        status: ProviderHealthStatus,
    ) -> None:
        """Set health status for a provider.

        Args:
            provider_name: Name of the provider.
            status: Health status.
        """
        self._health_states[provider_name] = status

    def get_health_status(
        self,
        provider_name: str,
    ) -> ProviderHealthStatus | None:
        """Get health status for a provider.

        Args:
            provider_name: Name of the provider.

        Returns:
            Health status or None.
        """
        return self._health_states.get(provider_name)

    def record_success(self, provider_name: str) -> None:
        """Record successful operation.

        Args:
            provider_name: Name of the provider.
        """
        self._failure_counts[provider_name] = 0

    def record_failure(self, provider_name: str) -> None:
        """Record failed operation.

        Args:
            provider_name: Name of the provider.
        """
        count = self._failure_counts.get(provider_name, 0) + 1
        self._failure_counts[provider_name] = count

        # Update health state if threshold exceeded
        if count >= self._failure_threshold:
            self._health_states[provider_name] = ProviderHealthStatus(
                provider_name=provider_name,
                status=HealthStatus.UNHEALTHY,
                is_available=False,
                consecutive_failures=count,
            )

    def set_failure_threshold(self, threshold: int) -> None:
        """Set failure threshold.

        Args:
            threshold: Number of failures before marking unhealthy.
        """
        self._failure_threshold = threshold

    def is_available(self, provider_name: str) -> bool:
        """Check if provider is available.

        Args:
            provider_name: Name of the provider.

        Returns:
            True if provider is available.
        """
        status = self._health_states.get(provider_name)
        if status is None:
            return True  # Unknown status means available

        return status.is_available

    def get_unavailable_providers(self) -> list[str]:
        """Get list of unavailable providers.

        Returns:
            List of provider names.
        """
        return [
            name
            for name, status in self._health_states.items()
            if not status.is_available
        ]

    def reset_provider(self, provider_name: str) -> None:
        """Reset provider health state.

        Args:
            provider_name: Name of the provider.
        """
        if provider_name in self._health_states:
            del self._health_states[provider_name]
        if provider_name in self._failure_counts:
            del self._failure_counts[provider_name]

    def reset_all(self) -> None:
        """Reset all provider health states."""
        self._health_states.clear()
        self._failure_counts.clear()
