"""Event models for the event system."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class EventType(Enum):
    """Enumeration of event types."""

    # Discovery events
    DISCOVERY_START = "discovery.start"
    DISCOVERY_STOP = "discovery.stop"
    DISCOVERY_PAUSE = "discovery.pause"
    DISCOVERY_RESUME = "discovery.resume"
    DISCOVERY_COMPLETED = "discovery.completed"

    # Candidate events
    CANDIDATE_COLLECTED = "candidate.collected"
    CANDIDATE_VALIDATED = "candidate.validated"
    CANDIDATE_FILTERED = "candidate.filtered"
    CANDIDATE_SCORED = "candidate.scored"
    CANDIDATE_QUEUED = "candidate.queued"

    # Provider events
    PROVIDER_SELECTED = "provider.selected"
    PROVIDER_FAILED = "provider.failed"

    # Pipeline events
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_STAGE_STARTED = "pipeline.stage_started"
    PIPELINE_STAGE_COMPLETED = "pipeline.stage_completed"

    # Queue events
    QUEUE_PUSHED = "queue.pushed"
    QUEUE_POPPED = "queue.popped"
    QUEUE_FULL = "queue.full"
    QUEUE_EMPTY = "queue.empty"

    # Error events
    ERROR = "error"

    # Custom event
    CUSTOM = "custom"


@dataclass(frozen=True)
class Event:
    """Base event class.

    All events are immutable (frozen dataclass).
    """

    event_type: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""
    task_id: str = ""
    priority: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None

    @property
    def event_name(self) -> str:
        """Get the event name."""
        return self.event_type.value

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "task_id": self.task_id,
            "priority": self.priority,
            "data": self.data,
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True)
class DiscoveryStartEvent(Event):
    """Event emitted when discovery starts."""

    def __post_init__(self) -> None:
        """Set event type."""
        object.__setattr__(self, "event_type", EventType.DISCOVERY_START)


@dataclass(frozen=True)
class DiscoveryStopEvent(Event):
    """Event emitted when discovery stops."""

    def __post_init__(self) -> None:
        """Set event type."""
        object.__setattr__(self, "event_type", EventType.DISCOVERY_STOP)


@dataclass(frozen=True)
class DiscoveryPauseEvent(Event):
    """Event emitted when discovery is paused."""

    def __post_init__(self) -> None:
        """Set event type."""
        object.__setattr__(self, "event_type", EventType.DISCOVERY_PAUSE)


@dataclass(frozen=True)
class DiscoveryResumeEvent(Event):
    """Event emitted when discovery resumes."""

    def __post_init__(self) -> None:
        """Set event type."""
        object.__setattr__(self, "event_type", EventType.DISCOVERY_RESUME)


@dataclass(frozen=True)
class DiscoveryCompletedEvent(Event):
    """Event emitted when discovery completes."""

    total_candidates: int = 0
    valid_candidates: int = 0
    duration_ms: float = 0.0

    def __post_init__(self) -> None:
        """Set event type and data."""
        object.__setattr__(self, "event_type", EventType.DISCOVERY_COMPLETED)
        object.__setattr__(
            self,
            "data",
            {
                "total_candidates": self.total_candidates,
                "valid_candidates": self.valid_candidates,
                "duration_ms": self.duration_ms,
            },
        )


@dataclass(frozen=True)
class CandidateCollectedEvent(Event):
    """Event emitted when a candidate is collected."""

    domain: str = ""
    source: str = ""

    def __post_init__(self) -> None:
        """Set event type and data."""
        object.__setattr__(self, "event_type", EventType.CANDIDATE_COLLECTED)
        object.__setattr__(
            self,
            "data",
            {"domain": self.domain, "source": self.source},
        )


@dataclass(frozen=True)
class CandidateValidatedEvent(Event):
    """Event emitted when a candidate is validated."""

    domain: str = ""
    is_valid: bool = True
    validation_result: str = ""

    def __post_init__(self) -> None:
        """Set event type and data."""
        object.__setattr__(self, "event_type", EventType.CANDIDATE_VALIDATED)
        object.__setattr__(
            self,
            "data",
            {
                "domain": self.domain,
                "is_valid": self.is_valid,
                "validation_result": self.validation_result,
            },
        )


@dataclass(frozen=True)
class CandidateFilteredEvent(Event):
    """Event emitted when a candidate is filtered."""

    domain: str = ""
    was_accepted: bool = True

    def __post_init__(self) -> None:
        """Set event type and data."""
        object.__setattr__(self, "event_type", EventType.CANDIDATE_FILTERED)
        object.__setattr__(
            self,
            "data",
            {"domain": self.domain, "was_accepted": self.was_accepted},
        )


@dataclass(frozen=True)
class CandidateScoredEvent(Event):
    """Event emitted when a candidate is scored."""

    domain: str = ""
    score: float = 0.0
    confidence: float = 0.0

    def __post_init__(self) -> None:
        """Set event type and data."""
        object.__setattr__(self, "event_type", EventType.CANDIDATE_SCORED)
        object.__setattr__(
            self,
            "data",
            {
                "domain": self.domain,
                "score": self.score,
                "confidence": self.confidence,
            },
        )


@dataclass(frozen=True)
class CandidateQueuedEvent(Event):
    """Event emitted when a candidate is queued."""

    domain: str = ""
    queue_size: int = 0
    priority: int = 0

    def __post_init__(self) -> None:
        """Set event type and data."""
        object.__setattr__(self, "event_type", EventType.CANDIDATE_QUEUED)
        object.__setattr__(
            self,
            "data",
            {
                "domain": self.domain,
                "queue_size": self.queue_size,
                "priority": self.priority,
            },
        )


@dataclass(frozen=True)
class ProviderSelectedEvent(Event):
    """Event emitted when a provider is selected."""

    provider_name: str = ""
    provider_type: str = ""

    def __post_init__(self) -> None:
        """Set event type and data."""
        object.__setattr__(self, "event_type", EventType.PROVIDER_SELECTED)
        object.__setattr__(
            self,
            "data",
            {"provider_name": self.provider_name, "provider_type": self.provider_type},
        )


@dataclass(frozen=True)
class ProviderFailedEvent(Event):
    """Event emitted when a provider fails."""

    provider_name: str = ""
    error: str = ""

    def __post_init__(self) -> None:
        """Set event type and data."""
        object.__setattr__(self, "event_type", EventType.PROVIDER_FAILED)
        object.__setattr__(
            self,
            "data",
            {"provider_name": self.provider_name, "error": self.error},
        )


@dataclass(frozen=True)
class PipelineCompletedEvent(Event):
    """Event emitted when pipeline completes."""

    total_processed: int = 0
    accepted: int = 0
    rejected: int = 0
    filtered: int = 0
    duration_ms: float = 0.0

    def __post_init__(self) -> None:
        """Set event type and data."""
        object.__setattr__(self, "event_type", EventType.PIPELINE_COMPLETED)
        object.__setattr__(
            self,
            "data",
            {
                "total_processed": self.total_processed,
                "accepted": self.accepted,
                "rejected": self.rejected,
                "filtered": self.filtered,
                "duration_ms": self.duration_ms,
            },
        )


@dataclass(frozen=True)
class ErrorEvent(Event):
    """Event emitted when an error occurs."""

    error_type: str = ""
    error_message: str = ""
    recoverable: bool = True

    def __post_init__(self) -> None:
        """Set event type and data."""
        object.__setattr__(self, "event_type", EventType.ERROR)
        object.__setattr__(
            self,
            "data",
            {
                "error_type": self.error_type,
                "error_message": self.error_message,
                "recoverable": self.recoverable,
            },
        )
