"""Event system for Kancell Shield v3.

Provides an internal event system for in-process event handling.
No networking, database, or message broker dependencies.
"""

from .models import (
    Event,
    EventType,
    # Discovery events
    DiscoveryStartEvent,
    DiscoveryStopEvent,
    DiscoveryPauseEvent,
    DiscoveryResumeEvent,
    DiscoveryCompletedEvent,
    # Candidate events
    CandidateCollectedEvent,
    CandidateValidatedEvent,
    CandidateFilteredEvent,
    CandidateScoredEvent,
    CandidateQueuedEvent,
    # Provider events
    ProviderSelectedEvent,
    ProviderFailedEvent,
    # Pipeline events
    PipelineCompletedEvent,
    # Error events
    ErrorEvent,
)

from .exceptions import (
    EventError,
    EventFilterError,
    EventHistoryError,
    EventTypeError,
    DispatchError,
    DispatcherClosedError,
    HandlerError,
    HandlerRegistrationError,
    InvalidHandlerError,
    PriorityError,
    PublisherError,
    SubscriptionError,
    SubscriberError,
    TooManyHandlersError,
    UnsubscribeError,
)

from .subscriber import (
    EventHandler,
    FilteredSubscriber,
    Subscriber,
    Subscription,
)

from .dispatcher import (
    EventDispatcher,
    EventHistoryEntry,
    PriorityEventDispatcher,
    SynchronizedEventDispatcher,
)

from .publisher import EventPublisher

__all__ = [
    # Models
    "Event",
    "EventType",
    "DiscoveryStartEvent",
    "DiscoveryStopEvent",
    "DiscoveryPauseEvent",
    "DiscoveryResumeEvent",
    "DiscoveryCompletedEvent",
    "CandidateCollectedEvent",
    "CandidateValidatedEvent",
    "CandidateFilteredEvent",
    "CandidateScoredEvent",
    "CandidateQueuedEvent",
    "ProviderSelectedEvent",
    "ProviderFailedEvent",
    "PipelineCompletedEvent",
    "ErrorEvent",
    # Exceptions
    "EventError",
    "EventFilterError",
    "EventHistoryError",
    "EventTypeError",
    "DispatchError",
    "DispatcherClosedError",
    "HandlerError",
    "HandlerRegistrationError",
    "InvalidHandlerError",
    "PriorityError",
    "PublisherError",
    "SubscriptionError",
    "SubscriberError",
    "TooManyHandlersError",
    "UnsubscribeError",
    # Subscriber
    "EventHandler",
    "FilteredSubscriber",
    "Subscriber",
    "Subscription",
    # Dispatcher
    "EventDispatcher",
    "EventHistoryEntry",
    "PriorityEventDispatcher",
    "SynchronizedEventDispatcher",
    # Publisher
    "EventPublisher",
]
