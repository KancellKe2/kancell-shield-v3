"""Event publisher implementation."""

from typing import Any, Optional

from .dispatcher import EventDispatcher
from .exceptions import PublisherError
from .models import Event, EventType


class EventPublisher:
    """Event publisher for emitting events.

    Provides a simple interface for publishing events
    through a dispatcher.
    """

    def __init__(
        self,
        dispatcher: EventDispatcher,
        source: str = "",
    ) -> None:
        """Initialize publisher.

        Args:
            dispatcher: Event dispatcher to use.
            source: Source identifier for published events.
        """
        self._dispatcher = dispatcher
        self._source = source

    @property
    def dispatcher(self) -> EventDispatcher:
        """Get the dispatcher."""
        return self._dispatcher

    @property
    def source(self) -> str:
        """Get the source identifier."""
        return self._source

    def publish(self, event: Event) -> None:
        """Publish an event.

        Args:
            event: Event to publish.
        """
        # Set source if not already set
        if not event.source and self._source:
            event = Event(
                event_type=event.event_type,
                timestamp=event.timestamp,
                source=self._source,
                task_id=event.task_id,
                priority=event.priority,
                data=event.data,
                correlation_id=event.correlation_id,
            )

        self._dispatcher.dispatch(event)

    def emit(
        self,
        event_type: EventType,
        task_id: str = "",
        data: dict[str, Any] | None = None,
        priority: int = 0,
        correlation_id: str | None = None,
    ) -> None:
        """Emit an event with the given type.

        Args:
            event_type: Type of event.
            task_id: Associated task ID.
            data: Event data.
            priority: Event priority.
            correlation_id: Correlation ID.
        """
        event = Event(
            event_type=event_type,
            source=self._source,
            task_id=task_id,
            priority=priority,
            data=data or {},
            correlation_id=correlation_id,
        )
        self.publish(event)

    # Convenience methods for discovery events

    def discovery_start(self, task_id: str) -> None:
        """Emit discovery start event."""
        self.emit(EventType.DISCOVERY_START, task_id=task_id)

    def discovery_stop(self, task_id: str) -> None:
        """Emit discovery stop event."""
        self.emit(EventType.DISCOVERY_STOP, task_id=task_id)

    def discovery_pause(self, task_id: str) -> None:
        """Emit discovery pause event."""
        self.emit(EventType.DISCOVERY_PAUSE, task_id=task_id)

    def discovery_resume(self, task_id: str) -> None:
        """Emit discovery resume event."""
        self.emit(EventType.DISCOVERY_RESUME, task_id=task_id)

    def discovery_completed(
        self,
        task_id: str,
        total: int = 0,
        valid: int = 0,
        duration_ms: float = 0.0,
    ) -> None:
        """Emit discovery completed event."""
        self.emit(
            EventType.DISCOVERY_COMPLETED,
            task_id=task_id,
            data={
                "total_candidates": total,
                "valid_candidates": valid,
                "duration_ms": duration_ms,
            },
        )

    def candidate_collected(
        self,
        task_id: str,
        domain: str,
        source: str,
    ) -> None:
        """Emit candidate collected event."""
        self.emit(
            EventType.CANDIDATE_COLLECTED,
            task_id=task_id,
            data={"domain": domain, "source": source},
        )

    def candidate_validated(
        self,
        task_id: str,
        domain: str,
        is_valid: bool,
        result: str = "",
    ) -> None:
        """Emit candidate validated event."""
        self.emit(
            EventType.CANDIDATE_VALIDATED,
            task_id=task_id,
            data={"domain": domain, "is_valid": is_valid, "validation_result": result},
        )

    def candidate_filtered(
        self,
        task_id: str,
        domain: str,
        accepted: bool,
    ) -> None:
        """Emit candidate filtered event."""
        self.emit(
            EventType.CANDIDATE_FILTERED,
            task_id=task_id,
            data={"domain": domain, "was_accepted": accepted},
        )

    def candidate_scored(
        self,
        task_id: str,
        domain: str,
        score: float,
        confidence: float,
    ) -> None:
        """Emit candidate scored event."""
        self.emit(
            EventType.CANDIDATE_SCORED,
            task_id=task_id,
            data={
                "domain": domain,
                "score": score,
                "confidence": confidence,
            },
        )

    def candidate_queued(
        self,
        task_id: str,
        domain: str,
        queue_size: int,
        priority: int,
    ) -> None:
        """Emit candidate queued event."""
        self.emit(
            EventType.CANDIDATE_QUEUED,
            task_id=task_id,
            data={
                "domain": domain,
                "queue_size": queue_size,
                "priority": priority,
            },
        )

    def provider_selected(
        self,
        task_id: str,
        provider_name: str,
        provider_type: str,
    ) -> None:
        """Emit provider selected event."""
        self.emit(
            EventType.PROVIDER_SELECTED,
            task_id=task_id,
            data={"provider_name": provider_name, "provider_type": provider_type},
        )

    def provider_failed(
        self,
        task_id: str,
        provider_name: str,
        error: str,
    ) -> None:
        """Emit provider failed event."""
        self.emit(
            EventType.PROVIDER_FAILED,
            task_id=task_id,
            data={"provider_name": provider_name, "error": error},
        )

    def pipeline_completed(
        self,
        task_id: str,
        total: int,
        accepted: int,
        rejected: int,
        filtered: int,
        duration_ms: float,
    ) -> None:
        """Emit pipeline completed event."""
        self.emit(
            EventType.PIPELINE_COMPLETED,
            task_id=task_id,
            data={
                "total_processed": total,
                "accepted": accepted,
                "rejected": rejected,
                "filtered": filtered,
                "duration_ms": duration_ms,
            },
        )

    def error(
        self,
        task_id: str,
        error_type: str,
        error_message: str,
        recoverable: bool = True,
    ) -> None:
        """Emit error event."""
        self.emit(
            EventType.ERROR,
            task_id=task_id,
            data={
                "error_type": error_type,
                "error_message": error_message,
                "recoverable": recoverable,
            },
        )
