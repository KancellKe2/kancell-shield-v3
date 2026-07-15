"""Rate limiter implementation using token bucket algorithm."""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from .interfaces import RateLimiter as IRateLimiter
from .models import RateLimitConfig, RateLimitInfo


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    tokens: float
    max_tokens: float
    refill_rate: float
    last_refill: float
    backoff_until: float | None = None

    def consume(self, tokens: float = 1.0) -> bool:
        """Consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            True if tokens were consumed, False otherwise.
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill

        # Calculate tokens to add
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now

    def is_in_backoff(self) -> bool:
        """Check if in backoff period."""
        if self.backoff_until is None:
            return False
        return time.monotonic() < self.backoff_until

    def set_backoff(self, duration: float) -> None:
        """Set backoff period.

        Args:
            duration: Duration in seconds.
        """
        self.backoff_until = time.monotonic() + duration

    def clear_backoff(self) -> None:
        """Clear backoff period."""
        self.backoff_until = None

    def get_wait_time(self) -> float:
        """Get time to wait for a token.

        Returns:
            Seconds to wait, 0 if tokens available.
        """
        self._refill()

        if self.tokens >= 1.0:
            return 0.0

        tokens_needed = 1.0 - self.tokens
        return tokens_needed / self.refill_rate


class TokenBucketRateLimiter(IRateLimiter):
    """Rate limiter implementation using token bucket algorithm.

    Each provider has its own token bucket that refills at a configured rate.
    Requests consume tokens, and if no tokens are available, the request
    must wait for the bucket to refill.
    """

    def __init__(
        self,
        configs: dict[str, RateLimitConfig] | None = None,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            configs: Provider-specific rate limit configurations.
        """
        self._buckets: dict[str, TokenBucket] = {}
        self._configs: dict[str, RateLimitConfig] = configs or {}

    async def acquire(self, provider: str) -> bool:
        """Acquire permission to make a request.

        Args:
            provider: Provider identifier.

        Returns:
            True if permission granted.
        """
        bucket = self._get_or_create_bucket(provider)

        # Check if in backoff
        if bucket.is_in_backoff():
            return False

        return bucket.consume()

    def release(self, provider: str) -> None:
        """Release rate limit token (no-op for token bucket).

        Args:
            provider: Provider identifier.
        """
        # Token bucket doesn't need explicit release
        pass

    def get_wait_time(self, provider: str) -> float:
        """Get estimated wait time in seconds.

        Args:
            provider: Provider identifier.

        Returns:
            Seconds to wait before next request.
        """
        bucket = self._get_or_create_bucket(provider)
        return bucket.get_wait_time()

    def is_limited(self, provider: str) -> bool:
        """Check if provider is rate limited.

        Args:
            provider: Provider identifier.

        Returns:
            True if rate limited.
        """
        bucket = self._get_or_create_bucket(provider)
        return bucket.is_in_backoff() or bucket.tokens < 1.0

    def get_rate_limit_info(self, provider: str) -> RateLimitInfo:
        """Get current rate limit state for a provider.

        Args:
            provider: Provider identifier.

        Returns:
            RateLimitInfo with current state.
        """
        bucket = self._get_or_create_bucket(provider)
        config = self._configs.get(provider, RateLimitConfig())

        now = datetime.now(timezone.utc)
        reset_at = datetime.fromtimestamp(
            time.time() + bucket.get_wait_time(),
            tz=timezone.utc,
        )

        backoff_until = None
        if bucket.backoff_until is not None:
            backoff_until = datetime.fromtimestamp(
                bucket.backoff_until,
                tz=timezone.utc,
            )

        return RateLimitInfo(
            provider_name=provider,
            requests_remaining=int(bucket.tokens),
            reset_at=reset_at,
            backoff_until=backoff_until,
            current_backoff=bucket.get_wait_time(),
        )

    def apply_backoff(self, provider: str, multiplier: float = 2.0) -> None:
        """Apply backoff to a provider.

        Args:
            provider: Provider identifier.
            multiplier: Backoff multiplier.
        """
        bucket = self._get_or_create_bucket(provider)
        config = self._configs.get(provider, RateLimitConfig())

        current_wait = bucket.get_wait_time()
        new_wait = min(
            current_wait * multiplier,
            config.max_backoff_seconds,
        )
        bucket.set_backoff(new_wait)

    def reset_backoff(self, provider: str) -> None:
        """Reset backoff for a provider.

        Args:
            provider: Provider identifier.
        """
        if provider in self._buckets:
            self._buckets[provider].clear_backoff()

    def reset_all(self) -> None:
        """Reset all rate limiters."""
        for bucket in self._buckets.values():
            bucket.clear_backoff()

    def _get_or_create_bucket(self, provider: str) -> TokenBucket:
        """Get or create a token bucket for a provider.

        Args:
            provider: Provider identifier.

        Returns:
            TokenBucket for the provider.
        """
        if provider not in self._buckets:
            config = self._configs.get(provider, RateLimitConfig())
            self._buckets[provider] = TokenBucket(
                tokens=float(config.requests_per_window),
                max_tokens=float(config.requests_per_window),
                refill_rate=float(config.requests_per_window) / config.window_seconds,
                last_refill=time.monotonic(),
            )
        return self._buckets[provider]


class SlidingWindowRateLimiter(IRateLimiter):
    """Rate limiter using sliding window algorithm.

    Tracks requests in a sliding time window and prevents exceeding
    the configured request limit within that window.
    """

    def __init__(
        self,
        configs: dict[str, RateLimitConfig] | None = None,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            configs: Provider-specific rate limit configurations.
        """
        self._timestamps: dict[str, list[float]] = {}
        self._configs: dict[str, RateLimitConfig] = configs or {}

    async def acquire(self, provider: str) -> bool:
        """Acquire permission to make a request.

        Args:
            provider: Provider identifier.

        Returns:
            True if permission granted.
        """
        config = self._get_config(provider)
        now = time.time()

        if provider not in self._timestamps:
            self._timestamps[provider] = []

        # Remove timestamps outside the window
        window_start = now - config.window_seconds
        self._timestamps[provider] = [
            ts for ts in self._timestamps[provider] if ts > window_start
        ]

        # Check if under limit
        if len(self._timestamps[provider]) < config.requests_per_window:
            self._timestamps[provider].append(now)
            return True

        return False

    def release(self, provider: str) -> None:
        """Remove the most recent request timestamp.

        Args:
            provider: Provider identifier.
        """
        if provider in self._timestamps and self._timestamps[provider]:
            self._timestamps[provider].pop()

    def get_wait_time(self, provider: str) -> float:
        """Get estimated wait time in seconds.

        Args:
            provider: Provider identifier.

        Returns:
            Seconds to wait before next request.
        """
        config = self._get_config(provider)
        now = time.time()

        if provider not in self._timestamps:
            return 0.0

        # Remove old timestamps
        window_start = now - config.window_seconds
        self._timestamps[provider] = [
            ts for ts in self._timestamps[provider] if ts > window_start
        ]

        if len(self._timestamps[provider]) < config.requests_per_window:
            return 0.0

        # Calculate wait time for oldest request to expire
        oldest = min(self._timestamps[provider])
        return max(0.0, (oldest + config.window_seconds) - now)

    def is_limited(self, provider: str) -> bool:
        """Check if provider is rate limited.

        Args:
            provider: Provider identifier.

        Returns:
            True if rate limited.
        """
        return self.get_wait_time(provider) > 0

    def _get_config(self, provider: str) -> RateLimitConfig:
        """Get config for a provider.

        Args:
            provider: Provider identifier.

        Returns:
            RateLimitConfig for the provider.
        """
        return self._configs.get(provider, RateLimitConfig())


class GlobalRateLimiter(IRateLimiter):
    """Global rate limiter that wraps another limiter.

    Adds a global rate limit across all providers in addition
    to per-provider limits.
    """

    def __init__(
        self,
        inner: IRateLimiter,
        global_config: RateLimitConfig,
    ) -> None:
        """Initialize the global rate limiter.

        Args:
            inner: Inner rate limiter for per-provider limits.
            global_config: Global rate limit configuration.
        """
        self._inner = inner
        self._global_bucket = TokenBucket(
            tokens=float(global_config.requests_per_window),
            max_tokens=float(global_config.requests_per_window),
            refill_rate=float(global_config.requests_per_window) / global_config.window_seconds,
            last_refill=time.monotonic(),
        )

    async def acquire(self, provider: str) -> bool:
        """Acquire permission to make a request.

        Args:
            provider: Provider identifier.

        Returns:
            True if permission granted by both global and inner limiters.
        """
        # Check global limit first
        if not self._global_bucket.consume():
            return False

        # Check provider-specific limit
        return await self._inner.acquire(provider)

    def release(self, provider: str) -> None:
        """Release rate limit tokens.

        Args:
            provider: Provider identifier.
        """
        self._inner.release(provider)

    def get_wait_time(self, provider: str) -> float:
        """Get estimated wait time in seconds.

        Args:
            provider: Provider identifier.

        Returns:
            Maximum wait time from global and inner limiters.
        """
        global_wait = self._global_bucket.get_wait_time()
        inner_wait = self._inner.get_wait_time(provider)
        return max(global_wait, inner_wait)

    def is_limited(self, provider: str) -> bool:
        """Check if globally rate limited.

        Args:
            provider: Provider identifier.

        Returns:
            True if globally rate limited.
        """
        return self._global_bucket.tokens < 1.0 or self._inner.is_limited(provider)
