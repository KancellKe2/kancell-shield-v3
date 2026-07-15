"""Data models for the Search Provider SDK.

This module contains immutable dataclasses and enums defining
the SDK contracts for provider implementations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import FrozenSet


class AuthMethod(Enum):
    """Supported authentication methods."""

    API_KEY = auto()
    OAUTH2 = auto()
    BASIC = auto()
    BEARER = auto()
    CUSTOM = auto()
    NONE = auto()


class PaginationType(Enum):
    """Types of pagination supported by providers."""

    OFFSET = auto()
    CURSOR = auto()
    PAGE = auto()


class RateLimitType(Enum):
    """Types of rate limiting supported."""

    TOKEN_BUCKET = auto()
    SLIDING_WINDOW = auto()
    FIXED_WINDOW = auto()
    NONE = auto()


class LimitScope(Enum):
    """Scope of rate limits."""

    GLOBAL = auto()
    PER_USER = auto()
    PER_IP = auto()
    PER_KEY = auto()


class HealthStatus(Enum):
    """Health status levels for providers."""

    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    UNKNOWN = auto()


class ErrorSeverity(Enum):
    """Severity levels for provider errors."""

    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass(frozen=True)
class ProviderVersion:
    """Version information for a provider."""

    major: int
    minor: int
    patch: int
    api_version: str
    deprecated_features: tuple[str, ...] = field(default_factory=tuple)
    experimental_features: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate version numbers."""
        if self.major < 0:
            raise ValueError("major version cannot be negative")
        if self.minor < 0:
            raise ValueError("minor version cannot be negative")
        if self.patch < 0:
            raise ValueError("patch version cannot be negative")

    def is_compatible_with(self, other: "ProviderVersion") -> bool:
        """Check if versions are compatible.

        Args:
            other: Version to compare against.

        Returns:
            True if versions are compatible.
        """
        return self.api_version == other.api_version

    def __str__(self) -> str:
        """String representation of version."""
        return f"{self.major}.{self.minor}.{self.patch} (API {self.api_version})"


@dataclass(frozen=True)
class ProviderInfo:
    """Metadata about a search provider."""

    name: str
    display_name: str
    version: ProviderVersion
    description: str
    homepage_url: str | None = None
    support_url: str | None = None
    documentation_url: str | None = None
    license: str = "MIT"
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate provider info."""
        if not self.name:
            raise ValueError("Provider name cannot be empty")
        if not self.display_name:
            raise ValueError("Display name cannot be empty")


@dataclass(frozen=True)
class ProviderCapabilities:
    """Capabilities supported by a provider."""

    supports_search: bool = True
    supports_pagination: PaginationType | None = PaginationType.OFFSET
    supports_filtering: bool = False
    supports_language_filter: bool = False
    supports_region_filter: bool = False
    supports_date_filter: bool = False
    supports_safe_search: bool = True
    max_results_per_page: int = 100
    max_page_size: int = 100
    min_page_size: int = 1
    default_page_size: int = 20
    supports_autocomplete: bool = False
    supports_suggestions: bool = False
    supports_related_searches: bool = False
    supported_auth_methods: tuple[AuthMethod, ...] = (AuthMethod.API_KEY,)
    supported_rate_limit_types: tuple[RateLimitType, ...] = (RateLimitType.TOKEN_BUCKET,)
    requires_authentication: bool = True
    supports_batch_search: bool = False
    custom_capabilities: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderFeatureFlags:
    """Feature flags for provider behavior control."""

    enable_autocomplete: bool = False
    enable_suggestions: bool = False
    enable_related_searches: bool = False
    enable_safe_search: bool = True
    enable_location: bool = False
    enable_filters: bool = True
    enable_deduplication: bool = True
    enable_caching: bool = False
    custom_flags: dict[str, bool] = field(default_factory=dict)

    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled.

        Args:
            flag_name: Name of the flag to check.

        Returns:
            True if enabled or not defined (defaults to True).
        """
        if flag_name in self.custom_flags:
            return self.custom_flags[flag_name]
        return True

    def get_flag(self, flag_name: str, default: bool = True) -> bool:
        """Get a feature flag value.

        Args:
            flag_name: Name of the flag.
            default: Default value if not found.

        Returns:
            Flag value or default.
        """
        return self.custom_flags.get(flag_name, default)


@dataclass(frozen=True)
class ProviderAuthentication:
    """Authentication credentials and state for a provider."""

    method: AuthMethod
    credentials: dict[str, str] = field(default_factory=dict)
    token: str | None = None
    token_expires_at: datetime | None = None
    refresh_token: str | None = None
    is_authenticated: bool = False
    last_auth_attempt: datetime | None = None
    auth_errors: int = 0

    def __post_init__(self) -> None:
        """Validate authentication state."""
        if self.method == AuthMethod.NONE and (self.token or self.credentials):
            raise ValueError("NONE auth cannot have credentials")

    def is_token_expired(self) -> bool:
        """Check if authentication token is expired.

        Returns:
            True if token is expired or not set.
        """
        if not self.token or not self.token_expires_at:
            return True
        return datetime.now(timezone.utc) >= self.token_expires_at

    def needs_refresh(self) -> bool:
        """Check if token needs refresh.

        Returns:
            True if refresh is needed.
        """
        if not self.refresh_token:
            return False
        return self.is_token_expired()

    def get_header_value(self) -> str | None:
        """Get authentication header value.

        Returns:
            Header value for Authorization header or None.
        """
        if self.method == AuthMethod.API_KEY:
            return self.credentials.get("X-API-Key") or self.token
        elif self.method == AuthMethod.BEARER:
            return f"Bearer {self.token}"
        elif self.method == AuthMethod.BASIC:
            return self.token
        return None


@dataclass(frozen=True)
class ProviderConfiguration:
    """Runtime configuration for a provider."""

    provider_name: str
    base_url: str
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    max_page_size: int = 100
    default_language: str = "en"
    default_region: str = "US"
    safe_search_default: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10
    custom_settings: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.provider_name:
            raise ValueError("Provider name cannot be empty")
        if not self.base_url:
            raise ValueError("Base URL cannot be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")

    def get_timeout_for_operation(self, operation: str) -> float:
        """Get operation-specific timeout.

        Args:
            operation: Operation name.

        Returns:
            Timeout in seconds.
        """
        return float(self.custom_settings.get(
            f"timeout_{operation}",
            str(self.timeout_seconds)
        ))


@dataclass(frozen=True)
class ProviderHealthStatus:
    """Health status and metrics for a provider."""

    provider_name: str
    status: HealthStatus
    is_available: bool = True
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_success: datetime | None = None
    last_failure: datetime | None = None
    avg_response_time_ms: float = 0.0
    success_rate: float = 1.0
    error_counts: dict[str, int] = field(default_factory=dict)
    health_check_failures: int = 0

    def __post_init__(self) -> None:
        """Validate health status."""
        if self.success_rate < 0.0 or self.success_rate > 1.0:
            raise ValueError("Success rate must be between 0.0 and 1.0")

    def is_healthy_enough(self, threshold: float = 0.5) -> bool:
        """Check if provider is healthy enough for use.

        Args:
            threshold: Minimum success rate threshold.

        Returns:
            True if healthy enough.
        """
        return (
            self.status == HealthStatus.HEALTHY
            and self.success_rate >= threshold
            and self.consecutive_failures < 3
        )


@dataclass(frozen=True)
class PaginationState:
    """Pagination state for a search operation."""

    pagination_type: PaginationType
    offset: int = 0
    cursor: str | None = None
    page: int = 1
    page_size: int = 20
    total_results: int | None = None
    has_more: bool = True
    next_page_token: str | None = None

    def __post_init__(self) -> None:
        """Validate pagination state."""
        if self.offset < 0:
            raise ValueError("Offset cannot be negative")
        if self.page < 1:
            raise ValueError("Page must be at least 1")
        if self.page_size < 1:
            raise ValueError("Page size must be at least 1")

    def next_offset(self, count: int) -> "PaginationState":
        """Create state for next offset page.

        Args:
            count: Number of results in current page.

        Returns:
            New pagination state.
        """
        return PaginationState(
            pagination_type=self.pagination_type,
            offset=self.offset + count,
            cursor=self.cursor,
            page=self.page,
            page_size=self.page_size,
            total_results=self.total_results,
            has_more=self.has_more,
            next_page_token=self.next_page_token,
        )

    def next_page(self) -> "PaginationState":
        """Create state for next page.

        Returns:
            New pagination state.
        """
        return PaginationState(
            pagination_type=self.pagination_type,
            offset=self.offset,
            cursor=self.cursor,
            page=self.page + 1,
            page_size=self.page_size,
            total_results=self.total_results,
            has_more=self.has_more,
            next_page_token=self.next_page_token,
        )


@dataclass(frozen=True)
class ProviderRequest:
    """A search request to a provider."""

    query: str
    pagination: PaginationState | None = None
    language: str | None = None
    region: str | None = None
    safe_search: bool = True
    date_range: tuple[datetime, datetime] | None = None
    custom_params: dict[str, str] = field(default_factory=dict)
    request_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate request."""
        if not self.query:
            raise ValueError("Query cannot be empty")


@dataclass(frozen=True)
class ProviderResponse:
    """A search response from a provider."""

    results: tuple[dict[str, object], ...]
    total_count: int
    pagination: PaginationState | None = None
    response_time_ms: float = 0.0
    provider_name: str = ""
    request: ProviderRequest | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate response."""
        if self.total_count < 0:
            raise ValueError("Total count cannot be negative")
        if self.response_time_ms < 0:
            raise ValueError("Response time cannot be negative")


@dataclass(frozen=True)
class RateLimitInfo:
    """Rate limiting information for a provider."""

    requests_remaining: int
    requests_limit: int
    reset_at: datetime
    backoff_until: datetime | None = None
    limit_type: RateLimitType = RateLimitType.TOKEN_BUCKET
    scope: LimitScope = LimitScope.GLOBAL
    retry_after_seconds: float | None = None

    def is_limited(self) -> bool:
        """Check if currently rate limited.

        Returns:
            True if rate limited.
        """
        if self.backoff_until and datetime.now(timezone.utc) < self.backoff_until:
            return True
        return self.requests_remaining <= 0

    def get_wait_time(self) -> float:
        """Get estimated wait time in seconds.

        Returns:
            Seconds to wait before next request.
        """
        if self.retry_after_seconds:
            return self.retry_after_seconds
        if self.backoff_until:
            delta = self.backoff_until - datetime.now(timezone.utc)
            return max(0.0, delta.total_seconds())
        return 0.0


@dataclass(frozen=True)
class ProviderStatistics:
    """Aggregated statistics for a provider."""

    provider_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_results: int = 0
    avg_response_time_ms: float = 0.0
    total_errors: int = 0
    rate_limit_hits: int = 0
    timeout_hits: int = 0
    auth_failures: int = 0
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def success_rate(self) -> float:
        """Calculate success rate.

        Returns:
            Success rate as a fraction.
        """
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def error_rate(self) -> float:
        """Calculate error rate.

        Returns:
            Error rate as a fraction.
        """
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def add_request(self, success: bool, response_time_ms: float, results_count: int) -> None:
        """Note: This is for documentation only - dataclass is immutable."""
        pass  # In actual implementation, use mutable version or return new instance
