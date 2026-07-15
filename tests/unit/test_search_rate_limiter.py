"""Unit tests for rate limiters."""

import pytest
import asyncio

from src.search.models import RateLimitConfig
from src.search.rate_limiter import (
    GlobalRateLimiter,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
)


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        config = RateLimitConfig(
            requests_per_window=5,
            window_seconds=60.0,
        )
        self.limiter = TokenBucketRateLimiter({"test": config})

    def test_acquire_allowed(self) -> None:
        """Test acquire when tokens available."""
        result = asyncio.run(self.limiter.acquire("test"))
        assert result is True

    def test_acquire_exhausted(self) -> None:
        """Test acquire when tokens exhausted."""
        # Consume all tokens
        for _ in range(5):
            asyncio.run(self.limiter.acquire("test"))

        # Should fail
        result = asyncio.run(self.limiter.acquire("test"))
        assert result is False

    def test_is_limited(self) -> None:
        """Test is_limited check."""
        assert self.limiter.is_limited("test") is False

    def test_get_wait_time(self) -> None:
        """Test getting wait time."""
        wait_time = self.limiter.get_wait_time("test")
        assert wait_time >= 0

    def test_apply_backoff(self) -> None:
        """Test applying backoff after consuming tokens."""
        # Consume all tokens
        for _ in range(5):
            asyncio.run(self.limiter.acquire("test"))
        
        # Now apply backoff - it should double the wait time
        self.limiter.apply_backoff("test", multiplier=2.0)
        # After consuming tokens and applying backoff, should be limited
        assert self.limiter.is_limited("test") is True

    def test_reset_backoff(self) -> None:
        """Test resetting backoff."""
        self.limiter.apply_backoff("test")
        self.limiter.reset_backoff("test")
        assert self.limiter.is_limited("test") is False

    def test_unknown_provider_uses_defaults(self) -> None:
        """Test unknown provider uses default config."""
        # Should use default RateLimitConfig
        asyncio.run(self.limiter.acquire("unknown"))
        wait_time = self.limiter.get_wait_time("unknown")
        assert wait_time >= 0


class TestSlidingWindowRateLimiter:
    """Tests for SlidingWindowRateLimiter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        config = RateLimitConfig(
            requests_per_window=3,
            window_seconds=60.0,
        )
        self.limiter = SlidingWindowRateLimiter({"test": config})

    def test_acquire_allowed(self) -> None:
        """Test acquire when under limit."""
        result = asyncio.run(self.limiter.acquire("test"))
        assert result is True

    def test_acquire_exhausted(self) -> None:
        """Test acquire when at limit."""
        # Use all requests
        for _ in range(3):
            asyncio.run(self.limiter.acquire("test"))

        result = asyncio.run(self.limiter.acquire("test"))
        assert result is False

    def test_is_limited(self) -> None:
        """Test is_limited check."""
        assert self.limiter.is_limited("test") is False

        # Exhaust limit
        for _ in range(3):
            asyncio.run(self.limiter.acquire("test"))

        assert self.limiter.is_limited("test") is True

    def test_release(self) -> None:
        """Test releasing a slot."""
        # Use some requests
        for _ in range(2):
            asyncio.run(self.limiter.acquire("test"))

        # Release one
        self.limiter.release("test")

        # Should be able to acquire again
        result = asyncio.run(self.limiter.acquire("test"))
        assert result is True


class TestGlobalRateLimiter:
    """Tests for GlobalRateLimiter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.inner = TokenBucketRateLimiter()
        global_config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=60.0,
        )
        self.limiter = GlobalRateLimiter(self.inner, global_config)

    def test_acquire_allowed(self) -> None:
        """Test acquire when both limits allow."""
        result = asyncio.run(self.limiter.acquire("provider1"))
        assert result is True

    def test_global_limit_exhausted(self) -> None:
        """Test when global limit is exhausted."""
        # Exhaust global limit
        global_config = RateLimitConfig(
            requests_per_window=2,
            window_seconds=60.0,
        )
        inner = TokenBucketRateLimiter()
        limiter = GlobalRateLimiter(inner, global_config)

        asyncio.run(limiter.acquire("p1"))
        asyncio.run(limiter.acquire("p2"))

        # Global limit exhausted
        result = asyncio.run(limiter.acquire("p3"))
        assert result is False

    def test_inner_limit_exhausted(self) -> None:
        """Test when inner (provider) limit is exhausted."""
        # Exhaust inner limit for a provider
        self.limiter = GlobalRateLimiter(
            TokenBucketRateLimiter({"p1": RateLimitConfig(requests_per_window=1)}),
            RateLimitConfig(requests_per_window=100),
        )

        asyncio.run(self.limiter.acquire("p1"))
        result = asyncio.run(self.limiter.acquire("p1"))
        assert result is False

    def test_get_wait_time(self) -> None:
        """Test getting maximum wait time."""
        wait_time = self.limiter.get_wait_time("provider1")
        assert wait_time >= 0

    def test_is_limited(self) -> None:
        """Test is_limited check."""
        assert self.limiter.is_limited("provider1") is False


class TestRateLimitConfig:
    """Tests for RateLimitConfig validation."""

    def test_invalid_requests_per_window(self) -> None:
        """Test invalid requests_per_window raises error."""
        with pytest.raises(ValueError, match="at least 1"):
            RateLimitConfig(requests_per_window=0)

    def test_invalid_window_seconds(self) -> None:
        """Test invalid window_seconds raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            RateLimitConfig(window_seconds=0)
