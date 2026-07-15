"""Provider pipeline for executing discovery through providers.

This module provides the pipeline for executing discovery operations
through registered search providers.
"""

from datetime import datetime, timezone
from typing import Callable, Sequence

from .models import (
    DiscoveryCandidate,
    DiscoverySource,
    DiscoveryTask,
    SourceResult,
)
from .provider_adapter import ProviderAdapter
from .provider_registry import ProviderRegistry


class ProviderPipeline:
    """Pipeline for executing discovery through providers.

    Orchestrates the execution of discovery operations through
    one or more providers.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
    ) -> None:
        """Initialize provider pipeline.

        Args:
            registry: Provider registry.
        """
        self._registry = registry
        self._results: dict[str, list[SourceResult]] = {}

    def execute(
        self,
        task: DiscoveryTask,
        domains: Sequence[str] | None = None,
    ) -> list[SourceResult]:
        """Execute discovery for a task.

        Args:
            task: Discovery task.
            domains: Optional domains to discover.

        Returns:
            List of source results.
        """
        results = []

        # Get enabled providers sorted by priority
        providers = self._registry.get_sorted_by_priority()

        for provider in providers:
            source_result = self._execute_provider(
                provider,
                task,
                domains,
            )
            results.append(source_result)

        # Store results
        self._results[task.task_id] = results

        return results

    def _execute_provider(
        self,
        provider: ProviderAdapter,
        task: DiscoveryTask,
        domains: Sequence[str] | None,
    ) -> SourceResult:
        """Execute discovery for a single provider.

        Args:
            provider: Provider to execute.
            task: Discovery task.
            domains: Domains to discover.

        Returns:
            Source result.
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Create mock response for testing
            response = provider.create_mock_response(domains)

            # Convert to candidates
            candidates = provider.to_discovery_candidates(response)

            # Add metadata from task
            enriched_candidates = []
            for candidate in candidates:
                # Create enriched candidate
                enriched = DiscoveryCandidate(
                    domain=candidate.domain,
                    source=provider.provider_name,
                    discovered_at=candidate.discovered_at,
                    status=candidate.status,
                    validation_result=candidate.validation_result,
                    score=candidate.score,
                    confidence=candidate.confidence,
                    metadata=candidate.metadata + (("task_id", task.task_id),),
                    parent_domain=candidate.parent_domain,
                )
                enriched_candidates.append(enriched)

            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return SourceResult(
                source_name=provider.provider_name,
                candidates=tuple(enriched_candidates),
                duration_ms=duration_ms,
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return SourceResult(
                source_name=provider.provider_name,
                candidates=(),
                duration_ms=duration_ms,
                errors=1,
                message=str(e),
            )

    def get_results(self, task_id: str) -> list[SourceResult]:
        """Get results for a task.

        Args:
            task_id: Task ID.

        Returns:
            List of source results.
        """
        return self._results.get(task_id, [])

    def clear_results(self, task_id: str | None = None) -> None:
        """Clear stored results.

        Args:
            task_id: Optional task ID. If None, clears all.
        """
        if task_id is None:
            self._results.clear()
        else:
            self._results.pop(task_id, None)

    def aggregate_candidates(
        self,
        results: Sequence[SourceResult],
    ) -> list[DiscoveryCandidate]:
        """Aggregate candidates from multiple results.

        Args:
            results: Source results.

        Returns:
            Aggregated and deduplicated candidates.
        """
        all_candidates: list[DiscoveryCandidate] = []
        seen_domains: set[str] = set()

        for result in results:
            for candidate in result.candidates:
                domain_str = str(candidate.domain)
                if domain_str not in seen_domains:
                    seen_domains.add(domain_str)
                    all_candidates.append(candidate)

        return all_candidates

    def get_statistics(
        self,
        results: Sequence[SourceResult],
    ) -> dict[str, int | float]:
        """Get statistics from results.

        Args:
            results: Source results.

        Returns:
            Statistics dictionary.
        """
        total_candidates = 0
        total_errors = 0
        total_warnings = 0
        total_duration_ms = 0.0
        providers_used = 0

        for result in results:
            total_candidates += len(result.candidates)
            total_errors += result.errors
            total_warnings += result.warnings
            total_duration_ms += result.duration_ms
            if result.candidates or result.errors:
                providers_used += 1

        return {
            "total_candidates": total_candidates,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "total_duration_ms": total_duration_ms,
            "providers_used": providers_used,
            "avg_duration_ms": total_duration_ms / providers_used if providers_used else 0.0,
        }


class FilteredProviderPipeline(ProviderPipeline):
    """Provider pipeline with result filtering.

    Applies filtering to results during pipeline execution.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        filter_func: Callable[[DiscoveryCandidate], bool] | None = None,
    ) -> None:
        """Initialize filtered pipeline.

        Args:
            registry: Provider registry.
            filter_func: Optional filter function.
        """
        super().__init__(registry)
        self._filter_func = filter_func or (lambda c: True)

    def set_filter(
        self,
        filter_func: Callable[[DiscoveryCandidate], bool],
    ) -> None:
        """Set the result filter.

        Args:
            filter_func: Filter function.
        """
        self._filter_func = filter_func

    def aggregate_candidates(
        self,
        results: Sequence[SourceResult],
    ) -> list[DiscoveryCandidate]:
        """Aggregate candidates with filtering.

        Args:
            results: Source results.

        Returns:
            Filtered and deduplicated candidates.
        """
        all_candidates = super().aggregate_candidates(results)

        # Apply filter
        filtered = [
            c for c in all_candidates
            if self._filter_func(c)
        ]

        return filtered


class FallbackProviderPipeline(ProviderPipeline):
    """Provider pipeline with fallback logic.

    Continues with remaining providers if one fails.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        min_success_providers: int = 1,
    ) -> None:
        """Initialize fallback pipeline.

        Args:
            registry: Provider registry.
            min_success_providers: Minimum providers that must succeed.
        """
        super().__init__(registry)
        self._min_success_providers = min_success_providers

    def execute(
        self,
        task: DiscoveryTask,
        domains: Sequence[str] | None = None,
    ) -> list[SourceResult]:
        """Execute with fallback logic.

        Args:
            task: Discovery task.
            domains: Optional domains to discover.

        Returns:
            List of source results.
        """
        results = []
        success_count = 0

        # Get enabled providers
        providers = self._registry.get_sorted_by_priority()

        for provider in providers:
            source_result = self._execute_provider(provider, task, domains)
            results.append(source_result)

            # Track successes
            if source_result.errors == 0 and len(source_result.candidates) > 0:
                success_count += 1

            # Check if we have enough successes
            if success_count >= self._min_success_providers:
                # Continue executing remaining providers but don't fail
                pass

        # Store results
        self._results[task.task_id] = results

        return results

    def get_successful_providers(self, results: list[SourceResult]) -> list[str]:
        """Get list of successful providers.

        Args:
            results: Source results.

        Returns:
            List of successful provider names.
        """
        return [
            r.source_name
            for r in results
            if r.errors == 0 and len(r.candidates) > 0
        ]

    def has_sufficient_results(self, results: list[SourceResult]) -> bool:
        """Check if there are sufficient successful results.

        Args:
            results: Source results.

        Returns:
            True if enough providers succeeded.
        """
        success_count = sum(
            1 for r in results
            if r.errors == 0 and len(r.candidates) > 0
        )
        return success_count >= self._min_success_providers


class BatchedProviderPipeline(ProviderPipeline):
    """Provider pipeline with batched execution.

    Processes domains in batches across providers.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        batch_size: int = 100,
    ) -> None:
        """Initialize batched pipeline.

        Args:
            registry: Provider registry.
            batch_size: Size of each batch.
        """
        super().__init__(registry)
        self._batch_size = batch_size

    def execute_batched(
        self,
        task: DiscoveryTask,
        domains: Sequence[str],
    ) -> list[SourceResult]:
        """Execute discovery in batches.

        Args:
            task: Discovery task.
            domains: Domains to discover.

        Returns:
            List of source results.
        """
        results = []
        providers = self._registry.get_sorted_by_priority()

        # Split domains into batches
        batches = self._split_batches(list(domains))

        for provider in providers:
            for batch_num, batch in enumerate(batches):
                source_result = self._execute_provider(
                    provider,
                    task,
                    batch,
                )
                results.append(source_result)

        # Store results
        self._results[task.task_id] = results

        return results

    def _split_batches(self, items: list[str]) -> list[list[str]]:
        """Split items into batches.

        Args:
            items: Items to split.

        Returns:
            List of batches.
        """
        batches = []
        for i in range(0, len(items), self._batch_size):
            batches.append(items[i:i + self._batch_size])
        return batches

    def get_batch_count(self, item_count: int) -> int:
        """Get number of batches for item count.

        Args:
            item_count: Number of items.

        Returns:
            Number of batches.
        """
        return (item_count + self._batch_size - 1) // self._batch_size
