"""Provider selector for deterministic provider selection.

This module provides deterministic selection logic for choosing
providers based on configuration, capabilities, and health.
"""

from typing import Sequence

from .models import DiscoverySource, SourceType
from .provider_adapter import (
    ProviderAdapter,
    ProviderCapabilityAdapter,
    ProviderHealthAdapter,
)
from .provider_registry import ProviderRegistry


class ProviderSelector:
    """Selector for choosing providers deterministically.

    Selects providers based on configuration and requirements
    without randomness.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        health_adapter: ProviderHealthAdapter | None = None,
        capability_adapter: ProviderCapabilityAdapter | None = None,
    ) -> None:
        """Initialize provider selector.

        Args:
            registry: Provider registry.
            health_adapter: Health adapter for health checks.
            capability_adapter: Capability adapter for capability checks.
        """
        self._registry = registry
        self._health_adapter = health_adapter or ProviderHealthAdapter()
        self._capability_adapter = capability_adapter or ProviderCapabilityAdapter()

    def select_providers(
        self,
        count: int | None = None,
        source_types: Sequence[SourceType] | None = None,
        require_healthy: bool = True,
    ) -> list[ProviderAdapter]:
        """Select providers deterministically.

        Args:
            count: Maximum number of providers to select.
            source_types: Filter by source types.
            require_healthy: Only select healthy providers.

        Returns:
            List of selected providers.
        """
        # Get enabled providers sorted by priority
        providers = self._registry.get_sorted_by_priority()

        # Filter by source type if specified
        if source_types:
            providers = [
                p for p in providers
                if p.provider_type in source_types
            ]

        # Filter by health if required
        if require_healthy:
            providers = [
                p for p in providers
                if self._health_adapter.is_available(p.provider_name)
            ]

        # Filter by capability if requirements are set
        if self._capability_adapter.get_requirements():
            providers = [
                p for p in providers
                if self._check_capabilities(p)
            ]

        # Limit count
        if count is not None:
            providers = providers[:count]

        return providers

    def select_best_provider(
        self,
        source_types: Sequence[SourceType] | None = None,
    ) -> ProviderAdapter | None:
        """Select the best single provider.

        Args:
            source_types: Filter by source types.

        Returns:
            Best provider or None.
        """
        providers = self.select_providers(
            count=1,
            source_types=source_types,
        )
        return providers[0] if providers else None

    def select_by_priority(
        self,
        min_priority: int = 0,
        source_types: Sequence[SourceType] | None = None,
    ) -> list[ProviderAdapter]:
        """Select providers by priority threshold.

        Args:
            min_priority: Minimum priority threshold.
            source_types: Filter by source types.

        Returns:
            List of providers meeting threshold.
        """
        all_providers = self.select_providers(source_types=source_types)

        return [
            p for p in all_providers
            if self._registry.get_priority(p.provider_name) >= min_priority
        ]

    def _check_capabilities(self, provider: ProviderAdapter) -> bool:
        """Check if provider meets capability requirements.

        Args:
            provider: Provider to check.

        Returns:
            True if provider meets requirements.
        """
        capabilities = provider.get_capabilities()
        matches, _ = self._capability_adapter.matches_capabilities(capabilities)
        return matches

    def get_provider_info(self, name: str) -> dict[str, object]:
        """Get information about a provider.

        Args:
            name: Provider name.

        Returns:
            Provider information dictionary.
        """
        provider = self._registry.get(name)
        if provider is None:
            return {}

        health = self._health_adapter.get_health_status(name)

        return {
            "name": provider.provider_name,
            "type": provider.provider_type.name,
            "enabled": self._registry.is_enabled(name),
            "priority": self._registry.get_priority(name),
            "healthy": self._health_adapter.is_available(name),
            "health_status": health.status.name if health else None,
            "consecutive_failures": health.consecutive_failures if health else 0,
        }

    def get_all_provider_info(self) -> list[dict[str, object]]:
        """Get information about all providers.

        Returns:
            List of provider information dictionaries.
        """
        return [
            self.get_provider_info(name)
            for name in self._registry.get_all()
        ]


class RoundRobinSelector(ProviderSelector):
    """Selector with round-robin provider selection.

    Distributes load across providers deterministically.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        health_adapter: ProviderHealthAdapter | None = None,
        capability_adapter: ProviderCapabilityAdapter | None = None,
    ) -> None:
        """Initialize round-robin selector.

        Args:
            registry: Provider registry.
            health_adapter: Health adapter.
            capability_adapter: Capability adapter.
        """
        super().__init__(registry, health_adapter, capability_adapter)
        self._round_robin_index: dict[str, int] = {}

    def select_round_robin(
        self,
        task_id: str,
        count: int = 1,
        source_types: Sequence[SourceType] | None = None,
    ) -> list[ProviderAdapter]:
        """Select providers using round-robin.

        Args:
            task_id: Task ID for tracking position.
            count: Number of providers to select.
            source_types: Filter by source types.

        Returns:
            List of selected providers.
        """
        # Get available providers
        providers = self.select_providers(source_types=source_types)

        if not providers:
            return []

        # Get current index for task
        current_index = self._round_robin_index.get(task_id, 0)

        # Select providers starting from current index
        selected = []
        for i in range(count):
            index = (current_index + i) % len(providers)
            selected.append(providers[index])

        # Update index
        self._round_robin_index[task_id] = (current_index + count) % len(providers)

        return selected

    def reset_task(self, task_id: str) -> None:
        """Reset round-robin position for a task.

        Args:
            task_id: Task ID.
        """
        self._round_robin_index.pop(task_id, None)

    def reset_all(self) -> None:
        """Reset all round-robin positions."""
        self._round_robin_index.clear()


class WeightedSelector(ProviderSelector):
    """Selector with weighted provider selection.

    Weights providers based on success rate and performance.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        health_adapter: ProviderHealthAdapter | None = None,
        capability_adapter: ProviderCapabilityAdapter | None = None,
    ) -> None:
        """Initialize weighted selector.

        Args:
            registry: Provider registry.
            health_adapter: Health adapter.
            capability_adapter: Capability adapter.
        """
        super().__init__(registry, health_adapter, capability_adapter)
        self._weights: dict[str, float] = {}
        self._success_counts: dict[str, int] = {}
        self._failure_counts: dict[str, int] = {}

    def select_weighted(
        self,
        count: int | None = None,
        source_types: Sequence[SourceType] | None = None,
    ) -> list[ProviderAdapter]:
        """Select providers using weighted selection.

        Args:
            count: Maximum number of providers.
            source_types: Filter by source types.

        Returns:
            List of providers ordered by weight.
        """
        # Get available providers
        providers = self.select_providers(source_types=source_types)

        if not providers:
            return []

        # Calculate weights for each provider
        weighted_providers = []
        for provider in providers:
            weight = self._calculate_weight(provider.provider_name)
            weighted_providers.append((weight, provider))

        # Sort by weight descending
        weighted_providers.sort(key=lambda x: x[0], reverse=True)

        # Extract providers
        selected = [p for _, p in weighted_providers]

        # Limit count
        if count is not None:
            selected = selected[:count]

        return selected

    def _calculate_weight(self, name: str) -> float:
        """Calculate weight for a provider.

        Args:
            name: Provider name.

        Returns:
            Calculated weight.
        """
        # Start with configured priority
        base_weight = self._registry.get_priority(name)

        # Adjust based on success rate
        successes = self._success_counts.get(name, 0)
        failures = self._failure_counts.get(name, 0)
        total = successes + failures

        if total > 0:
            success_rate = successes / total
            success_adjustment = success_rate * 10
        else:
            success_adjustment = 5.0  # Neutral for unknown

        # Combine
        return base_weight + success_adjustment

    def record_success(self, name: str) -> None:
        """Record successful provider use.

        Args:
            name: Provider name.
        """
        self._success_counts[name] = self._success_counts.get(name, 0) + 1

    def record_failure(self, name: str) -> None:
        """Record failed provider use.

        Args:
            name: Provider name.
        """
        self._failure_counts[name] = self._failure_counts.get(name, 0) + 1

    def get_success_rate(self, name: str) -> float:
        """Get success rate for a provider.

        Args:
            name: Provider name.

        Returns:
            Success rate (0.0 to 1.0).
        """
        successes = self._success_counts.get(name, 0)
        failures = self._failure_counts.get(name, 0)
        total = successes + failures

        if total == 0:
            return 0.5  # Neutral for unknown

        return successes / total

    def reset_statistics(self, name: str | None = None) -> None:
        """Reset provider statistics.

        Args:
            name: Optional provider name. If None, resets all.
        """
        if name is None:
            self._success_counts.clear()
            self._failure_counts.clear()
        else:
            self._success_counts.pop(name, None)
            self._failure_counts.pop(name, None)


class SourceTypeSelector(ProviderSelector):
    """Selector specialized for source type selection.

    Selects providers based on discovery source types.
    """

    def select_by_source_type(
        self,
        source_type: SourceType,
        count: int | None = None,
    ) -> list[ProviderAdapter]:
        """Select providers by source type.

        Args:
            source_type: Source type to select.
            count: Maximum number of providers.

        Returns:
            List of providers of the specified type.
        """
        providers = self.select_providers(source_types=(source_type,))

        if count is not None:
            providers = providers[:count]

        return providers

    def get_source_types(self) -> list[SourceType]:
        """Get all available source types.

        Returns:
            List of available source types.
        """
        providers = self._registry.get_all()
        return list(set(p.provider_type for p in providers))

    def get_providers_by_source_type(
        self,
    ) -> dict[SourceType, list[ProviderAdapter]]:
        """Get providers grouped by source type.

        Returns:
            Dictionary of source types to providers.
        """
        providers = self._registry.get_all()
        result: dict[SourceType, list[ProviderAdapter]] = {}

        for provider in providers:
            if provider.provider_type not in result:
                result[provider.provider_type] = []
            result[provider.provider_type].append(provider)

        return result
