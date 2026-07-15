"""Unit tests for CandidateQueue."""

import pytest

from src.discovery import (
    CandidateQueue,
    PriorityQueue,
    BoundedPriorityQueue,
    CandidateStatus,
    DiscoveryCandidate,
    Domain,
)


class TestCandidateQueue:
    """Tests for CandidateQueue."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.queue = CandidateQueue(capacity=10, deduplicate=True)

    def test_enqueue_single(self) -> None:
        """Test enqueuing a single candidate."""
        candidate = DiscoveryCandidate(
            domain=Domain(name="example.com"),
            source="test",
        )
        assert self.queue.enqueue(candidate, priority=0) is True
        assert len(self.queue) == 1

    def test_enqueue_batch(self) -> None:
        """Test enqueuing a batch."""
        candidates = [
            DiscoveryCandidate(domain=Domain(name=f"domain{i}.com"), source="test")
            for i in range(3)
        ]
        count = self.queue.enqueue_batch(candidates, priority=0)
        assert count == 3
        assert len(self.queue) == 3

    def test_dequeue(self) -> None:
        """Test dequeuing a candidate."""
        candidate = DiscoveryCandidate(
            domain=Domain(name="example.com"),
            source="test",
        )
        self.queue.enqueue(candidate, priority=0)
        dequeued = self.queue.dequeue()
        assert dequeued is not None
        assert str(dequeued.domain) == "example.com"
        assert len(self.queue) == 0

    def test_dequeue_batch(self) -> None:
        """Test dequeuing a batch."""
        for i in range(5):
            self.queue.enqueue(
                DiscoveryCandidate(domain=Domain(name=f"d{i}.com"), source="test"),
                priority=i,
            )
        batch = self.queue.dequeue_batch(3)
        assert len(batch) == 3
        assert len(self.queue) == 2

    def test_deduplication(self) -> None:
        """Test deduplication."""
        candidate = DiscoveryCandidate(
            domain=Domain(name="example.com"),
            source="test",
        )
        assert self.queue.enqueue(candidate, priority=0) is True
        assert self.queue.enqueue(candidate, priority=0) is False
        assert len(self.queue) == 1

    def test_capacity_limit(self) -> None:
        """Test capacity limit."""
        queue = CandidateQueue(capacity=2, deduplicate=False)
        for i in range(5):
            queue.enqueue(
                DiscoveryCandidate(domain=Domain(name=f"d{i}.com"), source="test"),
            )
        assert len(queue) == 2

    def test_priority_ordering(self) -> None:
        """Test priority ordering (higher priority first)."""
        self.queue.enqueue(
            DiscoveryCandidate(domain=Domain(name="low.com"), source="test"),
            priority=1,
        )
        self.queue.enqueue(
            DiscoveryCandidate(domain=Domain(name="high.com"), source="test"),
            priority=10,
        )
        self.queue.enqueue(
            DiscoveryCandidate(domain=Domain(name="mid.com"), source="test"),
            priority=5,
        )
        # High priority should come first
        first = self.queue.dequeue()
        assert str(first.domain) == "high.com"

    def test_peek(self) -> None:
        """Test peeking without removing."""
        self.queue.enqueue(
            DiscoveryCandidate(domain=Domain(name="a.com"), source="test"),
            priority=0,
        )
        self.queue.enqueue(
            DiscoveryCandidate(domain=Domain(name="b.com"), source="test"),
            priority=1,
        )
        peeked = self.queue.peek()
        assert str(peeked.domain) == "b.com"  # Higher priority
        assert len(self.queue) == 2  # Still there

    def test_remove(self) -> None:
        """Test removing a specific candidate."""
        candidate = DiscoveryCandidate(
            domain=Domain(name="a.com"),
            source="test",
        )
        self.queue.enqueue(candidate, priority=0)
        assert self.queue.remove(candidate) is True
        assert len(self.queue) == 0

    def test_clear(self) -> None:
        """Test clearing the queue."""
        for i in range(3):
            self.queue.enqueue(
                DiscoveryCandidate(domain=Domain(name=f"d{i}.com"), source="test"),
            )
        self.queue.clear()
        assert len(self.queue) == 0

    def test_contains(self) -> None:
        """Test contains check."""
        candidate = DiscoveryCandidate(
            domain=Domain(name="a.com"),
            source="test",
        )
        self.queue.enqueue(candidate)
        assert candidate in self.queue

    def test_iteration(self) -> None:
        """Test iteration."""
        for i in range(3):
            self.queue.enqueue(
                DiscoveryCandidate(domain=Domain(name=f"d{i}.com"), source="test"),
            )
        domains = [str(c.domain) for c in self.queue]
        assert len(domains) == 3

    def test_is_empty_full(self) -> None:
        """Test is_empty and is_full properties."""
        assert self.queue.is_empty is True
        assert self.queue.is_full is False

        queue = CandidateQueue(capacity=1)
        queue.enqueue(DiscoveryCandidate(domain=Domain(name="a.com"), source="test"))
        assert queue.is_empty is False
        assert queue.is_full is True

    def test_get_stats(self) -> None:
        """Test getting queue statistics."""
        self.queue.enqueue(
            DiscoveryCandidate(domain=Domain(name="a.com"), source="test"),
            priority=5,
        )
        stats = self.queue.get_stats()
        assert stats["size"] == 1
        assert stats["total_enqueued"] == 1


class TestPriorityQueue:
    """Tests for PriorityQueue."""

    def test_priority_function(self) -> None:
        """Test custom priority function."""
        def priority_func(candidate):
            # Use negative domain length so shorter domains have higher priority
            return -len(str(candidate.domain))

        queue = PriorityQueue(priority_func=priority_func)
        queue.enqueue(DiscoveryCandidate(domain=Domain(name="abc.com"), source="test"))
        queue.enqueue(DiscoveryCandidate(domain=Domain(name="a.com"), source="test"))
        # Shorter domain should have higher priority (processed first)
        first = queue.dequeue()
        assert str(first.domain) == "a.com"


class TestBoundedPriorityQueue:
    """Tests for BoundedPriorityQueue."""

    def test_priority_bounds(self) -> None:
        """Test priority bounds."""
        queue = BoundedPriorityQueue(min_priority=0, max_priority=100)

        # Test lower bound
        queue.enqueue(
            DiscoveryCandidate(domain=Domain(name="a.com"), source="test"),
            priority=-10,  # Should be clamped to 0
        )

        # Test upper bound
        queue.enqueue(
            DiscoveryCandidate(domain=Domain(name="b.com"), source="test"),
            priority=200,  # Should be clamped to 100
        )

        # Both should be in queue
        assert len(queue) == 2
