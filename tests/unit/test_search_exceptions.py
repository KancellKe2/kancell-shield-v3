"""Unit tests for search engine exceptions."""

import pytest

from src.search.exceptions import (
    ConfigurationError,
    DeduplicationError,
    HealthCheckError,
    ProviderDisabledError,
    ProviderError,
    ProviderNotFoundError,
    ProviderUnhealthyError,
    QueryError,
    RateLimitError,
    ResultError,
    RetryError,
    SearchEngineError,
    TimeoutError,
    ValidationError,
)


class TestSearchEngineExceptions:
    """Tests for search engine exception hierarchy."""

    def test_search_engine_error_is_base(self) -> None:
        """Test SearchEngineError is base exception."""
        error = SearchEngineError("test")
        assert isinstance(error, Exception)

    def test_provider_error_inheritance(self) -> None:
        """Test ProviderError inherits from base."""
        error = ProviderError("provider error")
        assert isinstance(error, SearchEngineError)

    def test_rate_limit_error_inheritance(self) -> None:
        """Test RateLimitError inherits from base."""
        error = RateLimitError("rate limit error")
        assert isinstance(error, SearchEngineError)

    def test_retry_error_inheritance(self) -> None:
        """Test RetryError inherits from base."""
        error = RetryError("retry error")
        assert isinstance(error, SearchEngineError)

    def test_configuration_error_inheritance(self) -> None:
        """Test ConfigurationError inherits from base."""
        error = ConfigurationError("config error")
        assert isinstance(error, SearchEngineError)

    def test_validation_error_inheritance(self) -> None:
        """Test ValidationError inherits from base."""
        error = ValidationError("validation error")
        assert isinstance(error, SearchEngineError)

    def test_query_error_inheritance(self) -> None:
        """Test QueryError inherits from base."""
        error = QueryError("query error")
        assert isinstance(error, SearchEngineError)

    def test_result_error_inheritance(self) -> None:
        """Test ResultError inherits from base."""
        error = ResultError("result error")
        assert isinstance(error, SearchEngineError)

    def test_health_check_error_inheritance(self) -> None:
        """Test HealthCheckError inherits from base."""
        error = HealthCheckError("health check error")
        assert isinstance(error, SearchEngineError)

    def test_provider_not_found_error_inheritance(self) -> None:
        """Test ProviderNotFoundError inherits from base."""
        error = ProviderNotFoundError("provider not found")
        assert isinstance(error, SearchEngineError)

    def test_provider_disabled_error_inheritance(self) -> None:
        """Test ProviderDisabledError inherits from base."""
        error = ProviderDisabledError("provider disabled")
        assert isinstance(error, SearchEngineError)

    def test_provider_unhealthy_error_inheritance(self) -> None:
        """Test ProviderUnhealthyError inherits from base."""
        error = ProviderUnhealthyError("provider unhealthy")
        assert isinstance(error, SearchEngineError)

    def test_timeout_error_inheritance(self) -> None:
        """Test TimeoutError inherits from base."""
        error = TimeoutError("timeout error")
        assert isinstance(error, SearchEngineError)

    def test_deduplication_error_inheritance(self) -> None:
        """Test DeduplicationError inherits from base."""
        error = DeduplicationError("dedup error")
        assert isinstance(error, SearchEngineError)

    def test_exception_message(self) -> None:
        """Test exception messages are preserved."""
        message = "specific error message"
        error = SearchEngineError(message)
        assert str(error) == message

    def test_exception_chaining(self) -> None:
        """Test exception chaining works."""
        cause = ValueError("cause")
        error = ProviderError("effect")
        error.__cause__ = cause
        assert error.__cause__ is cause
