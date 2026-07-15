"""Capability resolution implementation.

This module provides the CapabilityResolverImpl class that
resolves and validates provider capabilities.
"""

from dataclasses import dataclass

from .interfaces import Provider, ProviderCapabilityResolver
from .models import (
    AuthMethod,
    PaginationType,
    ProviderCapabilities,
    ProviderFeatureFlags,
    RateLimitType,
)


@dataclass
class CapabilityMatch:
    """Result of capability matching."""

    is_compatible: bool
    missing_capabilities: tuple[str, ...]
    supported_features: tuple[str, ...]
    unsupported_features: tuple[str, ...]


class CapabilityResolverImpl(ProviderCapabilityResolver):
    """Implementation of ProviderCapabilityResolver.

    This resolver validates and matches provider capabilities
    against requested features.
    """

    def __init__(self) -> None:
        """Initialize the resolver."""
        self._capability_registry: dict[str, ProviderCapabilities] = {}

    def register_capabilities(
        self,
        name: str,
        capabilities: ProviderCapabilities,
    ) -> None:
        """Register capabilities for a provider.

        Args:
            name: Provider name.
            capabilities: Capabilities to register.
        """
        self._capability_registry[name] = capabilities

    def resolve(
        self,
        provider: Provider,
        requested: ProviderFeatureFlags,
    ) -> ProviderFeatureFlags:
        """Resolve feature flags for a provider.

        Args:
            provider: Provider to resolve for.
            requested: Requested feature flags.

        Returns:
            Resolved feature flags.
        """
        capabilities = provider.capabilities

        enabled_flags: dict[str, bool] = {}

        if requested.enable_autocomplete and capabilities.supports_autocomplete:
            enabled_flags["enable_autocomplete"] = True

        if requested.enable_suggestions and capabilities.supports_suggestions:
            enabled_flags["enable_suggestions"] = True

        if requested.enable_related_searches and capabilities.supports_related_searches:
            enabled_flags["enable_related_searches"] = True

        enabled_flags["enable_safe_search"] = (
            requested.enable_safe_search and capabilities.supports_safe_search
        )

        enabled_flags["enable_location"] = requested.enable_location

        enabled_flags["enable_filters"] = (
            requested.enable_filters and capabilities.supports_filtering
        )

        enabled_flags["enable_caching"] = requested.enable_caching

        all_flags = ProviderFeatureFlags(
            enable_autocomplete=enabled_flags.get("enable_autocomplete", False),
            enable_suggestions=enabled_flags.get("enable_suggestions", False),
            enable_related_searches=enabled_flags.get("enable_related_searches", False),
            enable_safe_search=enabled_flags.get("enable_safe_search", True),
            enable_location=enabled_flags.get("enable_location", False),
            enable_filters=enabled_flags.get("enable_filters", True),
            enable_caching=enabled_flags.get("enable_caching", False),
            custom_flags={**requested.custom_flags, **enabled_flags},
        )

        return all_flags

    def validate(
        self,
        provider: Provider,
        requested: ProviderFeatureFlags,
    ) -> tuple[bool, list[str]]:
        """Validate requested features.

        Args:
            provider: Provider to validate against.
            requested: Requested features.

        Returns:
            Tuple of (is_valid, unsupported_features).
        """
        capabilities = provider.capabilities
        unsupported: list[str] = []

        if requested.enable_autocomplete and not capabilities.supports_autocomplete:
            unsupported.append("autocomplete")

        if requested.enable_suggestions and not capabilities.supports_suggestions:
            unsupported.append("suggestions")

        if requested.enable_related_searches and not capabilities.supports_related_searches:
            unsupported.append("related_searches")

        if requested.enable_safe_search and not capabilities.supports_safe_search:
            unsupported.append("safe_search")

        if requested.enable_filters and not capabilities.supports_filtering:
            unsupported.append("filters")

        if requested.enable_location and not capabilities.supports_filtering:
            unsupported.append("location")

        return len(unsupported) == 0, unsupported

    def get_required_capabilities(
        self,
        features: ProviderFeatureFlags,
    ) -> ProviderCapabilities:
        """Get required capabilities for features.

        Args:
            features: Features to check.

        Returns:
            Minimum required capabilities.
        """
        return ProviderCapabilities(
            supports_search=True,
            supports_pagination=PaginationType.OFFSET,
            supports_filtering=features.enable_filters,
            supports_language_filter=True,
            supports_region_filter=True,
            supports_safe_search=features.enable_safe_search,
            max_results_per_page=100,
            max_page_size=100,
            min_page_size=1,
            default_page_size=20,
            supports_autocomplete=features.enable_autocomplete,
            supports_suggestions=features.enable_suggestions,
            supports_related_searches=features.enable_related_searches,
            supported_auth_methods=(AuthMethod.API_KEY,),
            requires_authentication=True,
        )

    def match_capabilities(
        self,
        required: ProviderCapabilities,
        provided: ProviderCapabilities,
    ) -> CapabilityMatch:
        """Match required capabilities against provided.

        Args:
            required: Required capabilities.
            provided: Provided capabilities.

        Returns:
            CapabilityMatch with match details.
        """
        missing: list[str] = []
        supported: list[str] = []
        unsupported: list[str] = []

        if required.supports_search and not provided.supports_search:
            missing.append("search")

        if required.supports_pagination and not provided.supports_pagination:
            missing.append("pagination")
        elif required.supports_pagination and provided.supports_pagination:
            if required.supports_pagination != provided.supports_pagination:
                missing.append(
                    f"pagination_type:{required.supports_pagination.name}"
                )

        if required.supports_filtering and not provided.supports_filtering:
            missing.append("filtering")

        if required.supports_language_filter and not provided.supports_language_filter:
            missing.append("language_filter")

        if required.supports_region_filter and not provided.supports_region_filter:
            missing.append("region_filter")

        if required.supports_safe_search and not provided.supports_safe_search:
            missing.append("safe_search")

        if required.max_results_per_page > provided.max_results_per_page:
            missing.append(
                f"max_results_per_page:{required.max_results_per_page}"
            )

        if required.max_page_size > provided.max_page_size:
            missing.append(f"max_page_size:{required.max_page_size}")

        if required.supports_autocomplete and not provided.supports_autocomplete:
            missing.append("autocomplete")

        if required.supports_suggestions and not provided.supports_suggestions:
            missing.append("suggestions")

        for auth_method in required.supported_auth_methods:
            if auth_method not in provided.supported_auth_methods:
                missing.append(f"auth_method:{auth_method.name}")
            else:
                supported.append(f"auth_method:{auth_method.name}")

        for cap_name, value in required.custom_capabilities.items():
            if cap_name in provided.custom_capabilities:
                if provided.custom_capabilities[cap_name] == value:
                    supported.append(f"custom:{cap_name}")
                else:
                    unsupported.append(f"custom:{cap_name}")
            else:
                missing.append(f"custom:{cap_name}")

        return CapabilityMatch(
            is_compatible=len(missing) == 0,
            missing_capabilities=tuple(missing),
            supported_features=tuple(supported),
            unsupported_features=tuple(unsupported),
        )

    def get_compatible_providers(
        self,
        providers: tuple[Provider, ...],
        required: ProviderCapabilities,
    ) -> tuple[Provider, ...]:
        """Get providers compatible with required capabilities.

        Args:
            providers: Providers to check.
            required: Required capabilities.

        Returns:
            Tuple of compatible providers.
        """
        compatible: list[Provider] = []
        for provider in providers:
            match = self.match_capabilities(required, provider.capabilities)
            if match.is_compatible:
                compatible.append(provider)
        return tuple(compatible)


class StrictCapabilityResolver(CapabilityResolverImpl):
    """Strict resolver that requires all capabilities.

    This resolver is more strict about capability matching
    and will reject providers that don't fully support
    all requested features.
    """

    def validate(
        self,
        provider: Provider,
        requested: ProviderFeatureFlags,
    ) -> tuple[bool, list[str]]:
        """Validate with strict checking.

        Args:
            provider: Provider to validate.
            requested: Requested features.

        Returns:
            Tuple of (is_valid, unsupported_features).
        """
        is_valid, unsupported = super().validate(provider, requested)

        capabilities = provider.capabilities

        if requested.enable_autocomplete and not capabilities.supports_autocomplete:
            unsupported.append("autocomplete:required")

        if requested.enable_suggestions and not capabilities.supports_suggestions:
            unsupported.append("suggestions:required")

        if requested.enable_related_searches and not capabilities.supports_related_searches:
            unsupported.append("related_searches:required")

        return len(unsupported) == 0, unsupported


class LenientCapabilityResolver(CapabilityResolverImpl):
    """Lenient resolver that allows partial capabilities.

    This resolver is more lenient about capability matching
    and will accept providers that support at least the
    core required features.
    """

    CORE_FEATURES = frozenset(["search", "pagination", "filtering"])

    def validate(
        self,
        provider: Provider,
        requested: ProviderFeatureFlags,
    ) -> tuple[bool, list[str]]:
        """Validate with lenient checking.

        Args:
            provider: Provider to validate.
            requested: Requested features.

        Returns:
            Tuple of (is_valid, unsupported_features).
        """
        capabilities = provider.capabilities
        unsupported: list[str] = []

        if not capabilities.supports_search:
            unsupported.append("search")

        if not capabilities.supports_pagination:
            unsupported.append("pagination")

        if requested.enable_safe_search and not capabilities.supports_safe_search:
            unsupported.append("safe_search")

        return len(unsupported) == 0, unsupported
