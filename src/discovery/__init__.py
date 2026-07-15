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
]
