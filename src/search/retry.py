"""Retry strategy implementation with various backoff algorithms."""

import random
from typing import Sequence

from .interfaces import RetryStrategy
from .models import RetryConfig, RetryMode


class ExponentialBackoffRetry(RetryStrategy):
    """Retry strategy with exponential backoff.

    Implements exponential backoff with optional jitter to prevent
    thundering herd problems.
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        """Initialize the retry strategy.

        Args:
            config: Retry configuration.
        """
        self._config = config or RetryConfig()

    def should_retry(
        self,
        attempt: int,
        error: Exception,
    ) -> bool:
        """Determine if request should be retried.

        Args:
            attempt: Current attempt number (1-based).
            error: The exception that occurred.

        Returns:
            True if should retry.
        """
        # Check if max attempts exceeded
        if attempt >= self._config.max_attempts:
            return False

        # Determine if error is retryable
        error_type = type(error)
        error_name = error_type.__name__.lower()

        # Non-retryable errors
        non_retryable = (
            "validationerror",
            "configurationerror",
            "queryerror",
        )
        if any(term in error_name for term in non_retryable):
            return False

        return True

    def get_backoff_delay(self, attempt: int) -> float:
        """Calculate backoff delay in seconds.

        Args:
            attempt: Current attempt number (1-based).

        Returns:
            Delay in seconds before next attempt.
        """
        delay = self._calculate_base_delay(attempt)

        if self._config.jitter:
            delay = self._add_jitter(delay)

        return min(delay, self._config.max_delay)

    def get_config(self) -> RetryConfig:
        """Get retry configuration.

        Returns:
            RetryConfig being used.
        """
        return self._config

    def _calculate_base_delay(self, attempt: int) -> float:
        """Calculate base delay based on retry mode.

        Args:
            attempt: Current attempt number.

        Returns:
            Base delay in seconds.
        """
        if self._config.mode == RetryMode.FIXED:
            return self._config.initial_delay

        elif self._config.mode == RetryMode.LINEAR:
            return self._config.initial_delay * attempt

        elif self._config.mode == RetryMode.EXPONENTIAL:
            return min(
                self._config.initial_delay * (self._config.exponential_base ** attempt),
                self._config.max_delay,
            )

        elif self._config.mode == RetryMode.JITTERED:
            return self._config.initial_delay * (self._config.exponential_base ** attempt)

        return self._config.initial_delay

    def _add_jitter(self, delay: float) -> float:
        """Add random jitter to delay.

        Args:
            delay: Base delay.

        Returns:
            Delay with jitter applied.
        """
        jitter_range = 0.5
        jitter_factor = 1.0 + random.uniform(-jitter_range, jitter_range)
        return delay * jitter_factor


class FixedRetryStrategy(RetryStrategy):
    """Retry strategy with fixed delay between retries."""

    def __init__(self, delay: float = 1.0, max_attempts: int = 3) -> None:
        """Initialize the fixed retry strategy.

        Args:
            delay: Fixed delay between retries.
            max_attempts: Maximum number of attempts.
        """
        self._delay = delay
        self._max_attempts = max_attempts

    def should_retry(
        self,
        attempt: int,
        error: Exception,
    ) -> bool:
        """Determine if request should be retried.

        Args:
            attempt: Current attempt number.
            error: The exception that occurred.

        Returns:
            True if should retry.
        """
        return attempt < self._max_attempts

    def get_backoff_delay(self, attempt: int) -> float:
        """Get fixed delay.

        Args:
            attempt: Current attempt number.

        Returns:
            Fixed delay in seconds.
        """
        return self._delay

    def get_config(self) -> RetryConfig:
        """Get retry configuration.

        Returns:
            RetryConfig being used.
        """
        return RetryConfig(
            max_attempts=self._max_attempts,
            initial_delay=self._delay,
            mode=RetryMode.FIXED,
        )


class LinearRetryStrategy(RetryStrategy):
    """Retry strategy with linear backoff."""

    def __init__(
        self,
        initial_delay: float = 1.0,
        increment: float = 1.0,
        max_attempts: int = 3,
    ) -> None:
        """Initialize the linear retry strategy.

        Args:
            initial_delay: Initial delay in seconds.
            increment: Increment for each retry.
            max_attempts: Maximum number of attempts.
        """
        self._initial_delay = initial_delay
        self._increment = increment
        self._max_attempts = max_attempts

    def should_retry(
        self,
        attempt: int,
        error: Exception,
    ) -> bool:
        """Determine if request should be retried.

        Args:
            attempt: Current attempt number.
            error: The exception that occurred.

        Returns:
            True if should retry.
        """
        return attempt < self._max_attempts

    def get_backoff_delay(self, attempt: int) -> float:
        """Calculate linear backoff delay.

        Args:
            attempt: Current attempt number.

        Returns:
            Delay in seconds.
        """
        return self._initial_delay + (attempt * self._increment)

    def get_config(self) -> RetryConfig:
        """Get retry configuration.

        Returns:
            RetryConfig being used.
        """
        return RetryConfig(
            max_attempts=self._max_attempts,
            initial_delay=self._initial_delay,
            mode=RetryMode.LINEAR,
        )


class JitteredRetryStrategy(RetryStrategy):
    """Retry strategy with jittered exponential backoff."""

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        max_attempts: int = 3,
    ) -> None:
        """Initialize the jittered retry strategy.

        Args:
            initial_delay: Initial delay in seconds.
            max_delay: Maximum delay cap.
            max_attempts: Maximum number of attempts.
        """
        self._initial_delay = initial_delay
        self._max_delay = max_delay
        self._max_attempts = max_attempts

    def should_retry(
        self,
        attempt: int,
        error: Exception,
    ) -> bool:
        """Determine if request should be retried.

        Args:
            attempt: Current attempt number.
            error: The exception that occurred.

        Returns:
            True if should retry.
        """
        return attempt < self._max_attempts

    def get_backoff_delay(self, attempt: int) -> float:
        """Calculate jittered exponential backoff delay.

        Args:
            attempt: Current attempt number.

        Returns:
            Jittered delay in seconds.
        """
        base_delay = min(
            self._initial_delay * (2 ** attempt),
            self._max_delay,
        )
        # Add full jitter
        jitter = random.uniform(0, base_delay)
        return base_delay + jitter

    def get_config(self) -> RetryConfig:
        """Get retry configuration.

        Returns:
            RetryConfig being used.
        """
        return RetryConfig(
            max_attempts=self._max_attempts,
            initial_delay=self._initial_delay,
            max_delay=self._max_delay,
            mode=RetryMode.JITTERED,
            jitter=True,
        )


class SelectiveRetryStrategy(RetryStrategy):
    """Retry strategy that only retries specific error types."""

    def __init__(
        self,
        retryable_errors: Sequence[type[Exception]],
        config: RetryConfig | None = None,
    ) -> None:
        """Initialize the selective retry strategy.

        Args:
            retryable_errors: Tuple of exception types to retry.
            config: Retry configuration.
        """
        self._retryable_errors = tuple(retryable_errors)
        self._config = config or RetryConfig()
        self._inner = ExponentialBackoffRetry(self._config)

    def should_retry(
        self,
        attempt: int,
        error: Exception,
    ) -> bool:
        """Determine if request should be retried.

        Args:
            attempt: Current attempt number.
            error: The exception that occurred.

        Returns:
            True if error is retryable and under max attempts.
        """
        # Check if error is in retryable list
        is_retryable = isinstance(error, self._retryable_errors)
        under_limit = attempt < self._config.max_attempts

        return is_retryable and under_limit

    def get_backoff_delay(self, attempt: int) -> float:
        """Get backoff delay from inner strategy.

        Args:
            attempt: Current attempt number.

        Returns:
            Delay in seconds.
        """
        return self._inner.get_backoff_delay(attempt)

    def get_config(self) -> RetryConfig:
        """Get retry configuration.

        Returns:
            RetryConfig being used.
        """
        return self._config
