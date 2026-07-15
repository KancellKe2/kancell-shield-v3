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

from src.search.provider.exceptions import (
    ProviderError as ProviderSdkError,
    ConfigurationError as ProviderConfigError,
    AuthenticationError,
    InvalidCredentialsError,
    ExpiredTokenError,
    OAuthError,
    RateLimitError as ProviderRateLimitError,
    QuotaExceededError,
    ProviderAlreadyRegisteredError,
    ProviderNotFoundError as ProviderNotFoundSdkError,
    CapabilityError,
    HealthCheckError as ProviderHealthCheckError,
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


class TestProviderSdkExceptions:
    """Tests for provider SDK exception hierarchy."""

    def test_provider_error_base(self) -> None:
        """Test ProviderSdkError is base exception."""
        error = ProviderSdkError("test error")
        assert isinstance(error, Exception)
        assert error.message == "test error"

    def test_provider_error_with_name(self) -> None:
        """Test ProviderSdkError with provider name."""
        error = ProviderSdkError("test error", provider_name="test_provider")
        assert error.provider_name == "test_provider"

    def test_configuration_error_inheritance(self) -> None:
        """Test ProviderConfigError inherits from ProviderSdkError."""
        error = ProviderConfigError("config error")
        assert isinstance(error, ProviderSdkError)

    def test_authentication_error_inheritance(self) -> None:
        """Test AuthenticationError inherits from ProviderSdkError."""
        error = AuthenticationError("auth error")
        assert isinstance(error, ProviderSdkError)

    def test_invalid_credentials_error_inheritance(self) -> None:
        """Test InvalidCredentialsError inherits from AuthenticationError."""
        error = InvalidCredentialsError("invalid credentials")
        assert isinstance(error, AuthenticationError)
        assert isinstance(error, ProviderSdkError)

    def test_expired_token_error_inheritance(self) -> None:
        """Test ExpiredTokenError inherits from AuthenticationError."""
        error = ExpiredTokenError("expired token")
        assert isinstance(error, AuthenticationError)
        assert isinstance(error, ProviderSdkError)

    def test_oauth_error_inheritance(self) -> None:
        """Test OAuthError inherits from AuthenticationError."""
        error = OAuthError("oauth error", oauth_error="invalid_grant")
        assert isinstance(error, AuthenticationError)
        assert isinstance(error, ProviderSdkError)
        assert error.oauth_error == "invalid_grant"

    def test_oauth_error_with_provider(self) -> None:
        """Test OAuthError with provider name."""
        error = OAuthError(
            "oauth error",
            provider_name="test_provider",
            oauth_error="invalid_grant"
        )
        assert error.provider_name == "test_provider"
        assert error.oauth_error == "invalid_grant"

    def test_rate_limit_error_inheritance(self) -> None:
        """Test ProviderRateLimitError inherits from ProviderSdkError."""
        error = ProviderRateLimitError("rate limit error")
        assert isinstance(error, ProviderSdkError)

    def test_quota_exceeded_error_inheritance(self) -> None:
        """Test QuotaExceededError inherits from RateLimitError."""
        error = QuotaExceededError("quota exceeded")
        assert isinstance(error, ProviderRateLimitError)
        assert isinstance(error, ProviderSdkError)

    def test_provider_already_registered_error_inheritance(self) -> None:
        """Test ProviderAlreadyRegisteredError inherits from ProviderSdkError."""
        error = ProviderAlreadyRegisteredError("already registered")
        assert isinstance(error, ProviderSdkError)

    def test_provider_not_found_error_inheritance(self) -> None:
        """Test ProviderNotFoundSdkError inherits from ProviderSdkError."""
        error = ProviderNotFoundSdkError("provider not found")
        assert isinstance(error, ProviderSdkError)

    def test_capability_error_inheritance(self) -> None:
        """Test CapabilityError inherits from ProviderSdkError."""
        error = CapabilityError("capability error")
        assert isinstance(error, ProviderSdkError)

    def test_health_check_error_inheritance(self) -> None:
        """Test ProviderHealthCheckError inherits from ProviderSdkError."""
        error = ProviderHealthCheckError("health check error")
        assert isinstance(error, ProviderSdkError)

    def test_all_exceptions_have_provider_name(self) -> None:
        """Test all provider exceptions accept provider_name."""
        errors = [
            ProviderSdkError("test", provider_name="p1"),
            ProviderConfigError("test", provider_name="p2"),
            AuthenticationError("test", provider_name="p3"),
            InvalidCredentialsError("test", provider_name="p4"),
            ExpiredTokenError("test", provider_name="p5"),
            OAuthError("test", provider_name="p6", oauth_error="e"),
            ProviderRateLimitError("test", provider_name="p7"),
            QuotaExceededError("test", provider_name="p8"),
            ProviderAlreadyRegisteredError("test", provider_name="p9"),
            ProviderNotFoundSdkError("test", provider_name="p10"),
            CapabilityError("test", provider_name="p11"),
            ProviderHealthCheckError("test", provider_name="p12"),
        ]
        for error in errors:
            assert error.provider_name is not None
