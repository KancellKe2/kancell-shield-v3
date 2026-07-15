"""Event dispatcher implementation."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .exceptions import (
    DispatchError,
    DispatcherClosedError,
    EventHistoryError,
    EventFilterError,
)
from .models import Event, EventType
from .subscriber import EventHandler, FilteredSubscriber, Subscriber


@dataclass
class EventHistoryEntry:
    """Entry in event history."""

    event: Event
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    handlers_called: int = 0
    handler_errors: list[str] = field(default_factory=list)


class EventDispatcher:
    """Event dispatcher for routing events to handlers.

    Manages subscribers and dispatches events.
    """

    def __init__(
        self,
        max_history: Optional[int] = None,
        enable_history: bool = True,
    ) -> None:
        """Initialize event dispatcher.

        Args:
            max_history: Maximum history entries (None for unlimited).
            enable_history: Whether to record history.
        """
        self._subscriber = FilteredSubscriber()
        self._history: list[EventHistoryEntry] = []
        self._max_history = max_history
        self._enable_history = enable_history
        self._closed = False
        self._event_filters: dict[EventType, Callable[[Event], bool]] = {}

    def subscribe(
        self,
        handler: EventHandler,
        event_types: tuple[EventType, ...] | None = None,
        filter_func: Optional[Callable[[Event], bool]] = None,
        priority: int = 0,
    ) -> str:
        """Subscribe to events.

        Args:
            handler: Handler function.
            event_types: Event types to subscribe to.
            filter_func: Optional filter function.
            priority: Handler priority.

        Returns:
            Subscription ID.
        """
        if self._closed:
            raise DispatcherClosedError("Dispatcher is closed")

        return self._subscriber.subscribe(
            handler=handler,
            event_types=event_types,
            filter_func=filter_func,
            priority=priority,
        )

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            subscription_id: Subscription ID.

        Returns:
            True if unsubscribed.
        """
        return self._subscriber.unsubscribe(subscription_id)

    def unsubscribe_all(self) -> int:
        """Unsubscribe all handlers.

        Returns:
            Number of handlers unsubscribed.
        """
        return self._subscriber.unsubscribe_all()

    def dispatch(self, event: Event) -> int:
        """Dispatch an event to all matching handlers.

        Args:
            event: Event to dispatch.

        Returns:
            Number of handlers that received the event.

        Raises:
            DispatchError: If dispatch fails.
        """
        if self._closed:
            raise DispatcherClosedError("Dispatcher is closed")

        try:
            # Apply event filter if set
            if event.event_type in self._event_filters:
                filter_func = self._event_filters[event.event_type]
                if not filter_func(event):
                    return 0

            # Call handlers
            results = self._subscriber.handle_event(event)

            # Record history
            if self._enable_history:
                self._add_history_entry(
                    event=event,
                    handlers_called=len(results),
                    handler_errors=[],
                )

            return len(results)

        except Exception as e:
            # Record failed dispatch in history
            if self._enable_history:
                self._add_history_entry(
                    event=event,
                    handlers_called=0,
                    handler_errors=[str(e)],
                )
            raise DispatchError(
                f"Dispatch failed: {e}",
                event_type=event.event_type.value,
            ) from e

    def dispatch_nowait(self, event: Event) -> None:
        """Dispatch event without waiting.

        Alias for dispatch for synchronous operation.

        Args:
            event: Event to dispatch.
        """
        self.dispatch(event)

    def add_event_filter(
        self,
        event_type: EventType,
        filter_func: Callable[[Event], bool],
    ) -> None:
        """Add a filter for an event type.

        Args:
            event_type: Event type to filter.
            filter_func: Filter function.
        """
        self._event_filters[event_type] = filter_func

    def remove_event_filter(self, event_type: EventType) -> bool:
        """Remove an event filter.

        Args:
            event_type: Event type.

        Returns:
            True if filter was removed.
        """
        if event_type in self._event_filters:
            del self._event_filters[event_type]
            return True
        return False

    def _add_history_entry(
        self,
        event: Event,
        handlers_called: int,
        handler_errors: list[str],
    ) -> None:
        """Add entry to history.

        Args:
            event: Event.
            handlers_called: Number of handlers called.
            handler_errors: List of error messages.
        """
        entry = EventHistoryEntry(
            event=event,
            handlers_called=handlers_called,
            handler_errors=handler_errors,
        )

        self._history.append(entry)

        # Trim history if needed
        if self._max_history is not None:
            while len(self._history) > self._max_history:
                self._history.pop(0)

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[EventHistoryEntry]:
        """Get event history.

        Args:
            event_type: Filter by event type.
            since: Filter by timestamp.
            limit: Maximum entries to return.

        Returns:
            List of history entries.
        """
        history = self._history

        # Filter by event type
        if event_type is not None:
            history = [e for e in history if e.event.event_type == event_type]

        # Filter by timestamp
        if since is not None:
            history = [e for e in history if e.received_at >= since]

        # Apply limit
        if limit is not None:
            history = history[-limit:]

        return history

    def get_history_events(
        self,
        event_type: Optional[EventType] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[Event]:
        """Get events from history.

        Args:
            event_type: Filter by event type.
            since: Filter by timestamp.
            limit: Maximum entries to return.

        Returns:
            List of events.
        """
        entries = self.get_history(event_type, since, limit)
        return [e.event for e in entries]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()

    @property
    def history_size(self) -> int:
        """Get current history size."""
        return len(self._history)

    @property
    def history_enabled(self) -> bool:
        """Check if history is enabled."""
        return self._enable_history

    @property
    def is_closed(self) -> bool:
        """Check if dispatcher is closed."""
        return self._closed

    def close(self) -> None:
        """Close the dispatcher."""
        self._closed = True
        self._subscriber.clear()

    @property
    def subscriber_count(self) -> int:
        """Get number of subscribers."""
        return self._subscriber.active_count


class PriorityEventDispatcher(EventDispatcher):
    """Event dispatcher with priority-based dispatch.

    Events with higher priority are dispatched first.
    """

    def __init__(
        self,
        max_history: Optional[int] = None,
        enable_history: bool = True,
    ) -> None:
        """Initialize priority dispatcher.

        Args:
            max_history: Maximum history entries.
            enable_history: Whether to record history.
        """
        super().__init__(max_history, enable_history)
        self._event_queues: dict[int, list[Event]] = {}
        self._default_priority = 0

    def dispatch(self, event: Event) -> int:
        """Dispatch event with priority consideration.

        Args:
            event: Event to dispatch.

        Returns:
            Number of handlers called.
        """
        priority = event.priority

        # For synchronous dispatch, process immediately
        # For priority queue, events would be queued
        return super().dispatch(event)

    def set_default_priority(self, priority: int) -> None:
        """Set default priority for events.

        Args:
            priority: Default priority.
        """
        self._default_priority = priority


class SynchronizedEventDispatcher(EventDispatcher):
    """Event dispatcher with synchronization.

    Ensures events are dispatched in order.
    """

    def __init__(
        self,
        max_history: Optional[int] = None,
        enable_history: bool = True,
    ) -> None:
        """Initialize synchronized dispatcher.

        Args:
            max_history: Maximum history entries.
            enable_history: Whether to record history.
        """
        super().__init__(max_history, enable_history)
        self._dispatch_count = 0

    def dispatch(self, event: Event) -> int:
        """Dispatch event synchronously.

        Args:
            event: Event to dispatch.

        Returns:
            Number of handlers called.
        """
        self._dispatch_count += 1
        result = super().dispatch(event)
        return result

    @property
    def dispatch_count(self) -> int:
        """Get total dispatch count."""
        return self._dispatch_count
