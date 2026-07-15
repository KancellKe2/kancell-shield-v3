"""Unit tests for Discovery Provider Integration."""

import pytest

from src.discovery import (
    DiscoveryTask,
    Domain,
    SourceType,
)
from src.discovery.provider_adapter import (
    MockSearchProviderAdapter,
    ProviderAdapter,
    ProviderCapabilityAdapter,
    ProviderHealthAdapter,
)
from src.discovery.provider_registry import (
    DefaultProviderRegistry,
    ProviderConfig,
    ProviderRegistry,
    ProviderRegistryBuilder,
)
from src.discovery.provider_pipeline import (
    BatchedProviderPipeline,
    FallbackProviderPipeline,
    FilteredProviderPipeline,
    ProviderPipeline,
)
from src.discovery.provider_selector import (
    ProviderSelector,
    RoundRobinSelector,
    SourceTypeSelector,
    WeightedSelector,
)


class TestProviderAdapter:
    """Tests for ProviderAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.adapter = ProviderAdapter("test_provider", SourceType.PASSIVE)

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        assert self.adapter.provider_name == "test_provider"
        assert self.adapter.provider_type == SourceType.PASSIVE

    def test_to_discovery_source(self) -> None:
        """Test conversion to discovery source."""
        source = self.adapter.to_discovery_source()
        assert source.name == "test_provider"
        assert source.source_type == SourceType.PASSIVE

    def test_to_provider_request(self) -> None:
        """Test conversion to provider request."""
        request = self.adapter.to_provider_request(["example.com", "test.net"])
        assert "example.com" in request.query
        assert "test.net" in request.query

    def test_extract_domain_from_url(self) -> None:
        """Test domain extraction from URL."""
        domain = self.adapter._extract_domain("https://example.com/path")
        assert domain == "example.com"

    def test_extract_domain_from_simple(self) -> None:
        """Test domain extraction from domain string."""
        domain = self.adapter._extract_domain("example.com")
        assert domain == "example.com"

    def test_check_health(self) -> None:
        """Test health checking."""
        from src.search.provider.models import ProviderHealthStatus, HealthStatus

        healthy = ProviderHealthStatus(
            provider_name="test",
            status=HealthStatus.HEALTHY,
        )
        assert self.adapter.check_health(healthy) is True

        unhealthy = ProviderHealthStatus(
            provider_name="test",
            status=HealthStatus.UNHEALTHY,
        )
        assert self.adapter.check_health(unhealthy) is False


class TestMockSearchProviderAdapter:
    """Tests for MockSearchProviderAdapter."""

    def test_mock_domains(self) -> None:
        """Test mock domain handling."""
        adapter = MockSearchProviderAdapter(
            provider_name="mock",
            mock_domains=["a.com", "b.net"],
        )
        assert len(adapter._mock_domains) == 2

    def test_create_mock_response(self) -> None:
        """Test mock response creation."""
        adapter = MockSearchProviderAdapter(provider_name="mock")
        adapter.set_mock_domains(["test.com"])
        response = adapter.create_mock_response()
        assert len(response.results) == 1

    def test_to_discovery_candidates(self) -> None:
        """Test conversion to discovery candidates."""
        adapter = MockSearchProviderAdapter(
            provider_name="mock",
            mock_domains=["test.com"],
        )
        response = adapter.create_mock_response()
        candidates = adapter.to_discovery_candidates(response)
        assert len(candidates) == 1
        assert str(candidates[0].domain) == "test.com"

    def test_add_mock_domain(self) -> None:
        """Test adding mock domains."""
        adapter = MockSearchProviderAdapter(provider_name="mock")
        adapter.add_mock_domain("new.com")
        assert "new.com" in adapter._mock_domains


class TestProviderCapabilityAdapter:
    """Tests for ProviderCapabilityAdapter."""

    def test_set_requirement(self) -> None:
        """Test setting requirements."""
        adapter = ProviderCapabilityAdapter()
        adapter.set_requirement("search", True)
        requirements = adapter.get_requirements()
        assert requirements["search"] is True

    def test_clear_requirements(self) -> None:
        """Test clearing requirements."""
        adapter = ProviderCapabilityAdapter()
        adapter.set_requirement("search", True)
        adapter.clear_requirements()
        assert len(adapter.get_requirements()) == 0


class TestProviderHealthAdapter:
    """Tests for ProviderHealthAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.adapter = ProviderHealthAdapter()

    def test_record_success(self) -> None:
        """Test recording success."""
        self.adapter.record_success("provider")
        assert self.adapter.is_available("provider") is True

    def test_record_failure(self) -> None:
        """Test recording failure."""
        self.adapter.set_failure_threshold(2)
        self.adapter.record_failure("provider")
        self.adapter.record_failure("provider")
        assert self.adapter.is_available("provider") is False

    def test_reset_provider(self) -> None:
        """Test resetting provider."""
        self.adapter.record_failure("provider")
        self.adapter.record_failure("provider")
        self.adapter.reset_provider("provider")
        assert self.adapter.is_available("provider") is True

    def test_get_unavailable_providers(self) -> None:
        """Test getting unavailable providers."""
        from src.search.provider.models import ProviderHealthStatus, HealthStatus

        status = ProviderHealthStatus(
            provider_name="unhealthy",
            status=HealthStatus.UNHEALTHY,
            is_available=False,
        )
        self.adapter.set_health_status("unhealthy", status)
        unavailable = self.adapter.get_unavailable_providers()
        assert "unhealthy" in unavailable


class TestProviderRegistry:
    """Tests for ProviderRegistry."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.registry = ProviderRegistry()
        self.adapter = MockSearchProviderAdapter(provider_name="test")

    def test_register(self) -> None:
        """Test registering a provider."""
        self.registry.register(self.adapter)
        assert "test" in self.registry

    def test_unregister(self) -> None:
        """Test unregistering a provider."""
        self.registry.register(self.adapter)
        assert self.registry.unregister("test") is True
        assert "test" not in self.registry

    def test_enable_disable(self) -> None:
        """Test enabling and disabling providers."""
        self.registry.register(self.adapter, enabled=False)
        assert self.registry.is_enabled("test") is False
        self.registry.enable("test")
        assert self.registry.is_enabled("test") is True
        self.registry.disable("test")
        assert self.registry.is_enabled("test") is False

    def test_get_enabled(self) -> None:
        """Test getting enabled providers."""
        self.registry.register(self.adapter, enabled=True)
        enabled = self.registry.get_enabled()
        assert len(enabled) == 1
        assert enabled[0].provider_name == "test"

    def test_set_priority(self) -> None:
        """Test setting priority."""
        self.registry.register(self.adapter, priority=50)
        self.registry.set_priority("test", 100)
        assert self.registry.get_priority("test") == 100

    def test_get_sorted_by_priority(self) -> None:
        """Test getting providers sorted by priority."""
        adapter2 = MockSearchProviderAdapter(provider_name="test2")
        self.registry.register(self.adapter, priority=50)
        self.registry.register(adapter2, priority=100)
        sorted_providers = self.registry.get_sorted_by_priority()
        assert sorted_providers[0].provider_name == "test2"

    def test_get_by_type(self) -> None:
        """Test getting providers by type."""
        self.registry.register(self.adapter, enabled=True)
        by_type = self.registry.get_by_type(SourceType.PASSIVE)
        assert len(by_type) == 1


class TestDefaultProviderRegistry:
    """Tests for DefaultProviderRegistry."""

    def test_default_providers(self) -> None:
        """Test default mock providers."""
        registry = DefaultProviderRegistry()
        assert len(registry) == 3
        assert registry.is_enabled("ct") is True
        assert registry.is_enabled("passive_dns") is True
        assert registry.is_enabled("dns_cache") is True


class TestProviderRegistryBuilder:
    """Tests for ProviderRegistryBuilder."""

    def test_add_mock(self) -> None:
        """Test adding mock providers."""
        builder = ProviderRegistryBuilder()
        builder.add_mock("test_mock", ["a.com"], priority=100)
        registry = builder.build()
        assert "test_mock" in registry
        assert registry.get_priority("test_mock") == 100

    def test_fluent_interface(self) -> None:
        """Test fluent interface."""
        builder = ProviderRegistryBuilder()
        builder.add_mock("a", priority=10).add_mock("b", priority=20)
        registry = builder.build()
        assert len(registry) == 2


class TestProviderPipeline:
    """Tests for ProviderPipeline."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.registry = ProviderRegistry()
        self.adapter = MockSearchProviderAdapter(
            provider_name="test",
            mock_domains=["example.com", "test.net"],
        )
        self.registry.register(self.adapter)
        self.pipeline = ProviderPipeline(self.registry)

    def test_execute(self) -> None:
        """Test pipeline execution."""
        task = DiscoveryTask(
            task_id="task-1",
            seed_domains=("seed.com",),
        )
        results = self.pipeline.execute(task)
        assert len(results) == 1
        assert results[0].source_name == "test"
        assert len(results[0].candidates) == 2

    def test_aggregate_candidates(self) -> None:
        """Test candidate aggregation."""
        task = DiscoveryTask(
            task_id="task-2",
            seed_domains=("seed.com",),
        )
        results = self.pipeline.execute(task)
        aggregated = self.pipeline.aggregate_candidates(results)
        assert len(aggregated) == 2

    def test_get_statistics(self) -> None:
        """Test getting statistics."""
        task = DiscoveryTask(
            task_id="task-3",
            seed_domains=("seed.com",),
        )
        results = self.pipeline.execute(task)
        stats = self.pipeline.get_statistics(results)
        assert "total_candidates" in stats
        assert stats["total_candidates"] == 2


class TestFilteredProviderPipeline:
    """Tests for FilteredProviderPipeline."""

    def test_filtering(self) -> None:
        """Test result filtering."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(
            provider_name="test",
            mock_domains=["a.com", "b.net"],
        )
        registry.register(adapter)

        def filter_func(candidate):
            return "a.com" in str(candidate.domain)

        pipeline = FilteredProviderPipeline(registry, filter_func)
        task = DiscoveryTask(task_id="t", seed_domains=("s.com",))
        results = pipeline.execute(task)
        aggregated = pipeline.aggregate_candidates(results)
        assert len(aggregated) == 1


class TestFallbackProviderPipeline:
    """Tests for FallbackProviderPipeline."""

    def test_min_success_providers(self) -> None:
        """Test minimum success providers."""
        registry = ProviderRegistry()
        adapter1 = MockSearchProviderAdapter(provider_name="p1", mock_domains=["a.com"])
        adapter2 = MockSearchProviderAdapter(provider_name="p2", mock_domains=["b.com"])
        registry.register(adapter1)
        registry.register(adapter2)

        pipeline = FallbackProviderPipeline(registry, min_success_providers=1)
        task = DiscoveryTask(task_id="t", seed_domains=("s.com",))
        results = pipeline.execute(task)
        assert pipeline.has_sufficient_results(results) is True

    def test_get_successful_providers(self) -> None:
        """Test getting successful providers."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(provider_name="p1", mock_domains=["a.com"])
        registry.register(adapter)

        pipeline = FallbackProviderPipeline(registry)
        task = DiscoveryTask(task_id="t", seed_domains=("s.com",))
        results = pipeline.execute(task)
        successful = pipeline.get_successful_providers(results)
        assert "p1" in successful


class TestBatchedProviderPipeline:
    """Tests for BatchedProviderPipeline."""

    def test_batching(self) -> None:
        """Test batched execution."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(provider_name="p1", mock_domains=[])
        registry.register(adapter)

        pipeline = BatchedProviderPipeline(registry, batch_size=2)
        task = DiscoveryTask(task_id="t", seed_domains=("s.com",))
        results = pipeline.execute_batched(task, ["a.com", "b.com", "c.com"])
        assert len(results) == 2  # Two batches


class TestProviderSelector:
    """Tests for ProviderSelector."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.registry = ProviderRegistry()
        self.adapter = MockSearchProviderAdapter(provider_name="test")
        self.registry.register(self.adapter, priority=50)
        self.selector = ProviderSelector(self.registry)

    def test_select_providers(self) -> None:
        """Test selecting providers."""
        providers = self.selector.select_providers()
        assert len(providers) == 1
        assert providers[0].provider_name == "test"

    def test_select_best_provider(self) -> None:
        """Test selecting best provider."""
        best = self.selector.select_best_provider()
        assert best is not None
        assert best.provider_name == "test"

    def test_select_by_priority(self) -> None:
        """Test selecting by priority."""
        providers = self.selector.select_by_priority(min_priority=40)
        assert len(providers) == 1

    def test_get_provider_info(self) -> None:
        """Test getting provider info."""
        info = self.selector.get_provider_info("test")
        assert info["name"] == "test"
        assert info["enabled"] is True


class TestRoundRobinSelector:
    """Tests for RoundRobinSelector."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.registry = ProviderRegistry()
        for i in range(3):
            adapter = MockSearchProviderAdapter(provider_name=f"p{i}")
            self.registry.register(adapter, priority=50)
        self.selector = RoundRobinSelector(self.registry)

    def test_round_robin_selection(self) -> None:
        """Test round-robin selection."""
        providers = self.selector.select_round_robin("task-1", count=2)
        assert len(providers) == 2
        # Verify providers have names
        names = [p.provider_name for p in providers]
        assert len(set(names)) == 2  # All different


class TestWeightedSelector:
    """Tests for WeightedSelector."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.registry = ProviderRegistry()
        self.adapter = MockSearchProviderAdapter(provider_name="test")
        self.registry.register(self.adapter, priority=50)
        self.selector = WeightedSelector(self.registry)

    def test_record_success(self) -> None:
        """Test recording successes."""
        self.selector.record_success("test")
        rate = self.selector.get_success_rate("test")
        assert rate == 1.0

    def test_record_failure(self) -> None:
        """Test recording failures."""
        self.selector.record_success("test")
        self.selector.record_failure("test")
        rate = self.selector.get_success_rate("test")
        assert rate == 0.5


class TestSourceTypeSelector:
    """Tests for SourceTypeSelector."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(
            provider_name="passive",
            mock_domains=[],
        )
        self.registry.register(adapter)
        self.selector = SourceTypeSelector(self.registry)

    def test_select_by_source_type(self) -> None:
        """Test selecting by source type."""
        providers = self.selector.select_by_source_type(SourceType.PASSIVE)
        assert len(providers) == 1

    def test_get_source_types(self) -> None:
        """Test getting source types."""
        types = self.selector.get_source_types()
        assert SourceType.PASSIVE in types

    def test_get_providers_by_source_type(self) -> None:
        """Test getting providers grouped by type."""
        grouped = self.selector.get_providers_by_source_type()
        assert SourceType.PASSIVE in grouped


class TestProviderConfig:
    """Tests for ProviderConfig."""

    def test_to_discovery_source(self) -> None:
        """Test converting config to discovery source."""
        config = ProviderConfig(
            name="test",
            enabled=True,
            priority=100,
            source_type=SourceType.PASSIVE,
        )
        source = config.to_discovery_source()
        assert source.name == "test"
        assert source.priority == 100


class TestProviderRegistryAdditional:
    """Additional provider registry tests."""

    def test_get_disabled(self) -> None:
        """Test getting disabled providers."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(provider_name="p1")
        registry.register(adapter, enabled=False)
        disabled = registry.get_disabled()
        assert len(disabled) == 1

    def test_clear(self) -> None:
        """Test clearing registry."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(provider_name="p1")
        registry.register(adapter)
        registry.clear()
        assert len(registry) == 0


class TestProviderPipelineAdditional:
    """Additional pipeline tests."""

    def test_clear_results(self) -> None:
        """Test clearing results."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(provider_name="p1", mock_domains=["a.com"])
        registry.register(adapter)
        pipeline = ProviderPipeline(registry)

        task = DiscoveryTask(task_id="t1", seed_domains=("s.com",))
        pipeline.execute(task)
        pipeline.clear_results("t1")
        assert len(pipeline.get_results("t1")) == 0

    def test_clear_all_results(self) -> None:
        """Test clearing all results."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(provider_name="p1", mock_domains=["a.com"])
        registry.register(adapter)
        pipeline = ProviderPipeline(registry)

        task = DiscoveryTask(task_id="t1", seed_domains=("s.com",))
        pipeline.execute(task)
        pipeline.clear_results()
        assert pipeline.get_results("t1") == []


class TestProviderSelectorAdditional:
    """Additional selector tests."""

    def test_select_count_limit(self) -> None:
        """Test selecting with count limit."""
        registry = ProviderRegistry()
        for i in range(3):
            adapter = MockSearchProviderAdapter(provider_name=f"p{i}")
            registry.register(adapter)
        selector = ProviderSelector(registry)
        providers = selector.select_providers(count=2)
        assert len(providers) == 2

    def test_select_require_healthy_false(self) -> None:
        """Test selecting with healthy requirement disabled."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(provider_name="p1")
        registry.register(adapter)
        selector = ProviderSelector(registry)
        providers = selector.select_providers(require_healthy=False)
        assert len(providers) == 1

    def test_select_by_multiple_types(self) -> None:
        """Test selecting by multiple source types."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(provider_name="p1")
        registry.register(adapter)
        selector = ProviderSelector(registry)
        providers = selector.select_providers(source_types=[SourceType.PASSIVE])
        assert len(providers) == 1


class TestWeightedSelectorAdditional:
    """Additional weighted selector tests."""

    def test_reset_statistics(self) -> None:
        """Test resetting statistics."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(provider_name="p1")
        registry.register(adapter)
        selector = WeightedSelector(registry)
        selector.record_success("p1")
        selector.reset_statistics("p1")
        assert selector.get_success_rate("p1") == 0.5

    def test_reset_all_statistics(self) -> None:
        """Test resetting all statistics."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(provider_name="p1")
        registry.register(adapter)
        selector = WeightedSelector(registry)
        selector.record_success("p1")
        selector.reset_statistics()
        assert selector.get_success_rate("p1") == 0.5


class TestRoundRobinSelectorAdditional:
    """Additional round-robin selector tests."""

    def test_reset_task(self) -> None:
        """Test resetting task position."""
        registry = ProviderRegistry()
        for i in range(2):
            adapter = MockSearchProviderAdapter(provider_name=f"p{i}")
            registry.register(adapter)
        selector = RoundRobinSelector(registry)
        selector.select_round_robin("task", count=1)
        selector.reset_task("task")
        # Reset should not raise

    def test_reset_all_positions(self) -> None:
        """Test resetting all positions."""
        registry = ProviderRegistry()
        adapter = MockSearchProviderAdapter(provider_name="p1")
        registry.register(adapter)
        selector = RoundRobinSelector(registry)
        selector.select_round_robin("task", count=1)
        selector.reset_all()
