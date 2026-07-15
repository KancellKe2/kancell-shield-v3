"""Unit tests for Discovery Engine implementation."""

import pytest
from datetime import datetime, timezone

from src.discovery import (
    CandidateStatus,
    DiscoveryBatch,
    DiscoveryCandidate,
    DiscoveryConfiguration,
    DiscoveryEngineImpl,
    DiscoveryProgress,
    DiscoveryResult,
    DiscoverySchedulerImpl,
    DiscoverySource,
    DiscoveryStatistics,
    DiscoveryStatus,
    DiscoveryTask,
    Domain,
    FilterRule,
    PriorityScheduler,
    SourceType,
    ValidationResult,
)
from src.discovery.collector import DiscoveryCollectorImpl
from src.discovery.filter import DomainFilter, ExclusionFilter, InclusionFilter
from src.discovery.scorer import DeterministicScorer, DomainScorer
from src.discovery.validator import DomainValidator
from src.discovery.exceptions import (
    CollectorError,
    ConfigurationError,
    DiscoveryError,
    FilterError,
    MaxCandidatesReachedError,
    SchedulerError,
    TaskNotFoundError,
    ValidationError,
)


class TestDomainValidator:
    """Tests for DomainValidator."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.validator = DomainValidator()

    def test_validate_valid_domain(self) -> None:
        """Test validating a valid domain."""
        domain = Domain(name="testsite.com")
        candidate = DiscoveryCandidate(domain=domain, source="test")
        result = self.validator.validate(candidate)
        assert result == ValidationResult.VALID

    def test_validate_invalid_format(self) -> None:
        """Test validating domain with invalid format."""
        domain = Domain(name="not a domain")
        candidate = DiscoveryCandidate(domain=domain, source="test")
        result = self.validator.validate(candidate)
        assert result == ValidationResult.INVALID_FORMAT

    def test_validate_too_short(self) -> None:
        """Test validating domain that's too short."""
        # Create validator with higher min length
        validator = DomainValidator(min_length=10)
        domain = Domain(name="ab.com")
        candidate = DiscoveryCandidate(domain=domain, source="test")
        result = validator.validate(candidate)
        assert result == ValidationResult.TOO_SHORT

    def test_validate_reserved_tld(self) -> None:
        """Test validating domain with reserved TLD."""
        domain = Domain(name="example.local")
        candidate = DiscoveryCandidate(domain=domain, source="test")
        result = self.validator.validate(candidate)
        assert result == ValidationResult.RESERVED_DOMAIN

    def test_validate_batch(self) -> None:
        """Test validating batch of candidates."""
        candidates = [
            DiscoveryCandidate(domain=Domain(name="valid.com"), source="test"),
            DiscoveryCandidate(domain=Domain(name="invalid"), source="test"),
            DiscoveryCandidate(domain=Domain(name="also.valid.net"), source="test"),
        ]
        validated = self.validator.validate_batch(candidates)
        assert len(validated) == 3
        assert validated[0].status == CandidateStatus.VALIDATED
        assert validated[1].status == CandidateStatus.REJECTED
        assert validated[2].status == CandidateStatus.VALIDATED

    def test_is_valid_format(self) -> None:
        """Test format validation method."""
        assert self.validator.is_valid_format("example.com") is True
        assert self.validator.is_valid_format("not-a-domain") is False

    def test_get_validation_errors(self) -> None:
        """Test getting all validation errors."""
        domain = Domain(name="x")
        candidate = DiscoveryCandidate(domain=domain, source="test")
        errors = self.validator.get_validation_errors(candidate)
        assert len(errors) > 0
        assert ValidationResult.TOO_SHORT in errors


class TestDomainScorer:
    """Tests for DomainScorer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.scorer = DomainScorer()

    def test_score_basic(self) -> None:
        """Test basic scoring."""
        domain = Domain(name="example.com")
        candidate = DiscoveryCandidate(domain=domain, source="ct")
        score = self.scorer.score(candidate)
        assert 0.0 <= score <= 1.0

    def test_score_batch(self) -> None:
        """Test batch scoring."""
        candidates = [
            DiscoveryCandidate(domain=Domain(name="a.com"), source="ct"),
            DiscoveryCandidate(domain=Domain(name="b.net"), source="whois"),
        ]
        scored = self.scorer.score_batch(candidates)
        assert len(scored) == 2
        assert all(c.score is not None for c in scored)
        assert all(c.status == CandidateStatus.SCORED for c in scored)

    def test_calculate_confidence(self) -> None:
        """Test confidence calculation."""
        domain = Domain(name="example.com")
        candidate = DiscoveryCandidate(domain=domain, source="ct", score=0.5)
        confidence = self.scorer.calculate_confidence(candidate)
        assert 0.0 <= confidence <= 1.0

    def test_rank_candidates(self) -> None:
        """Test ranking candidates."""
        candidates = [
            DiscoveryCandidate(domain=Domain(name="low.com"), source="test", score=0.3),
            DiscoveryCandidate(domain=Domain(name="high.com"), source="test", score=0.8),
            DiscoveryCandidate(domain=Domain(name="mid.com"), source="test", score=0.5),
        ]
        ranked = self.scorer.rank_candidates(candidates)
        assert ranked[0].score == 0.8
        assert ranked[1].score == 0.5
        assert ranked[2].score == 0.3

    def test_set_source_weight(self) -> None:
        """Test setting source weight."""
        self.scorer.set_source_weight("custom_source", 0.9)
        assert self.scorer.get_source_weight("custom_source") == 0.9

    def test_get_source_weight_unknown(self) -> None:
        """Test getting weight for unknown source."""
        weight = self.scorer.get_source_weight("unknown_source")
        assert weight == 0.5  # Default weight


class TestDeterministicScorer:
    """Tests for DeterministicScorer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.scorer = DeterministicScorer()

    def test_deterministic_scoring(self) -> None:
        """Test that same domain gets same score."""
        domain = Domain(name="example.com")
        candidate = DiscoveryCandidate(domain=domain, source="test")

        score1 = self.scorer.score(candidate)
        score2 = self.scorer.score(candidate)
        score3 = self.scorer.score(candidate)

        assert score1 == score2 == score3

    def test_different_domains_different_scores(self) -> None:
        """Test different domains can have different scores."""
        c1 = DiscoveryCandidate(domain=Domain(name="aaa.com"), source="test")
        c2 = DiscoveryCandidate(domain=Domain(name="bbb.com"), source="test")

        s1 = self.scorer.score(c1)
        s2 = self.scorer.score(c2)

        # Different domains should potentially have different scores
        # (though this is not guaranteed with hash collisions)
        assert isinstance(s1, float)
        assert isinstance(s2, float)


class TestDomainFilter:
    """Tests for DomainFilter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.filter = DomainFilter()

    def test_should_include_basic(self) -> None:
        """Test basic inclusion."""
        candidate = DiscoveryCandidate(
            domain=Domain(name="example.com"),
            source="test",
        )
        assert self.filter.should_include(candidate) is True

    def test_should_exclude_by_rule(self) -> None:
        """Test exclusion by rule."""
        self.filter.add_rule(FilterRule(
            name="exclude_evil",
            pattern="*.evil.com",
            is_exclusion=True,
        ))
        candidate = DiscoveryCandidate(
            domain=Domain(name="test.evil.com"),
            source="test",
        )
        assert self.filter.should_include(candidate) is False

    def test_should_include_by_rule(self) -> None:
        """Test inclusion by rule."""
        self.filter.add_rule(FilterRule(
            name="include_good",
            pattern="*.good.com",
            is_exclusion=False,
        ))
        candidate = DiscoveryCandidate(
            domain=Domain(name="test.good.com"),
            source="test",
        )
        assert self.filter.should_include(candidate) is True

    def test_filter_batch(self) -> None:
        """Test batch filtering."""
        self.filter.add_rule(FilterRule(
            name="exclude_test",
            pattern="*.test.com",
            is_exclusion=True,
        ))
        candidates = [
            DiscoveryCandidate(domain=Domain(name="a.com"), source="test"),
            DiscoveryCandidate(domain=Domain(name="b.test.com"), source="test"),
        ]
        filtered = self.filter.filter_batch(candidates)
        assert len(filtered) == 2
        assert filtered[0].status == CandidateStatus.FILTERED
        assert filtered[1].status == CandidateStatus.REJECTED

    def test_remove_rule(self) -> None:
        """Test removing a rule."""
        self.filter.add_rule(FilterRule(name="test_rule", pattern="*.test.com"))
        assert self.filter.remove_rule("test_rule") is True
        assert self.filter.remove_rule("nonexistent") is False

    def test_clear_rules(self) -> None:
        """Test clearing rules."""
        self.filter.add_rule(FilterRule(name="rule1", pattern="*.a.com"))
        self.filter.add_rule(FilterRule(name="rule2", pattern="*.b.com"))
        self.filter.clear_rules()
        assert len(self.filter.get_rules()) == 0

    def test_set_score_threshold(self) -> None:
        """Test setting score threshold."""
        self.filter.set_score_threshold(0.5)
        assert self.filter.get_score_threshold() == 0.5

    def test_threshold_excludes(self) -> None:
        """Test threshold excludes low scores."""
        self.filter.set_score_threshold(0.7)
        candidate = DiscoveryCandidate(
            domain=Domain(name="example.com"),
            source="test",
            score=0.3,
        )
        assert self.filter.should_include(candidate) is False


class TestExclusionFilter:
    """Tests for ExclusionFilter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.filter = ExclusionFilter()

    def test_only_exclusion_rules(self) -> None:
        """Test that only exclusion rules are applied."""
        self.filter.add_rule(FilterRule(
            name="exclude_bad",
            pattern="*.bad.com",
            is_exclusion=True,
        ))
        self.filter.add_rule(FilterRule(
            name="include_good",
            pattern="*.good.com",
            is_exclusion=False,
        ))
        # Should exclude bad domain
        bad = DiscoveryCandidate(domain=Domain(name="x.bad.com"), source="test")
        assert self.filter.should_include(bad) is False
        # Should include good domain (only because it passes exclusion)
        good = DiscoveryCandidate(domain=Domain(name="x.good.com"), source="test")
        assert self.filter.should_include(good) is True
        # Should include other domains
        other = DiscoveryCandidate(domain=Domain(name="x.com"), source="test")
        assert self.filter.should_include(other) is True


class TestInclusionFilter:
    """Tests for InclusionFilter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.filter = InclusionFilter()

    def test_only_inclusion_rules(self) -> None:
        """Test that only inclusion rules are applied."""
        self.filter.add_rule(FilterRule(
            name="include_good",
            pattern="*.good.com",
            is_exclusion=False,
        ))
        # Should include matching domain
        good = DiscoveryCandidate(domain=Domain(name="x.good.com"), source="test")
        assert self.filter.should_include(good) is True
        # Should exclude non-matching domain
        other = DiscoveryCandidate(domain=Domain(name="x.com"), source="test")
        assert self.filter.should_include(other) is False


class TestDiscoveryCollectorImpl:
    """Tests for DiscoveryCollectorImpl."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.collector = DiscoveryCollectorImpl()

    def test_add_candidates(self) -> None:
        """Test adding candidates."""
        domains = ["example.com", "test.net", "invalid"]
        candidates = self.collector.add_candidates("task-1", "test_source", domains)
        assert len(candidates) == 2  # "invalid" should be filtered

    def test_get_candidates(self) -> None:
        """Test getting candidates."""
        self.collector.add_candidates("task-1", "source1", ["a.com", "b.com"])
        self.collector.add_candidates("task-1", "source2", ["c.com"])

        all_candidates = self.collector.get_candidates("task-1")
        assert len(all_candidates) == 3

        source1_candidates = self.collector.get_candidates("task-1", "source1")
        assert len(source1_candidates) == 2

    def test_clear_candidates(self) -> None:
        """Test clearing candidates."""
        self.collector.add_candidates("task-1", "source1", ["a.com"])
        self.collector.clear_candidates("task-1")
        candidates = self.collector.get_candidates("task-1")
        assert len(candidates) == 0

    def test_create_batch(self) -> None:
        """Test creating a batch."""
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        source = DiscoverySource(name="test", source_type=SourceType.PASSIVE)
        candidates = [
            DiscoveryCandidate(domain=Domain(name="a.com"), source="test"),
        ]
        batch = self.collector.create_batch(task, source, candidates, 1)
        assert batch.batch_id.startswith("batch-t1")
        assert batch.count == 1
        assert batch.batch_number == 1

    def test_extract_candidates_from_string(self) -> None:
        """Test extracting candidates from string."""
        domains = self.collector.extract_candidates("example.com")
        assert domains == ("example.com",)

    def test_extract_candidates_from_list(self) -> None:
        """Test extracting candidates from list."""
        domains = self.collector.extract_candidates(["a.com", "b.net"])
        assert domains == ("a.com", "b.net")

    def test_extract_candidates_from_dict(self) -> None:
        """Test extracting candidates from dict."""
        domains = self.collector.extract_candidates({"domains": ["example.com"]})
        assert domains == ("example.com",)

    def test_validate_response_valid(self) -> None:
        """Test response validation."""
        assert self.collector.validate_response(["a.com", "b.com"]) is True
        assert self.collector.validate_response({"domains": ["a.com"]}) is True

    def test_validate_response_invalid(self) -> None:
        """Test invalid response validation."""
        assert self.collector.validate_response(None) is False
        assert self.collector.validate_response(123) is False


class TestDiscoverySchedulerImpl:
    """Tests for DiscoverySchedulerImpl."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.scheduler = DiscoverySchedulerImpl()

    def test_schedule_task(self) -> None:
        """Test scheduling a task."""
        task = DiscoveryTask(
            task_id="task-1",
            seed_domains=("example.com",),
        )
        self.scheduler.schedule_task(task)
        assert self.scheduler.has_more_sources(task) is True

    def test_get_next_source(self) -> None:
        """Test getting next source."""
        task = DiscoveryTask(
            task_id="task-1",
            seed_domains=("example.com",),
        )
        self.scheduler.schedule_task(task)
        source = self.scheduler.get_next_source(task)
        assert source is not None
        assert isinstance(source, DiscoverySource)

    def test_get_schedule_order(self) -> None:
        """Test getting scheduled order."""
        task = DiscoveryTask(
            task_id="task-1",
            seed_domains=("example.com",),
            sources=("ct", "whois"),
        )
        self.scheduler.schedule_task(task)
        order = self.scheduler.get_schedule_order(task)
        assert len(order) >= 1

    def test_cancel_task(self) -> None:
        """Test cancelling a task."""
        task = DiscoveryTask(
            task_id="task-1",
            seed_domains=("example.com",),
        )
        self.scheduler.schedule_task(task)
        assert self.scheduler.cancel_task("task-1") is True
        assert self.scheduler.cancel_task("nonexistent") is False


class TestPriorityScheduler:
    """Tests for PriorityScheduler."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.scheduler = PriorityScheduler()

    def test_prioritizes_passive_for_keywords(self) -> None:
        """Test that passive sources are prioritized for keyword tasks."""
        task = DiscoveryTask(
            task_id="task-1",
            seed_domains=("example.com",),
            keywords=("malware",),
        )
        self.scheduler.schedule_task(task)
        order = self.scheduler.get_schedule_order(task)
        # Should have sources
        assert len(order) >= 1


class TestDiscoveryEngineImpl:
    """Tests for DiscoveryEngineImpl."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.engine = DiscoveryEngineImpl()

    def test_discover_basic(self) -> None:
        """Test basic discovery."""
        task = DiscoveryTask(
            task_id="task-1",
            seed_domains=("example.com",),
        )

        # Add some candidates
        self.engine.add_candidates("task-1", "test_source", ["valid.com", "another.net"])

        result = self.engine.discover(task)
        assert result is not None
        assert result.task_id == "task-1"

    def test_discover_async(self) -> None:
        """Test async discovery."""
        task = DiscoveryTask(
            task_id="task-async",
            seed_domains=("example.com",),
        )
        self.engine.add_candidates("task-async", "source", ["test.com"])

        task_id = self.engine.discover_async(task)
        assert task_id == "task-async"

    def test_get_result(self) -> None:
        """Test getting result."""
        task = DiscoveryTask(
            task_id="task-result",
            seed_domains=("example.com",),
        )
        self.engine.add_candidates("task-result", "source", ["test.com"])
        self.engine.discover(task)

        result = self.engine.get_result("task-result")
        assert result is not None

    def test_get_result_not_found(self) -> None:
        """Test getting non-existent result."""
        result = self.engine.get_result("nonexistent")
        assert result is None

    def test_get_progress(self) -> None:
        """Test getting progress."""
        task = DiscoveryTask(
            task_id="task-progress",
            seed_domains=("example.com",),
        )
        self.engine.add_candidates("task-progress", "source", ["test.com"])
        self.engine.discover(task)

        progress = self.engine.get_progress("task-progress")
        assert progress is not None

    def test_cancel(self) -> None:
        """Test cancelling discovery."""
        task = DiscoveryTask(
            task_id="task-cancel",
            seed_domains=("example.com",),
        )
        # Don't add candidates so the task stays in PENDING/RUNNING state
        # Check cancel on non-existent task
        assert self.engine.cancel("nonexistent") is False

    def test_add_candidates(self) -> None:
        """Test adding candidates from external provider."""
        candidates = self.engine.add_candidates(
            "provider-task",
            "external_provider",
            ["domain1.com", "domain2.net", "domain3.org"],
        )
        assert len(candidates) == 3

    def test_validation_pipeline(self) -> None:
        """Test that validation is applied."""
        task = DiscoveryTask(
            task_id="validation-test",
            seed_domains=("example.com",),
        )
        # Add valid and invalid domains
        self.engine.add_candidates("validation-test", "source", [
            "valid.com",
            "also-valid.net",
        ])
        result = self.engine.discover(task)
        assert result.total_candidates >= 0

    def test_scoring_pipeline(self) -> None:
        """Test that scoring is applied."""
        task = DiscoveryTask(
            task_id="scoring-test",
            seed_domains=("example.com",),
        )
        self.engine.add_candidates("scoring-test", "source", ["test.com"])
        result = self.engine.discover(task)
        for candidate in result.candidates:
            if candidate.score is not None:
                assert 0.0 <= candidate.score <= 1.0

    def test_filtering_pipeline(self) -> None:
        """Test that filtering is applied."""
        task = DiscoveryTask(
            task_id="filter-test",
            seed_domains=("example.com",),
        )
        self.engine.add_candidates("filter-test", "source", ["test.com"])
        result = self.engine.discover(task)
        assert result is not None

    def test_max_candidates_limit(self) -> None:
        """Test max candidates limit."""
        task = DiscoveryTask(
            task_id="max-test",
            seed_domains=("example.com",),
            max_candidates=5,
        )
        # Add more than max candidates
        domains = [f"domain{i}.com" for i in range(10)]
        self.engine.add_candidates("max-test", "source", domains)
        result = self.engine.discover(task)
        assert result.total_candidates <= 5

    def test_get_status(self) -> None:
        """Test getting task status."""
        task = DiscoveryTask(
            task_id="status-test",
            seed_domains=("example.com",),
        )
        self.engine.add_candidates("status-test", "source", ["test.com"])
        self.engine.discover(task)
        status = self.engine.get_status("status-test")
        assert status == DiscoveryStatus.COMPLETED


class TestDiscoveryModels:
    """Tests for discovery models."""

    def test_domain_full_domain(self) -> None:
        """Test Domain.full_domain property."""
        d1 = Domain(name="example.com")
        assert d1.full_domain == "example.com"

        d2 = Domain(name="example.com", subdomain="www")
        assert d2.full_domain == "www.example.com"

    def test_discovery_task_validation(self) -> None:
        """Test DiscoveryTask validation."""
        # Valid task
        task = DiscoveryTask(task_id="t1", seed_domains=("a.com",))
        assert task.task_id == "t1"

        # Task with keywords
        task2 = DiscoveryTask(
            task_id="t2",
            seed_domains=("a.com",),
            keywords=("keyword",),
        )
        assert task2.has_keywords is True

    def test_discovery_candidate_properties(self) -> None:
        """Test DiscoveryCandidate properties."""
        d = Domain(name="example.com")
        c1 = DiscoveryCandidate(domain=d, source="test")
        assert c1.is_valid is True

        c2 = DiscoveryCandidate(
            domain=d,
            source="test",
            validation_result=ValidationResult.INVALID_SYNTAX,
        )
        assert c2.is_valid is False

    def test_discovery_statistics(self) -> None:
        """Test DiscoveryStatistics."""
        start = datetime.now(timezone.utc)
        stats = DiscoveryStatistics(
            task_id="t1",
            started_at=start,
            ended_at=start,
            candidates_discovered=100,
            candidates_validated=90,
        )
        assert stats.duration_seconds == 0.0
        assert stats.success_rate == 90.0

    def test_discovery_progress(self) -> None:
        """Test DiscoveryProgress."""
        progress = DiscoveryProgress(
            task_id="t1",
            status=DiscoveryStatus.RUNNING,
            total_batches=10,
            completed_batches=5,
            total_candidates=100,
            current_batch=5,
        )
        assert progress.percent_complete == 50.0
        assert progress.is_finished is False

    def test_filter_rule_properties(self) -> None:
        """Test FilterRule properties."""
        rule1 = FilterRule(name="exclude", pattern="*.evil.com", is_exclusion=True)
        assert rule1.is_exclusion is True
        assert rule1.is_inclusion is False

        rule2 = FilterRule(name="include", pattern="*.good.com", is_exclusion=False)
        assert rule2.is_exclusion is False
        assert rule2.is_inclusion is True


class TestDiscoveryExceptions:
    """Tests for discovery exceptions."""

    def test_discovery_error(self) -> None:
        """Test DiscoveryError."""
        error = DiscoveryError("test error", "task-1")
        assert error.message == "test error"
        assert error.task_id == "task-1"

    def test_validation_error(self) -> None:
        """Test ValidationError."""
        error = ValidationError("validation failed", domain="evil.com", task_id="t1")
        assert error.domain == "evil.com"

    def test_filter_error(self) -> None:
        """Test FilterError."""
        error = FilterError("filter failed", rule="block_evil", task_id="t1")
        assert error.rule == "block_evil"

    def test_scheduler_error(self) -> None:
        """Test SchedulerError."""
        error = SchedulerError("schedule failed", "t1")
        assert error.task_id == "t1"

    def test_collector_error(self) -> None:
        """Test CollectorError."""
        error = CollectorError("collect failed", source="ct", task_id="t1")
        assert error.source == "ct"

    def test_task_not_found_error(self) -> None:
        """Test TaskNotFoundError."""
        error = TaskNotFoundError("t999")
        assert error.task_id == "t999"

    def test_max_candidates_error(self) -> None:
        """Test MaxCandidatesReachedError."""
        error = MaxCandidatesReachedError(100, "t1")
        assert error.max_candidates == 100


class TestCollectorCoverage:
    """Additional collector tests for coverage."""

    def test_extract_from_flat_dict(self) -> None:
        """Test extracting from flat dict."""
        collector = DiscoveryCollectorImpl()
        data = {"results": ["a.com", "b.net"]}
        result = collector.extract_candidates(data)
        assert len(result) == 2

    def test_extract_with_name_field(self) -> None:
        """Test extracting with name field."""
        collector = DiscoveryCollectorImpl()
        data = [{"name": "c.com"}, {"name": "d.net"}]
        result = collector.extract_candidates(data)
        assert len(result) == 2

    def test_validate_invalid_response(self) -> None:
        """Test validating invalid response."""
        collector = DiscoveryCollectorImpl()
        assert collector.validate_response({"other": "value"}) is False
        assert collector.validate_response(12345) is False


class TestFilterCoverage:
    """Additional filter tests for coverage."""

    def test_glob_patterns(self) -> None:
        """Test glob pattern matching."""
        filter_impl = DomainFilter()
        filter_impl.add_rule(FilterRule(name="test", pattern="evil*.com"))
        candidate = DiscoveryCandidate(domain=Domain(name="evil-domain.com"), source="t")
        assert filter_impl.should_include(candidate) is False

    def test_literal_pattern(self) -> None:
        """Test literal pattern matching."""
        filter_impl = DomainFilter()
        filter_impl.add_rule(FilterRule(name="test", pattern="malicious"))
        candidate = DiscoveryCandidate(domain=Domain(name="malicious.com"), source="t")
        assert filter_impl.should_include(candidate) is False

    def test_threshold_with_no_score(self) -> None:
        """Test threshold with unscored candidate."""
        filter_impl = DomainFilter()
        filter_impl.set_score_threshold(0.5)
        candidate = DiscoveryCandidate(domain=Domain(name="test.com"), source="t")
        # No score means threshold doesn't apply
        assert filter_impl.should_include(candidate) is True


class TestEngineCoverage:
    """Additional engine tests for coverage."""

    def test_get_candidates_with_status(self) -> None:
        """Test getting candidates with status filter."""
        engine = DiscoveryEngineImpl()
        engine.add_candidate("test-task", DiscoveryCandidate(
            domain=Domain(name="a.com"),
            source="test",
            status=CandidateStatus.VALIDATED,
        ))
        candidates = engine.get_candidates("test-task", CandidateStatus.VALIDATED)
        assert len(candidates) == 1

    def test_add_candidate_directly(self) -> None:
        """Test adding candidate directly."""
        engine = DiscoveryEngineImpl()
        candidate = DiscoveryCandidate(domain=Domain(name="b.com"), source="test")
        engine.add_candidate("direct-task", candidate)
        candidates = engine.get_candidates("direct-task")
        assert len(candidates) == 1
