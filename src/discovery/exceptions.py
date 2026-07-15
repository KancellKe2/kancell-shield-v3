"""Discovery Engine exceptions."""


class DiscoveryError(Exception):
    """Base exception for discovery operations."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
    ) -> None:
        """Initialize discovery error.

        Args:
            message: Error message.
            task_id: Optional task ID associated with the error.
        """
        super().__init__(message)
        self.message = message
        self.task_id = task_id


class ConfigurationError(DiscoveryError):
    """Configuration error."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
    ) -> None:
        """Initialize configuration error."""
        super().__init__(message, task_id)


class ValidationError(DiscoveryError):
    """Validation error."""

    def __init__(
        self,
        message: str,
        domain: str | None = None,
        task_id: str | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message.
            domain: Domain that caused the error.
            task_id: Optional task ID.
        """
        super().__init__(message, task_id)
        self.domain = domain


class FilterError(DiscoveryError):
    """Filtering error."""

    def __init__(
        self,
        message: str,
        rule: str | None = None,
        task_id: str | None = None,
    ) -> None:
        """Initialize filter error.

        Args:
            message: Error message.
            rule: Filter rule that caused the error.
            task_id: Optional task ID.
        """
        super().__init__(message, task_id)
        self.rule = rule


class SchedulerError(DiscoveryError):
    """Scheduling error."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
    ) -> None:
        """Initialize scheduler error."""
        super().__init__(message, task_id)


class CollectorError(DiscoveryError):
    """Collector error."""

    def __init__(
        self,
        message: str,
        source: str | None = None,
        task_id: str | None = None,
    ) -> None:
        """Initialize collector error.

        Args:
            message: Error message.
            source: Source that caused the error.
            task_id: Optional task ID.
        """
        super().__init__(message, task_id)
        self.source = source


class ScorerError(DiscoveryError):
    """Scoring error."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
    ) -> None:
        """Initialize scorer error."""
        super().__init__(message, task_id)


class StateError(DiscoveryError):
    """State management error."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
    ) -> None:
        """Initialize state error."""
        super().__init__(message, task_id)


class TaskNotFoundError(DiscoveryError):
    """Task not found error."""

    def __init__(self, task_id: str) -> None:
        """Initialize task not found error.

        Args:
            task_id: ID of the task that was not found.
        """
        super().__init__(f"Task not found: {task_id}")
        self.task_id = task_id


class SourceNotFoundError(DiscoveryError):
    """Source not found error."""

    def __init__(
        self,
        source_name: str,
        task_id: str | None = None,
    ) -> None:
        """Initialize source not found error.

        Args:
            source_name: Name of the source.
            task_id: Optional task ID.
        """
        super().__init__(f"Source not found: {source_name}", task_id)
        self.source_name = source_name


class MaxCandidatesReachedError(DiscoveryError):
    """Maximum candidates reached error."""

    def __init__(
        self,
        max_candidates: int,
        task_id: str | None = None,
    ) -> None:
        """Initialize max candidates error.

        Args:
            max_candidates: Maximum number of candidates allowed.
            task_id: Optional task ID.
        """
        super().__init__(f"Maximum candidates reached: {max_candidates}", task_id)
        self.max_candidates = max_candidates
