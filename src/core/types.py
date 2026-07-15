"""Core types for Kancell Shield v3.

Type aliases and protocol definitions.
"""

from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from .enums import (
    CandidateStatus,
    DiscoveryStatus,
    PriorityLevel,
    ProviderStatus,
    ScoreLevel,
)
from .identifiers import (
    BatchId,
    CandidateId,
    EventId,
    ProviderId,
    RuleId,
    SourceId,
    TaskId,
)
from .value_objects import (
    ConfidenceScore,
    Domain,
    Hostname,
    Priority,
    Timestamp,
    URL,
)


# Primitive types
DomainName = str
HostnameStr = str
URLStr = str
EmailStr = str
IPAddress = str
JSON = Dict[str, Any]
Metadata = Dict[str, Any]

# Numeric types
ScoreValue = float  # 0.0 to 1.0
PriorityValue = int  # -100 to 100
ConfidenceValue = float  # 0.0 to 1.0
Percentage = int  # 0 to 100

# Identifier types
ProviderId = ProviderId
CandidateId = CandidateId
TaskId = TaskId
BatchId = BatchId
EventId = EventId
SourceId = SourceId
RuleId = RuleId

# Value object types
Domain = Domain
Hostname = Hostname
URL = URL
ConfidenceScore = ConfidenceScore
Priority = Priority
Timestamp = Timestamp

# Collection types
DomainList = List[Domain]
DomainSet = Set[Domain]
CandidateList = List[CandidateId]
TaskList = List[TaskId]
ProviderList = List[ProviderId]

# Status types
StatusValue = str
DiscoveryStatus = DiscoveryStatus
ProviderStatus = ProviderStatus
CandidateStatus = CandidateStatus
ScoreLevel = ScoreLevel
PriorityLevel = PriorityLevel

# Filter types
FilterFunc = Callable[[Domain], bool]
ScoreFunc = Callable[[Domain], float]
ValidationFunc = Callable[[Domain], bool]

# Handler types
EventHandler = Callable[[Any], None]
ErrorHandler = Callable[[Exception], None]

# Configuration types
ConfigDict = Dict[str, Any]
ConfigValue = Union[str, int, float, bool, None]

# Result types
ResultValue = Union[Domain, List[Domain], None]
ErrorValue = Optional[str]

# Serialization types
SerializedDict = Dict[str, Any]
SerializedList = List[SerializedDict]

# Time types
DurationMs = float
TimestampValue = Timestamp

# Bounds types
MinBound = int
MaxBound = int
BoundTuple = Tuple[int, int]

# Provider types
ProviderName = str
ProviderType = str
ProviderConfig = Dict[str, Any]

# Rule types
RulePattern = str
RuleName = str
RuleType = str
FilterRule = Dict[str, Any]

# Metric types
MetricName = str
MetricValue = Union[int, float]
MetricDict = Dict[MetricName, MetricValue]

# Event types
EventType = str
EventData = Dict[str, Any]
EventList = List[Any]


# Provider data classes (for concrete implementations)
class ProviderRequest:
    """Provider request data class."""

    def __init__(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
    ) -> None:
        self.query = query
        self.page = page
        self.page_size = page_size


class ProviderResponse:
    """Provider response data class."""

    def __init__(
        self,
        results: Tuple[Any, ...],
        total_count: int = 0,
        page: int = 1,
        has_more: bool = False,
    ) -> None:
        self.results = results
        self.total_count = total_count
        self.page = page
        self.has_more = has_more


class ProviderHealthStatus:
    """Provider health status data class."""

    def __init__(
        self,
        is_healthy: bool = True,
        latency_ms: float = 0.0,
        error_message: Optional[str] = None,
    ) -> None:
        self.is_healthy = is_healthy
        self.latency_ms = latency_ms
        self.error_message = error_message


class ProviderCapabilities:
    """Provider capabilities data class."""

    def __init__(
        self,
        supports_pagination: bool = True,
        supports_filters: bool = False,
        max_page_size: int = 100,
    ) -> None:
        self.supports_pagination = supports_pagination
        self.supports_filters = supports_filters
        self.max_page_size = max_page_size


class ProviderFeatureFlags:
    """Provider feature flags data class."""

    def __init__(
        self,
        enable_cache: bool = False,
        enable_retry: bool = True,
        enable_rate_limit: bool = True,
    ) -> None:
        self.enable_cache = enable_cache
        self.enable_retry = enable_retry
        self.enable_rate_limit = enable_rate_limit


# Protocol definitions for structural typing

class DiscoveryTask:
    """Protocol for discovery task."""

    task_id: TaskId
    status: DiscoveryStatus
    created_at: Timestamp
    updated_at: Timestamp

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...


class SearchProvider:
    """Protocol for search provider."""

    provider_id: ProviderId
    name: str
    status: ProviderStatus

    def search(self, query: str) -> List[Domain]: ...
    def health_check(self) -> bool: ...


class CandidateProcessor:
    """Protocol for candidate processor."""

    def validate(self, candidate: Domain) -> bool: ...
    def score(self, candidate: Domain) -> float: ...
    def filter(self, candidate: Domain) -> bool: ...


class EventEmitter:
    """Protocol for event emitter."""

    def emit(self, event_type: str, data: EventData) -> None: ...
    def on(self, event_type: str, handler: EventHandler) -> None: ...
    def off(self, event_type: str, handler: EventHandler) -> None: ...


# Type guard functions

def is_valid_domain(value: Any) -> bool:
    """Check if value is a valid Domain."""
    return isinstance(value, Domain)


def is_valid_url(value: Any) -> bool:
    """Check if value is a valid URL."""
    return isinstance(value, URL)


def is_valid_score(value: Any) -> bool:
    """Check if value is a valid score (0.0 to 1.0)."""
    return isinstance(value, (int, float)) and 0.0 <= value <= 1.0


def is_valid_priority(value: Any) -> bool:
    """Check if value is a valid priority."""
    return isinstance(value, int) and -100 <= value <= 100


def is_terminal_status(status: DiscoveryStatus) -> bool:
    """Check if status is terminal."""
    return status in (
        DiscoveryStatus.COMPLETED,
        DiscoveryStatus.FAILED,
        DiscoveryStatus.STOPPED,
        DiscoveryStatus.CANCELLED,
    )


def is_active_status(status: DiscoveryStatus) -> bool:
    """Check if status is active."""
    return status in (
        DiscoveryStatus.RUNNING,
        DiscoveryStatus.PAUSED,
    )
