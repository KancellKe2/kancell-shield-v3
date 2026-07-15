"""Unit tests for Event System."""

import pytest
from datetime import datetime, timezone

from src.core.events import (
    Event,
    EventDispatcher,
    EventHandler,
    EventPublisher,
    EventType,
    FilteredSubscriber,
    Subscriber,
    Subscription,
    SynchronizedEventDispatcher,
    PriorityEventDispatcher,
)
from src.core.events.exceptions import (
    DispatcherClosedError,
    HandlerError,
    InvalidHandlerError,
    TooManyHandlersError,
)
from src.core.events.models import (
    CandidateCollectedEvent,
    DiscoveryCompletedEvent,
)


class TestEvent:
    """Tests for Event model."""

    def test_event_creation(self) -> None:
        """Test basic event creation."""
        event = Event(
            event_type=EventType.DISCOVERY_START,
            task_id="task-1",
        )
        assert event.event_type == EventType.DISCOVERY_START
        assert event.task_id == "task-1"
        assert event.timestamp is not None

    def test_event_name(self) -> None:
        """Test event name property."""
        event = Event(event_type=EventType.CANDIDATE_COLLECTED)
        assert event.event_name == "candidate.collected"

    def test_event_to_dict(self) -> None:
        """Test event to_dict method."""
        event = Event(
            event_type=EventType.DISCOVERY_START,
            task_id="task-1",
            source="test",
            data={"key": "value"},
        )
        d = event.to_dict()
        assert d["event_type"] == "discovery.start"
        assert d["task_id"] == "task-1"
        assert d["source"] == "test"
        assert d["data"]["key"] == "value"


class TestEventDispatcher:
    """Tests for EventDispatcher."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.dispatcher = EventDispatcher()

    def test_subscribe_unsubscribe(self) -> None:
        """Test subscribe and unsubscribe."""
        received = []

        def handler(event: Event) -> None:
            received.append(event)

        sub_id = self.dispatcher.subscribe(handler, (EventType.DISCOVERY_START,))
        assert self.dispatcher.subscriber_count == 1

        self.dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))
        assert len(received) == 1

        self.dispatcher.unsubscribe(sub_id)
        assert self.dispatcher.subscriber_count == 0

    def test_unsubscribe_all(self) -> None:
        """Test unsubscribe all."""
        def handler(e: Event) -> None:
            pass

        self.dispatcher.subscribe(handler)
        self.dispatcher.subscribe(handler)
        assert self.dispatcher.subscriber_count == 2

        count = self.dispatcher.unsubscribe_all()
        assert count == 2

    def test_dispatch_to_multiple_handlers(self) -> None:
        """Test dispatching to multiple handlers."""
        received1 = []
        received2 = []

        def handler1(e: Event) -> None:
            received1.append(e)

        def handler2(e: Event) -> None:
            received2.append(e)

        self.dispatcher.subscribe(handler1)
        self.dispatcher.subscribe(handler2)

        self.dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))
        assert len(received1) == 1
        assert len(received2) == 1

    def test_event_filter(self) -> None:
        """Test event filtering."""
        received = []

        def handler(e: Event) -> None:
            received.append(e)

        def my_filter(e: Event) -> bool:
            return e.task_id == "allowed"

        self.dispatcher.subscribe(handler, filter_func=my_filter)
        self.dispatcher.dispatch(Event(
            event_type=EventType.DISCOVERY_START,
            task_id="denied",
        ))
        assert len(received) == 0

        self.dispatcher.dispatch(Event(
            event_type=EventType.DISCOVERY_START,
            task_id="allowed",
        ))
        assert len(received) == 1

    def test_priority_handlers(self) -> None:
        """Test priority-based handler ordering."""
        order = []

        def handler1(e: Event) -> None:
            order.append(1)

        def handler2(e: Event) -> None:
            order.append(2)

        self.dispatcher.subscribe(handler1, priority=10)
        self.dispatcher.subscribe(handler2, priority=5)

        self.dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))
        # Higher priority (10) should run first
        assert order == [1, 2]

    def test_history(self) -> None:
        """Test event history."""
        self.dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))
        self.dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_STOP))

        history = self.dispatcher.get_history()
        assert len(history) == 2

        history = self.dispatcher.get_history(event_type=EventType.DISCOVERY_START)
        assert len(history) == 1

    def test_clear_history(self) -> None:
        """Test clearing history."""
        self.dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))
        assert self.dispatcher.history_size == 1

        self.dispatcher.clear_history()
        assert self.dispatcher.history_size == 0

    def test_closed_dispatcher(self) -> None:
        """Test closed dispatcher."""
        self.dispatcher.close()
        with pytest.raises(DispatcherClosedError):
            self.dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))

    def test_dispatch_returns_count(self) -> None:
        """Test dispatch returns handler count."""
        def handler(e: Event) -> None:
            pass

        self.dispatcher.subscribe(handler)
        count = self.dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))
        assert count == 1


class TestFilteredSubscriber:
    """Tests for FilteredSubscriber."""

    def test_add_filter(self) -> None:
        """Test adding event filter."""
        subscriber = FilteredSubscriber()
        received = []

        def handler(e: Event) -> None:
            received.append(e)

        subscriber.subscribe(handler, (EventType.CANDIDATE_COLLECTED,))

        # Add filter to reject all
        subscriber.add_filter(EventType.CANDIDATE_COLLECTED, lambda e: False)

        subscriber.handle_event(Event(
            event_type=EventType.CANDIDATE_COLLECTED,
            data={"domain": "test.com"},
        ))
        assert len(received) == 0

    def test_remove_filter(self) -> None:
        """Test removing filter."""
        subscriber = FilteredSubscriber()
        received = []

        def handler(e: Event) -> None:
            received.append(e)

        subscriber.subscribe(handler, (EventType.CANDIDATE_COLLECTED,))
        subscriber.add_filter(EventType.CANDIDATE_COLLECTED, lambda e: False)
        subscriber.remove_filter(EventType.CANDIDATE_COLLECTED)

        subscriber.handle_event(Event(event_type=EventType.CANDIDATE_COLLECTED))
        assert len(received) == 1


class TestSubscription:
    """Tests for Subscription."""

    def test_matches(self) -> None:
        """Test subscription matching."""
        sub = Subscription(
            subscription_id="test",
            handler=lambda e: None,
            event_types=(EventType.DISCOVERY_START, EventType.DISCOVERY_STOP),
            filter_func=None,
            priority=0,
        )

        assert sub.matches(Event(event_type=EventType.DISCOVERY_START))
        assert sub.matches(Event(event_type=EventType.DISCOVERY_STOP))
        assert not sub.matches(Event(event_type=EventType.CANDIDATE_COLLECTED))

    def test_inactive_subscription(self) -> None:
        """Test inactive subscription."""
        sub = Subscription(
            subscription_id="test",
            handler=lambda e: None,
            event_types=(EventType.DISCOVERY_START,),
            filter_func=None,
            priority=0,
            active=False,
        )

        assert not sub.matches(Event(event_type=EventType.DISCOVERY_START))


class TestSubscriber:
    """Tests for Subscriber."""

    def test_max_handlers(self) -> None:
        """Test max handlers limit."""
        subscriber = Subscriber(max_handlers=2)

        subscriber.subscribe(lambda e: None)
        subscriber.subscribe(lambda e: None)

        with pytest.raises(TooManyHandlersError):
            subscriber.subscribe(lambda e: None)

    def test_invalid_handler(self) -> None:
        """Test invalid handler."""
        subscriber = Subscriber()

        with pytest.raises(InvalidHandlerError):
            subscriber.subscribe("not a handler")  # type: ignore

    def test_get_active_subscriptions(self) -> None:
        """Test getting active subscriptions."""
        subscriber = Subscriber()

        sub1_id = subscriber.subscribe(
            lambda e: None,
            event_types=(EventType.DISCOVERY_START,),
            priority=10,
        )
        sub2_id = subscriber.subscribe(
            lambda e: None,
            event_types=(EventType.DISCOVERY_START,),
            priority=5,
        )

        subs = subscriber.get_active_subscriptions(EventType.DISCOVERY_START)
        assert len(subs) == 2
        # Should be sorted by priority
        assert subs[0].subscription_id == sub1_id
        assert subs[1].subscription_id == sub2_id

    def test_clear(self) -> None:
        """Test clearing subscriptions."""
        subscriber = Subscriber()
        subscriber.subscribe(lambda e: None)
        subscriber.subscribe(lambda e: None)

        assert subscriber.subscription_count == 2
        subscriber.clear()
        assert subscriber.subscription_count == 0


class TestEventPublisher:
    """Tests for EventPublisher."""

    def test_publish(self) -> None:
        """Test publishing events."""
        dispatcher = EventDispatcher()
        publisher = EventPublisher(dispatcher, source="test_source")

        received = []

        def handler(e: Event) -> None:
            received.append(e)

        dispatcher.subscribe(handler)

        publisher.publish(Event(
            event_type=EventType.CANDIDATE_COLLECTED,
            data={"domain": "test.com"},
        ))

        assert len(received) == 1
        assert received[0].source == "test_source"

    def test_emit(self) -> None:
        """Test emit convenience method."""
        dispatcher = EventDispatcher()
        publisher = EventPublisher(dispatcher, source="test")

        received = []
        dispatcher.subscribe(lambda e: received.append(e))

        publisher.emit(EventType.DISCOVERY_START, task_id="task-1")

        assert len(received) == 1
        assert received[0].task_id == "task-1"

    def test_convenience_methods(self) -> None:
        """Test discovery convenience methods."""
        dispatcher = EventDispatcher()
        publisher = EventPublisher(dispatcher)

        received = []
        dispatcher.subscribe(lambda e: received.append(e))

        publisher.discovery_start("task-1")
        assert len(received) == 1
        assert received[0].event_type == EventType.DISCOVERY_START

        publisher.discovery_stop("task-1")
        assert received[1].event_type == EventType.DISCOVERY_STOP

    def test_candidate_events(self) -> None:
        """Test candidate convenience methods."""
        dispatcher = EventDispatcher()
        publisher = EventPublisher(dispatcher)

        received = []
        dispatcher.subscribe(lambda e: received.append(e))

        publisher.candidate_collected("task-1", "example.com", "ct")
        assert received[0].event_type == EventType.CANDIDATE_COLLECTED
        assert received[0].data["domain"] == "example.com"


class TestSynchronizedEventDispatcher:
    """Tests for SynchronizedEventDispatcher."""

    def test_dispatch_count(self) -> None:
        """Test dispatch count."""
        dispatcher = SynchronizedEventDispatcher()

        def handler(e: Event) -> None:
            pass

        dispatcher.subscribe(handler)
        dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))
        dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))

        assert dispatcher.dispatch_count == 2


class TestPriorityEventDispatcher:
    """Tests for PriorityEventDispatcher."""

    def test_default_priority(self) -> None:
        """Test setting default priority."""
        dispatcher = PriorityEventDispatcher()
        dispatcher.set_default_priority(5)

        assert dispatcher._default_priority == 5


class TestEventHistoryEntry:
    """Tests for EventHistoryEntry."""

    def test_history_entry(self) -> None:
        """Test history entry creation."""
        from src.core.events.dispatcher import EventHistoryEntry

        event = Event(event_type=EventType.DISCOVERY_START)
        entry = EventHistoryEntry(
            event=event,
            handlers_called=2,
            handler_errors=["error1"],
        )

        assert entry.event == event
        assert entry.handlers_called == 2
        assert len(entry.handler_errors) == 1


class TestEventModels:
    """Tests for event model classes."""

    def test_discovery_completed_event(self) -> None:
        """Test DiscoveryCompletedEvent."""
        event = DiscoveryCompletedEvent(
            event_type=EventType.DISCOVERY_COMPLETED,
            task_id="t1",
            total_candidates=100,
            valid_candidates=90,
            duration_ms=500.0,
        )
        assert event.event_type == EventType.DISCOVERY_COMPLETED
        assert event.data["total_candidates"] == 100

    def test_candidate_collected_event(self) -> None:
        """Test CandidateCollectedEvent."""
        event = CandidateCollectedEvent(
            event_type=EventType.CANDIDATE_COLLECTED,
            task_id="t1",
            domain="example.com",
            source="ct",
        )
        assert event.event_type == EventType.CANDIDATE_COLLECTED
        assert event.domain == "example.com"
        assert event.source == "ct"

    def test_dispatcher_get_history_limit(self) -> None:
        """Test getting history with limit."""
        dispatcher = EventDispatcher()

        for i in range(10):
            dispatcher.dispatch(Event(
                event_type=EventType.DISCOVERY_START,
                task_id=f"task-{i}",
            ))

        history = dispatcher.get_history(limit=5)
        assert len(history) == 5

    def test_dispatcher_get_history_since(self) -> None:
        """Test getting history since timestamp."""
        dispatcher = EventDispatcher()

        dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))

        import time
        time.sleep(0.01)  # Small delay

        from datetime import datetime, timezone
        since = datetime.now(timezone.utc)

        dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_STOP))

        history = dispatcher.get_history(since=since)
        assert len(history) == 1
        assert history[0].event.event_type == EventType.DISCOVERY_STOP

    def test_dispatcher_get_history_events(self) -> None:
        """Test getting history events."""
        dispatcher = EventDispatcher()

        dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))
        dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_STOP))

        events = dispatcher.get_history_events()
        assert len(events) == 2

    def test_dispatcher_remove_event_filter(self) -> None:
        """Test removing event filter."""
        dispatcher = EventDispatcher()

        dispatcher.add_event_filter(EventType.DISCOVERY_START, lambda e: True)
        assert dispatcher.remove_event_filter(EventType.DISCOVERY_START)

    def test_dispatcher_no_history(self) -> None:
        """Test dispatcher without history."""
        dispatcher = EventDispatcher(enable_history=False)

        received = []
        dispatcher.subscribe(lambda e: received.append(e))
        dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))

        assert len(received) == 1
        assert dispatcher.history_size == 0

    def test_dispatcher_max_history(self) -> None:
        """Test dispatcher with max history."""
        dispatcher = EventDispatcher(max_history=5)

        for i in range(10):
            dispatcher.dispatch(Event(
                event_type=EventType.DISCOVERY_START,
                task_id=f"task-{i}",
            ))

        assert dispatcher.history_size == 5

    def test_priority_dispatcher(self) -> None:
        """Test priority dispatcher."""
        dispatcher = PriorityEventDispatcher()

        received = []
        dispatcher.subscribe(lambda e: received.append(e))

        dispatcher.dispatch(Event(
            event_type=EventType.DISCOVERY_START,
            priority=5,
        ))

        assert len(received) == 1

    def test_publisher_discovery_events(self) -> None:
        """Test all discovery convenience methods."""
        dispatcher = EventDispatcher()
        publisher = EventPublisher(dispatcher)

        received = []
        dispatcher.subscribe(lambda e: received.append(e))

        publisher.discovery_pause("task-1")
        assert received[-1].event_type == EventType.DISCOVERY_PAUSE

        publisher.discovery_resume("task-1")
        assert received[-1].event_type == EventType.DISCOVERY_RESUME

        publisher.discovery_completed("task-1", 100, 90, 500.0)
        assert received[-1].event_type == EventType.DISCOVERY_COMPLETED

    def test_publisher_candidate_events(self) -> None:
        """Test all candidate convenience methods."""
        dispatcher = EventDispatcher()
        publisher = EventPublisher(dispatcher)

        received = []
        dispatcher.subscribe(lambda e: received.append(e))

        publisher.candidate_validated("task-1", "test.com", True, "valid")
        assert received[-1].event_type == EventType.CANDIDATE_VALIDATED

        publisher.candidate_filtered("task-1", "test.com", True)
        assert received[-1].event_type == EventType.CANDIDATE_FILTERED

        publisher.candidate_scored("task-1", "test.com", 0.8, 0.9)
        assert received[-1].event_type == EventType.CANDIDATE_SCORED

        publisher.candidate_queued("task-1", "test.com", 10, 5)
        assert received[-1].event_type == EventType.CANDIDATE_QUEUED

    def test_publisher_provider_events(self) -> None:
        """Test provider convenience methods."""
        dispatcher = EventDispatcher()
        publisher = EventPublisher(dispatcher)

        received = []
        dispatcher.subscribe(lambda e: received.append(e))

        publisher.provider_selected("task-1", "ct_provider", "passive")
        assert received[-1].event_type == EventType.PROVIDER_SELECTED

        publisher.provider_failed("task-1", "ct_provider", "timeout")
        assert received[-1].event_type == EventType.PROVIDER_FAILED

    def test_publisher_pipeline_completed(self) -> None:
        """Test pipeline completed event."""
        dispatcher = EventDispatcher()
        publisher = EventPublisher(dispatcher)

        received = []
        dispatcher.subscribe(lambda e: received.append(e))

        publisher.pipeline_completed("task-1", 100, 80, 10, 10, 500.0)
        assert received[-1].event_type == EventType.PIPELINE_COMPLETED

    def test_publisher_error_event(self) -> None:
        """Test error event."""
        dispatcher = EventDispatcher()
        publisher = EventPublisher(dispatcher)

        received = []
        dispatcher.subscribe(lambda e: received.append(e))

        publisher.error("task-1", "ValidationError", "invalid domain", True)
        assert received[-1].event_type == EventType.ERROR

    def test_handler_error_propagation(self) -> None:
        """Test handler error propagation."""
        from src.core.events.exceptions import DispatchError
        dispatcher = EventDispatcher()

        def failing_handler(e: Event) -> None:
            raise ValueError("Handler failed")

        dispatcher.subscribe(failing_handler)

        with pytest.raises(DispatchError):
            dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))

    def test_dispatcher_filtered_event(self) -> None:
        """Test event filtered by dispatcher filter."""
        dispatcher = EventDispatcher()

        # Set filter to reject all
        dispatcher.add_event_filter(EventType.DISCOVERY_START, lambda e: False)

        received = []
        dispatcher.subscribe(lambda e: received.append(e))

        dispatcher.dispatch(Event(event_type=EventType.DISCOVERY_START))
        assert len(received) == 0

    def test_get_subscription(self) -> None:
        """Test getting subscription by ID."""
        dispatcher = EventDispatcher()

        sub_id = dispatcher.subscribe(lambda e: None)
        subscription = dispatcher._subscriber.get_subscription(sub_id)
        assert subscription is not None

    def test_remove_nonexistent_filter(self) -> None:
        """Test removing nonexistent filter."""
        dispatcher = EventDispatcher()
        assert dispatcher.remove_event_filter(EventType.DISCOVERY_START) is False

    def test_all_event_types(self) -> None:
        """Test all event types are valid."""
        for event_type in EventType:
            assert event_type.value  # Should have a value
            assert event_type.name   # Should have a name

    def test_all_typed_events(self) -> None:
        """Test all typed event classes can be created."""
        # Test all typed event classes
        from src.core.events.models import (
            DiscoveryStopEvent,
            DiscoveryPauseEvent,
            DiscoveryResumeEvent,
            CandidateValidatedEvent,
            CandidateFilteredEvent,
            CandidateScoredEvent,
            CandidateQueuedEvent,
            ProviderSelectedEvent,
            ProviderFailedEvent,
            PipelineCompletedEvent,
            ErrorEvent,
        )

        events = [
            DiscoveryStopEvent(event_type=EventType.DISCOVERY_STOP, task_id="t1"),
            DiscoveryPauseEvent(event_type=EventType.DISCOVERY_PAUSE, task_id="t1"),
            DiscoveryResumeEvent(event_type=EventType.DISCOVERY_RESUME, task_id="t1"),
            CandidateValidatedEvent(event_type=EventType.CANDIDATE_VALIDATED, task_id="t1", domain="a.com", is_valid=True),
            CandidateFilteredEvent(event_type=EventType.CANDIDATE_FILTERED, task_id="t1", domain="a.com"),
            CandidateScoredEvent(event_type=EventType.CANDIDATE_SCORED, task_id="t1", domain="a.com", score=0.8),
            CandidateQueuedEvent(event_type=EventType.CANDIDATE_QUEUED, task_id="t1", domain="a.com", queue_size=10),
            ProviderSelectedEvent(event_type=EventType.PROVIDER_SELECTED, task_id="t1", provider_name="ct"),
            ProviderFailedEvent(event_type=EventType.PROVIDER_FAILED, task_id="t1", provider_name="ct", error="timeout"),
            PipelineCompletedEvent(event_type=EventType.PIPELINE_COMPLETED, task_id="t1", total_processed=100),
            ErrorEvent(event_type=EventType.ERROR, task_id="t1", error_type="RuntimeError", error_message="failed"),
        ]

        for event in events:
            assert event.task_id == "t1"

    def test_subscriber_remove_listener(self) -> None:
        """Test removing listener from subscriber."""
        # Subscriber uses different pattern - test get_active_subscriptions with event_type
        from src.core.events.subscriber import Subscriber
        from src.core.events.models import EventType

        subscriber = Subscriber()
        subscriber.subscribe(lambda e: None)

        # Get subscriptions with filter
        subs = subscriber.get_active_subscriptions(EventType.DISCOVERY_START)
        assert len(subs) == 1

        # Get with no filter
        subs = subscriber.get_active_subscriptions()
        assert len(subs) == 1
