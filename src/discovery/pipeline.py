"""Candidate processing pipeline.

This module defines the stages for processing candidates
through the discovery pipeline.
"""

from dataclasses import dataclass
from typing import Callable, Sequence

from .models import (
    CandidateStatus,
    DiscoveryCandidate,
    DiscoveryTask,
    ValidationResult,
)
from .validator import DomainValidator
from .filter import DomainFilter
from .scorer import DomainScorer


@dataclass
class PipelineContext:
    """Context passed through pipeline stages."""

    task: DiscoveryTask
    results: list[DiscoveryCandidate] = None
    stage: str = "initial"
    errors: list[str] = None
    warnings: list[str] = None

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.results is None:
            self.results = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class PipelineResult:
    """Result of pipeline execution."""

    candidates: tuple[DiscoveryCandidate, ...]
    accepted: int
    rejected: int
    filtered: int
    errors: int
    warnings: int
    duration_ms: float


class PipelineStage:
    """Base class for pipeline stages."""

    def __init__(self, name: str) -> None:
        """Initialize stage.

        Args:
            name: Name of the stage.
        """
        self._name = name

    @property
    def name(self) -> str:
        """Get stage name."""
        return self._name

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute the stage.

        Args:
            context: Pipeline context.

        Returns:
            Updated context.
        """
        raise NotImplementedError


class CollectStage(PipelineStage):
    """Stage for collecting candidates from sources.

    Note: This stage expects candidates to be pre-collected
    via the provider integration layer.
    """

    def __init__(self) -> None:
        """Initialize collect stage."""
        super().__init__("collect")

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Process collect stage.

        Args:
            context: Pipeline context.

        Returns:
            Updated context.
        """
        context.stage = self._name
        # Candidates are collected externally via provider integration
        return context


class ValidateStage(PipelineStage):
    """Stage for validating candidate format."""

    def __init__(
        self,
        validator: DomainValidator | None = None,
    ) -> None:
        """Initialize validate stage.

        Args:
            validator: Domain validator to use.
        """
        super().__init__("validate")
        self._validator = validator or DomainValidator()

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Process validation stage.

        Args:
            context: Pipeline context.

        Returns:
            Updated context.
        """
        context.stage = self._name
        validated = []

        for candidate in context.results:
            result = self._validator.validate(candidate)

            if result == ValidationResult.VALID:
                updated = DiscoveryCandidate(
                    domain=candidate.domain,
                    source=candidate.source,
                    discovered_at=candidate.discovered_at,
                    status=CandidateStatus.VALIDATED,
                    validation_result=result,
                    score=candidate.score,
                    confidence=candidate.confidence,
                    metadata=candidate.metadata,
                    parent_domain=candidate.parent_domain,
                )
                validated.append(updated)
            else:
                updated = DiscoveryCandidate(
                    domain=candidate.domain,
                    source=candidate.source,
                    discovered_at=candidate.discovered_at,
                    status=CandidateStatus.REJECTED,
                    validation_result=result,
                    score=candidate.score,
                    confidence=candidate.confidence,
                    metadata=candidate.metadata,
                    parent_domain=candidate.parent_domain,
                )
                validated.append(updated)

                if result in (ValidationResult.INVALID_FORMAT, ValidationResult.INVALID_SYNTAX):
                    context.warnings.append(f"Invalid format: {candidate.domain}")

        context.results = validated
        return context


class FilterStage(PipelineStage):
    """Stage for filtering candidates."""

    def __init__(
        self,
        filter_impl: DomainFilter | None = None,
    ) -> None:
        """Initialize filter stage.

        Args:
            filter_impl: Domain filter to use.
        """
        super().__init__("filter")
        self._filter = filter_impl or DomainFilter()

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Process filter stage.

        Args:
            context: Pipeline context.

        Returns:
            Updated context.
        """
        context.stage = self._name
        filtered = list(self._filter.filter_batch(context.results))
        context.results = filtered
        return context


class ScoreStage(PipelineStage):
    """Stage for scoring candidates."""

    def __init__(
        self,
        scorer: DomainScorer | None = None,
    ) -> None:
        """Initialize score stage.

        Args:
            scorer: Domain scorer to use.
        """
        super().__init__("score")
        self._scorer = scorer or DomainScorer()

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Process scoring stage.

        Args:
            context: Pipeline context.

        Returns:
            Updated context.
        """
        context.stage = self._name
        scored = list(self._scorer.score_batch(context.results))
        context.results = scored
        return context


class EnqueueStage(PipelineStage):
    """Stage for enqueuing candidates.

    Writes candidates to the candidate queue.
    """

    def __init__(
        self,
        enqueue_func: Callable[[DiscoveryCandidate], bool] | None = None,
    ) -> None:
        """Initialize enqueue stage.

        Args:
            enqueue_func: Function to enqueue a candidate.
        """
        super().__init__("enqueue")
        self._enqueue_func = enqueue_func or (lambda c: True)
        self._enqueued_count = 0

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Process enqueue stage.

        Args:
            context: Pipeline context.

        Returns:
            Updated context.
        """
        context.stage = self._name

        for candidate in context.results:
            if self._enqueue_func(candidate):
                self._enqueued_count += 1

        return context

    @property
    def enqueued_count(self) -> int:
        """Get number of candidates enqueued."""
        return self._enqueued_count


class DiscoveryPipeline:
    """Pipeline for processing discovery candidates.

    Orchestrates the stages: collect, validate, filter, score, enqueue.
    """

    def __init__(
        self,
        validator: DomainValidator | None = None,
        filter_impl: DomainFilter | None = None,
        scorer: DomainScorer | None = None,
        enqueue_func: Callable[[DiscoveryCandidate], bool] | None = None,
    ) -> None:
        """Initialize discovery pipeline.

        Args:
            validator: Domain validator.
            filter_impl: Domain filter.
            scorer: Domain scorer.
            enqueue_func: Function to enqueue candidates.
        """
        self._stages: list[PipelineStage] = [
            CollectStage(),
            ValidateStage(validator),
            FilterStage(filter_impl),
            ScoreStage(scorer),
            EnqueueStage(enqueue_func),
        ]

    def execute(
        self,
        task: DiscoveryTask,
        candidates: Sequence[DiscoveryCandidate],
    ) -> PipelineResult:
        """Execute the pipeline.

        Args:
            task: Discovery task.
            candidates: Initial candidates.

        Returns:
            Pipeline result.
        """
        import time
        start_time = time.monotonic()

        # Initialize context
        context = PipelineContext(
            task=task,
            results=list(candidates),
        )

        # Execute stages
        for stage in self._stages:
            context = stage.execute(context)

        end_time = time.monotonic()
        duration_ms = (end_time - start_time) * 1000

        # Calculate statistics
        accepted = sum(
            1 for c in context.results
            if c.status not in (CandidateStatus.REJECTED,)
        )
        rejected = sum(
            1 for c in context.results
            if c.status == CandidateStatus.REJECTED
        )
        filtered = sum(
            1 for c in context.results
            if c.status == CandidateStatus.FILTERED
        )

        return PipelineResult(
            candidates=tuple(context.results),
            accepted=accepted,
            rejected=rejected,
            filtered=filtered,
            errors=len(context.errors),
            warnings=len(context.warnings),
            duration_ms=duration_ms,
        )

    def add_stage(self, stage: PipelineStage) -> None:
        """Add a stage to the pipeline.

        Args:
            stage: Stage to add.
        """
        self._stages.append(stage)

    def insert_stage(self, index: int, stage: PipelineStage) -> None:
        """Insert a stage at a specific position.

        Args:
            index: Position to insert at.
            stage: Stage to insert.
        """
        self._stages.insert(index, stage)

    def remove_stage(self, name: str) -> bool:
        """Remove a stage by name.

        Args:
            name: Name of stage to remove.

        Returns:
            True if stage was removed.
        """
        for i, stage in enumerate(self._stages):
            if stage.name == name:
                del self._stages[i]
                return True
        return False

    def get_stage(self, name: str) -> PipelineStage | None:
        """Get a stage by name.

        Args:
            name: Stage name.

        Returns:
            Stage or None.
        """
        for stage in self._stages:
            if stage.name == name:
                return stage
        return None

    @property
    def stages(self) -> tuple[PipelineStage, ...]:
        """Get pipeline stages in order."""
        return tuple(self._stages)


class FilteredPipeline(DiscoveryPipeline):
    """Pipeline with configurable stage filtering.

    Allows disabling specific stages during execution.
    """

    def __init__(
        self,
        validator: DomainValidator | None = None,
        filter_impl: DomainFilter | None = None,
        scorer: DomainScorer | None = None,
        enqueue_func: Callable[[DiscoveryCandidate], bool] | None = None,
    ) -> None:
        """Initialize filtered pipeline.

        Args:
            validator: Domain validator.
            filter_impl: Domain filter.
            scorer: Domain scorer.
            enqueue_func: Function to enqueue candidates.
        """
        super().__init__(validator, filter_impl, scorer, enqueue_func)
        self._enabled_stages: set[str] = {
            "collect", "validate", "filter", "score", "enqueue"
        }

    def execute(
        self,
        task: DiscoveryTask,
        candidates: Sequence[DiscoveryCandidate],
    ) -> PipelineResult:
        """Execute pipeline with stage filtering.

        Args:
            task: Discovery task.
            candidates: Initial candidates.

        Returns:
            Pipeline result.
        """
        import time
        start_time = time.monotonic()

        # Initialize context
        context = PipelineContext(
            task=task,
            results=list(candidates),
        )

        # Execute enabled stages only
        for stage in self._stages:
            if stage.name in self._enabled_stages:
                context = stage.execute(context)

        end_time = time.monotonic()
        duration_ms = (end_time - start_time) * 1000

        # Calculate statistics
        accepted = sum(
            1 for c in context.results
            if c.status not in (CandidateStatus.REJECTED,)
        )
        rejected = sum(
            1 for c in context.results
            if c.status == CandidateStatus.REJECTED
        )
        filtered = sum(
            1 for c in context.results
            if c.status == CandidateStatus.FILTERED
        )

        return PipelineResult(
            candidates=tuple(context.results),
            accepted=accepted,
            rejected=rejected,
            filtered=filtered,
            errors=len(context.errors),
            warnings=len(context.warnings),
            duration_ms=duration_ms,
        )

    def enable_stage(self, name: str) -> None:
        """Enable a stage.

        Args:
            name: Stage name.
        """
        self._enabled_stages.add(name)

    def disable_stage(self, name: str) -> None:
        """Disable a stage.

        Args:
            name: Stage name.
        """
        self._enabled_stages.discard(name)

    def is_stage_enabled(self, name: str) -> bool:
        """Check if a stage is enabled.

        Args:
            name: Stage name.

        Returns:
            True if stage is enabled.
        """
        return name in self._enabled_stages
