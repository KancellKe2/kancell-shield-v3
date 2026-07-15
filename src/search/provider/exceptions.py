"""Exception classes for the Search Provider SDK.

This module defines a hierarchy of exceptions for provider operations.
All exceptions inherit from ProviderError.
"""

from dataclasses import dataclass


class ProviderError(Exception):
    """Base exception for all provider errors.

    This is the root exception class for the provider SDK.
    All other provider-related exceptions should inherit from this.
    """

    def __init__(self, message: str, provider_name: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            provider_name: Optional provider name that caused the error.
        """
        super().__init__(message)
        self.message = message
        self.provider_name = provider_name


class ConfigurationError(ProviderError):
    """Raised when provider configuration is invalid.

    This includes missing required fields, invalid values,
    or incompatible configuration options.
    """


class AuthenticationError(ProviderError):
    """Base exception for authentication failures.

    This covers all authentication-related errors including
    invalid credentials, expired tokens, and auth service issues.
    """


class InvalidCredentialsError(AuthenticationError):
    """Raised when provided credentials are invalid.

    This occurs when API keys, tokens, or other credentials
    are malformed or do not match the expected format.
    """


class ExpiredTokenError(AuthenticationError):
    """Raised when authentication token has expired.

    This occurs when using OAuth tokens or API keys that
    have exceeded their validity period.
    """


class OAuthError(AuthenticationError):
    """Raised when OAuth authentication fails.

    This covers OAuth flow errors including invalid state,
    authorization failures, and token exchange issues.
    """

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        oauth_error: str | None = None,
    ) -> None:
        """Initialize the OAuth error.

        Args:
            message: Error message.
            provider_name: Optional provider name.
            oauth_error: Specific OAuth error code.
        """
        super().__init__(message, provider_name)
        self.oauth_error = oauth_error


class RateLimitError(ProviderError):
    """Base exception for rate limiting errors.

    This covers rate limit violations and backoff requirements.
    """


class QuotaExceededError(RateLimitError):
    """Raised when provider quota is exceeded.

    This occurs when the allocated quota for API calls,
    results, or other resources has been exhausted.
    """

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        quota_type: str | None = None,
        reset_at: str | None = None,
    ) -> None:
        """Initialize the quota error.

        Args:
            message: Error message.
            provider_name: Optional provider name.
            quota_type: Type of quota exceeded.
            reset_at: When the quota resets.
        """
        super().__init__(message, provider_name)
        self.quota_type = quota_type
        self.reset_at = reset_at


class BackoffRequiredError(RateLimitError):
    """Raised when backoff is required before retry.

    This indicates that the provider requires a waiting period
    before accepting new requests.
    """

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        backoff_seconds: float | None = None,
    ) -> None:
        """Initialize the backoff error.

        Args:
            message: Error message.
            provider_name: Optional provider name.
            backoff_seconds: Required wait time in seconds.
        """
        super().__init__(message, provider_name)
        self.backoff_seconds = backoff_seconds


class RequestError(ProviderError):
    """Base exception for request-related errors.

    This covers validation, timeout, and network issues.
    """


class ValidationError(RequestError):
    """Raised when request validation fails.

    This occurs when query parameters, pagination settings,
    or other request components are invalid.
    """


class TimeoutError(RequestError):
    """Raised when a request times out.

    This occurs when the provider does not respond within
    the configured timeout period.
    """

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        """Initialize the timeout error.

        Args:
            message: Error message.
            provider_name: Optional provider name.
            timeout_seconds: Configured timeout value.
        """
        super().__init__(message, provider_name)
        self.timeout_seconds = timeout_seconds


class NetworkError(RequestError):
    """Raised when a network error occurs.

    This covers DNS failures, connection refused, and
    other network-level issues.
    """


class ResponseError(ProviderError):
    """Base exception for response-related errors.

    This covers parsing, quota, and server errors.
    """


class ParseError(ResponseError):
    """Raised when response parsing fails.

    This occurs when the provider returns data in an
    unexpected or malformed format.
    """

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        response_format: str | None = None,
    ) -> None:
        """Initialize the parse error.

        Args:
            message: Error message.
            provider_name: Optional provider name.
            response_format: Expected format that failed to parse.
        """
        super().__init__(message, provider_name)
        self.response_format = response_format


class QuotaError(ResponseError):
    """Raised when quota-related response is received.

    This indicates the provider has rejected the request
    due to quota constraints.
    """


class ServerError(ResponseError):
    """Raised when provider server returns an error.

    This covers 5xx HTTP status codes and internal errors.
    """

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        status_code: int | None = None,
    ) -> None:
        """Initialize the server error.

        Args:
            message: Error message.
            provider_name: Optional provider name.
            status_code: HTTP status code if available.
        """
        super().__init__(message, provider_name)
        self.status_code = status_code


class ProviderNotFoundError(ProviderError):
    """Raised when a requested provider is not found.

    This occurs when attempting to access a provider that
    has not been registered.
    """


class ProviderAlreadyRegisteredError(ProviderError):
    """Raised when attempting to register a duplicate provider.

    This occurs when a provider with the same name is already
    registered in the system.
    """


class CapabilityError(ProviderError):
    """Raised when provider lacks required capabilities.

    This occurs when a provider does not support a required
    feature or capability.
    """

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        missing_capability: str | None = None,
    ) -> None:
        """Initialize the capability error.

        Args:
            message: Error message.
            provider_name: Optional provider name.
            missing_capability: Name of missing capability.
        """
        super().__init__(message, provider_name)
        self.missing_capability = missing_capability


class HealthCheckError(ProviderError):
    """Raised when a health check fails.

    This indicates the provider is not healthy and should
    not receive requests.
    """

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        health_status: str | None = None,
    ) -> None:
        """Initialize the health check error.

        Args:
            message: Error message.
            provider_name: Provider that failed health check.
            health_status: Current health status.
        """
        super().__init__(message, provider_name)
        self.health_status = health_status


class PaginationError(ProviderError):
    """Raised when pagination operation fails.

    This covers invalid pagination state, exhausted pages,
    and pagination parameter errors.
    """


class VersionError(ProviderError):
    """Raised when version compatibility check fails.

    This occurs when provider and SDK versions are incompatible.
    """
