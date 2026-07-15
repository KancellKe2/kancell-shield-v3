"""Unit tests for Discovery Engine models."""

import pytest
from datetime import datetime, timezone

from src.discovery.models import (
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


class TestDomain:
    """Tests for Domain model."""

    def test_create_domain(self) -> None:
        """Test creating a domain."""
        domain = Domain(name="example.com")
        assert domain.name == "example.com"
        assert domain.full_domain == "example.com"

    def test_create_domain_with_subdomain(self) -> None:
        """Test creating a domain with subdomain."""
        domain = Domain(name="example.com", subdomain="www")
        assert domain.subdomain == "www"
        assert domain.full_domain == "www.example.com"

    def test_create_domain_with_tld(self) -> None:
        """Test creating a domain with TLD."""
        domain = Domain(name="example", tld="com")
        assert domain.tld == "com"
        assert domain.full_domain == "example"

    def test_empty_domain_raises(self) -> None:
        """Test that empty domain raises."""
        with pytest.raises(ValueError):
            Domain(name="")

    def test_str_representation(self) -> None:
        """Test string representation."""
        domain = Domain(name="test.org")
        assert str(domain) == "test.org"


class TestDiscoveryTask:
    """Tests for DiscoveryTask model."""

    def test_create_task_with_domains(self) -> None:
        """Test creating task with seed domains."""
        task = DiscoveryTask(
            task_id="task-1",
            seed_domains=("domain1.com", "domain2.com"),
        )
        assert task.task_id == "task-1"
        assert len(task.seed_domains) == 2
        assert task.has_seeds is True
        assert task.has_keywords is False

    def test_create_task_with_keywords(self) -> None:
        """Test creating task with keywords."""
        task = DiscoveryTask(
            task_id="task-2",
            seed_domains=("placeholder.com",),
            keywords=("keyword1", "keyword2"),
        )
        assert len(task.keywords) == 2
        assert task.has_keywords is True

    def test_create_task_with_both(self) -> None:
        """Test creating task with both domains and keywords."""
        task = DiscoveryTask(
            task_id="task-3",
            seed_domains=("domain.com",),
            keywords=("keyword",),
        )
        assert task.has_seeds is True
        assert task.has_keywords is True

    def test_task_empty_seeds_and_keywords_raises(self) -> None:
        """Test that task without seeds or keywords raises."""
        with pytest.raises(ValueError):
            DiscoveryTask(
                task_id="task-empty",
                seed_domains=(),
                keywords=(),
            )

    def test_task_invalid_max_candidates_raises(self) -> None:
        """Test that invalid max_candidates raises."""
        with pytest.raises(ValueError):
            DiscoveryTask(
                task_id="task",
                seed_domains=("domain.com",),
                max_candidates=0,
            )

    def test_task_invalid_batch_size_raises(self) -> None:
        """Test that invalid batch_size raises."""
        with pytest.raises(ValueError):
            DiscoveryTask(
                task_id="task",
                seed_domains=("domain.com",),
                batch_size=0,
            )


class TestDiscoveryCandidate:
    """Tests for DiscoveryCandidate model."""

    def test_create_candidate(self) -> None:
        """Test creating a candidate."""
        domain = Domain(name="test.com")
        candidate = DiscoveryCandidate(
            domain=domain,
            source="test_source",
        )
        assert candidate.domain == domain
        assert candidate.source == "test_source"
        assert candidate.status == CandidateStatus.DISCOVERED

    def test_candidate_is_valid(self) -> None:
        """Test candidate is_valid property."""
        domain = Domain(name="test.com")
        candidate = DiscoveryCandidate(
            domain=domain,
            source="test",
            validation_result=ValidationResult.VALID,
        )
        assert candidate.is_valid is True

    def test_candidate_is_invalid(self) -> None:
        """Test candidate is_invalid property."""
        domain = Domain(name="test.com")
        candidate = DiscoveryCandidate(
            domain=domain,
            source="test",
            validation_result=ValidationResult.INVALID_SYNTAX,
        )
        assert candidate.is_valid is False

    def test_candidate_domain_string(self) -> None:
        """Test candidate domain_string property."""
        domain = Domain(name="test.com")
        candidate = DiscoveryCandidate(domain=domain, source="test")
        assert candidate.domain_string == "test.com"


class TestDiscoverySource:
    """Tests for DiscoverySource model."""

    def test_create_source(self) -> None:
        """Test creating a source."""
        source = DiscoverySource(
            name="test_source",
            source_type=SourceType.PASSIVE,
        )
        assert source.name == "test_source"
        assert source.source_type == SourceType.PASSIVE
        assert source.is_passive is True

    def test_passive_source_check(self) -> None:
        """Test passive source detection."""
        passive = DiscoverySource(
            name="passive",
            source_type=SourceType.PASSIVE_DNS,
        )
        assert passive.is_passive is True

        active = DiscoverySource(
            name="active",
            source_type=SourceType.WHOIS,
        )
        assert active.is_passive is False


class TestDiscoveryStatistics:
    """Tests for DiscoveryStatistics model."""

    def test_create_statistics(self) -> None:
        """Test creating statistics."""
        stats = DiscoveryStatistics(
            task_id="task-1",
            started_at=datetime.now(timezone.utc),
            candidates_discovered=100,
        )
        assert stats.task_id == "task-1"
        assert stats.candidates_discovered == 100

    def test_duration_calculation(self) -> None:
        """Test duration calculation."""
        start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 12, 1, 0, tzinfo=timezone.utc)
        stats = DiscoveryStatistics(
            task_id="task-1",
            started_at=start,
            ended_at=end,
        )
        assert stats.duration_seconds == 60.0

    def test_duration_none_without_end(self) -> None:
        """Test duration is None without end time."""
        stats = DiscoveryStatistics(
            task_id="task-1",
            started_at=datetime.now(timezone.utc),
        )
        assert stats.duration_seconds is None

    def test_success_rate(self) -> None:
        """Test success rate calculation."""
        stats = DiscoveryStatistics(
            task_id="task-1",
            started_at=datetime.now(timezone.utc),
            candidates_discovered=100,
            candidates_validated=80,
        )
        assert stats.success_rate == 80.0

    def test_success_rate_none_with_no_discoveries(self) -> None:
        """Test success rate is None with no discoveries."""
        stats = DiscoveryStatistics(
            task_id="task-1",
            started_at=datetime.now(timezone.utc),
            candidates_discovered=0,
        )
        assert stats.success_rate is None


class TestDiscoveryProgress:
    """Tests for DiscoveryProgress model."""

    def test_create_progress(self) -> None:
        """Test creating progress."""
        progress = DiscoveryProgress(
            task_id="task-1",
            status=DiscoveryStatus.RUNNING,
            total_batches=10,
            completed_batches=5,
            total_candidates=100,
            current_batch=5,
        )
        assert progress.percent_complete == 50.0
        assert progress.is_finished is False

    def test_progress_finished_check(self) -> None:
        """Test finished check."""
        progress = DiscoveryProgress(
            task_id="task-1",
            status=DiscoveryStatus.COMPLETED,
            total_batches=10,
            completed_batches=10,
            total_candidates=100,
            current_batch=10,
        )
        assert progress.is_finished is True

    def test_progress_zero_batches(self) -> None:
        """Test progress with zero batches."""
        progress = DiscoveryProgress(
            task_id="task-1",
            status=DiscoveryStatus.PENDING,
            total_batches=0,
            completed_batches=0,
            total_candidates=0,
            current_batch=0,
        )
        assert progress.percent_complete == 0.0


class TestDiscoveryBatch:
    """Tests for DiscoveryBatch model."""

    def test_create_batch(self) -> None:
        """Test creating a batch."""
        domain = Domain(name="test.com")
        candidate = DiscoveryCandidate(domain=domain, source="test")
        batch = DiscoveryBatch(
            batch_id="batch-1",
            task_id="task-1",
            candidates=(candidate,),
            source="test_source",
            batch_number=1,
        )
        assert batch.batch_id == "batch-1"
        assert batch.count == 1
        assert batch.is_empty is False

    def test_batch_empty_check(self) -> None:
        """Test empty batch check."""
        batch = DiscoveryBatch(
            batch_id="batch-empty",
            task_id="task-1",
            candidates=(),
            source="test",
            batch_number=1,
        )
        assert batch.is_empty is True


class TestDiscoveryConfiguration:
    """Tests for DiscoveryConfiguration model."""

    def test_default_configuration(self) -> None:
        """Test default configuration."""
        config = DiscoveryConfiguration()
        assert config.max_candidates == 1000
        assert config.timeout_seconds == 300.0
        assert config.enable_deduplication is True

    def test_custom_configuration(self) -> None:
        """Test custom configuration."""
        config = DiscoveryConfiguration(
            max_candidates=5000,
            default_score_threshold=0.5,
        )
        assert config.max_candidates == 5000
        assert config.default_score_threshold == 0.5


class TestDiscoveryResult:
    """Tests for DiscoveryResult model."""

    def test_create_result(self) -> None:
        """Test creating a result."""
        domain = Domain(name="test.com")
        candidate = DiscoveryCandidate(domain=domain, source="test")
        stats = DiscoveryStatistics(
            task_id="task-1",
            started_at=datetime.now(timezone.utc),
        )
        config = DiscoveryConfiguration()
        result = DiscoveryResult(
            task_id="task-1",
            status=DiscoveryStatus.COMPLETED,
            candidates=(candidate,),
            statistics=stats,
            configuration=config,
        )
        assert result.total_candidates == 1
        assert result.success is True
        assert result.failed is False

    def test_valid_candidates(self) -> None:
        """Test getting valid candidates."""
        domain1 = Domain(name="valid.com")
        domain2 = Domain(name="invalid.com")
        candidate1 = DiscoveryCandidate(
            domain=domain1,
            source="test",
            validation_result=ValidationResult.VALID,
        )
        candidate2 = DiscoveryCandidate(
            domain=domain2,
            source="test",
            validation_result=ValidationResult.INVALID_SYNTAX,
        )
        stats = DiscoveryStatistics(
            task_id="task-1",
            started_at=datetime.now(timezone.utc),
        )
        result = DiscoveryResult(
            task_id="task-1",
            status=DiscoveryStatus.COMPLETED,
            candidates=(candidate1, candidate2),
            statistics=stats,
            configuration=DiscoveryConfiguration(),
        )
        assert len(result.valid_candidates) == 1


class TestFilterRule:
    """Tests for FilterRule model."""

    def test_create_exclusion_rule(self) -> None:
        """Test creating an exclusion rule."""
        rule = FilterRule(
            name="exclude_test",
            pattern="test*.evil.com",
        )
        assert rule.name == "exclude_test"
        assert rule.is_exclusion is True
        assert rule.is_inclusion is False

    def test_create_inclusion_rule(self) -> None:
        """Test creating an inclusion rule."""
        rule = FilterRule(
            name="include_good",
            pattern="good*.com",
            is_exclusion=False,
        )
        assert rule.is_exclusion is False
        assert rule.is_inclusion is True


class TestSourceResult:
    """Tests for SourceResult model."""

    def test_create_source_result(self) -> None:
        """Test creating a source result."""
        domain = Domain(name="test.com")
        candidate = DiscoveryCandidate(domain=domain, source="test")
        result = SourceResult(
            source_name="test_source",
            candidates=(candidate,),
            duration_ms=100.0,
        )
        assert result.source_name == "test_source"
        assert len(result.candidates) == 1
        assert result.duration_ms == 100.0


class TestEnums:
    """Tests for enum values."""

    def test_candidate_status_values(self) -> None:
        """Test CandidateStatus enum values exist."""
        assert CandidateStatus.DISCOVERED is not None
        assert CandidateStatus.VALIDATED is not None
        assert CandidateStatus.SCORED is not None
        assert CandidateStatus.FILTERED is not None

    def test_discovery_status_values(self) -> None:
        """Test DiscoveryStatus enum values exist."""
        assert DiscoveryStatus.PENDING is not None
        assert DiscoveryStatus.RUNNING is not None
        assert DiscoveryStatus.COMPLETED is not None
        assert DiscoveryStatus.FAILED is not None

    def test_source_type_values(self) -> None:
        """Test SourceType enum values exist."""
        assert SourceType.PASSIVE is not None
        assert SourceType.ACTIVE is not None
        assert SourceType.WHOIS is not None
        assert SourceType.DNS is not None

    def test_validation_result_values(self) -> None:
        """Test ValidationResult enum values exist."""
        assert ValidationResult.VALID is not None
        assert ValidationResult.INVALID_FORMAT is not None
        assert ValidationResult.INVALID_SYNTAX is not None
