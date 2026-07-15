"""Metrics tracking for discovery pipeline.

This module provides metrics collection and reporting
for candidate processing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from .models import CandidateStatus


@dataclass
class MetricsSnapshot:
    """Snapshot of metrics at a point in time."""

    timestamp: datetime
    processed_candidates: int
    filtered_candidates: int
    accepted_candidates: int
    rejected_candidates: int
    average_processing_time_ms: float
    queue_size: int
    throughput_per_second: float


@dataclass
class StageMetrics:
    """Metrics for a specific pipeline stage."""

    stage_name: str
    executions: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    errors: int = 0

    @property
    def average_duration_ms(self) -> float:
        """Get average duration."""
        if self.executions == 0:
            return 0.0
        return self.total_duration_ms / self.executions


class MetricsCollector:
    """Collector for pipeline metrics.

    Tracks processed candidates, timing, and throughput.
    """

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._start_time: datetime | None = None
        self._processed = 0
        self._filtered = 0
        self._accepted = 0
        self._rejected = 0
        self._processing_times: list[float] = []
        self._stage_metrics: dict[str, StageMetrics] = {}
        self._listeners: list[Callable[[MetricsSnapshot], None]] = []

    def start(self) -> None:
        """Start metrics collection."""
        self._start_time = datetime.now(timezone.utc)

    def stop(self) -> None:
        """Stop metrics collection."""
        pass  # Collection continues but time window is fixed

    def reset(self) -> None:
        """Reset all metrics."""
        self._start_time = None
        self._processed = 0
        self._filtered = 0
        self._accepted = 0
        self._rejected = 0
        self._processing_times.clear()
        self._stage_metrics.clear()

    def record_processed(
        self,
        count: int = 1,
        processing_time_ms: float = 0.0,
    ) -> None:
        """Record processed candidates.

        Args:
            count: Number of candidates processed.
            processing_time_ms: Total processing time.
        """
        self._processed += count
        if processing_time_ms > 0:
            self._processing_times.append(processing_time_ms)

    def record_filtered(self, count: int = 1) -> None:
        """Record filtered candidates.

        Args:
            count: Number of candidates filtered.
        """
        self._filtered += count

    def record_accepted(self, count: int = 1) -> None:
        """Record accepted candidates.

        Args:
            count: Number of candidates accepted.
        """
        self._accepted += count

    def record_rejected(self, count: int = 1) -> None:
        """Record rejected candidates.

        Args:
            count: Number of candidates rejected.
        """
        self._rejected += count

    def record_candidate_status(self, status: CandidateStatus) -> None:
        """Record candidate by status.

        Args:
            status: Candidate status.
        """
        if status == CandidateStatus.FILTERED:
            self.record_filtered()
        elif status == CandidateStatus.REJECTED:
            self.record_rejected()
        elif status in (CandidateStatus.SCORED, CandidateStatus.VALIDATED, CandidateStatus.DISCOVERED):
            self.record_accepted()

    def record_stage_timing(
        self,
        stage_name: str,
        duration_ms: float,
        error: bool = False,
    ) -> None:
        """Record stage execution timing.

        Args:
            stage_name: Name of the stage.
            duration_ms: Duration in milliseconds.
            error: Whether an error occurred.
        """
        if stage_name not in self._stage_metrics:
            self._stage_metrics[stage_name] = StageMetrics(stage_name=stage_name)

        metrics = self._stage_metrics[stage_name]
        metrics.executions += 1
        metrics.total_duration_ms += duration_ms
        metrics.min_duration_ms = min(metrics.min_duration_ms, duration_ms)
        metrics.max_duration_ms = max(metrics.max_duration_ms, duration_ms)
        if error:
            metrics.errors += 1

    def get_snapshot(self, queue_size: int = 0) -> MetricsSnapshot:
        """Get current metrics snapshot.

        Args:
            queue_size: Current queue size.

        Returns:
            Metrics snapshot.
        """
        avg_time = 0.0
        if self._processing_times:
            avg_time = sum(self._processing_times) / len(self._processing_times)

        throughput = 0.0
        if self._start_time:
            elapsed = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            if elapsed > 0:
                throughput = self._processed / elapsed

        return MetricsSnapshot(
            timestamp=datetime.now(timezone.utc),
            processed_candidates=self._processed,
            filtered_candidates=self._filtered,
            accepted_candidates=self._accepted,
            rejected_candidates=self._rejected,
            average_processing_time_ms=avg_time,
            queue_size=queue_size,
            throughput_per_second=throughput,
        )

    def get_stage_metrics(self, stage_name: str) -> StageMetrics | None:
        """Get metrics for a specific stage.

        Args:
            stage_name: Name of the stage.

        Returns:
            Stage metrics or None.
        """
        return self._stage_metrics.get(stage_name)

    def get_all_stage_metrics(self) -> tuple[StageMetrics, ...]:
        """Get metrics for all stages.

        Returns:
            Tuple of stage metrics.
        """
        return tuple(self._stage_metrics.values())

    def add_listener(
        self,
        listener: Callable[[MetricsSnapshot], None],
    ) -> None:
        """Add a metrics listener.

        Args:
            listener: Function to call on metrics update.
        """
        self._listeners.append(listener)

    def remove_listener(
        self,
        listener: Callable[[MetricsSnapshot], None],
    ) -> bool:
        """Remove a metrics listener.

        Args:
            listener: Listener to remove.

        Returns:
            True if listener was removed.
        """
        try:
            self._listeners.remove(listener)
            return True
        except ValueError:
            return False

    @property
    def processed_count(self) -> int:
        """Get total processed count."""
        return self._processed

    @property
    def filtered_count(self) -> int:
        """Get total filtered count."""
        return self._filtered

    @property
    def accepted_count(self) -> int:
        """Get total accepted count."""
        return self._accepted

    @property
    def rejected_count(self) -> int:
        """Get total rejected count."""
        return self._rejected

    def get_summary(self) -> dict[str, int | float]:
        """Get summary of all metrics.

        Returns:
            Dictionary of metric summaries.
        """
        snapshot = self.get_snapshot()
        return {
            "processed": snapshot.processed_candidates,
            "filtered": snapshot.filtered_candidates,
            "accepted": snapshot.accepted_candidates,
            "rejected": snapshot.rejected_candidates,
            "avg_processing_time_ms": snapshot.average_processing_time_ms,
            "throughput_per_second": snapshot.throughput_per_second,
        }


class DeterministicMetricsCollector(MetricsCollector):
    """Metrics collector with deterministic ordering.

    Ensures consistent metric collection without randomness.
    """

    def __init__(self) -> None:
        """Initialize deterministic metrics collector."""
        super().__init__()
        self._tick_count = 0
        self._report_interval = 10  # Report every N ticks

    def tick(self) -> None:
        """Increment internal tick counter."""
        self._tick_count += 1

        # Notify listeners at intervals
        if self._tick_count % self._report_interval == 0:
            snapshot = self.get_snapshot()
            for listener in self._listeners:
                listener(snapshot)

    def set_report_interval(self, interval: int) -> None:
        """Set reporting interval.

        Args:
            interval: Number of ticks between reports.
        """
        self._report_interval = max(1, interval)

    @property
    def tick_count(self) -> int:
        """Get current tick count."""
        return self._tick_count
