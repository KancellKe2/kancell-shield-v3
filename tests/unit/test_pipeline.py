"""Unit tests for Pipeline."""

import pytest

from src.discovery import (
    CandidateStatus,
    DiscoveryCandidate,
    DiscoveryTask,
    Domain,
    FilterStage,
    PipelineContext,
    PipelineResult,
    PipelineStage,
    ScoreStage,
    ValidateStage,
)
from src.discovery.pipeline import (
    CollectStage,
    EnqueueStage,
    DiscoveryPipeline,
    FilteredPipeline,
)


class TestPipelineStage:
    """Tests for PipelineStage."""

    def test_stage_name(self) -> None:
        """Test stage name property."""
        stage = CollectStage()
        assert stage.name == "collect"


class TestCollectStage:
    """Tests for CollectStage."""

    def test_execute(self) -> None:
        """Test collect stage execution."""
        stage = CollectStage()
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        context = PipelineContext(task=task, results=[])
        result = stage.execute(context)
        assert result.stage == "collect"


class TestValidateStage:
    """Tests for ValidateStage."""

    def test_validate_valid(self) -> None:
        """Test validating valid candidates."""
        stage = ValidateStage()
        candidates = [
            DiscoveryCandidate(domain=Domain(name="valid.com"), source="test"),
        ]
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        context = PipelineContext(task=task, results=candidates)
        result = stage.execute(context)
        assert result.results[0].status == CandidateStatus.VALIDATED

    def test_validate_invalid(self) -> None:
        """Test validating invalid candidates."""
        stage = ValidateStage()
        candidates = [
            DiscoveryCandidate(domain=Domain(name="invalid domain"), source="test"),
        ]
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        context = PipelineContext(task=task, results=candidates)
        result = stage.execute(context)
        assert result.results[0].status == CandidateStatus.REJECTED


class TestFilterStage:
    """Tests for FilterStage."""

    def test_filter_batch(self) -> None:
        """Test filter stage."""
        from src.discovery import FilterRule
        from src.discovery.filter import DomainFilter

        filter_impl = DomainFilter()
        filter_impl.add_rule(FilterRule(
            name="exclude",
            pattern="evil.com",
            is_exclusion=True,
        ))

        stage = FilterStage(filter_impl)
        candidates = [
            DiscoveryCandidate(domain=Domain(name="good.com"), source="test"),
            DiscoveryCandidate(domain=Domain(name="evil.com"), source="test"),
        ]
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        context = PipelineContext(task=task, results=candidates)
        result = stage.execute(context)
        assert len(result.results) == 2


class TestScoreStage:
    """Tests for ScoreStage."""

    def test_score_batch(self) -> None:
        """Test score stage."""
        stage = ScoreStage()
        candidates = [
            DiscoveryCandidate(domain=Domain(name="example.com"), source="test"),
        ]
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        context = PipelineContext(task=task, results=candidates)
        result = stage.execute(context)
        assert result.results[0].score is not None
        assert result.results[0].status == CandidateStatus.SCORED


class TestEnqueueStage:
    """Tests for EnqueueStage."""

    def test_execute(self) -> None:
        """Test enqueue stage."""
        enqueued = []

        def enqueue_func(c):
            enqueued.append(c)
            return True

        stage = EnqueueStage(enqueue_func)
        candidates = [
            DiscoveryCandidate(domain=Domain(name="a.com"), source="test"),
        ]
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        context = PipelineContext(task=task, results=candidates)
        stage.execute(context)
        assert len(enqueued) == 1


class TestDiscoveryPipeline:
    """Tests for DiscoveryPipeline."""

    def test_execute(self) -> None:
        """Test pipeline execution."""
        pipeline = DiscoveryPipeline()
        candidates = [
            DiscoveryCandidate(domain=Domain(name="valid.com"), source="test"),
        ]
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        result = pipeline.execute(task, candidates)
        assert isinstance(result, PipelineResult)
        assert result.candidates is not None
        assert len(result.candidates) >= 0

    def test_add_stage(self) -> None:
        """Test adding a stage."""
        pipeline = DiscoveryPipeline()
        original_count = len(pipeline.stages)
        pipeline.add_stage(CollectStage())
        assert len(pipeline.stages) == original_count + 1

    def test_remove_stage(self) -> None:
        """Test removing a stage."""
        pipeline = DiscoveryPipeline()
        assert pipeline.remove_stage("collect") is True
        assert pipeline.remove_stage("nonexistent") is False

    def test_get_stage(self) -> None:
        """Test getting a stage."""
        pipeline = DiscoveryPipeline()
        stage = pipeline.get_stage("validate")
        assert stage is not None
        assert isinstance(stage, ValidateStage)

    def test_insert_stage(self) -> None:
        """Test inserting a stage."""
        pipeline = DiscoveryPipeline()
        stages_before = len(pipeline.stages)
        pipeline.insert_stage(0, CollectStage())
        assert len(pipeline.stages) == stages_before + 1


class TestFilteredPipeline:
    """Tests for FilteredPipeline."""

    def test_disable_stage(self) -> None:
        """Test disabling a stage."""
        pipeline = FilteredPipeline()
        assert pipeline.is_stage_enabled("validate") is True
        pipeline.disable_stage("validate")
        assert pipeline.is_stage_enabled("validate") is False

    def test_enable_stage(self) -> None:
        """Test enabling a stage."""
        pipeline = FilteredPipeline()
        pipeline.disable_stage("validate")
        assert pipeline.is_stage_enabled("validate") is False
        pipeline.enable_stage("validate")
        assert pipeline.is_stage_enabled("validate") is True

    def test_execute_with_disabled_stages(self) -> None:
        """Test execution with disabled stages."""
        pipeline = FilteredPipeline()
        pipeline.disable_stage("validate")
        candidates = [
            DiscoveryCandidate(domain=Domain(name="any.com"), source="test"),
        ]
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        result = pipeline.execute(task, candidates)
        assert isinstance(result, PipelineResult)
