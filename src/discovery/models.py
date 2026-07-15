"""Data models for the Discovery Engine.

This module contains immutable dataclasses and enums defining
the contracts for discovery operations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import FrozenSet

# Import core enums to maintain backward compatibility
from src.core import (
    CandidateStatus,
    DiscoveryStatus,
    SourceType,
)


class ValidationResult(Enum):
    """Result of candidate validation."""

    VALID = auto()
    INVALID_FORMAT = auto()
    INVALID_SYNTAX = auto()
    INVALID_TLD = auto()
    RESERVED_DOMAIN = auto()
    TOO_SHORT = auto()
    TOO_LONG = auto()


@dataclass(frozen=True)
class Domain:
    """A domain name representation."""

    name: str
    tld: str | None = None
    subdomain: str | None = None

    def __post_init__(self) -> None:
        """Validate domain name."""
        if not self.name:
            raise ValueError("Domain name cannot be empty")

    @property
    def full_domain(self) -> str:
        """Get the full domain string."""
        parts = []
        if self.subdomain:
            parts.append(self.subdomain)
        parts.append(self.name)
        return ".".join(parts)

    def __str__(self) -> str:
        """String representation."""
        return self.full_domain


@dataclass(frozen=True)
class DiscoverySource:
    """Information about a discovery source."""

    name: str
    source_type: SourceType
    description: str | None = None
    priority: int = 0
    rate_limit: int = 0
    timeout_seconds: float = 30.0
    enabled: bool = True
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @property
    def is_passive(self) -> bool:
        """Check if source is passive."""
        return self.source_type in (
            SourceType.PASSIVE,
            SourceType.PASSIVE_DNS,
            SourceType.CERTIFICATE_TRANSPARENCY,
        )


@dataclass(frozen=True)
class DiscoveryCandidate:
    """A discovered domain candidate."""

    domain: Domain
    source: str
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: CandidateStatus = CandidateStatus.DISCOVERED
    validation_result: ValidationResult | None = None
    score: float | None = None
    confidence: float | None = None
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    parent_domain: str | None = None

    @property
    def is_valid(self) -> bool:
        """Check if candidate is valid."""
        return (
            self.validation_result is None
            or self.validation_result == ValidationResult.VALID
        )

    @property
    def domain_string(self) -> str:
        """Get the domain as a string."""
        return str(self.domain)


@dataclass(frozen=True)
class DiscoveryTask:
    """Defines what to discover and how."""

    task_id: str
    seed_domains: tuple[str, ...]
    keywords: tuple[str, ...] = field(default_factory=tuple)
    sources: tuple[str, ...] = field(default_factory=tuple)
    max_candidates: int = 1000
    timeout_seconds: float = 300.0
    retry_count: int = 3
    batch_size: int = 100
    score_threshold: float = 0.0
    include_subdomains: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: int = 0
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate task."""
        if not self.seed_domains and not self.keywords:
            raise ValueError("Task must have at least one seed domain or keyword")
        if self.max_candidates < 1:
            raise ValueError("max_candidates must be at least 1")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")

    @property
    def has_seeds(self) -> bool:
        """Check if task has seed domains."""
        return len(self.seed_domains) > 0

    @property
    def has_keywords(self) -> bool:
        """Check if task has keywords."""
        return len(self.keywords) > 0


@dataclass(frozen=True)
class DiscoveryStatistics:
    """Metrics about a discovery operation."""

    task_id: str
    started_at: datetime
    ended_at: datetime | None = None
    status: DiscoveryStatus = DiscoveryStatus.PENDING
    candidates_discovered: int = 0
    candidates_validated: int = 0
    candidates_scored: int = 0
    candidates_filtered: int = 0
    candidates_rejected: int = 0
    duplicates: int = 0
    source_stats: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    errors: int = 0
    warnings: int = 0
    retries: int = 0

    @property
    def duration_seconds(self) -> float | None:
        """Calculate duration in seconds."""
        if self.ended_at and self.started_at:
            delta = self.ended_at - self.started_at
            return delta.total_seconds()
        return None

    @property
    def success_rate(self) -> float | None:
        """Calculate success rate."""
        total = self.candidates_discovered
        if total == 0:
            return None
        return (self.candidates_validated / total) * 100


@dataclass(frozen=True)
class DiscoveryProgress:
    """Progress tracking for discovery operations."""

    task_id: str
    status: DiscoveryStatus
    total_batches: int
    completed_batches: int
    total_candidates: int
    current_batch: int
    current_source: str | None = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    next_retry_at: datetime | None = None
    message: str | None = None

    @property
    def percent_complete(self) -> float:
        """Calculate percent complete."""
        if self.total_batches == 0:
            return 0.0
        return (self.completed_batches / self.total_batches) * 100

    @property
    def is_finished(self) -> bool:
        """Check if discovery is finished."""
        return self.status in (
            DiscoveryStatus.COMPLETED,
            DiscoveryStatus.FAILED,
            DiscoveryStatus.CANCELLED,
        )


@dataclass(frozen=True)
class DiscoveryBatch:
    """A batch of candidates for processing."""

    batch_id: str
    task_id: str
    candidates: tuple[DiscoveryCandidate, ...]
    source: str
    batch_number: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: float | None = None

    @property
    def count(self) -> int:
        """Get number of candidates in batch."""
        return len(self.candidates)

    @property
    def is_empty(self) -> bool:
        """Check if batch is empty."""
        return len(self.candidates) == 0


@dataclass(frozen=True)
class DiscoveryConfiguration:
    """Runtime configuration for discovery."""

    max_candidates: int = 1000
    max_candidates_per_source: int = 500
    timeout_seconds: float = 300.0
    default_retry_count: int = 3
    default_batch_size: int = 100
    default_score_threshold: float = 0.0
    default_timeout_per_source: float = 30.0
    enable_deduplication: bool = True
    enable_scoring: bool = True
    enable_filtering: bool = True
    max_retries_per_source: int = 3
    backoff_multiplier: float = 2.0
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    rate_limit_window_seconds: float = 60.0
    max_rate_limit_errors: int = 10


@dataclass(frozen=True)
class DiscoveryResult:
    """Aggregated discovery results."""

    task_id: str
    status: DiscoveryStatus
    candidates: tuple[DiscoveryCandidate, ...]
    statistics: DiscoveryStatistics
    configuration: DiscoveryConfiguration
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: str | None = None

    @property
    def total_candidates(self) -> int:
        """Get total number of candidates."""
        return len(self.candidates)

    @property
    def valid_candidates(self) -> tuple[DiscoveryCandidate, ...]:
        """Get only valid candidates."""
        return tuple(c for c in self.candidates if c.is_valid)

    @property
    def failed(self) -> bool:
        """Check if discovery failed."""
        return self.status == DiscoveryStatus.FAILED

    @property
    def success(self) -> bool:
        """Check if discovery succeeded."""
        return self.status == DiscoveryStatus.COMPLETED


@dataclass(frozen=True)
class SourceResult:
    """Result from a single discovery source."""

    source_name: str
    candidates: tuple[DiscoveryCandidate, ...]
    duration_ms: float
    errors: int = 0
    warnings: int = 0
    status_code: int | None = None
    message: str | None = None


@dataclass(frozen=True)
class FilterRule:
    """A rule for filtering candidates."""

    name: str
    pattern: str
    is_exclusion: bool = True
    description: str | None = None
    priority: int = 0

    @property
    def is_inclusion(self) -> bool:
        """Check if this is an inclusion rule."""
        return not self.is_exclusion
