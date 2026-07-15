"""Health checking implementation.

This module provides the ProviderHealthCheckerImpl class that
monitors and reports provider health.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .interfaces import Provider, ProviderHealthChecker
from .models import HealthStatus, ProviderHealthStatus


@dataclass
class HealthMetrics:
    """Metrics for health calculation."""

    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    avg_response_time_ms: float = 0.0
    last_check_time: datetime | None = None


class ProviderHealthCheckerImpl(ProviderHealthChecker):
    """Implementation of ProviderHealthChecker.

    This checker monitors provider health and calculates
    health status based on configurable thresholds.
    """

    def __init__(
        self,
        healthy_threshold: float = 0.9,
        degraded_threshold: float = 0.5,
        consecutive_failure_limit: int = 3,
        consecutive_success_limit: int = 2,
        slow_response_threshold_ms: float = 1000.0,
    ) -> None:
        """Initialize the health checker.

        Args:
            healthy_threshold: Minimum success rate for HEALTHY.
            degraded_threshold: Minimum success rate for DEGRADED.
            consecutive_failure_limit: Failures before UNHEALTHY.
            consecutive_success_limit: Successes before HEALTHY.
            slow_response_threshold_ms: Threshold for slow response.
        """
        self._healthy_threshold = healthy_threshold
        self._degraded_threshold = degraded_threshold
        self._consecutive_failure_limit = consecutive_failure_limit
        self._consecutive_success_limit = consecutive_success_limit
        self._slow_response_threshold_ms = slow_response_threshold_ms
        self._metrics: dict[str, HealthMetrics] = {}

    async def check(self, provider: Provider) -> ProviderHealthStatus:
        """Check provider health.

        Args:
            provider: Provider to check.

        Returns:
            Updated health status.
        """
        provider_name = provider.info.name
        metrics = self._get_metrics(provider_name)

        metrics.total_checks += 1
        metrics.last_check_time = datetime.now(timezone.utc)

        is_healthy = await self.health_check_provider(provider)
        response_time = await self._measure_response_time(provider)

        if response_time > self._slow_response_threshold_ms:
            is_healthy = False

        if is_healthy:
            metrics.successful_checks += 1
            metrics.consecutive_successes += 1
            metrics.consecutive_failures = 0
        else:
            metrics.failed_checks += 1
            metrics.consecutive_failures += 1
            metrics.consecutive_successes = 0

        if metrics.total_checks > 0:
            metrics.avg_response_time_ms = (
                (metrics.avg_response_time_ms * (metrics.total_checks - 1) + response_time)
                / metrics.total_checks
            )

        status = self._calculate_status(metrics)

        return ProviderHealthStatus(
            provider_name=provider_name,
            status=status,
            is_available=status != HealthStatus.UNHEALTHY,
            consecutive_failures=metrics.consecutive_failures,
            consecutive_successes=metrics.consecutive_successes,
            last_check=metrics.last_check_time,
            last_success=datetime.now(timezone.utc) if is_healthy else None,
            last_failure=datetime.now(timezone.utc) if not is_healthy else None,
            avg_response_time_ms=metrics.avg_response_time_ms,
            success_rate=self._calculate_success_rate(metrics),
        )

    async def check_all(
        self,
        providers: tuple[Provider, ...],
    ) -> dict[str, ProviderHealthStatus]:
        """Check health of multiple providers.

        Args:
            providers: Providers to check.

        Returns:
            Map of provider name to health status.
        """
        results: dict[str, ProviderHealthStatus] = {}
        for provider in providers:
            try:
                results[provider.info.name] = await self.check(provider)
            except Exception:
                results[provider.info.name] = ProviderHealthStatus(
                    provider_name=provider.info.name,
                    status=HealthStatus.UNKNOWN,
                    is_available=False,
                )
        return results

    def is_healthy(self, status: ProviderHealthStatus) -> bool:
        """Check if health status indicates healthy.

        Args:
            status: Health status to check.

        Returns:
            True if provider is healthy.
        """
        return status.status == HealthStatus.HEALTHY and status.is_available

    def should_retry(self, status: ProviderHealthStatus) -> bool:
        """Check if provider should be retried.

        Args:
            status: Health status to check.

        Returns:
            True if retry should be attempted.
        """
        if status.status == HealthStatus.UNHEALTHY:
            if status.consecutive_failures >= self._consecutive_failure_limit:
                return False
        if not status.is_available:
            return False
        return True

    def get_metrics(self, provider_name: str) -> HealthMetrics | None:
        """Get health metrics for a provider.

        Args:
            provider_name: Provider name.

        Returns:
            HealthMetrics if available, None otherwise.
        """
        return self._metrics.get(provider_name)

    def reset_metrics(self, provider_name: str | None = None) -> None:
        """Reset health metrics.

        Args:
            provider_name: Specific provider to reset, or None for all.
        """
        if provider_name:
            self._metrics.pop(provider_name, None)
        else:
            self._metrics.clear()

    def _get_metrics(self, provider_name: str) -> HealthMetrics:
        """Get or create metrics for a provider.

        Args:
            provider_name: Provider name.

        Returns:
            HealthMetrics for the provider.
        """
        if provider_name not in self._metrics:
            self._metrics[provider_name] = HealthMetrics()
        return self._metrics[provider_name]

    async def health_check_provider(self, provider: Provider) -> bool:
        """Perform actual health check on provider.

        Args:
            provider: Provider to check.

        Returns:
            True if health check passed.
        """
        try:
            return await provider.health_check()
        except Exception:
            return False

    async def _measure_response_time(self, provider: Provider) -> float:
        """Measure provider response time.

        Args:
            provider: Provider to measure.

        Returns:
            Response time in milliseconds.
        """
        return 0.0

    def _calculate_status(self, metrics: HealthMetrics) -> HealthStatus:
        """Calculate health status from metrics.

        Args:
            metrics: Health metrics.

        Returns:
            Calculated HealthStatus.
        """
        if metrics.total_checks == 0:
            return HealthStatus.UNKNOWN

        if metrics.consecutive_failures >= self._consecutive_failure_limit:
            return HealthStatus.UNHEALTHY

        success_rate = self._calculate_success_rate(metrics)

        if success_rate >= self._healthy_threshold:
            return HealthStatus.HEALTHY

        if success_rate >= self._degraded_threshold:
            return HealthStatus.DEGRADED

        return HealthStatus.UNHEALTHY

    def _calculate_success_rate(self, metrics: HealthMetrics) -> float:
        """Calculate success rate.

        Args:
            metrics: Health metrics.

        Returns:
            Success rate as a fraction.
        """
        if metrics.total_checks == 0:
            return 0.0
        return metrics.successful_checks / metrics.total_checks


class AggregatedHealthChecker(ProviderHealthChecker):
    """Aggregates health from multiple health checkers.

    This combines multiple health checker results to provide
    an overall health assessment.
    """

    def __init__(self, checkers: tuple[ProviderHealthChecker, ...]) -> None:
        """Initialize with multiple checkers.

        Args:
            checkers: Tuple of health checkers to aggregate.
        """
        self._checkers = checkers

    async def check(self, provider: Provider) -> ProviderHealthStatus:
        """Check using all registered checkers.

        Args:
            provider: Provider to check.

        Returns:
            Aggregated health status.
        """
        if not self._checkers:
            return ProviderHealthStatus(
                provider_name=provider.info.name,
                status=HealthStatus.UNKNOWN,
            )

        results: list[ProviderHealthStatus] = []
        for checker in self._checkers:
            result = await checker.check(provider)
            results.append(result)

        return self._aggregate_results(results)

    async def check_all(
        self,
        providers: tuple[Provider, ...],
    ) -> dict[str, ProviderHealthStatus]:
        """Check all providers using all checkers.

        Args:
            providers: Providers to check.

        Returns:
            Map of provider name to aggregated health status.
        """
        results: dict[str, ProviderHealthStatus] = {}
        for provider in providers:
            results[provider.info.name] = await self.check(provider)
        return results

    def is_healthy(self, status: ProviderHealthStatus) -> bool:
        """Check if aggregated status is healthy.

        Args:
            status: Aggregated status to check.

        Returns:
            True if majority of checkers report healthy.
        """
        return status.status == HealthStatus.HEALTHY

    def should_retry(self, status: ProviderHealthStatus) -> bool:
        """Check if should retry based on aggregated status.

        Args:
            status: Aggregated status to check.

        Returns:
            True if any checker allows retry.
        """
        return status.is_available

    def _aggregate_results(
        self,
        results: list[ProviderHealthStatus],
    ) -> ProviderHealthStatus:
        """Aggregate multiple health results.

        Args:
            results: List of health statuses.

        Returns:
            Aggregated health status.
        """
        if not results:
            return ProviderHealthStatus(
                provider_name="unknown",
                status=HealthStatus.UNKNOWN,
            )

        if len(results) == 1:
            return results[0]

        healthy_count = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for r in results if r.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)

        if healthy_count > len(results) / 2:
            status = HealthStatus.HEALTHY
        elif degraded_count > len(results) / 2:
            status = HealthStatus.DEGRADED
        elif unhealthy_count > len(results) / 2:
            status = HealthStatus.UNHEALTHY
        else:
            status = HealthStatus.DEGRADED

        return ProviderHealthStatus(
            provider_name=results[0].provider_name,
            status=status,
            is_available=any(r.is_available for r in results),
            avg_response_time_ms=sum(r.avg_response_time_ms for r in results) / len(results),
        )
