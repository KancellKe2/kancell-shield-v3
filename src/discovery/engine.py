"""Discovery engine core implementation."""

from datetime import datetime, timezone
from typing import Callable, Iterator, Sequence

from .collector import DiscoveryCollectorImpl
from .exceptions import (
    DiscoveryError,
    MaxCandidatesReachedError,
    TaskNotFoundError,
)
from .filter import DomainFilter
from .interfaces import DiscoveryEngine
from .models import (
    CandidateStatus,
    DiscoveryBatch,
    DiscoveryCandidate,
    DiscoveryConfiguration,
    DiscoveryProgress,
    DiscoveryResult,
    DiscoverySource,
    DiscoveryStatistics,
    DiscoveryStatus,
    DiscoveryTask,
    SourceResult,
)
from .scheduler import DiscoverySchedulerImpl
from .scorer import DomainScorer
from .validator import DomainValidator


class DiscoveryEngineImpl(DiscoveryEngine):
    """Implementation of DiscoveryEngine.

    Orchestrates the discovery process by coordinating
    scheduler, collector, validator, scorer, and filter
    components.
    """

    def __init__(
        self,
        configuration: DiscoveryConfiguration | None = None,
        validator: DomainValidator | None = None,
        scorer: DomainScorer | None = None,
        filter_impl: DomainFilter | None = None,
    ) -> None:
        """Initialize discovery engine.

        Args:
            configuration: Discovery configuration.
            validator: Custom validator (optional).
            scorer: Custom scorer (optional).
            filter_impl: Custom filter (optional).
        """
        self._config = configuration or DiscoveryConfiguration()
        self._scheduler = DiscoverySchedulerImpl()
        self._collector = DiscoveryCollectorImpl()
        self._validator = validator or DomainValidator()
        self._scorer = scorer or DomainScorer()
        self._filter = filter_impl or DomainFilter()

        # State management
        self._tasks: dict[str, DiscoveryTask] = {}
        self._results: dict[str, DiscoveryResult] = {}
        self._progress: dict[str, DiscoveryProgress] = {}
        self._statistics: dict[str, DiscoveryStatistics] = {}
        self._candidates: dict[str, list[DiscoveryCandidate]] = {}

    def discover(self, task: DiscoveryTask) -> DiscoveryResult:
        """Start a discovery operation.

        Args:
            task: Task to execute.

        Returns:
            Discovery results.
        """
        # Initialize task state
        self._initialize_task(task)

        try:
            # Update status to running
            self._update_status(task.task_id, DiscoveryStatus.RUNNING)

            # Get sources in scheduled order
            sources = self._scheduler.get_schedule_order(task)

            # Collect candidates from all sources
            all_candidates = []
            for source in sources:
                source_candidates = self._collector.get_candidates(
                    task.task_id,
                    source.name,
                )
                all_candidates.extend(source_candidates)

            # Get all candidates for task
            if not all_candidates:
                all_candidates = list(self._collector.get_candidates(task.task_id))

            # Validate candidates
            validated = self._validator.validate_batch(all_candidates)

            # Score candidates
            scored = self._scorer.score_batch(validated)

            # Filter candidates
            filtered = self._filter.filter_batch(scored)

            # Apply max candidates limit
            final_candidates = self._apply_max_candidates(task, filtered)

            # Create result
            result = self._create_result(task, final_candidates)

            # Store result
            self._results[task.task_id] = result

            # Update statistics
            self._update_statistics_final(task.task_id, final_candidates)

            # Update status to completed
            self._update_status(task.task_id, DiscoveryStatus.COMPLETED)

            return result

        except DiscoveryError:
            self._update_status(task.task_id, DiscoveryStatus.FAILED)
            raise
        except Exception as e:
            self._update_status(task.task_id, DiscoveryStatus.FAILED)
            raise DiscoveryError(str(e), task.task_id) from e

    def discover_async(self, task: DiscoveryTask) -> str:
        """Start a discovery operation asynchronously.

        Note: This implementation is synchronous. Subclasses
        can override to provide actual async behavior.

        Args:
            task: Task to execute.

        Returns:
            Task ID for tracking.
        """
        self._initialize_task(task)
        self._update_status(task.task_id, DiscoveryStatus.RUNNING)

        # Synchronous execution for now
        self.discover(task)

        return task.task_id

    def get_result(self, task_id: str) -> DiscoveryResult | None:
        """Get results of a discovery operation.

        Args:
            task_id: ID of the task.

        Returns:
            Results if available.
        """
        return self._results.get(task_id)

    def get_progress(self, task_id: str) -> DiscoveryProgress | None:
        """Get progress of a discovery operation.

        Args:
            task_id: ID of the task.

        Returns:
            Progress if available.
        """
        return self._progress.get(task_id)

    def cancel(self, task_id: str) -> bool:
        """Cancel a running discovery.

        Args:
            task_id: ID of task to cancel.

        Returns:
            True if cancelled.
        """
        if task_id not in self._tasks:
            return False

        status = self._progress.get(task_id)
        if status and status.is_finished:
            return False

        self._update_status(task_id, DiscoveryStatus.CANCELLED)
        self._scheduler.cancel_task(task_id)
        return True

    def get_state(self) -> "DiscoveryEngineImpl":
        """Get the discovery state manager.

        Returns:
            Self (implements DiscoveryState interface).
        """
        return self

    def add_candidates(
        self,
        task_id: str,
        source_name: str,
        domains: Sequence[str],
    ) -> list[DiscoveryCandidate]:
        """Add candidates from an external provider.

        This is the main interface for external providers to
        supply candidates to the discovery engine.

        Args:
            task_id: Task ID.
            source_name: Source name.
            domains: List of domain strings.

        Returns:
            Created candidates.
        """
        return self._collector.add_candidates(task_id, source_name, list(domains))

    def _initialize_task(self, task: DiscoveryTask) -> None:
        """Initialize task state.

        Args:
            task: Task to initialize.
        """
        self._tasks[task.task_id] = task
        self._scheduler.schedule_task(task)

        # Initialize statistics
        self._statistics[task.task_id] = DiscoveryStatistics(
            task_id=task.task_id,
            started_at=datetime.now(timezone.utc),
            status=DiscoveryStatus.PENDING,
        )

        # Initialize progress
        self._progress[task.task_id] = DiscoveryProgress(
            task_id=task.task_id,
            status=DiscoveryStatus.PENDING,
            total_batches=len(task.sources) if task.sources else 1,
            completed_batches=0,
            total_candidates=0,
            current_batch=0,
        )

        # Initialize candidates list
        if task.task_id not in self._candidates:
            self._candidates[task.task_id] = []

    def _update_status(self, task_id: str, status: DiscoveryStatus) -> None:
        """Update task status.

        Args:
            task_id: Task ID.
            status: New status.
        """
        if task_id in self._progress:
            progress = self._progress[task_id]
            self._progress[task_id] = DiscoveryProgress(
                task_id=task_id,
                status=status,
                total_batches=progress.total_batches,
                completed_batches=progress.completed_batches,
                total_candidates=progress.total_candidates,
                current_batch=progress.current_batch,
                last_updated=datetime.now(timezone.utc),
            )

        if task_id in self._statistics:
            stats = self._statistics[task_id]
            self._statistics[task_id] = DiscoveryStatistics(
                task_id=task_id,
                started_at=stats.started_at,
                ended_at=datetime.now(timezone.utc) if status in (
                    DiscoveryStatus.COMPLETED,
                    DiscoveryStatus.FAILED,
                    DiscoveryStatus.CANCELLED,
                ) else None,
                status=status,
                candidates_discovered=stats.candidates_discovered,
                candidates_validated=stats.candidates_validated,
                candidates_scored=stats.candidates_scored,
                candidates_filtered=stats.candidates_filtered,
                candidates_rejected=stats.candidates_rejected,
                duplicates=stats.duplicates,
                source_stats=stats.source_stats,
                errors=stats.errors,
                warnings=stats.warnings,
                retries=stats.retries,
            )

    def _apply_max_candidates(
        self,
        task: DiscoveryTask,
        candidates: Sequence[DiscoveryCandidate],
    ) -> list[DiscoveryCandidate]:
        """Apply max candidates limit.

        Args:
            task: Task configuration.
            candidates: Candidates to limit.

        Returns:
            Limited candidates.
        """
        if len(candidates) <= task.max_candidates:
            return list(candidates)

        # Take top candidates by score
        scored = [(c.score or 0.0, c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)

        return [c for _, c in scored[:task.max_candidates]]

    def _create_result(
        self,
        task: DiscoveryTask,
        candidates: Sequence[DiscoveryCandidate],
    ) -> DiscoveryResult:
        """Create a discovery result.

        Args:
            task: Task that was executed.
            candidates: Final candidates.

        Returns:
            Discovery result.
        """
        statistics = self._statistics.get(task.task_id)
        if statistics is None:
            statistics = DiscoveryStatistics(
                task_id=task.task_id,
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
                status=DiscoveryStatus.COMPLETED,
                candidates_discovered=len(candidates),
                candidates_validated=len(candidates),
                candidates_scored=len(candidates),
                candidates_filtered=len(candidates),
            )

        return DiscoveryResult(
            task_id=task.task_id,
            status=DiscoveryStatus.COMPLETED,
            candidates=tuple(candidates),
            statistics=statistics,
            configuration=self._config,
            completed_at=datetime.now(timezone.utc),
        )

    def _update_statistics_final(
        self,
        task_id: str,
        candidates: Sequence[DiscoveryCandidate],
    ) -> None:
        """Update final statistics.

        Args:
            task_id: Task ID.
            candidates: Final candidates.
        """
        discovered = len(candidates)
        validated = sum(1 for c in candidates if c.validation_result is None)
        scored = sum(1 for c in candidates if c.score is not None)
        filtered = sum(1 for c in candidates if c.status == CandidateStatus.FILTERED)
        rejected = sum(1 for c in candidates if c.status == CandidateStatus.REJECTED)

        if task_id in self._statistics:
            stats = self._statistics[task_id]
            self._statistics[task_id] = DiscoveryStatistics(
                task_id=task_id,
                started_at=stats.started_at,
                ended_at=datetime.now(timezone.utc),
                status=DiscoveryStatus.COMPLETED,
                candidates_discovered=discovered,
                candidates_validated=validated,
                candidates_scored=scored,
                candidates_filtered=filtered,
                candidates_rejected=rejected,
                duplicates=stats.duplicates,
                source_stats=stats.source_stats,
                errors=stats.errors,
                warnings=stats.warnings,
                retries=stats.retries,
            )

    # DiscoveryState interface methods
    def get_status(self, task_id: str) -> DiscoveryStatus:
        """Get the current status of a task.

        Args:
            task_id: ID of the task.

        Returns:
            Current status of the task.
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(task_id)
        progress = self._progress.get(task_id)
        if progress:
            return progress.status
        return DiscoveryStatus.PENDING

    def get_statistics(self, task_id: str) -> DiscoveryStatistics | None:
        """Get statistics for a task.

        Args:
            task_id: ID of the task.

        Returns:
            Statistics if available.
        """
        return self._statistics.get(task_id)

    def get_candidates(
        self,
        task_id: str,
        status: CandidateStatus | None = None,
    ) -> tuple[DiscoveryCandidate, ...]:
        """Get candidates for a task.

        Args:
            task_id: ID of the task.
            status: Optional status to filter by.

        Returns:
            Tuple of matching candidates.
        """
        candidates = self._candidates.get(task_id, [])
        if status is not None:
            return tuple(c for c in candidates if c.status == status)
        return tuple(candidates)

    def add_candidate(self, task_id: str, candidate: DiscoveryCandidate) -> None:
        """Add a candidate to a task.

        Args:
            task_id: ID of the task.
            candidate: Candidate to add.
        """
        if task_id not in self._candidates:
            self._candidates[task_id] = []
        self._candidates[task_id].append(candidate)
