"""Strongly typed identifiers for Kancell Shield v3.

These provide type safety over plain strings.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderId:
    """Unique identifier for a search provider."""

    value: str

    def __post_init__(self) -> None:
        """Validate the identifier."""
        if not self.value:
            raise ValueError("ProviderId cannot be empty")
        if len(self.value) > 100:
            raise ValueError("ProviderId too long")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class CandidateId:
    """Unique identifier for a discovery candidate."""

    value: str

    def __post_init__(self) -> None:
        """Validate the identifier."""
        if not self.value:
            raise ValueError("CandidateId cannot be empty")
        if len(self.value) > 200:
            raise ValueError("CandidateId too long")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class TaskId:
    """Unique identifier for a discovery task."""

    value: str

    def __post_init__(self) -> None:
        """Validate the identifier."""
        if not self.value:
            raise ValueError("TaskId cannot be empty")
        if len(self.value) > 200:
            raise ValueError("TaskId too long")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class BatchId:
    """Unique identifier for a processing batch."""

    value: str

    def __post_init__(self) -> None:
        """Validate the identifier."""
        if not self.value:
            raise ValueError("BatchId cannot be empty")
        if len(self.value) > 200:
            raise ValueError("BatchId too long")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class EventId:
    """Unique identifier for an event."""

    value: str

    def __post_init__(self) -> None:
        """Validate the identifier."""
        if not self.value:
            raise ValueError("EventId cannot be empty")
        if len(self.value) > 200:
            raise ValueError("EventId too long")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class SourceId:
    """Unique identifier for a discovery source."""

    value: str

    def __post_init__(self) -> None:
        """Validate the identifier."""
        if not self.value:
            raise ValueError("SourceId cannot be empty")
        if len(self.value) > 100:
            raise ValueError("SourceId too long")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class RuleId:
    """Unique identifier for a filter rule."""

    value: str

    def __post_init__(self) -> None:
        """Validate the identifier."""
        if not self.value:
            raise ValueError("RuleId cannot be empty")
        if len(self.value) > 100:
            raise ValueError("RuleId too long")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value
