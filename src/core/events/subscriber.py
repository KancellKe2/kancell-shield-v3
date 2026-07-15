"""Event subscriber implementation."""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .exceptions import (
    HandlerError,
    InvalidHandlerError,
    TooManyHandlersError,
)
from .models import Event, EventType


# Type alias for event handlers
EventHandler = Callable[[Event], None]


@dataclass
class Subscription:
    """Represents a subscription to events."""

    subscription_id: str
    handler: EventHandler
    event_types: tuple[EventType, ...]
    filter_func: Optional[Callable[[Event], bool]]
    priority: int
    active: bool = True

    def matches(self, event: Event) -> bool:
        """Check if this subscription matches the event.

        Args:
            event: Event to check.

        Returns:
            True if subscription matches.
        """
        if not self.active:
            return False

        if event.event_type not in self.event_types:
            return False

        if self.filter_func is not None:
            return self.filter_func(event)

        return True


class Subscriber:
    """Event subscriber for handling events.

    Manages subscriptions and event handlers.
    """

    def __init__(
        self,
        max_handlers: Optional[int] = None,
    ) -> None:
        """Initialize subscriber.

        Args:
            max_handlers: Maximum number of handlers (None for unlimited).
        """
        self._subscriptions: dict[str, Subscription] = {}
        self._subscription_counter = 0
        self._max_handlers = max_handlers

    def subscribe(
        self,
        handler: EventHandler,
        event_types: tuple[EventType, ...] | None = None,
        filter_func: Optional[Callable[[Event], bool]] = None,
        priority: int = 0,
    ) -> str:
        """Subscribe to events.

        Args:
            handler: Handler function to call.
            event_types: Event types to subscribe to (None for all).
            filter_func: Optional filter function.
            priority: Handler priority (higher = called first).

        Returns:
            Subscription ID.

        Raises:
            InvalidHandlerError: If handler is not callable.
            TooManyHandlersError: If max handlers exceeded.
        """
        if not callable(handler):
            raise InvalidHandlerError("Handler must be callable")

        if self._max_handlers is not None:
            active_count = sum(1 for s in self._subscriptions.values() if s.active)
            if active_count >= self._max_handlers:
                raise TooManyHandlersError(
                    f"Maximum handlers ({self._max_handlers}) exceeded"
                )

        self._subscription_counter += 1
        subscription_id = f"sub_{self._subscription_counter}"

        if event_types is None:
            event_types = tuple(EventType)

        subscription = Subscription(
            subscription_id=subscription_id,
            handler=handler,
            event_types=event_types,
            filter_func=filter_func,
            priority=priority,
        )

        self._subscriptions[subscription_id] = subscription
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            subscription_id: ID of subscription to remove.

        Returns:
            True if unsubscribed.
        """
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id].active = False
            return True
        return False

    def unsubscribe_all(self) -> int:
        """Unsubscribe all handlers.

        Returns:
            Number of handlers unsubscribed.
        """
        count = 0
        for subscription in self._subscriptions.values():
            if subscription.active:
                subscription.active = False
                count += 1
        return count

    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get a subscription by ID.

        Args:
            subscription_id: Subscription ID.

        Returns:
            Subscription or None.
        """
        return self._subscriptions.get(subscription_id)

    def get_active_subscriptions(
        self,
        event_type: Optional[EventType] = None,
    ) -> list[Subscription]:
        """Get active subscriptions.

        Args:
            event_type: Optional filter by event type.

        Returns:
            List of active subscriptions.
        """
        subscriptions = [
            s for s in self._subscriptions.values()
            if s.active
        ]

        if event_type is not None:
            subscriptions = [
                s for s in subscriptions
                if event_type in s.event_types
            ]

        # Sort by priority (higher first)
        subscriptions.sort(key=lambda s: s.priority, reverse=True)
        return subscriptions

    def handle_event(self, event: Event) -> list[Any]:
        """Handle an event by calling matching handlers.

        Args:
            event: Event to handle.

        Returns:
            List of handler results.
        """
        results = []
        subscriptions = self.get_active_subscriptions(event.event_type)

        for subscription in subscriptions:
            if subscription.matches(event):
                try:
                    result = subscription.handler(event)
                    results.append(result)
                except Exception as e:
                    raise HandlerError(
                        f"Handler error: {e}",
                        event_type=event.event_type.value,
                    ) from e

        return results

    @property
    def subscription_count(self) -> int:
        """Get number of subscriptions."""
        return len(self._subscriptions)

    @property
    def active_count(self) -> int:
        """Get number of active subscriptions."""
        return sum(1 for s in self._subscriptions.values() if s.active)

    def clear(self) -> None:
        """Clear all subscriptions."""
        self._subscriptions.clear()


class FilteredSubscriber(Subscriber):
    """Subscriber with built-in event filtering."""

    def __init__(
        self,
        max_handlers: Optional[int] = None,
    ) -> None:
        """Initialize filtered subscriber.

        Args:
            max_handlers: Maximum number of handlers.
        """
        super().__init__(max_handlers)
        self._event_filters: dict[EventType, Callable[[Event], bool]] = {}

    def add_filter(
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

    def remove_filter(self, event_type: EventType) -> bool:
        """Remove a filter for an event type.

        Args:
            event_type: Event type.

        Returns:
            True if filter was removed.
        """
        if event_type in self._event_filters:
            del self._event_filters[event_type]
            return True
        return False

    def handle_event(self, event: Event) -> list[Any]:
        """Handle event with filters applied.

        Args:
            event: Event to handle.

        Returns:
            List of handler results.
        """
        # Apply filter if set
        if event.event_type in self._event_filters:
            filter_func = self._event_filters[event.event_type]
            if not filter_func(event):
                return []

        return super().handle_event(event)
