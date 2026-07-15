"""Candidate collection for discovery."""

from typing import Callable, Iterator

from .exceptions import CollectorError
from .interfaces import DiscoveryCollector
from .models import (
    DiscoveryBatch,
    DiscoveryCandidate,
    DiscoverySource,
    DiscoveryTask,
    Domain,
    SourceResult,
)


class DiscoveryCollectorImpl(DiscoveryCollector):
    """Implementation of DiscoveryCollector.

    Collects and processes candidates from discovery sources.
    Accepts candidates from external providers.
    """

    def __init__(self) -> None:
        """Initialize collector."""
        self._candidates: dict[str, list[DiscoveryCandidate]] = {}
        self._batch_counter: int = 0

    def collect(
        self,
        source: DiscoverySource,
        task: DiscoveryTask,
    ) -> SourceResult:
        """Collect candidates from a source.

        Note: This implementation requires external providers to
        supply candidates. Actual network collection is handled
        by provider implementations.

        Args:
            source: Source to collect from.
            task: Parent task with configuration.

        Returns:
            Results from the source.
        """
        task_key = f"{task.task_id}:{source.name}"

        # Get pre-collected candidates for this task/source
        candidates = self._candidates.get(task_key, [])

        return SourceResult(
            source_name=source.name,
            candidates=tuple(candidates),
            duration_ms=0.0,
        )

    def extract_candidates(self, raw_response: object) -> tuple[str, ...]:
        """Extract domain candidates from raw response.

        Args:
            raw_response: Raw response from source.

        Returns:
            Tuple of domain strings.
        """
        if raw_response is None:
            return ()

        if isinstance(raw_response, str):
            return (raw_response,) if self._is_valid_domain_format(raw_response) else ()

        if isinstance(raw_response, (list, tuple)):
            domains = []
            for item in raw_response:
                if isinstance(item, str):
                    if self._is_valid_domain_format(item):
                        domains.append(item)
                elif isinstance(item, dict):
                    domain = item.get("domain") or item.get("name")
                    if isinstance(domain, str) and self._is_valid_domain_format(domain):
                        domains.append(domain)
            return tuple(domains)

        if isinstance(raw_response, dict):
            # Try common field names
            for field in ("domains", "data", "results", "candidates"):
                if field in raw_response:
                    value = raw_response[field]
                    if isinstance(value, (list, tuple)):
                        return self.extract_candidates(value)
                    elif isinstance(value, str):
                        return (value,) if self._is_valid_domain_format(value) else ()

        return ()

    def validate_response(self, raw_response: object) -> bool:
        """Validate that a response is well-formed.

        Args:
            raw_response: Response to validate.

        Returns:
            True if response is valid.
        """
        if raw_response is None:
            return False

        if isinstance(raw_response, str):
            return True

        if isinstance(raw_response, (list, tuple)):
            return True

        if isinstance(raw_response, dict):
            # Check for at least one valid field
            valid_fields = {"domains", "data", "results", "candidates", "domain", "name"}
            return bool(valid_fields.intersection(raw_response.keys()))

        return False

    def add_candidates(
        self,
        task_id: str,
        source_name: str,
        domains: list[str],
    ) -> list[DiscoveryCandidate]:
        """Add candidates from an external provider.

        Args:
            task_id: Task ID.
            source_name: Source name.
            domains: List of domain strings.

        Returns:
            List of created candidates.
        """
        task_key = f"{task_id}:{source_name}"

        if task_key not in self._candidates:
            self._candidates[task_key] = []

        candidates = []
        for domain_str in domains:
            domain = self._parse_domain(domain_str)
            if domain is not None:
                candidate = DiscoveryCandidate(
                    domain=domain,
                    source=source_name,
                )
                candidates.append(candidate)
                self._candidates[task_key].append(candidate)

        return candidates

    def get_candidates(
        self,
        task_id: str,
        source_name: str | None = None,
    ) -> tuple[DiscoveryCandidate, ...]:
        """Get collected candidates.

        Args:
            task_id: Task ID.
            source_name: Optional source name filter.

        Returns:
            Tuple of candidates.
        """
        if source_name:
            task_key = f"{task_id}:{source_name}"
            return tuple(self._candidates.get(task_key, []))
        else:
            all_candidates = []
            prefix = f"{task_id}:"
            for key, candidates in self._candidates.items():
                if key.startswith(prefix):
                    all_candidates.extend(candidates)
            return tuple(all_candidates)

    def clear_candidates(self, task_id: str) -> None:
        """Clear candidates for a task.

        Args:
            task_id: Task ID.
        """
        prefix = f"{task_id}:"
        keys_to_remove = [k for k in self._candidates.keys() if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._candidates[key]

    def create_batch(
        self,
        task: DiscoveryTask,
        source: DiscoverySource,
        candidates: list[DiscoveryCandidate],
        batch_number: int,
    ) -> DiscoveryBatch:
        """Create a batch from candidates.

        Args:
            task: Parent task.
            source: Source of candidates.
            candidates: Candidates to batch.
            batch_number: Batch number.

        Returns:
            Created batch.
        """
        self._batch_counter += 1
        batch_id = f"batch-{task.task_id}-{batch_number}-{self._batch_counter}"

        return DiscoveryBatch(
            batch_id=batch_id,
            task_id=task.task_id,
            candidates=tuple(candidates),
            source=source.name,
            batch_number=batch_number,
        )

    def _is_valid_domain_format(self, domain: str) -> bool:
        """Check if domain has valid format.

        Args:
            domain: Domain string.

        Returns:
            True if format is valid.
        """
        if not domain or len(domain) > 253:
            return False

        # Basic format check
        parts = domain.lower().split(".")
        if len(parts) < 2:
            return False

        # Check each part
        for part in parts:
            if not part or len(part) > 63:
                return False
            if not part[0].isalnum() or not part[-1].isalnum():
                return False
            if not all(c.isalnum() or c in "-_" for c in part):
                return False

        return True

    def _parse_domain(self, domain_str: str) -> Domain | None:
        """Parse a domain string into a Domain object.

        Args:
            domain_str: Domain string.

        Returns:
            Domain object or None if invalid.
        """
        if not self._is_valid_domain_format(domain_str):
            return None

        parts = domain_str.lower().split(".")
        name = ".".join(parts)

        return Domain(name=name)
