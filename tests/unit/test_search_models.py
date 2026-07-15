"""Unit tests for search models.

These tests verify model creation, default values, enum behavior,
and interface existence. No implementation tests are included.
"""

import pytest
from datetime import datetime, timezone

from src.search.models import (
    PaginationState,
    PaginationType,
    ProviderConfig,
    ProviderHealth,
    ProviderMetrics,
    ProviderState,
    RateLimitConfig,
    RateLimitInfo,
    RetryConfig,
    RetryMode,
    SearchConfig,
    SearchQuery,
    SearchResult,
    SearchResultSet,
)
from src.search.interfaces import (
    DeduplicationStrategy,
    HealthChecker,
    PaginationHandler,
    ProviderRegistry,
    QueryBuilder,
    RateLimiter,
    ResultNormalizer,
    RetryStrategy,
    SearchEngine,
    SearchProvider,
)


class TestProviderState:
    """Tests for ProviderState enum."""

    def test_enum_values_exist(self) -> None:
        """Verify all expected state values exist."""
        assert ProviderState.HEALTHY is not None
        assert ProviderState.DEGRADED is not None
        assert ProviderState.UNHEALTHY is not None
        assert ProviderState.DISABLED is not None
        assert ProviderState.RATE_LIMITED is not None

    def test_enum_count(self) -> None:
        """Verify the number of enum values."""
        expected_count = 5
        actual_count = len(ProviderState)
        assert actual_count == expected_count


class TestPaginationType:
    """Tests for PaginationType enum."""

    def test_enum_values_exist(self) -> None:
        """Verify all pagination types exist."""
        assert PaginationType.OFFSET is not None
        assert PaginationType.CURSOR is not None
        assert PaginationType.PAGE is not None


class TestRetryMode:
    """Tests for RetryMode enum."""

    def test_enum_values_exist(self) -> None:
        """Verify all retry modes exist."""
        assert RetryMode.FIXED is not None
        assert RetryMode.LINEAR is not None
        assert RetryMode.EXPONENTIAL is not None
        assert RetryMode.JITTERED is not None


class TestSearchQuery:
    """Tests for SearchQuery dataclass."""

    def test_creation_with_required_fields(self) -> None:
        """Verify SearchQuery can be created with required fields."""
        query = SearchQuery(query="malware test")
        assert query.query == "malware test"
        assert query.language == "en"
        assert query.region == "US"
        assert query.safe_search is True
        assert query.keywords == frozenset()

    def test_creation_with_all_fields(self) -> None:
        """Verify SearchQuery can be created with all fields."""
        query = SearchQuery(
            query="test query",
            keywords=frozenset({"test", "keyword"}),
            language="es",
            region="ES",
            safe_search=False,
        )
        assert query.query == "test query"
        assert "test" in query.keywords
        assert "keyword" in query.keywords
        assert query.language == "es"
        assert query.region == "ES"
        assert query.safe_search is False

    def test_empty_query_raises_error(self) -> None:
        """Verify empty query raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SearchQuery(query="")


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_creation_with_required_fields(self) -> None:
        """Verify SearchResult can be created with required fields."""
        result = SearchResult(
            url="https://example.com",
            title="Example Page",
            snippet="This is an example",
            provider="test_provider",
        )
        assert result.url == "https://example.com"
        assert result.title == "Example Page"
        assert result.snippet == "This is an example"
        assert result.provider == "test_provider"
        assert result.confidence == 0.5

    def test_creation_with_all_fields(self) -> None:
        """Verify SearchResult can be created with all fields."""
        now = datetime.now(timezone.utc)
        result = SearchResult(
            url="https://test.com",
            title="Test",
            snippet="Test snippet",
            provider="test",
            confidence=0.8,
            keywords=("test", "keyword"),
            discovered_at=now,
            position=1,
        )
        assert result.confidence == 0.8
        assert result.position == 1
        assert "test" in result.keywords

    def test_empty_url_raises_error(self) -> None:
        """Verify empty URL raises ValueError."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            SearchResult(url="", title="Test", snippet="Test", provider="test")

    def test_empty_title_raises_error(self) -> None:
        """Verify empty title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            SearchResult(url="https://test.com", title="", snippet="Test", provider="test")

    def test_invalid_confidence_raises_error(self) -> None:
        """Verify invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            SearchResult(
                url="https://test.com",
                title="Test",
                snippet="Test",
                provider="test",
                confidence=1.5,
            )


class TestSearchResultSet:
    """Tests for SearchResultSet dataclass."""

    def test_creation(self) -> None:
        """Verify SearchResultSet can be created."""
        results = (
            SearchResult(url="https://a.com", title="A", snippet="A", provider="p1"),
            SearchResult(url="https://b.com", title="B", snippet="B", provider="p2"),
        )
        result_set = SearchResultSet(
            results=results,
            total_count=2,
            unique_count=2,
        )
        assert len(result_set.results) == 2
        assert result_set.total_count == 2

    def test_filter_by_provider(self) -> None:
        """Verify filtering by provider."""
        results = (
            SearchResult(url="https://a.com", title="A", snippet="A", provider="p1"),
            SearchResult(url="https://b.com", title="B", snippet="B", provider="p2"),
        )
        result_set = SearchResultSet(
            results=results,
            total_count=2,
            unique_count=2,
        )
        filtered = result_set.filter_by_provider("p1")
        assert len(filtered.results) == 1
        assert filtered.results[0].provider == "p1"

    def test_filter_by_confidence(self) -> None:
        """Verify filtering by confidence."""
        results = (
            SearchResult(url="https://a.com", title="A", snippet="A", provider="p1", confidence=0.9),
            SearchResult(url="https://b.com", title="B", snippet="B", provider="p2", confidence=0.3),
        )
        result_set = SearchResultSet(
            results=results,
            total_count=2,
            unique_count=2,
        )
        filtered = result_set.filter_by_confidence(0.5)
        assert len(filtered.results) == 1
        assert filtered.results[0].confidence >= 0.5

    def test_negative_count_raises_error(self) -> None:
        """Verify negative counts raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            SearchResultSet(results=(), total_count=-1, unique_count=0)


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_default_values(self) -> None:
        """Verify default values."""
        config = RateLimitConfig()
        assert config.requests_per_window == 10
        assert config.window_seconds == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.max_backoff_seconds == 300.0

    def test_custom_values(self) -> None:
        """Verify custom values."""
        config = RateLimitConfig(
            requests_per_window=100,
            window_seconds=30.0,
        )
        assert config.requests_per_window == 100
        assert config.window_seconds == 30.0

    def test_invalid_requests_raises_error(self) -> None:
        """Verify invalid requests raises ValueError."""
        with pytest.raises(ValueError, match="at least 1"):
            RateLimitConfig(requests_per_window=0)

    def test_invalid_window_raises_error(self) -> None:
        """Verify invalid window raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            RateLimitConfig(window_seconds=0)


class TestRateLimitInfo:
    """Tests for RateLimitInfo dataclass."""

    def test_creation(self) -> None:
        """Verify RateLimitInfo can be created."""
        reset_time = datetime.now(timezone.utc)
        info = RateLimitInfo(
            provider_name="test",
            requests_remaining=5,
            reset_at=reset_time,
        )
        assert info.provider_name == "test"
        assert info.requests_remaining == 5

    def test_is_limited_false(self) -> None:
        """Verify not limited when no backoff."""
        info = RateLimitInfo(
            provider_name="test",
            requests_remaining=5,
            reset_at=datetime.now(timezone.utc),
            backoff_until=None,
        )
        assert info.is_limited() is False

    def test_is_limited_true(self) -> None:
        """Verify limited when backoff set."""
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        info = RateLimitInfo(
            provider_name="test",
            requests_remaining=0,
            reset_at=datetime.now(timezone.utc),
            backoff_until=future,
        )
        assert info.is_limited() is True


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self) -> None:
        """Verify default values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.jitter is True
        assert config.mode == RetryMode.EXPONENTIAL

    def test_invalid_max_attempts_raises_error(self) -> None:
        """Verify invalid max_attempts raises ValueError."""
        with pytest.raises(ValueError, match="at least 1"):
            RetryConfig(max_attempts=0)

    def test_invalid_delay_raises_error(self) -> None:
        """Verify invalid delay raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            RetryConfig(initial_delay=0)

    def test_invalid_max_delay_raises_error(self) -> None:
        """Verify invalid max_delay raises ValueError."""
        with pytest.raises(ValueError, match="must be >= initial_delay"):
            RetryConfig(initial_delay=5.0, max_delay=2.0)


class TestProviderHealth:
    """Tests for ProviderHealth dataclass."""

    def test_creation(self) -> None:
        """Verify ProviderHealth can be created."""
        health = ProviderHealth(
            provider_name="test",
            state=ProviderState.HEALTHY,
        )
        assert health.provider_name == "test"
        assert health.state == ProviderState.HEALTHY
        assert health.success_rate == 1.0

    def test_invalid_success_rate_raises_error(self) -> None:
        """Verify invalid success_rate raises ValueError."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            ProviderHealth(
                provider_name="test",
                state=ProviderState.HEALTHY,
                success_rate=1.5,
            )


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_creation_with_required_fields(self) -> None:
        """Verify ProviderConfig can be created."""
        config = ProviderConfig(name="test_provider")
        assert config.name == "test_provider"
        assert config.priority == 1
        assert config.enabled is True
        assert config.weight == 1.0

    def test_creation_with_all_fields(self) -> None:
        """Verify ProviderConfig with all fields."""
        rate_limit = RateLimitConfig(requests_per_window=50)
        retry = RetryConfig(max_attempts=5)
        config = ProviderConfig(
            name="test",
            priority=10,
            enabled=False,
            timeout=60.0,
            rate_limit=rate_limit,
            retry_config=retry,
            weight=0.8,
        )
        assert config.priority == 10
        assert config.enabled is False
        assert config.timeout == 60.0
        assert config.weight == 0.8

    def test_empty_name_raises_error(self) -> None:
        """Verify empty name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ProviderConfig(name="")

    def test_invalid_weight_raises_error(self) -> None:
        """Verify invalid weight raises ValueError."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            ProviderConfig(name="test", weight=2.0)


class TestSearchConfig:
    """Tests for SearchConfig dataclass."""

    def test_default_values(self) -> None:
        """Verify default values."""
        config = SearchConfig()
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.batch_size == 10
        assert config.enable_deduplication is True
        assert config.confidence_threshold == 0.5

    def test_invalid_timeout_raises_error(self) -> None:
        """Verify invalid timeout raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            SearchConfig(timeout=0)

    def test_invalid_batch_size_raises_error(self) -> None:
        """Verify invalid batch_size raises ValueError."""
        with pytest.raises(ValueError, match="at least 1"):
            SearchConfig(batch_size=0)

    def test_invalid_confidence_raises_error(self) -> None:
        """Verify invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            SearchConfig(confidence_threshold=2.0)


class TestPaginationState:
    """Tests for PaginationState dataclass."""

    def test_default_values(self) -> None:
        """Verify default values."""
        state = PaginationState()
        assert state.pagination_type == PaginationType.OFFSET
        assert state.offset == 0
        assert state.page == 1
        assert state.page_size == 20

    def test_next_offset(self) -> None:
        """Verify next offset calculation."""
        state = PaginationState(offset=0, page_size=10)
        next_state = state.next_offset(10)
        assert next_state.offset == 10

    def test_next_page(self) -> None:
        """Verify next page calculation."""
        state = PaginationState(page=1)
        next_state = state.next_page()
        assert next_state.page == 2

    def test_invalid_offset_raises_error(self) -> None:
        """Verify invalid offset raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            PaginationState(offset=-1)

    def test_invalid_page_raises_error(self) -> None:
        """Verify invalid page raises ValueError."""
        with pytest.raises(ValueError, match="at least 1"):
            PaginationState(page=0)


class TestProviderMetrics:
    """Tests for ProviderMetrics dataclass."""

    def test_creation(self) -> None:
        """Verify ProviderMetrics can be created."""
        metrics = ProviderMetrics(provider_name="test")
        assert metrics.provider_name == "test"
        assert metrics.total_queries == 0
        assert metrics.success_rate() == 0.0

    def test_success_rate_calculation(self) -> None:
        """Verify success rate calculation."""
        metrics = ProviderMetrics(
            provider_name="test",
            total_queries=100,
            success_count=90,
        )
        assert metrics.success_rate() == 0.9


class TestInterfacesExist:
    """Tests to verify all interfaces are defined."""

    def test_search_provider_interface_exists(self) -> None:
        """Verify SearchProvider protocol exists."""
        assert SearchProvider is not None

    def test_rate_limiter_interface_exists(self) -> None:
        """Verify RateLimiter protocol exists."""
        assert RateLimiter is not None

    def test_retry_strategy_interface_exists(self) -> None:
        """Verify RetryStrategy protocol exists."""
        assert RetryStrategy is not None

    def test_result_normalizer_interface_exists(self) -> None:
        """Verify ResultNormalizer protocol exists."""
        assert ResultNormalizer is not None

    def test_query_builder_interface_exists(self) -> None:
        """Verify QueryBuilder protocol exists."""
        assert QueryBuilder is not None

    def test_provider_registry_interface_exists(self) -> None:
        """Verify ProviderRegistry protocol exists."""
        assert ProviderRegistry is not None

    def test_health_checker_interface_exists(self) -> None:
        """Verify HealthChecker protocol exists."""
        assert HealthChecker is not None

    def test_search_engine_interface_exists(self) -> None:
        """Verify SearchEngine abstract class exists."""
        assert SearchEngine is not None

    def test_deduplication_strategy_interface_exists(self) -> None:
        """Verify DeduplicationStrategy protocol exists."""
        assert DeduplicationStrategy is not None

    def test_pagination_handler_interface_exists(self) -> None:
        """Verify PaginationHandler protocol exists."""
        assert PaginationHandler is not None
