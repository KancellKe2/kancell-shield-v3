"""Unit tests for retry strategies."""

import pytest
from unittest import mock

from src.search.models import RetryConfig, RetryMode
from src.search.retry import (
    ExponentialBackoffRetry,
    FixedRetryStrategy,
    JitteredRetryStrategy,
    LinearRetryStrategy,
    SelectiveRetryStrategy,
)


class TestExponentialBackoffRetry:
    """Tests for ExponentialBackoffRetry."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.retry = ExponentialBackoffRetry()

    def test_should_retry_under_limit(self) -> None:
        """Test retry under max attempts."""
        error = RuntimeError("test error")
        assert self.retry.should_retry(1, error) is True

    def test_should_not_retry_at_limit(self) -> None:
        """Test no retry at max attempts."""
        error = RuntimeError("test error")
        # Default max_attempts is 3
        assert self.retry.should_retry(3, error) is False

    def test_should_not_retry_validation_error(self) -> None:
        """Test no retry for validation errors."""
        from src.search.exceptions import ValidationError
        error = ValidationError("validation error")
        assert self.retry.should_retry(1, error) is False

    def test_should_not_retry_configuration_error(self) -> None:
        """Test no retry for configuration errors."""
        from src.search.exceptions import ConfigurationError
        error = ConfigurationError("config error")
        assert self.retry.should_retry(1, error) is False

    def test_backoff_delay_increases(self) -> None:
        """Test backoff delay increases with attempts using jitter-free retry."""
        # Use a retry strategy without jitter for deterministic ordering test
        retry_no_jitter = ExponentialBackoffRetry(RetryConfig(jitter=False))
        delay1 = retry_no_jitter.get_backoff_delay(1)
        delay2 = retry_no_jitter.get_backoff_delay(2)
        # Without jitter, delays strictly increase
        assert delay2 > delay1
        # Verify exponential growth base (2.0 is base for attempt 2)
        assert abs(delay2 - delay1 * 2.0) < 0.001

    def test_backoff_delay_capped_at_max(self) -> None:
        """Test backoff delay is capped at max_delay."""
        config = RetryConfig(max_delay=5.0)
        retry = ExponentialBackoffRetry(config)
        delay = retry.get_backoff_delay(100)
        assert delay <= 5.0

    def test_get_config(self) -> None:
        """Test getting configuration."""
        config = self.retry.get_config()
        assert isinstance(config, RetryConfig)


class TestFixedRetryStrategy:
    """Tests for FixedRetryStrategy."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.retry = FixedRetryStrategy(delay=2.0, max_attempts=3)

    def test_should_retry_under_limit(self) -> None:
        """Test retry under max attempts."""
        assert self.retry.should_retry(1, RuntimeError()) is True

    def test_should_not_retry_at_limit(self) -> None:
        """Test no retry at max attempts."""
        assert self.retry.should_retry(3, RuntimeError()) is False

    def test_fixed_delay(self) -> None:
        """Test fixed delay is constant."""
        delay1 = self.retry.get_backoff_delay(1)
        delay2 = self.retry.get_backoff_delay(2)
        assert delay1 == delay2 == 2.0

    def test_get_config(self) -> None:
        """Test getting configuration."""
        config = self.retry.get_config()
        assert config.max_attempts == 3
        assert config.initial_delay == 2.0


class TestLinearRetryStrategy:
    """Tests for LinearRetryStrategy."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.retry = LinearRetryStrategy(
            initial_delay=1.0,
            increment=1.0,
            max_attempts=5,
        )

    def test_linear_increase(self) -> None:
        """Test delay increases linearly."""
        delay1 = self.retry.get_backoff_delay(1)
        delay2 = self.retry.get_backoff_delay(2)
        assert delay2 == delay1 + 1.0

    def test_should_retry(self) -> None:
        """Test retry behavior."""
        assert self.retry.should_retry(1, RuntimeError()) is True
        assert self.retry.should_retry(5, RuntimeError()) is False


class TestJitteredRetryStrategy:
    """Tests for JitteredRetryStrategy."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.retry = JitteredRetryStrategy(
            initial_delay=1.0,
            max_delay=60.0,
            max_attempts=5,
        )

    def test_variance_in_delays(self) -> None:
        """Test delays have variance due to jitter."""
        delays = [self.retry.get_backoff_delay(1) for _ in range(10)]
        # At least some delays should be different due to jitter
        unique_delays = set(delays)
        assert len(unique_delays) > 1

    def test_delays_increase_exponentially(self) -> None:
        """Test base delay increases exponentially."""
        delay1 = self.retry.get_backoff_delay(1)
        delay2 = self.retry.get_backoff_delay(2)
        # With jitter, we check base increase
        assert delay2 > delay1

    def test_capped_at_max_delay(self) -> None:
        """Test delay is capped."""
        # Multiple attempts should not exceed max
        for attempt in range(10):
            delay = self.retry.get_backoff_delay(attempt)
            assert delay <= 120.0  # 2 * max_delay for jitter


class TestSelectiveRetryStrategy:
    """Tests for SelectiveRetryStrategy."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.retry = SelectiveRetryStrategy(
            retryable_errors=(ValueError, TypeError),
            config=RetryConfig(max_attempts=3),
        )

    def test_retryable_error(self) -> None:
        """Test retry for retryable error."""
        assert self.retry.should_retry(1, ValueError("test")) is True

    def test_non_retryable_error(self) -> None:
        """Test no retry for non-retryable error."""
        assert self.retry.should_retry(1, RuntimeError("test")) is False

    def test_at_max_attempts(self) -> None:
        """Test no retry at max attempts."""
        assert self.retry.should_retry(3, ValueError("test")) is False


class TestRetryConfig:
    """Tests for RetryConfig validation."""

    def test_invalid_max_attempts(self) -> None:
        """Test invalid max_attempts raises error."""
        with pytest.raises(ValueError, match="at least 1"):
            RetryConfig(max_attempts=0)

    def test_invalid_initial_delay(self) -> None:
        """Test invalid initial_delay raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            RetryConfig(initial_delay=0)

    def test_invalid_max_delay(self) -> None:
        """Test invalid max_delay raises error."""
        with pytest.raises(ValueError, match="must be >= initial_delay"):
            RetryConfig(initial_delay=5.0, max_delay=2.0)
