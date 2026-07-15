"""Discovery pipeline orchestrator.

This module coordinates the entire discovery pipeline
including queue, stages, state management, and metrics.
"""

from datetime import datetime, timezone
from typing import Callable, Sequence

from .candidate_queue import CandidateQueue
from .metrics import DeterministicMetricsCollector, MetricsCollector, MetricsSnapshot
from .models import (
    CandidateStatus,
    DiscoveryCandidate,
    DiscoveryTask,
    DiscoveryStatus,
)
from .pipeline import (
    DiscoveryPipeline,
    FilteredPipeline,
    PipelineContext,
    PipelineResult,
    PipelineStage,
)
from .state_manager import PipelineState, StateManager, StateSnapshot


class DiscoveryOrchestrator:
    """Orchestrator for discovery pipeline.

    Coordinates queue, pipeline, state, and metrics
    to execute discovery operations.
    """

    def __init__(
        self,
        queue_capacity: int | None = None,
        enable_metrics: bool = True,
        enable_state: bool = True,
    ) -> None:
        """Initialize discovery orchestrator.

        Args:
            queue_capacity: Maximum queue size.
            enable_metrics: Whether to enable metrics.
            enable_state: Whether to enable state management.
        """
        self._queue = CandidateQueue(capacity=queue_capacity, deduplicate=True)
        self._state_manager = StateManager() if enable_state else None
        self._metrics = DeterministicMetricsCollector() if enable_metrics else None
        self._pipeline: DiscoveryPipeline | None = None
        self._task: DiscoveryTask | None = None

        # Enqueue function for pipeline
        self._enqueue_func: Callable[[DiscoveryCandidate], bool] = (
            self._queue.enqueue
        )

    def configure_pipeline(
        self,
        pipeline: DiscoveryPipeline | None = None,
    ) -> None:
        """Configure the processing pipeline.

        Args:
            pipeline: Pipeline to use.
        """
        if pipeline is None:
            # Create default pipeline
            self._pipeline = DiscoveryPipeline(enqueue_func=self._enqueue_func)
        else:
            self._pipeline = pipeline

    def set_task(self, task: DiscoveryTask) -> None:
        """Set the current task.

        Args:
            task: Discovery task.
        """
        self._task = task

    def start(self, task: DiscoveryTask | None = None) -> None:
        """Start the orchestrator.

        Args:
            task: Optional task to run.
        """
        if task is not None:
            self._task = task

        if self._task is None:
            raise ValueError("No task configured")

        # Start metrics if enabled
        if self._metrics:
            self._metrics.start()

        # Transition state
        if self._state_manager:
            self._state_manager.transition_to_running(self._task.task_id)

    def pause(self) -> None:
        """Pause the orchestrator."""
        if self._state_manager:
            self._state_manager.transition_to_paused("User requested pause")

    def resume(self) -> None:
        """Resume the orchestrator."""
        if self._state_manager:
            self._state_manager.set_state(PipelineState.RUNNING, reason="Resumed")

    def stop(self) -> None:
        """Stop the orchestrator."""
        if self._state_manager:
            if self._state_manager.is_running():
                self._state_manager.transition_to_stopping()
            self._state_manager.transition_to_stopped()

        if self._metrics:
            self._metrics.stop()

    def enqueue_candidates(
        self,
        candidates: Sequence[DiscoveryCandidate],
        priority: int = 0,
    ) -> int:
        """Add candidates to the processing queue.

        Args:
            candidates: Candidates to enqueue.
            priority: Priority for all candidates.

        Returns:
            Number of candidates actually enqueued.
        """
        count = self._queue.enqueue_batch(list(candidates), priority)

        if self._metrics:
            self._metrics.record_processed(count)

        return count

    def process_batch(self, batch_size: int = 100) -> PipelineResult | None:
        """Process a batch of candidates.

        Args:
            batch_size: Number of candidates to process.

        Returns:
            Pipeline result or None if queue is empty.
        """
        if self._task is None:
            return None

        # Get batch from queue
        candidates = self._queue.dequeue_batch(batch_size)
        if not candidates:
            return None

        # Update state
        if self._state_manager:
            self._state_manager.increment_processed(len(candidates))

        # Create and configure pipeline if needed
        if self._pipeline is None:
            self.configure_pipeline()

        # Execute pipeline
        result = self._pipeline.execute(self._task, candidates)

        # Record metrics
        if self._metrics:
            self._metrics.record_processed(len(candidates))
            self._metrics.record_accepted(result.accepted)
            self._metrics.record_rejected(result.rejected)
            self._metrics.record_filtered(result.filtered)

        # Record status metrics
        for candidate in result.candidates:
            if self._metrics:
                self._metrics.record_candidate_status(candidate.status)

        return result

    def process_all(self) -> list[PipelineResult]:
        """Process all queued candidates.

        Returns:
            List of pipeline results.
        """
        results = []

        while not self._queue.is_empty:
            if self._state_manager and self._state_manager.is_stopped():
                break

            result = self.process_batch()
            if result:
                results.append(result)

        return results

    def run(self, task: DiscoveryTask) -> tuple[DiscoveryCandidate, ...]:
        """Run the full discovery pipeline.

        Args:
            task: Discovery task to run.

        Returns:
            Final candidates.
        """
        self.start(task)

        results = []
        while not self._queue.is_empty:
            if self._state_manager and self._state_manager.is_stopped():
                break

            batch_result = self.process_batch()
            if batch_result:
                results.append(batch_result)

        # Complete
        if self._state_manager:
            self._state_manager.transition_to_completed()

        # Return all candidates
        all_candidates = []
        for result in results:
            all_candidates.extend(result.candidates)

        return tuple(all_candidates)

    def get_status(self) -> dict[str, object]:
        """Get current orchestrator status.

        Returns:
            Status dictionary.
        """
        status: dict[str, object] = {
            "queue_size": len(self._queue),
            "queue_capacity": self._queue.capacity,
            "pipeline_configured": self._pipeline is not None,
        }

        if self._state_manager:
            status["state"] = self._state_manager.state.value
            status["task_id"] = self._state_manager.task_id
            status["current_stage"] = self._state_manager.current_stage
            status["is_running"] = self._state_manager.is_running()
            status["is_paused"] = self._state_manager.is_paused()
            status["is_stopped"] = self._state_manager.is_stopped()

        if self._metrics:
            snapshot = self._metrics.get_snapshot(len(self._queue))
            status["metrics"] = {
                "processed": snapshot.processed_candidates,
                "filtered": snapshot.filtered_candidates,
                "accepted": snapshot.accepted_candidates,
                "rejected": snapshot.rejected_candidates,
                "avg_processing_time_ms": snapshot.average_processing_time_ms,
                "throughput_per_second": snapshot.throughput_per_second,
            }

        return status

    def get_state_snapshot(self) -> StateSnapshot | None:
        """Get current state snapshot.

        Returns:
            State snapshot or None if state is disabled.
        """
        if self._state_manager is None:
            return None

        snapshot = self._state_manager.get_snapshot()
        snapshot.queue_size = len(self._queue)
        return snapshot

    def get_metrics_snapshot(self) -> MetricsSnapshot | None:
        """Get current metrics snapshot.

        Returns:
            Metrics snapshot or None if metrics are disabled.
        """
        if self._metrics is None:
            return None

        return self._metrics.get_snapshot(len(self._queue))

    def get_queue(self) -> CandidateQueue:
        """Get the candidate queue.

        Returns:
            Candidate queue.
        """
        return self._queue

    def get_pipeline(self) -> DiscoveryPipeline | None:
        """Get the processing pipeline.

        Returns:
            Pipeline or None.
        """
        return self._pipeline

    def reset(self) -> None:
        """Reset the orchestrator."""
        self._queue.clear()

        if self._state_manager:
            self._state_manager.reset()

        if self._metrics:
            self._metrics.reset()

        self._task = None


class StreamingOrchestrator(DiscoveryOrchestrator):
    """Orchestrator for streaming candidate processing.

    Processes candidates as they arrive.
    """

    def __init__(
        self,
        queue_capacity: int | None = None,
        batch_size: int = 100,
    ) -> None:
        """Initialize streaming orchestrator.

        Args:
            queue_capacity: Maximum queue size.
            batch_size: Default batch size.
        """
        super().__init__(queue_capacity)
        self._batch_size = batch_size
        self._pending_results: list[PipelineResult] = []

    def add_candidates(
        self,
        candidates: Sequence[DiscoveryCandidate],
    ) -> int:
        """Add candidates and process immediately.

        Args:
            candidates: Candidates to add.

        Returns:
            Number of candidates processed.
        """
        # Enqueue
        count = self.enqueue_candidates(candidates)

        # Process batch
        if not self._queue.is_empty:
            result = self.process_batch(self._batch_size)
            if result:
                self._pending_results.append(result)

        return count

    def get_results(self) -> tuple[PipelineResult, ...]:
        """Get pending results.

        Returns:
            Tuple of pipeline results.
        """
        return tuple(self._pending_results)

    def clear_results(self) -> None:
        """Clear pending results."""
        self._pending_results.clear()


class BatchOrchestrator(DiscoveryOrchestrator):
    """Orchestrator for batch candidate processing.

    Collects candidates and processes in batches.
    """

    def __init__(
        self,
        batch_size: int = 100,
        trigger_threshold: int | None = None,
    ) -> None:
        """Initialize batch orchestrator.

        Args:
            batch_size: Size of each batch.
            trigger_threshold: Queue size to trigger processing.
        """
        super().__init__()
        self._batch_size = batch_size
        self._trigger_threshold = trigger_threshold or batch_size

    def add_candidates(
        self,
        candidates: Sequence[DiscoveryCandidate],
    ) -> int:
        """Add candidates (does not auto-process).

        Args:
            candidates: Candidates to add.

        Returns:
            Number of candidates added.
        """
        return self.enqueue_candidates(candidates)

    def process_if_ready(self) -> PipelineResult | None:
        """Process if queue meets threshold.

        Returns:
            Pipeline result or None.
        """
        if len(self._queue) >= self._trigger_threshold:
            return self.process_batch(self._batch_size)
        return None

    def process_all_batches(self) -> list[PipelineResult]:
        """Process all queued candidates in batches.

        Returns:
            List of pipeline results.
        """
        results = []

        while not self._queue.is_empty:
            result = self.process_batch(self._batch_size)
            if result:
                results.append(result)

        return results
