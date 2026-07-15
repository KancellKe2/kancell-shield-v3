"""Event system exceptions."""


class EventError(Exception):
    """Base exception for event system errors."""

    def __init__(
        self,
        message: str,
        event_type: str | None = None,
    ) -> None:
        """Initialize event error.

        Args:
            message: Error message.
            event_type: Associated event type.
        """
        super().__init__(message)
        self.message = message
        self.event_type = event_type


class SubscriberError(EventError):
    """Error related to event subscribers."""


class DispatchError(EventError):
    """Error during event dispatch."""


class HandlerError(EventError):
    """Error in event handler."""


class SubscriptionError(EventError):
    """Error during subscription."""


class UnsubscribeError(EventError):
    """Error during unsubscription."""


class EventFilterError(EventError):
    """Error in event filtering."""


class EventHistoryError(EventError):
    """Error in event history."""


class PriorityError(EventError):
    """Error related to event priorities."""


class PublisherError(EventError):
    """Error in event publisher."""


class DispatcherClosedError(DispatchError):
    """Error when dispatcher is closed."""


class TooManyHandlersError(HandlerError):
    """Error when too many handlers are registered."""


class HandlerRegistrationError(HandlerError):
    """Error during handler registration."""


class EventTypeError(EventError):
    """Error for invalid event type."""


class InvalidHandlerError(HandlerError):
    """Error for invalid event handler."""
