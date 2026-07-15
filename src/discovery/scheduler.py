"""Discovery task and source scheduling."""

from typing import Iterator

from .interfaces import DiscoveryScheduler, DiscoverySource
from .models import DiscoverySource as SourceModel
from .models import DiscoveryTask, SourceType


class DiscoverySchedulerImpl(DiscoveryScheduler):
    """Implementation of DiscoveryScheduler.

    Manages the ordering and scheduling of discovery tasks
    and sources based on priority and configuration.
    """

    def __init__(self) -> None:
        """Initialize scheduler."""
        self._scheduled_tasks: dict[str, DiscoveryTask] = {}
        self._source_order: dict[str, list[str]] = {}

    def schedule_task(self, task: DiscoveryTask) -> None:
        """Schedule a discovery task.

        Args:
            task: Task to schedule.
        """
        self._scheduled_tasks[task.task_id] = task
        self._calculate_source_order(task)

    def get_next_source(self, task: DiscoveryTask) -> DiscoverySource | None:
        """Get the next source to query.

        Args:
            task: Current task.

        Returns:
            Next source to query, or None if done.
        """
        if task.task_id not in self._scheduled_tasks:
            self.schedule_task(task)

        source_names = self._source_order.get(task.task_id, [])
        if not source_names:
            return None

        # Return the first source and remove it from the list
        source_name = source_names.pop(0)
        return self._get_source_by_name(source_name)

    def has_more_sources(self, task: DiscoveryTask) -> bool:
        """Check if more sources are available.

        Args:
            task: Current task.

        Returns:
            True if more sources to query.
        """
        source_names = self._source_order.get(task.task_id, [])
        return len(source_names) > 0

    def get_schedule_order(
        self,
        task: DiscoveryTask,
    ) -> tuple[DiscoverySource, ...]:
        """Get sources in scheduled order.

        Args:
            task: Task to get schedule for.

        Returns:
            Ordered tuple of sources.
        """
        if task.task_id not in self._scheduled_tasks:
            self.schedule_task(task)

        source_names = self._source_order.get(task.task_id, [])
        return tuple(
            s for s in (self._get_source_by_name(name) for name in source_names)
            if s is not None
        )

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task.

        Args:
            task_id: ID of task to cancel.

        Returns:
            True if task was cancelled.
        """
        if task_id in self._scheduled_tasks:
            del self._scheduled_tasks[task_id]
        if task_id in self._source_order:
            del self._source_order[task_id]
            return True
        return False

    def _calculate_source_order(self, task: DiscoveryTask) -> None:
        """Calculate the order of sources for a task.

        Args:
            task: Task to calculate order for.
        """
        # Get source names from task configuration
        requested_sources = task.sources

        # If no specific sources requested, use all
        if not requested_sources:
            source_names = self._get_default_source_names()
        else:
            source_names = list(requested_sources)

        # Sort by priority (higher priority first)
        sources = [
            (name, self._get_source_priority(name))
            for name in source_names
            if self._get_source_by_name(name) is not None
        ]
        sources.sort(key=lambda x: x[1], reverse=True)

        self._source_order[task.task_id] = [name for name, _ in sources]

    def _get_source_by_name(self, name: str) -> DiscoverySource | None:
        """Get a source by name.

        Args:
            name: Source name.

        Returns:
            Source if found, None otherwise.
        """
        # Return a basic source model for scheduling purposes
        # Actual source providers will be used in the pipeline
        return SourceModel(
            name=name,
            source_type=SourceType.PASSIVE,
            description=f"Discovery source: {name}",
            priority=self._get_source_priority(name),
        )

    def _get_source_priority(self, name: str) -> int:
        """Get priority for a source.

        Args:
            name: Source name.

        Returns:
            Priority value.
        """
        # Priority order for default sources
        priority_map = {
            "ct": 100,
            "certificate_transparency": 100,
            "passive_dns": 90,
            "dns_cache": 80,
            "whois": 70,
            "dns_enum": 60,
            "subdomain_enum": 50,
        }
        return priority_map.get(name.lower(), 0)

    def _get_default_source_names(self) -> tuple[str, ...]:
        """Get default source names in priority order.

        Returns:
            Tuple of default source names.
        """
        return (
            "ct",
            "passive_dns",
            "dns_cache",
            "whois",
        )


class PriorityScheduler(DiscoverySchedulerImpl):
    """Scheduler that prioritizes by source type and yield.

    Extends base scheduler with type-based prioritization.
    """

    def _calculate_source_order(self, task: DiscoveryTask) -> None:
        """Calculate source order with type-based prioritization.

        Args:
            task: Task to calculate order for.
        """
        requested_sources = task.sources or self._get_default_source_names()
        sources = []

        for name in requested_sources:
            source = self._get_source_by_name(name)
            if source is None:
                continue

            # Calculate effective priority
            effective_priority = self._calculate_effective_priority(
                source,
                task,
            )
            sources.append((name, effective_priority))

        # Sort by effective priority (higher first)
        sources.sort(key=lambda x: x[1], reverse=True)
        self._source_order[task.task_id] = [name for name, _ in sources]

    def _calculate_effective_priority(
        self,
        source: SourceModel,
        task: DiscoveryTask,
    ) -> int:
        """Calculate effective priority for a source.

        Args:
            source: Source to calculate priority for.
            task: Associated task.

        Returns:
            Effective priority value.
        """
        base_priority = source.priority

        # Boost passive sources if task has no keywords
        if not task.has_keywords and source.is_passive:
            base_priority += 10

        # Boost active sources if task has keywords
        if task.has_keywords and not source.is_passive:
            base_priority += 5

        return base_priority
