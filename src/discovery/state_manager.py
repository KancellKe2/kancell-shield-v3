"""State manager for discovery pipeline.

This module manages the state of discovery operations
including pause, resume, and stop functionality.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Sequence

from .models import DiscoveryCandidate, DiscoveryTask, DiscoveryStatus


class PipelineState(Enum):
    """States of the discovery pipeline."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StateSnapshot:
    """Snapshot of pipeline state at a point in time."""

    state: PipelineState
    task_id: str
    timestamp: datetime
    processed_count: int
    queue_size: int
    current_stage: str | None = None
    error: str | None = None


@dataclass
class StateTransition:
    """Record of a state transition."""

    from_state: PipelineState
    to_state: PipelineState
    timestamp: datetime
    reason: str | None = None


class StateManager:
    """Manager for pipeline state.

    Tracks state transitions and provides state queries.
    """

    def __init__(self) -> None:
        """Initialize state manager."""
        self._current_state: PipelineState = PipelineState.IDLE
        self._task_id: str | None = None
        self._transitions: list[StateTransition] = []
        self._listeners: list[Callable[[PipelineState, PipelineState], None]] = []
        self._processed_count = 0
        self._current_stage: str | None = None
        self._last_error: str | None = None

    @property
    def state(self) -> PipelineState:
        """Get current state."""
        return self._current_state

    @property
    def task_id(self) -> str | None:
        """Get current task ID."""
        return self._task_id

    @property
    def processed_count(self) -> int:
        """Get processed candidate count."""
        return self._processed_count

    @property
    def current_stage(self) -> str | None:
        """Get current stage name."""
        return self._current_stage

    @property
    def last_error(self) -> str | None:
        """Get last error message."""
        return self._last_error

    def set_state(
        self,
        state: PipelineState,
        task_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Set the pipeline state.

        Args:
            state: New state.
            task_id: Associated task ID.
            reason: Reason for transition.
        """
        old_state = self._current_state
        self._current_state = state

        if task_id is not None:
            self._task_id = task_id

        # Record transition
        transition = StateTransition(
            from_state=old_state,
            to_state=state,
            timestamp=datetime.now(timezone.utc),
            reason=reason,
        )
        self._transitions.append(transition)

        # Notify listeners
        for listener in self._listeners:
            listener(old_state, state)

    def transition_to_running(self, task_id: str) -> None:
        """Transition to running state.

        Args:
            task_id: Task ID.
        """
        self.set_state(PipelineState.RUNNING, task_id, "Task started")

    def transition_to_paused(self, reason: str | None = None) -> None:
        """Transition to paused state.

        Args:
            reason: Reason for pausing.
        """
        self.set_state(PipelineState.PAUSED, reason=reason)

    def transition_to_stopping(self) -> None:
        """Transition to stopping state."""
        self.set_state(PipelineState.STOPPING, reason="Stop requested")

    def transition_to_stopped(self) -> None:
        """Transition to stopped state."""
        self.set_state(PipelineState.STOPPED, reason="Task stopped")

    def transition_to_completed(self) -> None:
        """Transition to completed state."""
        self.set_state(PipelineState.COMPLETED, reason="Task completed")

    def transition_to_failed(self, error: str) -> None:
        """Transition to failed state.

        Args:
            error: Error message.
        """
        self._last_error = error
        self.set_state(PipelineState.FAILED, reason=error)

    def reset(self) -> None:
        """Reset to idle state."""
        self._current_state = PipelineState.IDLE
        self._task_id = None
        self._transitions.clear()
        self._processed_count = 0
        self._current_stage = None
        self._last_error = None

    def add_listener(
        self,
        listener: Callable[[PipelineState, PipelineState], None],
    ) -> None:
        """Add a state change listener.

        Args:
            listener: Function to call on state change.
        """
        self._listeners.append(listener)

    def remove_listener(
        self,
        listener: Callable[[PipelineState, PipelineState], None],
    ) -> bool:
        """Remove a state change listener.

        Args:
            listener: Listener to remove.

        Returns:
            True if listener was removed.
        """
        try:
            self._listeners.remove(listener)
            return True
        except ValueError:
            return False

    def increment_processed(self, count: int = 1) -> None:
        """Increment processed candidate count.

        Args:
            count: Number to add.
        """
        self._processed_count += count

    def set_current_stage(self, stage: str | None) -> None:
        """Set current stage name.

        Args:
            stage: Stage name.
        """
        self._current_stage = stage

    def get_snapshot(self) -> StateSnapshot:
        """Get current state snapshot.

        Returns:
            Current state snapshot.
        """
        return StateSnapshot(
            state=self._current_state,
            task_id=self._task_id or "",
            timestamp=datetime.now(timezone.utc),
            processed_count=self._processed_count,
            queue_size=0,  # Will be set by orchestrator
            current_stage=self._current_stage,
            error=self._last_error,
        )

    def get_transitions(
        self,
        since: datetime | None = None,
    ) -> tuple[StateTransition, ...]:
        """Get state transitions.

        Args:
            since: Optional timestamp to filter by.

        Returns:
            Tuple of transitions.
        """
        if since is None:
            return tuple(self._transitions)

        return tuple(
            t for t in self._transitions
            if t.timestamp >= since
        )

    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._current_state == PipelineState.RUNNING

    def is_paused(self) -> bool:
        """Check if pipeline is paused."""
        return self._current_state == PipelineState.PAUSED

    def is_stopped(self) -> bool:
        """Check if pipeline is stopped."""
        return self._current_state in (
            PipelineState.STOPPED,
            PipelineState.FAILED,
            PipelineState.COMPLETED,
        )

    def can_start(self) -> bool:
        """Check if pipeline can be started."""
        return self._current_state in (
            PipelineState.IDLE,
            PipelineState.STOPPED,
            PipelineState.COMPLETED,
        )

    def can_pause(self) -> bool:
        """Check if pipeline can be paused."""
        return self._current_state == PipelineState.RUNNING

    def can_resume(self) -> bool:
        """Check if pipeline can be resumed."""
        return self._current_state == PipelineState.PAUSED

    def can_stop(self) -> bool:
        """Check if pipeline can be stopped."""
        return self._current_state in (
            PipelineState.RUNNING,
            PipelineState.PAUSED,
        )
