"""Provider context for managing runtime state.

This module provides the ProviderContext class that holds
runtime state for provider operations.
"""

from dataclasses import dataclass, field
from typing import Any

from .models import (
    AuthMethod,
    ProviderAuthentication,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderFeatureFlags,
    ProviderHealthStatus,
    ProviderInfo,
    ProviderRequest,
    ProviderStatistics,
    ProviderVersion,
    RateLimitInfo,
)


@dataclass
class ProviderContext:
    """Context holding runtime state for provider operations.

    This class provides dependency injection for provider components
    and maintains state across operations.
    """

    provider_info: ProviderInfo
    configuration: ProviderConfiguration
    capabilities: ProviderCapabilities
    version: ProviderVersion
    health_status: ProviderHealthStatus | None = None
    authentication: ProviderAuthentication | None = None
    feature_flags: ProviderFeatureFlags | None = None
    rate_limit_info: RateLimitInfo | None = None
    statistics: ProviderStatistics | None = None
    custom_state: dict[str, Any] = field(default_factory=dict)

    def get_auth_method(self) -> AuthMethod:
        """Get the configured authentication method.

        Returns:
            AuthMethod from configuration or authentication state.
        """
        if self.authentication:
            return self.authentication.method
        return AuthMethod.NONE

    def is_authenticated(self) -> bool:
        """Check if provider is authenticated.

        Returns:
            True if authenticated and token is valid.
        """
        if not self.authentication:
            return False
        if self.authentication.method == AuthMethod.NONE:
            return True
        return self.authentication.is_authenticated and not self.authentication.is_token_expired()

    def requires_authentication(self) -> bool:
        """Check if provider requires authentication.

        Returns:
            True if authentication is required.
        """
        return self.capabilities.requires_authentication

    def supports_pagination(self) -> bool:
        """Check if provider supports pagination.

        Returns:
            True if pagination is supported.
        """
        return self.capabilities.supports_pagination is not None

    def supports_filtering(self) -> bool:
        """Check if provider supports result filtering.

        Returns:
            True if filtering is supported.
        """
        return self.capabilities.supports_filtering

    def get_max_page_size(self) -> int:
        """Get maximum page size for this provider.

        Returns:
            Maximum number of results per page.
        """
        return self.capabilities.max_page_size

    def get_default_page_size(self) -> int:
        """Get default page size for this provider.

        Returns:
            Default number of results per page.
        """
        return self.capabilities.default_page_size

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled.

        Args:
            feature_name: Name of the feature to check.

        Returns:
            True if feature is enabled.
        """
        if not self.feature_flags:
            return True
        return self.feature_flags.is_enabled(feature_name)

    def update_health(self, status: ProviderHealthStatus) -> None:
        """Update the health status in context.

        Args:
            status: New health status.
        """
        self.health_status = status

    def update_authentication(self, auth: ProviderAuthentication) -> None:
        """Update authentication state in context.

        Args:
            auth: New authentication state.
        """
        self.authentication = auth

    def update_rate_limit(self, info: RateLimitInfo) -> None:
        """Update rate limit info in context.

        Args:
            info: New rate limit information.
        """
        self.rate_limit_info = info

    def update_statistics(self, stats: ProviderStatistics) -> None:
        """Update statistics in context.

        Args:
            stats: New statistics.
        """
        self.statistics = stats

    def set_custom_state(self, key: str, value: Any) -> None:
        """Set a custom state value.

        Args:
            key: State key.
            value: State value.
        """
        self.custom_state[key] = value

    def get_custom_state(self, key: str, default: Any = None) -> Any:
        """Get a custom state value.

        Args:
            key: State key.
            default: Default value if not found.

        Returns:
            State value or default.
        """
        return self.custom_state.get(key, default)

    def clear_custom_state(self) -> None:
        """Clear all custom state."""
        self.custom_state.clear()

    def create_request(
        self,
        query: str,
        language: str | None = None,
        region: str | None = None,
        page_size: int | None = None,
    ) -> ProviderRequest:
        """Create a provider request from context.

        Args:
            query: Search query string.
            language: Optional language code override.
            region: Optional region code override.
            page_size: Optional page size override.

        Returns:
            Configured ProviderRequest.
        """
        return ProviderRequest(
            query=query,
            language=language or self.configuration.default_language,
            region=region or self.configuration.default_region,
            safe_search=self.configuration.safe_search_default,
            custom_params={"page_size": str(page_size or self.get_default_page_size())},
        )

    def validate_request(self, request: ProviderRequest) -> tuple[bool, list[str]]:
        """Validate a request against provider capabilities.

        Args:
            request: Request to validate.

        Returns:
            Tuple of (is_valid, list of error messages).
        """
        errors: list[str] = []

        if not request.query:
            errors.append("Query cannot be empty")

        if self.capabilities.supports_language_filter and request.language:
            if len(request.language) != 2:
                errors.append("Language must be a 2-letter code")

        if self.capabilities.supports_region_filter and request.region:
            if len(request.region) != 2:
                errors.append("Region must be a 2-letter code")

        max_size = self.get_max_page_size()
        page_size = request.custom_params.get("page_size")
        if page_size:
            try:
                size = int(page_size)
                if size > max_size:
                    errors.append(f"Page size {size} exceeds maximum {max_size}")
                if size < self.capabilities.min_page_size:
                    errors.append(f"Page size {size} below minimum {self.capabilities.min_page_size}")
            except ValueError:
                errors.append("Page size must be a number")

        return len(errors) == 0, errors

    def with_feature_flags(self, flags: ProviderFeatureFlags) -> "ProviderContext":
        """Create a copy with updated feature flags.

        Args:
            flags: New feature flags.

        Returns:
            New context with updated flags.
        """
        return ProviderContext(
            provider_info=self.provider_info,
            configuration=self.configuration,
            capabilities=self.capabilities,
            version=self.version,
            health_status=self.health_status,
            authentication=self.authentication,
            feature_flags=flags,
            rate_limit_info=self.rate_limit_info,
            statistics=self.statistics,
            custom_state=self.custom_state.copy(),
        )

    def with_configuration(self, config: ProviderConfiguration) -> "ProviderContext":
        """Create a copy with updated configuration.

        Args:
            config: New configuration.

        Returns:
            New context with updated config.
        """
        return ProviderContext(
            provider_info=self.provider_info,
            configuration=config,
            capabilities=self.capabilities,
            version=self.version,
            health_status=self.health_status,
            authentication=self.authentication,
            feature_flags=self.feature_flags,
            rate_limit_info=self.rate_limit_info,
            statistics=self.statistics,
            custom_state=self.custom_state.copy(),
        )
