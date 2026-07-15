"""Core enums for Kancell Shield v3.

Enumeration types for domain model.
"""

from enum import Enum


class PriorityLevel(str, Enum):
    """Priority levels for tasks and candidates."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_value(cls, value: str) -> "PriorityLevel":
        """Create from string value.

        Args:
            value: String value.

        Returns:
            PriorityLevel enum value.
        """
        for level in cls:
            if level.value == value.lower():
                return level
        return cls.NORMAL

    @property
    def sort_order(self) -> int:
        """Get sort order for priority level.

        Returns:
            Integer sort order (higher = more important).
        """
        orders = {
            PriorityLevel.LOW: 0,
            PriorityLevel.NORMAL: 1,
            PriorityLevel.HIGH: 2,
            PriorityLevel.CRITICAL: 3,
        }
        return orders.get(self, 0)


class DiscoveryStatus(str, Enum):
    """Status of discovery operations."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """Check if status is terminal.

        Returns:
            True if status is terminal.
        """
        return self in (
            DiscoveryStatus.COMPLETED,
            DiscoveryStatus.FAILED,
            DiscoveryStatus.STOPPED,
            DiscoveryStatus.CANCELLED,
        )

    @property
    def is_active(self) -> bool:
        """Check if status is active.

        Returns:
            True if status is active.
        """
        return self in (
            DiscoveryStatus.RUNNING,
            DiscoveryStatus.PAUSED,
        )


class ProviderStatus(str, Enum):
    """Status of search providers."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"

    @property
    def is_available(self) -> bool:
        """Check if provider is available.

        Returns:
            True if provider can be used.
        """
        return self in (
            ProviderStatus.HEALTHY,
            ProviderStatus.DEGRADED,
        )


class CandidateStatus(str, Enum):
    """Status of discovery candidates."""

    DISCOVERED = "discovered"
    VALIDATED = "validated"
    SCORED = "scored"
    FILTERED = "filtered"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    ENQUEUED = "enqueued"
    PROCESSED = "processed"

    @property
    def is_terminal(self) -> bool:
        """Check if status is terminal.

        Returns:
            True if status is terminal.
        """
        return self in (
            CandidateStatus.REJECTED,
            CandidateStatus.DUPLICATE,
            CandidateStatus.PROCESSED,
        )

    @property
    def is_valid(self) -> bool:
        """Check if status indicates valid candidate.

        Returns:
            True if candidate passed processing.
        """
        return self in (
            CandidateStatus.VALIDATED,
            CandidateStatus.SCORED,
            CandidateStatus.FILTERED,
            CandidateStatus.ENQUEUED,
            CandidateStatus.PROCESSED,
        )


class ScoreLevel(str, Enum):
    """Score levels for classification."""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_score(cls, score: float) -> "ScoreLevel":
        """Create from numeric score.

        Args:
            score: Score value (0.0 to 1.0).

        Returns:
            ScoreLevel enum value.
        """
        if score < 0.0:
            return cls.UNKNOWN
        if score < 0.25:
            return cls.LOW
        if score < 0.5:
            return cls.MEDIUM
        if score < 0.75:
            return cls.HIGH
        return cls.CRITICAL

    @property
    def risk_weight(self) -> float:
        """Get risk weight for score level.

        Returns:
            Risk weight value.
        """
        weights = {
            ScoreLevel.UNKNOWN: 0.0,
            ScoreLevel.LOW: 0.25,
            ScoreLevel.MEDIUM: 0.5,
            ScoreLevel.HIGH: 0.75,
            ScoreLevel.CRITICAL: 1.0,
        }
        return weights.get(self, 0.0)
