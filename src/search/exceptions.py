"""Custom exceptions for the Search Engine."""


class SearchEngineError(Exception):
    """Base exception for Search Engine errors."""

    pass


class ProviderError(SearchEngineError):
    """Raised when a search provider operation fails."""

    pass


class RateLimitError(SearchEngineError):
    """Raised when rate limit is exceeded."""

    pass


class RetryError(SearchEngineError):
    """Raised when retry operation fails."""

    pass


class ConfigurationError(SearchEngineError):
    """Raised when configuration is invalid."""

    pass


class ValidationError(SearchEngineError):
    """Raised when validation fails."""

    pass


class QueryError(SearchEngineError):
    """Raised when query construction fails."""

    pass


class ResultError(SearchEngineError):
    """Raised when result processing fails."""

    pass


class HealthCheckError(SearchEngineError):
    """Raised when health check fails."""

    pass


class ProviderNotFoundError(SearchEngineError):
    """Raised when a provider is not found."""

    pass


class ProviderDisabledError(SearchEngineError):
    """Raised when a provider is disabled."""

    pass


class ProviderUnhealthyError(SearchEngineError):
    """Raised when a provider is unhealthy."""

    pass


class TimeoutError(SearchEngineError):
    """Raised when a search operation times out."""

    pass


class DeduplicationError(SearchEngineError):
    """Raised when deduplication fails."""

    pass


class PaginationError(SearchEngineError):
    """Raised when pagination operation fails."""

    pass
