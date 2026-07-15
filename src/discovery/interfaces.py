"""Protocol interfaces for the Discovery Engine.

This module contains Protocol interface definitions.
No implementation should be placed here.
"""

from typing import Protocol, Sequence

from .models import (
    CandidateStatus,
    DiscoveryBatch,
    DiscoveryCandidate,
    DiscoveryConfiguration,
    DiscoveryProgress,
    DiscoveryResult,
    DiscoverySource,
    DiscoveryStatistics,
    DiscoveryTask,
    DiscoveryStatus,
    FilterRule,
    SourceResult,
    ValidationResult,
)


class DiscoveryState(Protocol):
    """Manages the state of discovery operations.

    Implementations track the progress and results of
    discovery tasks.
    """

    def get_status(self, task_id: str) -> DiscoveryStatus:
        """Get the current status of a task.

        Args:
            task_id: ID of the task.

        Returns:
            Current status of the task.
        """
        ...

    def get_progress(self, task_id: str) -> DiscoveryProgress | None:
        """Get progress information for a task.

        Args:
            task_id: ID of the task.

        Returns:
            Progress information if available.
        """
        ...

    def get_statistics(self, task_id: str) -> DiscoveryStatistics | None:
        """Get statistics for a task.

        Args:
            task_id: ID of the task.

        Returns:
            Statistics if available.
        """
        ...

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
        ...

    def update_status(self, task_id: str, status: DiscoveryStatus) -> None:
        """Update the status of a task.

        Args:
            task_id: ID of the task.
            status: New status.
        """
        ...

    def add_candidates(
        self,
        task_id: str,
        candidates: Sequence[DiscoveryCandidate],
    ) -> None:
        """Add candidates to a task.

        Args:
            task_id: ID of the task.
            candidates: Candidates to add.
        """
        ...

    def increment_statistic(
        self,
        task_id: str,
        statistic: str,
        value: int = 1,
    ) -> None:
        """Increment a statistic counter.

        Args:
            task_id: ID of the task.
            statistic: Name of the statistic.
            value: Amount to increment by.
        """
        ...


class DiscoveryScheduler(Protocol):
    """Schedules discovery tasks and sources.

    Implementations determine the order and timing
    of discovery operations.
    """

    def schedule_task(self, task: DiscoveryTask) -> None:
        """Schedule a discovery task.

        Args:
            task: Task to schedule.
        """
        ...

    def get_next_source(self, task: DiscoveryTask) -> DiscoverySource | None:
        """Get the next source to query.

        Args:
            task: Current task.

        Returns:
            Next source to query, or None if done.
        """
        ...

    def has_more_sources(self, task: DiscoveryTask) -> bool:
        """Check if more sources are available.

        Args:
            task: Current task.

        Returns:
            True if more sources to query.
        """
        ...

    def get_schedule_order(
        self,
        task: DiscoveryTask,
    ) -> tuple[DiscoverySource, ...]:
        """Get sources in scheduled order.

        Args:
            task: Task to get schedule for.

        Returns:
            Ordered tuple of sources.
        """
        ...

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task.

        Args:
            task_id: ID of task to cancel.

        Returns:
            True if task was cancelled.
        """
        ...


class DiscoveryPipeline(Protocol):
    """Executes the discovery workflow.

    Implementations orchestrate the discovery process
    from scheduling through result collection.
    """

    def execute(self, task: DiscoveryTask) -> DiscoveryResult:
        """Execute a discovery task.

        Args:
            task: Task to execute.

        Returns:
            Discovery results.
        """
        ...

    def execute_batch(
        self,
        task: DiscoveryTask,
        source: DiscoverySource,
    ) -> SourceResult:
        """Execute discovery for a single source.

        Args:
            task: Parent task.
            source: Source to query.

        Returns:
            Results from the source.
        """
        ...

    def collect_candidates(
        self,
        source_result: SourceResult,
    ) -> tuple[DiscoveryCandidate, ...]:
        """Collect candidates from source result.

        Args:
            source_result: Result from source.

        Returns:
            Extracted candidates.
        """
        ...

    def aggregate_results(
        self,
        task_id: str,
        source_results: Sequence[SourceResult],
    ) -> DiscoveryResult:
        """Aggregate results from all sources.

        Args:
            task_id: ID of the task.
            source_results: Results from all sources.

        Returns:
            Aggregated discovery result.
        """
        ...


class DiscoveryCollector(Protocol):
    """Collects candidates from discovery sources.

    Implementations handle the mechanics of querying
    discovery sources and extracting candidates.
    """

    def collect(self, source: DiscoverySource, task: DiscoveryTask) -> SourceResult:
        """Collect candidates from a source.

        Args:
            source: Source to collect from.
            task: Parent task with configuration.

        Returns:
            Results from the source.
        """
        ...

    def extract_candidates(self, raw_response: object) -> tuple[str, ...]:
        """Extract domain candidates from raw response.

        Args:
            raw_response: Raw response from source.

        Returns:
            Tuple of domain strings.
        """
        ...

    def validate_response(self, raw_response: object) -> bool:
        """Validate that a response is well-formed.

        Args:
            raw_response: Response to validate.

        Returns:
            True if response is valid.
        """
        ...


class CandidateValidator(Protocol):
    """Validates discovery candidates.

    Implementations check that candidates meet
    format and validity requirements.
    """

    def validate(self, candidate: DiscoveryCandidate) -> ValidationResult:
        """Validate a candidate.

        Args:
            candidate: Candidate to validate.

        Returns:
            Validation result.
        """
        ...

    def validate_batch(
        self,
        candidates: Sequence[DiscoveryCandidate],
    ) -> tuple[DiscoveryCandidate, ...]:
        """Validate multiple candidates.

        Args:
            candidates: Candidates to validate.

        Returns:
            Validated candidates with updated status.
        """
        ...

    def is_valid_format(self, domain_string: str) -> bool:
        """Check if domain format is valid.

        Args:
            domain_string: Domain to check.

        Returns:
            True if format is valid.
        """
        ...

    def get_validation_errors(
        self,
        candidate: DiscoveryCandidate,
    ) -> tuple[ValidationResult, ...]:
        """Get all validation errors for a candidate.

        Args:
            candidate: Candidate to validate.

        Returns:
            Tuple of validation errors.
        """
        ...


class CandidateScorer(Protocol):
    """Scores discovery candidates.

    Implementations assign relevance and confidence
    scores to candidates based on discovery context.
    """

    def score(self, candidate: DiscoveryCandidate) -> float:
        """Score a single candidate.

        Args:
            candidate: Candidate to score.

        Returns:
            Relevance score (0.0 to 1.0).
        """
        ...

    def score_batch(
        self,
        candidates: Sequence[DiscoveryCandidate],
    ) -> tuple[DiscoveryCandidate, ...]:
        """Score multiple candidates.

        Args:
            candidates: Candidates to score.

        Returns:
            Candidates with updated scores.
        """
        ...

    def calculate_confidence(
        self,
        candidate: DiscoveryCandidate,
    ) -> float:
        """Calculate confidence in the score.

        Args:
            candidate: Candidate with score.

        Returns:
            Confidence score (0.0 to 1.0).
        """
        ...

    def rank_candidates(
        self,
        candidates: Sequence[DiscoveryCandidate],
    ) -> tuple[DiscoveryCandidate, ...]:
        """Rank candidates by score.

        Args:
            candidates: Candidates to rank.

        Returns:
            Candidates sorted by score descending.
        """
        ...


class CandidateFilter(Protocol):
    """Filters discovery candidates.

    Implementations apply inclusion/exclusion rules
    and threshold checks to candidates.
    """

    def should_include(self, candidate: DiscoveryCandidate) -> bool:
        """Check if candidate should be included.

        Args:
            candidate: Candidate to check.

        Returns:
            True if candidate should be included.
        """
        ...

    def filter_batch(
        self,
        candidates: Sequence[DiscoveryCandidate],
    ) -> tuple[DiscoveryCandidate, ...]:
        """Filter multiple candidates.

        Args:
            candidates: Candidates to filter.

        Returns:
            Filtered candidates.
        """
        ...

    def add_rule(self, rule: FilterRule) -> None:
        """Add a filter rule.

        Args:
            rule: Rule to add.
        """
        ...

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a filter rule.

        Args:
            rule_name: Name of rule to remove.

        Returns:
            True if rule was removed.
        """
        ...

    def clear_rules(self) -> None:
        """Clear all filter rules."""
        ...


class DiscoveryEngine(Protocol):
    """Main discovery engine interface.

    This is the primary interface for initiating
    and managing discovery operations.
    """

    def discover(self, task: DiscoveryTask) -> DiscoveryResult:
        """Start a discovery operation.

        Args:
            task: Task to execute.

        Returns:
            Discovery results.
        """
        ...

    def discover_async(self, task: DiscoveryTask) -> str:
        """Start a discovery operation asynchronously.

        Args:
            task: Task to execute.

        Returns:
            Task ID for tracking.
        """
        ...

    def get_result(self, task_id: str) -> DiscoveryResult | None:
        """Get results of a discovery operation.

        Args:
            task_id: ID of the task.

        Returns:
            Results if available.
        """
        ...

    def get_progress(self, task_id: str) -> DiscoveryProgress | None:
        """Get progress of a discovery operation.

        Args:
            task_id: ID of the task.

        Returns:
            Progress if available.
        """
        ...

    def cancel(self, task_id: str) -> bool:
        """Cancel a running discovery.

        Args:
            task_id: ID of task to cancel.

        Returns:
            True if cancelled.
        """
        ...

    def get_state(self) -> DiscoveryState:
        """Get the discovery state manager.

        Returns:
            Current state manager.
        """
        ...


class DiscoverySourceProvider(Protocol):
    """Provides discovery sources.

    Implementations supply sources that can be
    queried for domain candidates.
    """

    def get_sources(self) -> tuple[DiscoverySource, ...]:
        """Get all available sources.

        Returns:
            Tuple of available sources.
        """
        ...

    def get_source(self, name: str) -> DiscoverySource | None:
        """Get a source by name.

        Args:
            name: Name of the source.

        Returns:
            Source if found.
        """
        ...

    def get_enabled_sources(self) -> tuple[DiscoverySource, ...]:
        """Get all enabled sources.

        Returns:
            Tuple of enabled sources.
        """
        ...

    def get_sources_by_type(
        self,
        source_type: "SourceType",
    ) -> tuple[DiscoverySource, ...]:
        """Get sources by type.

        Args:
            source_type: Type to filter by.

        Returns:
            Matching sources.
        """
        ...


class SourceType:
    """Type hint for source type enum."""
    pass
