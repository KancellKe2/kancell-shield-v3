"""Candidate queue for managing discovered candidates.

This module provides a priority queue for managing candidates
with deduplication and deterministic ordering.
"""

from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional, Sequence

from .models import DiscoveryCandidate


@dataclass(order=True)
class QueueEntry:
    """Entry in the candidate queue.

    Uses priority for ordering (lower priority = higher in queue).
    """

    priority: int
    candidate: DiscoveryCandidate = field(compare=False)
    enqueued_at: int = field(compare=False, default=0)


class CandidateQueue:
    """Priority queue for discovery candidates.

    Supports deduplication, configurable capacity, and
    deterministic ordering.
    """

    def __init__(
        self,
        capacity: Optional[int] = None,
        deduplicate: bool = True,
    ) -> None:
        """Initialize candidate queue.

        Args:
            capacity: Maximum queue size (None for unlimited).
            deduplicate: Whether to deduplicate candidates.
        """
        self._capacity = capacity
        self._deduplicate = deduplicate
        self._queue: list[QueueEntry] = []
        self._seen_domains: set[str] = set()
        self._enqueued_count = 0

    def enqueue(self, candidate: DiscoveryCandidate, priority: int = 0) -> bool:
        """Add a candidate to the queue.

        Args:
            candidate: Candidate to enqueue.
            priority: Priority value (higher = processed first).

        Returns:
            True if candidate was enqueued.
        """
        domain_str = str(candidate.domain)

        # Check deduplication
        if self._deduplicate:
            if domain_str in self._seen_domains:
                return False

        # Check capacity
        if self._capacity is not None and len(self._queue) >= self._capacity:
            return False

        # Create entry (use negative priority so higher values come first)
        self._enqueued_count += 1
        entry = QueueEntry(
            priority=-priority,
            candidate=candidate,
            enqueued_at=self._enqueued_count,
        )

        # Add to queue (maintains sorted order)
        self._queue.append(entry)
        self._queue.sort()

        # Track seen domain
        if self._deduplicate:
            self._seen_domains.add(domain_str)

        return True

    def enqueue_batch(
        self,
        candidates: Sequence[DiscoveryCandidate],
        priority: int = 0,
    ) -> int:
        """Add multiple candidates to the queue.

        Args:
            candidates: Candidates to enqueue.
            priority: Priority value for all candidates.

        Returns:
            Number of candidates actually enqueued.
        """
        count = 0
        for candidate in candidates:
            if self.enqueue(candidate, priority):
                count += 1
        return count

    def dequeue(self) -> Optional[DiscoveryCandidate]:
        """Remove and return the highest priority candidate.

        Returns:
            Highest priority candidate or None if queue is empty.
        """
        if not self._queue:
            return None

        entry = self._queue.pop(0)
        return entry.candidate

    def dequeue_batch(self, batch_size: int) -> list[DiscoveryCandidate]:
        """Remove and return multiple candidates.

        Args:
            batch_size: Maximum number to return.

        Returns:
            List of candidates (may be fewer if queue has less).
        """
        candidates = []
        for _ in range(batch_size):
            candidate = self.dequeue()
            if candidate is None:
                break
            candidates.append(candidate)
        return candidates

    def peek(self) -> Optional[DiscoveryCandidate]:
        """View the highest priority candidate without removing.

        Returns:
            Highest priority candidate or None if queue is empty.
        """
        if not self._queue:
            return None
        return self._queue[0].candidate

    def peek_batch(self, batch_size: int) -> list[DiscoveryCandidate]:
        """View multiple candidates without removing.

        Args:
            batch_size: Maximum number to return.

        Returns:
            List of candidates (may be fewer if queue has less).
        """
        candidates = []
        for entry in self._queue[:batch_size]:
            candidates.append(entry.candidate)
        return candidates

    def remove(self, candidate: DiscoveryCandidate) -> bool:
        """Remove a specific candidate from the queue.

        Args:
            candidate: Candidate to remove.

        Returns:
            True if candidate was removed.
        """
        domain_str = str(candidate.domain)
        for i, entry in enumerate(self._queue):
            if str(entry.candidate.domain) == domain_str:
                del self._queue[i]
                if self._deduplicate:
                    self._seen_domains.discard(domain_str)
                return True
        return False

    def clear(self) -> None:
        """Clear all candidates from the queue."""
        self._queue.clear()
        self._seen_domains.clear()

    def __len__(self) -> int:
        """Get the number of candidates in the queue."""
        return len(self._queue)

    def __contains__(self, candidate: DiscoveryCandidate) -> bool:
        """Check if a candidate is in the queue.

        Args:
            candidate: Candidate to check.

        Returns:
            True if candidate is in the queue.
        """
        return str(candidate.domain) in self._seen_domains

    def __iter__(self) -> Iterator[DiscoveryCandidate]:
        """Iterate over candidates in priority order."""
        for entry in self._queue:
            yield entry.candidate

    @property
    def capacity(self) -> Optional[int]:
        """Get the queue capacity."""
        return self._capacity

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0

    @property
    def is_full(self) -> bool:
        """Check if queue is at capacity."""
        if self._capacity is None:
            return False
        return len(self._queue) >= self._capacity

    def get_stats(self) -> dict[str, int]:
        """Get queue statistics.

        Returns:
            Dictionary of statistics.
        """
        priorities = [e.priority for e in self._queue]
        return {
            "size": len(self._queue),
            "capacity": self._capacity or 0,
            "unique_domains": len(self._seen_domains),
            "total_enqueued": self._enqueued_count,
            "min_priority": min(priorities) if priorities else 0,
            "max_priority": max(priorities) if priorities else 0,
        }


class PriorityQueue(CandidateQueue):
    """Priority queue with configurable priority extraction.

    Allows dynamic priority calculation based on candidate properties.
    """

    def __init__(
        self,
        capacity: Optional[int] = None,
        deduplicate: bool = True,
        priority_func: Optional[Callable[[DiscoveryCandidate], int]] = None,
    ) -> None:
        """Initialize priority queue.

        Args:
            capacity: Maximum queue size.
            deduplicate: Whether to deduplicate.
            priority_func: Function to calculate priority from candidate.
        """
        super().__init__(capacity, deduplicate)
        self._priority_func = priority_func or (lambda c: 0)

    def enqueue(self, candidate: DiscoveryCandidate) -> bool:
        """Add a candidate with dynamic priority.

        Args:
            candidate: Candidate to enqueue.

        Returns:
            True if candidate was enqueued.
        """
        priority = self._priority_func(candidate)
        return super().enqueue(candidate, priority)


class BoundedPriorityQueue(CandidateQueue):
    """Priority queue with bounded priority values.

    Ensures priorities remain within specified range.
    """

    def __init__(
        self,
        capacity: Optional[int] = None,
        deduplicate: bool = True,
        min_priority: int = 0,
        max_priority: int = 100,
    ) -> None:
        """Initialize bounded priority queue.

        Args:
            capacity: Maximum queue size.
            deduplicate: Whether to deduplicate.
            min_priority: Minimum priority value.
            max_priority: Maximum priority value.
        """
        super().__init__(capacity, deduplicate)
        self._min_priority = min_priority
        self._max_priority = max_priority

    def enqueue(self, candidate: DiscoveryCandidate, priority: int = 0) -> bool:
        """Add a candidate with bounded priority.

        Args:
            candidate: Candidate to enqueue.
            priority: Priority value (will be bounded).

        Returns:
            True if candidate was enqueued.
        """
        bounded_priority = max(self._min_priority, min(priority, self._max_priority))
        return super().enqueue(candidate, bounded_priority)
