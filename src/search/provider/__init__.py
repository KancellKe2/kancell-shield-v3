"""Search Provider SDK for Kancell Shield v3.

This module provides the SDK for implementing search providers
that integrate with the Search Engine.
"""

from .models import (
    AuthMethod,
    ErrorSeverity,
    HealthStatus,
    LimitScope,
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
    RateLimitType,
)

from .interfaces import (
    Provider,
    ProviderAction,
    ProviderAuthenticator,
    ProviderCapabilityResolver,
    ProviderErrorHandler,
    ProviderFactory,
    ProviderHealthChecker,
    ProviderPaginator,
    ProviderRateLimiter,
    ProviderRegistry,
)

__all__ = [
    # Enums
    "AuthMethod",
    "ErrorSeverity",
    "HealthStatus",
    "LimitScope",
    "PaginationType",
    "RateLimitType",
    # Models
    "PaginationState",
    "ProviderAuthentication",
    "ProviderCapabilities",
    "ProviderConfiguration",
    "ProviderFeatureFlags",
    "ProviderHealthStatus",
    "ProviderInfo",
    "ProviderRequest",
    "ProviderResponse",
    "ProviderStatistics",
    "ProviderVersion",
    "RateLimitInfo",
    # Interfaces
    "Provider",
    "ProviderAction",
    "ProviderAuthenticator",
    "ProviderCapabilityResolver",
    "ProviderErrorHandler",
    "ProviderFactory",
    "ProviderHealthChecker",
    "ProviderPaginator",
    "ProviderRateLimiter",
    "ProviderRegistry",
]
