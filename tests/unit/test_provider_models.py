"""Unit tests for Search Provider SDK models.

These tests verify model creation, default values, enum behavior,
immutability, and protocol existence.
"""

import pytest
from datetime import datetime, timezone

from src.search.provider.models import (
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
from src.search.provider.interfaces import (
    Provider,
    ProviderFactory,
    ProviderRegistry,
    ProviderAuthenticator,
    ProviderHealthChecker,
    ProviderCapabilityResolver,
    ProviderRateLimiter,
    ProviderPaginator,
    ProviderErrorHandler,
    ProviderAction,
)


class TestProviderVersion:
    """Tests for ProviderVersion."""

    def test_creation(self) -> None:
        """Test basic creation."""
        version = ProviderVersion(
            major=1,
            minor=0,
            patch=0,
            api_version="v1",
        )
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0
        assert version.api_version == "v1"

    def test_invalid_major_version(self) -> None:
        """Test negative major version raises error."""
        with pytest.raises(ValueError, match="major"):
            ProviderVersion(major=-1, minor=0, patch=0, api_version="v1")

    def test_is_compatible_with(self) -> None:
        """Test version compatibility check."""
        v1 = ProviderVersion(major=1, minor=0, patch=0, api_version="v1")
        v2 = ProviderVersion(major=1, minor=0, patch=0, api_version="v1")
        v3 = ProviderVersion(major=1, minor=0, patch=0, api_version="v2")

        assert v1.is_compatible_with(v2) is True
        assert v1.is_compatible_with(v3) is False

    def test_string_representation(self) -> None:
        """Test string representation."""
        version = ProviderVersion(major=1, minor=2, patch=3, api_version="v1")
        assert str(version) == "1.2.3 (API v1)"


class TestProviderInfo:
    """Tests for ProviderInfo."""

    def test_creation(self) -> None:
        """Test basic creation."""
        info = ProviderInfo(
            name="test_provider",
            display_name="Test Provider",
            version=ProviderVersion(1, 0, 0, "v1"),
            description="A test provider",
        )
        assert info.name == "test_provider"
        assert info.display_name == "Test Provider"

    def test_empty_name_raises_error(self) -> None:
        """Test empty name raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ProviderInfo(
                name="",
                display_name="Test",
                version=ProviderVersion(1, 0, 0, "v1"),
                description="Test",
            )

    def test_empty_display_name_raises_error(self) -> None:
        """Test empty display name raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ProviderInfo(
                name="test",
                display_name="",
                version=ProviderVersion(1, 0, 0, "v1"),
                description="Test",
            )


class TestProviderCapabilities:
    """Tests for ProviderCapabilities."""

    def test_defaults(self) -> None:
        """Test default values."""
        caps = ProviderCapabilities()
        assert caps.supports_search is True
        assert caps.max_results_per_page == 100
        assert AuthMethod.API_KEY in caps.supported_auth_methods

    def test_custom_capabilities(self) -> None:
        """Test custom capability values."""
        caps = ProviderCapabilities(
            supports_pagination=PaginationType.CURSOR,
            supports_filtering=True,
        )
        assert caps.supports_pagination == PaginationType.CURSOR
        assert caps.supports_filtering is True


class TestProviderFeatureFlags:
    """Tests for ProviderFeatureFlags."""

    def test_defaults(self) -> None:
        """Test default values."""
        flags = ProviderFeatureFlags()
        assert flags.enable_safe_search is True
        assert flags.enable_filters is True

    def test_custom_flags(self) -> None:
        """Test custom feature flags."""
        flags = ProviderFeatureFlags(
            custom_flags={"feature_a": True, "feature_b": False}
        )
        assert flags.is_enabled("feature_a") is True
        assert flags.is_enabled("feature_b") is False
        assert flags.is_enabled("unknown") is True  # Defaults to True

    def test_get_flag(self) -> None:
        """Test getting flag with default."""
        flags = ProviderFeatureFlags()
        assert flags.get_flag("unknown") is True
        assert flags.get_flag("unknown", False) is False


class TestProviderAuthentication:
    """Tests for ProviderAuthentication."""

    def test_creation(self) -> None:
        """Test basic creation."""
        auth = ProviderAuthentication(
            method=AuthMethod.API_KEY,
            credentials={"X-API-Key": "test-key"},
        )
        assert auth.method == AuthMethod.API_KEY
        assert auth.is_authenticated is False

    def test_is_token_expired_no_token(self) -> None:
        """Test expired when no token."""
        auth = ProviderAuthentication(method=AuthMethod.API_KEY)
        assert auth.is_token_expired() is True

    def test_is_token_expired_with_expiry(self) -> None:
        """Test expired with future expiry."""
        auth = ProviderAuthentication(
            method=AuthMethod.API_KEY,
            token="test-token",
            token_expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )
        assert auth.is_token_expired() is False

    def test_none_auth_no_credentials(self) -> None:
        """Test NONE auth with no credentials."""
        auth = ProviderAuthentication(method=AuthMethod.NONE)
        assert auth.is_authenticated is False

    def test_get_header_value_api_key(self) -> None:
        """Test getting header for API key."""
        auth = ProviderAuthentication(
            method=AuthMethod.API_KEY,
            credentials={"X-API-Key": "test-key"},
        )
        assert auth.get_header_value() == "test-key"

    def test_get_header_value_bearer(self) -> None:
        """Test getting header for bearer token."""
        auth = ProviderAuthentication(
            method=AuthMethod.BEARER,
            token="test-token",
        )
        assert auth.get_header_value() == "Bearer test-token"


class TestProviderConfiguration:
    """Tests for ProviderConfiguration."""

    def test_creation(self) -> None:
        """Test basic creation."""
        config = ProviderConfiguration(
            provider_name="test",
            base_url="https://api.example.com",
        )
        assert config.provider_name == "test"
        assert config.base_url == "https://api.example.com"

    def test_invalid_timeout(self) -> None:
        """Test invalid timeout raises error."""
        with pytest.raises(ValueError, match="positive"):
            ProviderConfiguration(
                provider_name="test",
                base_url="https://api.example.com",
                timeout_seconds=0,
            )

    def test_invalid_max_retries(self) -> None:
        """Test invalid max retries raises error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            ProviderConfiguration(
                provider_name="test",
                base_url="https://api.example.com",
                max_retries=-1,
            )


class TestProviderHealthStatus:
    """Tests for ProviderHealthStatus."""

    def test_creation(self) -> None:
        """Test basic creation."""
        health = ProviderHealthStatus(
            provider_name="test",
            status=HealthStatus.HEALTHY,
        )
        assert health.provider_name == "test"
        assert health.status == HealthStatus.HEALTHY
        assert health.is_available is True

    def test_invalid_success_rate(self) -> None:
        """Test invalid success rate raises error."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            ProviderHealthStatus(
                provider_name="test",
                status=HealthStatus.HEALTHY,
                success_rate=1.5,
            )

    def test_is_healthy_enough(self) -> None:
        """Test healthy enough check."""
        health = ProviderHealthStatus(
            provider_name="test",
            status=HealthStatus.HEALTHY,
            success_rate=0.8,
        )
        assert health.is_healthy_enough() is True
        assert health.is_healthy_enough(threshold=0.9) is False


class TestPaginationState:
    """Tests for PaginationState."""

    def test_defaults(self) -> None:
        """Test default values."""
        state = PaginationState(pagination_type=PaginationType.OFFSET)
        assert state.offset == 0
        assert state.page == 1
        assert state.page_size == 20

    def test_invalid_offset(self) -> None:
        """Test invalid offset raises error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            PaginationState(pagination_type=PaginationType.OFFSET, offset=-1)

    def test_invalid_page(self) -> None:
        """Test invalid page raises error."""
        with pytest.raises(ValueError, match="at least 1"):
            PaginationState(pagination_type=PaginationType.PAGE, page=0)

    def test_next_offset(self) -> None:
        """Test next offset calculation."""
        state = PaginationState(
            pagination_type=PaginationType.OFFSET,
            offset=0,
        )
        next_state = state.next_offset(10)
        assert next_state.offset == 10

    def test_next_page(self) -> None:
        """Test next page calculation."""
        state = PaginationState(
            pagination_type=PaginationType.PAGE,
            page=1,
        )
        next_state = state.next_page()
        assert next_state.page == 2


class TestProviderRequest:
    """Tests for ProviderRequest."""

    def test_creation(self) -> None:
        """Test basic creation."""
        request = ProviderRequest(query="test query")
        assert request.query == "test query"

    def test_empty_query_raises_error(self) -> None:
        """Test empty query raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ProviderRequest(query="")


class TestProviderResponse:
    """Tests for ProviderResponse."""

    def test_creation(self) -> None:
        """Test basic creation."""
        response = ProviderResponse(
            results=({"url": "https://example.com"},),
            total_count=1,
        )
        assert len(response.results) == 1
        assert response.total_count == 1

    def test_invalid_total_count(self) -> None:
        """Test invalid total count raises error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            ProviderResponse(results=(), total_count=-1)


class TestRateLimitInfo:
    """Tests for RateLimitInfo."""

    def test_creation(self) -> None:
        """Test basic creation."""
        info = RateLimitInfo(
            requests_remaining=100,
            requests_limit=100,
            reset_at=datetime.now(timezone.utc),
        )
        assert info.requests_remaining == 100

    def test_is_limited_no_limit(self) -> None:
        """Test not limited when under limit."""
        info = RateLimitInfo(
            requests_remaining=50,
            requests_limit=100,
            reset_at=datetime.now(timezone.utc),
        )
        assert info.is_limited() is False

    def test_is_limited_exhausted(self) -> None:
        """Test limited when exhausted."""
        info = RateLimitInfo(
            requests_remaining=0,
            requests_limit=100,
            reset_at=datetime.now(timezone.utc),
        )
        assert info.is_limited() is True

    def test_get_wait_time_no_wait(self) -> None:
        """Test no wait when not limited."""
        info = RateLimitInfo(
            requests_remaining=50,
            requests_limit=100,
            reset_at=datetime.now(timezone.utc),
        )
        assert info.get_wait_time() == 0.0


class TestProviderStatistics:
    """Tests for ProviderStatistics."""

    def test_creation(self) -> None:
        """Test basic creation."""
        stats = ProviderStatistics(provider_name="test")
        assert stats.provider_name == "test"
        assert stats.total_requests == 0

    def test_success_rate_zero_requests(self) -> None:
        """Test success rate with no requests."""
        stats = ProviderStatistics(provider_name="test")
        assert stats.success_rate() == 0.0

    def test_success_rate_calculation(self) -> None:
        """Test success rate calculation."""
        stats = ProviderStatistics(
            provider_name="test",
            total_requests=100,
            successful_requests=90,
        )
        assert stats.success_rate() == 0.9


class TestEnums:
    """Tests for enum values."""

    def test_auth_method_values(self) -> None:
        """Test AuthMethod enum values."""
        assert AuthMethod.API_KEY is not None
        assert AuthMethod.OAUTH2 is not None
        assert AuthMethod.BASIC is not None
        assert AuthMethod.BEARER is not None
        assert AuthMethod.NONE is not None

    def test_pagination_type_values(self) -> None:
        """Test PaginationType enum values."""
        assert PaginationType.OFFSET is not None
        assert PaginationType.CURSOR is not None
        assert PaginationType.PAGE is not None

    def test_rate_limit_type_values(self) -> None:
        """Test RateLimitType enum values."""
        assert RateLimitType.TOKEN_BUCKET is not None
        assert RateLimitType.SLIDING_WINDOW is not None
        assert RateLimitType.FIXED_WINDOW is not None

    def test_health_status_values(self) -> None:
        """Test HealthStatus enum values."""
        assert HealthStatus.HEALTHY is not None
        assert HealthStatus.DEGRADED is not None
        assert HealthStatus.UNHEALTHY is not None
        assert HealthStatus.UNKNOWN is not None


class TestImmutability:
    """Tests for model immutability."""

    def test_provider_version_immutable(self) -> None:
        """Test ProviderVersion is immutable."""
        version = ProviderVersion(major=1, minor=0, patch=0, api_version="v1")
        with pytest.raises(AttributeError):
            version.major = 2

    def test_provider_info_immutable(self) -> None:
        """Test ProviderInfo is immutable."""
        info = ProviderInfo(
            name="test",
            display_name="Test",
            version=ProviderVersion(1, 0, 0, "v1"),
            description="Test",
        )
        with pytest.raises(AttributeError):
            info.name = "other"

    def test_pagination_state_immutable(self) -> None:
        """Test PaginationState is immutable."""
        state = PaginationState(pagination_type=PaginationType.OFFSET)
        with pytest.raises(AttributeError):
            state.offset = 10


class TestInterfacesExist:
    """Tests to verify all interfaces are defined."""

    def test_provider_interface_exists(self) -> None:
        """Verify Provider protocol exists."""
        assert Provider is not None

    def test_provider_factory_interface_exists(self) -> None:
        """Verify ProviderFactory protocol exists."""
        assert ProviderFactory is not None

    def test_provider_registry_interface_exists(self) -> None:
        """Verify ProviderRegistry protocol exists."""
        assert ProviderRegistry is not None

    def test_provider_authenticator_interface_exists(self) -> None:
        """Verify ProviderAuthenticator protocol exists."""
        assert ProviderAuthenticator is not None

    def test_provider_health_checker_interface_exists(self) -> None:
        """Verify ProviderHealthChecker protocol exists."""
        assert ProviderHealthChecker is not None

    def test_provider_capability_resolver_interface_exists(self) -> None:
        """Verify ProviderCapabilityResolver protocol exists."""
        assert ProviderCapabilityResolver is not None

    def test_provider_rate_limiter_interface_exists(self) -> None:
        """Verify ProviderRateLimiter protocol exists."""
        assert ProviderRateLimiter is not None

    def test_provider_paginator_interface_exists(self) -> None:
        """Verify ProviderPaginator protocol exists."""
        assert ProviderPaginator is not None

    def test_provider_error_handler_interface_exists(self) -> None:
        """Verify ProviderErrorHandler protocol exists."""
        assert ProviderErrorHandler is not None

    def test_provider_action_enum_exists(self) -> None:
        """Verify ProviderAction enum exists."""
        assert ProviderAction is not None
        assert ProviderAction.RETRY is not None
        assert ProviderAction.FAIL is not None
