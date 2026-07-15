"""Rate limiting implementation.

This module provides the ProviderRateLimiterImpl class that
handles provider rate limiting abstraction.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from .interfaces import ProviderRateLimiter
from .models import (
    LimitScope,
    RateLimitInfo,
    RateLimitType,
)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting.

    Attributes:
        tokens: Current number of tokens available.
        max_tokens: Maximum token capacity.
        refill_rate: Tokens added per second.
        last_refill: Timestamp of last refill.
        backoff_until: Optional backoff deadline.
    """

    tokens: float
    max_tokens: float
    refill_rate: float
    last_refill: datetime
    backoff_until: datetime | None = None

    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            True if tokens were consumed.
        """
        self._refill()

        if self.backoff_until and datetime.now(timezone.utc) < self.backoff_until:
            return False

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = datetime.now(timezone.utc)
        elapsed = (now - self.last_refill).total_seconds()
        tokens_to_add = elapsed * self.refill_rate

        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now

    def set_backoff(self, duration_seconds: float) -> None:
        """Set backoff period.

        Args:
            duration_seconds: Duration in seconds.
        """
        self.backoff_until = datetime.now(timezone.utc) + timedelta(
            seconds=duration_seconds
        )

    def clear_backoff(self) -> None:
        """Clear backoff period."""
        self.backoff_until = None

    def is_in_backoff(self) -> bool:
        """Check if in backoff period.

        Returns:
            True if in backoff.
        """
        if not self.backoff_until:
            return False
        return datetime.now(timezone.utc) < self.backoff_until

    def get_wait_time(self) -> float:
        """Get time to wait for a token.

        Returns:
            Seconds to wait, 0 if tokens available.
        """
        self._refill()

        if self.tokens >= 1.0:
            return 0.0

        if self.is_in_backoff() and self.backoff_until:
            delta = self.backoff_until - datetime.now(timezone.utc)
            return max(0.0, delta.total_seconds())

        tokens_needed = 1.0 - self.tokens
        return tokens_needed / self.refill_rate

    def get_info(self, name: str, limit_type: RateLimitType) -> RateLimitInfo:
        """Get rate limit info.

        Args:
            name: Provider name.
            limit_type: Type of rate limit.

        Returns:
            RateLimitInfo with current state.
        """
        self._refill()

        return RateLimitInfo(
            requests_remaining=int(self.tokens),
            requests_limit=int(self.max_tokens),
            reset_at=self.last_refill + timedelta(seconds=self.max_tokens / self.refill_rate),
            backoff_until=self.backoff_until,
            limit_type=limit_type,
            scope=LimitScope.PER_KEY,
            retry_after_seconds=self.get_wait_time() if self.tokens < 1.0 else None,
        )


@dataclass
class SlidingWindow:
    """Sliding window rate limiter.

    Attributes:
        requests: List of request timestamps.
        window_seconds: Time window in seconds.
        max_requests: Maximum requests in window.
    """

    requests: list[datetime] = field(default_factory=list)
    window_seconds: float = 60.0
    max_requests: int = 60
    backoff_until: datetime | None = None

    def try_request(self) -> bool:
        """Try to make a request.

        Returns:
            True if request is allowed.
        """
        if self.backoff_until and datetime.now(timezone.utc) < self.backoff_until:
            return False

        self._clean_old_requests()
        now = datetime.now(timezone.utc)

        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True

        return False

    def _clean_old_requests(self) -> None:
        """Remove requests outside the window."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)
        self.requests = [r for r in self.requests if r > cutoff]

    def set_backoff(self, duration_seconds: float) -> None:
        """Set backoff period.

        Args:
            duration_seconds: Duration in seconds.
        """
        self.backoff_until = datetime.now(timezone.utc) + timedelta(
            seconds=duration_seconds
        )

    def clear_backoff(self) -> None:
        """Clear backoff period."""
        self.backoff_until = None

    def is_in_backoff(self) -> bool:
        """Check if in backoff period.

        Returns:
            True if in backoff.
        """
        if not self.backoff_until:
            return False
        return datetime.now(timezone.utc) < self.backoff_until

    def get_wait_time(self) -> float:
        """Get time to wait.

        Returns:
            Seconds to wait.
        """
        if self.is_in_backoff() and self.backoff_until:
            delta = self.backoff_until - datetime.now(timezone.utc)
            return max(0.0, delta.total_seconds())

        self._clean_old_requests()
        if len(self.requests) < self.max_requests:
            return 0.0

        oldest = min(self.requests)
        next_available = oldest + timedelta(seconds=self.window_seconds)
        delta = next_available - datetime.now(timezone.utc)
        return max(0.0, delta.total_seconds())

    def get_info(self, name: str, limit_type: RateLimitType) -> RateLimitInfo:
        """Get rate limit info.

        Args:
            name: Provider name.
            limit_type: Type of rate limit.

        Returns:
            RateLimitInfo with current state.
        """
        self._clean_old_requests()
        now = datetime.now(timezone.utc)
        oldest = min(self.requests) if self.requests else now

        return RateLimitInfo(
            requests_remaining=max(0, self.max_requests - len(self.requests)),
            requests_limit=self.max_requests,
            reset_at=oldest + timedelta(seconds=self.window_seconds),
            backoff_until=self.backoff_until,
            limit_type=limit_type,
            scope=LimitScope.PER_KEY,
            retry_after_seconds=self.get_wait_time(),
        )


@dataclass
class FixedWindow:
    """Fixed window rate limiter.

    Attributes:
        current_count: Current request count.
        window_start: Start of current window.
        window_seconds: Window duration.
        max_requests: Maximum requests per window.
    """

    current_count: int = 0
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    window_seconds: float = 60.0
    max_requests: int = 60
    backoff_until: datetime | None = None

    def try_request(self) -> bool:
        """Try to make a request.

        Returns:
            True if request is allowed.
        """
        if self.backoff_until and datetime.now(timezone.utc) < self.backoff_until:
            return False

        self._check_window()
        now = datetime.now(timezone.utc)

        if self.current_count < self.max_requests:
            self.current_count += 1
            return True

        return False

    def _check_window(self) -> None:
        """Check and reset window if expired."""
        now = datetime.now(timezone.utc)
        window_end = self.window_start + timedelta(seconds=self.window_seconds)

        if now >= window_end:
            self.current_count = 0
            self.window_start = now

    def set_backoff(self, duration_seconds: float) -> None:
        """Set backoff period.

        Args:
            duration_seconds: Duration in seconds.
        """
        self.backoff_until = datetime.now(timezone.utc) + timedelta(
            seconds=duration_seconds
        )

    def clear_backoff(self) -> None:
        """Clear backoff period."""
        self.backoff_until = None

    def is_in_backoff(self) -> bool:
        """Check if in backoff period.

        Returns:
            True if in backoff.
        """
        if not self.backoff_until:
            return False
        return datetime.now(timezone.utc) < self.backoff_until

    def get_wait_time(self) -> float:
        """Get time to wait.

        Returns:
            Seconds to wait.
        """
        if self.is_in_backoff() and self.backoff_until:
            delta = self.backoff_until - datetime.now(timezone.utc)
            return max(0.0, delta.total_seconds())

        self._check_window()
        if self.current_count < self.max_requests:
            return 0.0

        window_end = self.window_start + timedelta(seconds=self.window_seconds)
        delta = window_end - datetime.now(timezone.utc)
        return max(0.0, delta.total_seconds())

    def get_info(self, name: str, limit_type: RateLimitType) -> RateLimitInfo:
        """Get rate limit info.

        Args:
            name: Provider name.
            limit_type: Type of rate limit.

        Returns:
            RateLimitInfo with current state.
        """
        self._check_window()

        return RateLimitInfo(
            requests_remaining=max(0, self.max_requests - self.current_count),
            requests_limit=self.max_requests,
            reset_at=self.window_start + timedelta(seconds=self.window_seconds),
            backoff_until=self.backoff_until,
            limit_type=limit_type,
            scope=LimitScope.PER_KEY,
            retry_after_seconds=self.get_wait_time(),
        )


class ProviderRateLimiterImpl(ProviderRateLimiter):
    """Implementation of ProviderRateLimiter.

    This rate limiter supports multiple rate limiting algorithms
    and provider-specific configurations.
    """

    def __init__(
        self,
        default_requests_per_minute: int = 60,
        default_burst: int = 10,
        default_type: RateLimitType = RateLimitType.TOKEN_BUCKET,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            default_requests_per_minute: Default rate limit.
            default_burst: Default burst capacity.
            default_type: Default rate limit algorithm.
        """
        self._default_requests_per_minute = default_requests_per_minute
        self._default_burst = default_burst
        self._default_type = default_type
        self._token_buckets: dict[str, TokenBucket] = {}
        self._sliding_windows: dict[str, SlidingWindow] = {}
        self._fixed_windows: dict[str, FixedWindow] = {}
        self._limiters: dict[str, RateLimitType] = {}

    async def acquire(
        self,
        provider_name: str,
        tokens: int = 1,
    ) -> bool:
        """Acquire rate limit tokens.

        Args:
            provider_name: Provider to acquire tokens for.
            tokens: Number of tokens to acquire.

        Returns:
            True if tokens acquired.
        """
        limiter_type = self._limiters.get(provider_name, self._default_type)

        if limiter_type == RateLimitType.TOKEN_BUCKET:
            bucket = self._get_or_create_token_bucket(provider_name)
            return bucket.consume(float(tokens))

        elif limiter_type == RateLimitType.SLIDING_WINDOW:
            window = self._get_or_create_sliding_window(provider_name)
            return window.try_request()

        elif limiter_type == RateLimitType.FIXED_WINDOW:
            window = self._get_or_create_fixed_window(provider_name)
            return window.try_request()

        return True

    def release(
        self,
        provider_name: str,
        tokens: int = 1,
    ) -> None:
        """Release rate limit tokens.

        Args:
            provider_name: Provider to release tokens for.
            tokens: Number of tokens to release.
        """
        pass

    def get_wait_time(self, provider_name: str) -> float:
        """Get wait time before next request.

        Args:
            provider_name: Provider to check.

        Returns:
            Seconds to wait.
        """
        limiter_type = self._limiters.get(provider_name, self._default_type)

        if limiter_type == RateLimitType.TOKEN_BUCKET:
            bucket = self._token_buckets.get(provider_name)
            if bucket:
                return bucket.get_wait_time()

        elif limiter_type == RateLimitType.SLIDING_WINDOW:
            window = self._sliding_windows.get(provider_name)
            if window:
                return window.get_wait_time()

        elif limiter_type == RateLimitType.FIXED_WINDOW:
            window = self._fixed_windows.get(provider_name)
            if window:
                return window.get_wait_time()

        return 0.0

    def get_info(self, provider_name: str) -> RateLimitInfo:
        """Get rate limit information.

        Args:
            provider_name: Provider to check.

        Returns:
            Current rate limit info.
        """
        limiter_type = self._limiters.get(provider_name, self._default_type)

        if limiter_type == RateLimitType.TOKEN_BUCKET:
            bucket = self._get_or_create_token_bucket(provider_name)
            return bucket.get_info(provider_name, limiter_type)

        elif limiter_type == RateLimitType.SLIDING_WINDOW:
            window = self._get_or_create_sliding_window(provider_name)
            return window.get_info(provider_name, limiter_type)

        elif limiter_type == RateLimitType.FIXED_WINDOW:
            window = self._get_or_create_fixed_window(provider_name)
            return window.get_info(provider_name, limiter_type)

        return RateLimitInfo(
            requests_remaining=self._default_requests_per_minute,
            requests_limit=self._default_requests_per_minute,
            reset_at=datetime.now(timezone.utc),
            limit_type=limiter_type,
        )

    def is_limited(self, provider_name: str) -> bool:
        """Check if provider is rate limited.

        Args:
            provider_name: Provider to check.

        Returns:
            True if rate limited.
        """
        return self.get_wait_time(provider_name) > 0

    def apply_backoff(
        self,
        provider_name: str,
        duration_seconds: float,
    ) -> None:
        """Apply backoff to a provider.

        Args:
            provider_name: Provider to backoff.
            duration_seconds: Duration in seconds.
        """
        limiter_type = self._limiters.get(provider_name, self._default_type)

        if limiter_type == RateLimitType.TOKEN_BUCKET:
            bucket = self._token_buckets.get(provider_name)
            if bucket:
                bucket.set_backoff(duration_seconds)

        elif limiter_type == RateLimitType.SLIDING_WINDOW:
            window = self._sliding_windows.get(provider_name)
            if window:
                window.set_backoff(duration_seconds)

        elif limiter_type == RateLimitType.FIXED_WINDOW:
            window = self._fixed_windows.get(provider_name)
            if window:
                window.set_backoff(duration_seconds)

    def set_provider_type(
        self,
        provider_name: str,
        limiter_type: RateLimitType,
    ) -> None:
        """Set rate limiter type for a provider.

        Args:
            provider_name: Provider name.
            limiter_type: Type of rate limiter to use.
        """
        self._limiters[provider_name] = limiter_type

    def reset(self, provider_name: str | None = None) -> None:
        """Reset rate limiter state.

        Args:
            provider_name: Provider to reset, or None for all.
        """
        if provider_name:
            self._token_buckets.pop(provider_name, None)
            self._sliding_windows.pop(provider_name, None)
            self._fixed_windows.pop(provider_name, None)
        else:
            self._token_buckets.clear()
            self._sliding_windows.clear()
            self._fixed_windows.clear()

    def _get_or_create_token_bucket(self, provider_name: str) -> TokenBucket:
        """Get or create a token bucket.

        Args:
            provider_name: Provider name.

        Returns:
            TokenBucket instance.
        """
        if provider_name not in self._token_buckets:
            refill_rate = self._default_requests_per_minute / 60.0
            self._token_buckets[provider_name] = TokenBucket(
                tokens=float(self._default_burst),
                max_tokens=float(self._default_burst),
                refill_rate=refill_rate,
                last_refill=datetime.now(timezone.utc),
            )
        return self._token_buckets[provider_name]

    def _get_or_create_sliding_window(self, provider_name: str) -> SlidingWindow:
        """Get or create a sliding window.

        Args:
            provider_name: Provider name.

        Returns:
            SlidingWindow instance.
        """
        if provider_name not in self._sliding_windows:
            self._sliding_windows[provider_name] = SlidingWindow(
                max_requests=self._default_requests_per_minute,
                window_seconds=60.0,
            )
        return self._sliding_windows[provider_name]

    def _get_or_create_fixed_window(self, provider_name: str) -> FixedWindow:
        """Get or create a fixed window.

        Args:
            provider_name: Provider name.

        Returns:
            FixedWindow instance.
        """
        if provider_name not in self._fixed_windows:
            self._fixed_windows[provider_name] = FixedWindow(
                max_requests=self._default_requests_per_minute,
                window_seconds=60.0,
            )
        return self._fixed_windows[provider_name]


class GlobalRateLimiter(ProviderRateLimiter):
    """Global rate limiter across all providers."""

    def __init__(self, inner: ProviderRateLimiter) -> None:
        """Initialize with inner rate limiter.

        Args:
            inner: Inner rate limiter to use.
        """
        self._inner = inner
        self._global_bucket = TokenBucket(
            tokens=100,
            max_tokens=100,
            refill_rate=100 / 60.0,
            last_refill=datetime.now(timezone.utc),
        )

    async def acquire(self, provider_name: str, tokens: int = 1) -> bool:
        """Acquire from global and provider limiters.

        Args:
            provider_name: Provider name.
            tokens: Number of tokens.

        Returns:
            True if both limits allow.
        """
        if not self._global_bucket.consume(float(tokens)):
            return False

        return await self._inner.acquire(provider_name, tokens)

    def release(self, provider_name: str, tokens: int = 1) -> None:
        """Release tokens.

        Args:
            provider_name: Provider name.
            tokens: Number of tokens.
        """
        self._inner.release(provider_name, tokens)

    def get_wait_time(self, provider_name: str) -> float:
        """Get maximum wait time.

        Args:
            provider_name: Provider name.

        Returns:
            Maximum wait time from all limiters.
        """
        inner_wait = self._inner.get_wait_time(provider_name)
        global_wait = self._global_bucket.get_wait_time()
        return max(inner_wait, global_wait)

    def get_info(self, provider_name: str) -> RateLimitInfo:
        """Get rate limit info.

        Args:
            provider_name: Provider name.

        Returns:
            Combined rate limit info.
        """
        inner_info = self._inner.get_info(provider_name)
        global_info = self._global_bucket.get_info(provider_name, RateLimitType.TOKEN_BUCKET)

        return RateLimitInfo(
            requests_remaining=min(
                inner_info.requests_remaining,
                int(self._global_bucket.tokens),
            ),
            requests_limit=min(
                inner_info.requests_limit,
                int(self._global_bucket.max_tokens),
            ),
            reset_at=inner_info.reset_at,
            backoff_until=inner_info.backoff_until or global_info.backoff_until,
            limit_type=RateLimitType.TOKEN_BUCKET,
            scope=LimitScope.GLOBAL,
            retry_after_seconds=self.get_wait_time(provider_name),
        )

    def is_limited(self, provider_name: str) -> bool:
        """Check if limited.

        Args:
            provider_name: Provider name.

        Returns:
            True if any limiter is limited.
        """
        return (
            self._global_bucket.tokens < 1.0
            or self._inner.is_limited(provider_name)
        )
