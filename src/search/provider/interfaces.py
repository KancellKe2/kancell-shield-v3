"""Protocol interfaces for the Search Provider SDK.

This module contains Protocol and ABC interface definitions.
No implementation should be placed here.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Protocol, Sequence

from .models import (
    AuthMethod,
    PaginationState,
    PaginationType,
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


class Provider(Protocol):
    """Main protocol for search provider implementations.

    Providers implement this protocol to integrate with the SDK
    and Search Engine.
    """

    @property
    def info(self) -> ProviderInfo:
        """Get provider information."""
        ...

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        ...

    @property
    def version(self) -> ProviderVersion:
        """Get provider version."""
        ...

    async def search(
        self,
        request: ProviderRequest,
        config: ProviderConfiguration,
    ) -> ProviderResponse:
        """Execute a search request.

        Args:
            request: The search request.
            config: Provider configuration.

        Returns:
            ProviderResponse with search results.

        Raises:
            ProviderError: If search fails.
        """
        ...

    async def authenticate(
        self,
        credentials: ProviderAuthentication,
    ) -> ProviderAuthentication:
        """Authenticate with the provider.

        Args:
            credentials: Authentication credentials.

        Returns:
            Updated credentials with auth state.

        Raises:
            AuthenticationError: If authentication fails.
        """
        ...

    async def refresh_auth(
        self,
        credentials: ProviderAuthentication,
    ) -> ProviderAuthentication:
        """Refresh authentication token.

        Args:
            credentials: Current credentials.

        Returns:
            Updated credentials with new token.

        Raises:
            AuthenticationError: If refresh fails.
        """
        ...

    def get_rate_limit_info(self) -> RateLimitInfo:
        """Get current rate limit information.

        Returns:
            RateLimitInfo with current state.
        """
        ...

    def get_health_status(self) -> ProviderHealthStatus:
        """Get current health status.

        Returns:
            ProviderHealthStatus with current state.
        """
        ...

    def get_statistics(self) -> ProviderStatistics:
        """Get aggregated statistics.

        Returns:
            ProviderStatistics for this provider.
        """
        ...

    async def health_check(self) -> bool:
        """Perform a health check.

        Returns:
            True if provider is healthy.
        """
        ...

    def validate_config(self, config: ProviderConfiguration) -> bool:
        """Validate provider configuration.

        Args:
            config: Configuration to validate.

        Returns:
            True if configuration is valid.
        """
        ...

    def get_auth_headers(
        self,
        credentials: ProviderAuthentication,
    ) -> dict[str, str]:
        """Get authentication headers for requests.

        Args:
            credentials: Current credentials.

        Returns:
            Headers to attach to requests.
        """
        ...

    def supports_feature(self, feature: str) -> bool:
        """Check if a feature is supported.

        Args:
            feature: Feature name to check.

        Returns:
            True if feature is supported.
        """
        ...


class ProviderFactory(Protocol):
    """Protocol for creating provider instances."""

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
        ...

    def supports(self, provider_name: str) -> bool:
        """Check if this factory supports a provider.

        Args:
            provider_name: Name of provider to check.

        Returns:
            True if this factory creates the named provider.
        """
        ...

    def get_supported_providers(self) -> tuple[str, ...]:
        """Get names of providers this factory supports.

        Returns:
            Tuple of supported provider names.
        """
        ...


class ProviderRegistry(Protocol):
    """Protocol for managing provider registration and discovery."""

    def register(
        self,
        provider: Provider,
        config: ProviderConfiguration,
    ) -> None:
        """Register a provider.

        Args:
            provider: Provider instance to register.
            config: Provider configuration.
        """
        ...

    def unregister(self, provider_name: str) -> None:
        """Unregister a provider.

        Args:
            provider_name: Name of provider to remove.
        """
        ...

    def get(self, provider_name: str) -> Provider | None:
        """Get a registered provider.

        Args:
            provider_name: Name of provider to get.

        Returns:
            Provider if registered, None otherwise.
        """
        ...

    def list_providers(self) -> Sequence[str]:
        """List all registered provider names.

        Returns:
            Tuple of provider names.
        """
        ...

    def get_by_capability(self, capability: str) -> Sequence[Provider]:
        """Get providers supporting a capability.

        Args:
            capability: Capability name to filter by.

        Returns:
            Sequence of matching providers.
        """
        ...

    def get_healthy(self) -> Sequence[Provider]:
        """Get all healthy providers.

        Returns:
            Sequence of healthy providers.
        """
        ...


class ProviderAuthenticator(Protocol):
    """Protocol for handling provider authentication."""

    async def authenticate(
        self,
        provider: Provider,
        credentials: ProviderAuthentication,
    ) -> ProviderAuthentication:
        """Authenticate with a provider.

        Args:
            provider: Provider to authenticate with.
            credentials: Credentials to use.

        Returns:
            Updated credentials with auth state.

        Raises:
            AuthenticationError: If authentication fails.
        """
        ...

    async def refresh(
        self,
        provider: Provider,
        credentials: ProviderAuthentication,
    ) -> ProviderAuthentication:
        """Refresh authentication.

        Args:
            provider: Provider to refresh auth for.
            credentials: Current credentials.

        Returns:
            Updated credentials with new token.

        Raises:
            AuthenticationError: If refresh fails.
        """
        ...

    def is_authenticated(
        self,
        credentials: ProviderAuthentication,
    ) -> bool:
        """Check if credentials are authenticated.

        Args:
            credentials: Credentials to check.

        Returns:
            True if authenticated and not expired.
        """
        ...

    def get_auth_headers(
        self,
        method: AuthMethod,
        credentials: ProviderAuthentication,
    ) -> dict[str, str]:
        """Get authentication headers.

        Args:
            method: Authentication method.
            credentials: Credentials to use.

        Returns:
            Headers for authentication.
        """
        ...


class ProviderHealthChecker(Protocol):
    """Protocol for checking provider health."""

    async def check(self, provider: Provider) -> ProviderHealthStatus:
        """Check provider health.

        Args:
            provider: Provider to check.

        Returns:
            Updated health status.
        """
        ...

    async def check_all(
        self,
        providers: Sequence[Provider],
    ) -> dict[str, ProviderHealthStatus]:
        """Check health of multiple providers.

        Args:
            providers: Providers to check.

        Returns:
            Map of provider name to health status.
        """
        ...

    def is_healthy(
        self,
        status: ProviderHealthStatus,
    ) -> bool:
        """Check if health status indicates healthy.

        Args:
            status: Health status to check.

        Returns:
            True if provider is healthy.
        """
        ...

    def should_retry(
        self,
        status: ProviderHealthStatus,
    ) -> bool:
        """Check if provider should be retried.

        Args:
            status: Health status to check.

        Returns:
            True if retry should be attempted.
        """
        ...


class ProviderCapabilityResolver(Protocol):
    """Protocol for resolving provider capabilities."""

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
        ...

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
        ...

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
        ...


class ProviderRateLimiter(Protocol):
    """Protocol for provider-specific rate limiting."""

    async def acquire(
        self,
        provider_name: str,
        tokens: int = 1,
    ) -> bool:
        """Acquire rate limit tokens.

        Args:
            provider_name: Provider to acquire tokens for.
            tokens: Number of tokens to acquire.

        Returns:
            True if tokens acquired.
        """
        ...

    def release(
        self,
        provider_name: str,
        tokens: int = 1,
    ) -> None:
        """Release rate limit tokens.

        Args:
            provider_name: Provider to release tokens for.
            tokens: Number of tokens to release.
        """
        ...

    def get_wait_time(self, provider_name: str) -> float:
        """Get wait time before next request.

        Args:
            provider_name: Provider to check.

        Returns:
            Seconds to wait.
        """
        ...

    def get_info(self, provider_name: str) -> RateLimitInfo:
        """Get rate limit information.

        Args:
            provider_name: Provider to check.

        Returns:
            Current rate limit info.
        """
        ...

    def is_limited(self, provider_name: str) -> bool:
        """Check if provider is rate limited.

        Args:
            provider_name: Provider to check.

        Returns:
            True if rate limited.
        """
        ...


class ProviderPaginator(Protocol):
    """Protocol for handling pagination."""

    def create_initial_state(
        self,
        pagination_type: "PaginationType",
        page_size: int,
    ) -> PaginationState:
        """Create initial pagination state.

        Args:
            pagination_type: Type of pagination.
            page_size: Page size to use.

        Returns:
            Initial pagination state.
        """
        ...

    def get_next_state(
        self,
        current: PaginationState,
        response: ProviderResponse,
    ) -> PaginationState:
        """Calculate next pagination state.

        Args:
            current: Current pagination state.
            response: Response with results.

        Returns:
            Next pagination state.
        """
        ...

    def has_more(
        self,
        state: PaginationState,
        response: ProviderResponse,
    ) -> bool:
        """Check if more pages are available.

        Args:
            state: Current pagination state.
            response: Response with results.

        Returns:
            True if more pages available.
        """
        ...

    def create_request(
        self,
        base_request: ProviderRequest,
        pagination: PaginationState,
    ) -> ProviderRequest:
        """Create paginated request.

        Args:
            base_request: Base request to paginate.
            pagination: Pagination state to use.

        Returns:
            Request with pagination parameters.
        """
        ...


class ProviderErrorHandler(Protocol):
    """Protocol for handling provider errors."""

    def handle(
        self,
        error: Exception,
        provider: Provider,
    ) -> "ProviderAction":
        """Handle a provider error.

        Args:
            error: Error that occurred.
            provider: Provider that errored.

        Returns:
            Action to take.
        """
        ...

    def should_retry(
        self,
        error: Exception,
        attempt: int,
    ) -> bool:
        """Check if error should be retried.

        Args:
            error: Error to check.
            attempt: Current attempt number.

        Returns:
            True if should retry.
        """
        ...

    def get_backoff_delay(
        self,
        attempt: int,
        error: Exception,
    ) -> float:
        """Get backoff delay for retry.

        Args:
            attempt: Current attempt number.
            error: Error that occurred.

        Returns:
            Delay in seconds.
        """
        ...


class ProviderAction(Enum):
    """Actions to take for provider errors."""

    RETRY = auto()
    RETRY_WITH_BACKOFF = auto()
    SWITCH_PROVIDER = auto()
    FAIL = auto()
    AUTHENTICATE = auto()
    WAIT = auto()
