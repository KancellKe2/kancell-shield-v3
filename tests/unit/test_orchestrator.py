"""Unit tests for Orchestrator."""

import pytest

from src.discovery import (
    CandidateQueue,
    CandidateStatus,
    DiscoveryCandidate,
    DiscoveryOrchestrator,
    DiscoveryTask,
    Domain,
    PipelineState,
)
from src.discovery.metrics import (
    DeterministicMetricsCollector,
    MetricsCollector,
    MetricsSnapshot,
    StageMetrics,
)
from src.discovery.orchestrator import (
    BatchOrchestrator,
    StreamingOrchestrator,
)
from src.discovery.state_manager import (
    StateManager,
    StateSnapshot,
    StateTransition,
)


class TestStateManager:
    """Tests for StateManager."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.manager = StateManager()

    def test_initial_state(self) -> None:
        """Test initial state."""
        assert self.manager.state == PipelineState.IDLE
        assert self.manager.task_id is None

    def test_transition_to_running(self) -> None:
        """Test transition to running."""
        self.manager.transition_to_running("task-1")
        assert self.manager.state == PipelineState.RUNNING
        assert self.manager.task_id == "task-1"

    def test_transition_to_paused(self) -> None:
        """Test transition to paused."""
        self.manager.transition_to_running("task-1")
        self.manager.transition_to_paused("reason")
        assert self.manager.state == PipelineState.PAUSED

    def test_transition_to_stopped(self) -> None:
        """Test transition to stopped."""
        self.manager.transition_to_running("task-1")
        self.manager.transition_to_stopped()
        assert self.manager.state == PipelineState.STOPPED

    def test_transition_to_completed(self) -> None:
        """Test transition to completed."""
        self.manager.transition_to_running("task-1")
        self.manager.transition_to_completed()
        assert self.manager.state == PipelineState.COMPLETED

    def test_transition_to_failed(self) -> None:
        """Test transition to failed."""
        self.manager.transition_to_running("task-1")
        self.manager.transition_to_failed("error message")
        assert self.manager.state == PipelineState.FAILED
        assert self.manager.last_error == "error message"

    def test_increment_processed(self) -> None:
        """Test incrementing processed count."""
        self.manager.increment_processed(5)
        assert self.manager.processed_count == 5
        self.manager.increment_processed(3)
        assert self.manager.processed_count == 8

    def test_set_current_stage(self) -> None:
        """Test setting current stage."""
        self.manager.set_current_stage("validate")
        assert self.manager.current_stage == "validate"

    def test_get_snapshot(self) -> None:
        """Test getting state snapshot."""
        self.manager.transition_to_running("task-1")
        snapshot = self.manager.get_snapshot()
        assert isinstance(snapshot, StateSnapshot)
        assert snapshot.state == PipelineState.RUNNING
        assert snapshot.task_id == "task-1"

    def test_can_start(self) -> None:
        """Test can_start check."""
        assert self.manager.can_start() is True
        self.manager.transition_to_running("task-1")
        assert self.manager.can_start() is False

    def test_can_pause(self) -> None:
        """Test can_pause check."""
        assert self.manager.can_pause() is False
        self.manager.transition_to_running("task-1")
        assert self.manager.can_pause() is True

    def test_can_resume(self) -> None:
        """Test can_resume check."""
        assert self.manager.can_resume() is False
        self.manager.transition_to_running("task-1")
        self.manager.transition_to_paused()
        assert self.manager.can_resume() is True

    def test_can_stop(self) -> None:
        """Test can_stop check."""
        assert self.manager.can_stop() is False
        self.manager.transition_to_running("task-1")
        assert self.manager.can_stop() is True

    def test_reset(self) -> None:
        """Test reset."""
        self.manager.transition_to_running("task-1")
        self.manager.increment_processed(5)
        self.manager.reset()
        assert self.manager.state == PipelineState.IDLE
        assert self.manager.processed_count == 0

    def test_listener(self) -> None:
        """Test state change listener."""
        transitions = []

        def listener(from_state, to_state):
            transitions.append((from_state, to_state))

        self.manager.add_listener(listener)
        self.manager.transition_to_running("task-1")
        assert len(transitions) == 1
        assert transitions[0][0] == PipelineState.IDLE
        assert transitions[0][1] == PipelineState.RUNNING


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.collector = MetricsCollector()

    def test_record_processed(self) -> None:
        """Test recording processed count."""
        self.collector.record_processed(10)
        assert self.collector.processed_count == 10

    def test_record_filtered(self) -> None:
        """Test recording filtered count."""
        self.collector.record_filtered(5)
        assert self.collector.filtered_count == 5

    def test_record_accepted(self) -> None:
        """Test recording accepted count."""
        self.collector.record_accepted(8)
        assert self.collector.accepted_count == 8

    def test_record_rejected(self) -> None:
        """Test recording rejected count."""
        self.collector.record_rejected(2)
        assert self.collector.rejected_count == 2

    def test_record_candidate_status(self) -> None:
        """Test recording by status."""
        self.collector.record_candidate_status(CandidateStatus.FILTERED)
        self.collector.record_candidate_status(CandidateStatus.REJECTED)
        self.collector.record_candidate_status(CandidateStatus.SCORED)
        assert self.collector.filtered_count == 1
        assert self.collector.rejected_count == 1
        assert self.collector.accepted_count == 1

    def test_record_stage_timing(self) -> None:
        """Test recording stage timing."""
        self.collector.record_stage_timing("validate", 10.0)
        self.collector.record_stage_timing("validate", 20.0)
        metrics = self.collector.get_stage_metrics("validate")
        assert metrics.executions == 2
        assert metrics.average_duration_ms == 15.0

    def test_get_snapshot(self) -> None:
        """Test getting metrics snapshot."""
        self.collector.record_processed(100)
        snapshot = self.collector.get_snapshot(50)
        assert isinstance(snapshot, MetricsSnapshot)
        assert snapshot.processed_candidates == 100
        assert snapshot.queue_size == 50

    def test_get_summary(self) -> None:
        """Test getting summary."""
        self.collector.record_processed(100)
        self.collector.record_accepted(80)
        self.collector.record_rejected(20)
        summary = self.collector.get_summary()
        assert summary["processed"] == 100
        assert summary["accepted"] == 80
        assert summary["rejected"] == 20


class TestDeterministicMetricsCollector:
    """Tests for DeterministicMetricsCollector."""

    def test_tick(self) -> None:
        """Test tick counter."""
        collector = DeterministicMetricsCollector()
        assert collector.tick_count == 0
        collector.tick()
        assert collector.tick_count == 1

    def test_report_interval(self) -> None:
        """Test report interval."""
        collector = DeterministicMetricsCollector()
        collector.set_report_interval(5)
        assert collector._report_interval == 5


class TestDiscoveryOrchestrator:
    """Tests for DiscoveryOrchestrator."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.orchestrator = DiscoveryOrchestrator(queue_capacity=100)

    def test_initial_status(self) -> None:
        """Test initial status."""
        status = self.orchestrator.get_status()
        assert status["queue_size"] == 0
        assert status["pipeline_configured"] is False

    def test_configure_pipeline(self) -> None:
        """Test pipeline configuration."""
        from src.discovery.pipeline import DiscoveryPipeline
        pipeline = DiscoveryPipeline()
        self.orchestrator.configure_pipeline(pipeline)
        status = self.orchestrator.get_status()
        assert status["pipeline_configured"] is True

    def test_enqueue_candidates(self) -> None:
        """Test enqueueing candidates."""
        candidates = [
            DiscoveryCandidate(domain=Domain(name="a.com"), source="test"),
            DiscoveryCandidate(domain=Domain(name="b.com"), source="test"),
        ]
        count = self.orchestrator.enqueue_candidates(candidates)
        assert count == 2
        assert len(self.orchestrator.get_queue()) == 2

    def test_process_batch(self) -> None:
        """Test processing a batch."""
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        self.orchestrator.set_task(task)
        self.orchestrator.configure_pipeline()

        candidates = [
            DiscoveryCandidate(domain=Domain(name="valid.com"), source="test"),
        ]
        self.orchestrator.enqueue_candidates(candidates)

        result = self.orchestrator.process_batch()
        assert result is not None
        assert len(result.candidates) >= 0

    def test_start_stop(self) -> None:
        """Test start and stop."""
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        self.orchestrator.start(task)
        status = self.orchestrator.get_status()
        assert status["is_running"] is True

        self.orchestrator.stop()
        status = self.orchestrator.get_status()
        assert status["is_stopped"] is True

    def test_pause_resume(self) -> None:
        """Test pause and resume."""
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        self.orchestrator.start(task)
        self.orchestrator.pause()
        status = self.orchestrator.get_status()
        assert status["is_paused"] is True

        self.orchestrator.resume()
        status = self.orchestrator.get_status()
        assert status["is_running"] is True

    def test_reset(self) -> None:
        """Test reset."""
        task = DiscoveryTask(task_id="t1", seed_domains=("seed.com",))
        self.orchestrator.set_task(task)
        self.orchestrator.enqueue_candidates([
            DiscoveryCandidate(domain=Domain(name="a.com"), source="test"),
        ])
        self.orchestrator.reset()
        assert len(self.orchestrator.get_queue()) == 0


class TestStreamingOrchestrator:
    """Tests for StreamingOrchestrator."""

    def test_add_candidates(self) -> None:
        """Test adding candidates with immediate processing."""
        orchestrator = StreamingOrchestrator(batch_size=10)
        orchestrator.configure_pipeline()
        orchestrator.start(DiscoveryTask(task_id="t1", seed_domains=("seed.com",)))

        count = orchestrator.add_candidates([
            DiscoveryCandidate(domain=Domain(name="a.com"), source="test"),
        ])
        assert count == 1

        results = orchestrator.get_results()
        assert len(results) == 1

        orchestrator.stop()


class TestBatchOrchestrator:
    """Tests for BatchOrchestrator."""

    def test_process_if_ready(self) -> None:
        """Test processing when threshold is met."""
        orchestrator = BatchOrchestrator(batch_size=5, trigger_threshold=3)
        orchestrator.configure_pipeline()
        orchestrator.start(DiscoveryTask(task_id="t1", seed_domains=("seed.com",)))

        # Add below threshold
        orchestrator.add_candidates([
            DiscoveryCandidate(domain=Domain(name="a.com"), source="test"),
        ])
        assert orchestrator.process_if_ready() is None

        # Add to meet threshold
        orchestrator.add_candidates([
            DiscoveryCandidate(domain=Domain(name="b.com"), source="test"),
            DiscoveryCandidate(domain=Domain(name="c.com"), source="test"),
        ])
        result = orchestrator.process_if_ready()
        assert result is not None

        orchestrator.stop()

    def test_process_all_batches(self) -> None:
        """Test processing all batches."""
        orchestrator = BatchOrchestrator(batch_size=3)
        orchestrator.configure_pipeline()
        orchestrator.start(DiscoveryTask(task_id="t1", seed_domains=("seed.com",)))

        orchestrator.add_candidates([
            DiscoveryCandidate(domain=Domain(name=f"d{i}.com"), source="test")
            for i in range(7)
        ])

        results = orchestrator.process_all_batches()
        assert len(results) >= 1

        orchestrator.stop()
