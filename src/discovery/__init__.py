"""Discovery Engine for Kancell Shield v3.

This module provides the architecture for discovering
domain candidates for malicious activity evaluation.
"""

from .models import (
    CandidateStatus,
    DiscoveryBatch,
    DiscoveryCandidate,
    DiscoveryConfiguration,
    DiscoveryProgress,
    DiscoveryResult,
    DiscoverySource,
    DiscoveryStatistics,
    DiscoveryStatus,
    DiscoveryTask,
    Domain,
    FilterRule,
    SourceResult,
    SourceType,
    ValidationResult,
)

from .interfaces import (
    CandidateFilter,
    CandidateScorer,
    CandidateValidator,
    DiscoveryCollector,
    DiscoveryEngine,
    DiscoveryPipeline,
    DiscoveryScheduler,
    DiscoverySourceProvider,
    DiscoveryState,
)

from .exceptions import (
    CollectorError,
    ConfigurationError,
    DiscoveryError,
    FilterError,
    MaxCandidatesReachedError,
    SchedulerError,
    ScorerError,
    SourceNotFoundError,
    StateError,
    TaskNotFoundError,
    ValidationError,
)

from .engine import DiscoveryEngineImpl
from .scheduler import DiscoverySchedulerImpl, PriorityScheduler
from .collector import DiscoveryCollectorImpl
from .validator import DomainValidator
from .filter import DomainFilter, ExclusionFilter, InclusionFilter
from .scorer import DomainScorer, DeterministicScorer

from .provider_adapter import (
    ProviderAdapter,
    MockSearchProviderAdapter,
    ProviderCapabilityAdapter,
    ProviderHealthAdapter,
)

from .provider_registry import (
    ProviderRegistry,
    DefaultProviderRegistry,
    ProviderConfig,
    ProviderRegistryBuilder,
)

from .provider_pipeline import (
    ProviderPipeline,
    FilteredProviderPipeline,
    FallbackProviderPipeline,
    BatchedProviderPipeline,
)

from .provider_selector import (
    ProviderSelector,
    RoundRobinSelector,
    WeightedSelector,
    SourceTypeSelector,
)

__all__ = [
    # Enums
    "CandidateStatus",
    "DiscoveryStatus",
    "SourceType",
    "ValidationResult",
    # Models
    "Domain",
    "DiscoveryBatch",
    "DiscoveryCandidate",
    "DiscoveryConfiguration",
    "DiscoveryProgress",
    "DiscoveryResult",
    "DiscoverySource",
    "DiscoveryStatistics",
    "DiscoveryTask",
    "FilterRule",
    "SourceResult",
    # Interfaces
    "CandidateFilter",
    "CandidateScorer",
    "CandidateValidator",
    "DiscoveryCollector",
    "DiscoveryEngine",
    "DiscoveryPipeline",
    "DiscoveryScheduler",
    "DiscoverySourceProvider",
    "DiscoveryState",
    # Exceptions
    "CollectorError",
    "ConfigurationError",
    "DiscoveryError",
    "FilterError",
    "MaxCandidatesReachedError",
    "SchedulerError",
    "ScorerError",
    "SourceNotFoundError",
    "StateError",
    "TaskNotFoundError",
    "ValidationError",
    # Core Implementations
    "DiscoveryEngineImpl",
    "DiscoverySchedulerImpl",
    "PriorityScheduler",
    "DiscoveryCollectorImpl",
    "DomainValidator",
    "DomainFilter",
    "ExclusionFilter",
    "InclusionFilter",
    "DomainScorer",
    "DeterministicScorer",
    # Provider Integration
    "ProviderAdapter",
    "MockSearchProviderAdapter",
    "ProviderCapabilityAdapter",
    "ProviderHealthAdapter",
    "ProviderRegistry",
    "DefaultProviderRegistry",
    "ProviderConfig",
    "ProviderRegistryBuilder",
    "ProviderPipeline",
    "FilteredProviderPipeline",
    "FallbackProviderPipeline",
    "BatchedProviderPipeline",
    "ProviderSelector",
    "RoundRobinSelector",
    "WeightedSelector",
    "SourceTypeSelector",
]
