"""Candidate filtering for discovery."""

import re
from typing import Sequence

from .exceptions import FilterError
from .interfaces import CandidateFilter
from .models import (
    CandidateStatus,
    DiscoveryCandidate,
    FilterRule,
)


class DomainFilter(CandidateFilter):
    """Implementation of CandidateFilter.

    Applies configurable inclusion/exclusion rules and
    threshold checks to candidates.
    """

    def __init__(self) -> None:
        """Initialize filter."""
        self._rules: list[FilterRule] = []
        self._score_threshold: float = 0.0
        self._exclude_scores_below: float = 0.0

    def should_include(self, candidate: DiscoveryCandidate) -> bool:
        """Check if candidate should be included.

        Args:
            candidate: Candidate to check.

        Returns:
            True if candidate should be included.
        """
        # Check score threshold
        if candidate.score is not None and candidate.score < self._exclude_scores_below:
            return False

        domain_str = candidate.domain.name.lower()

        # Apply exclusion rules first
        for rule in self._rules:
            if not rule.is_exclusion:
                continue
            if self._matches_rule(domain_str, rule.pattern):
                return False

        # Apply inclusion rules
        inclusion_rules = [r for r in self._rules if not r.is_exclusion]
        if inclusion_rules:
            # If there are inclusion rules, candidate must match at least one
            for rule in inclusion_rules:
                if self._matches_rule(domain_str, rule.pattern):
                    return True
            return False

        return True

    def filter_batch(
        self,
        candidates: Sequence[DiscoveryCandidate],
    ) -> tuple[DiscoveryCandidate, ...]:
        """Filter multiple candidates.

        Args:
            candidates: Candidates to filter.

        Returns:
            Filtered candidates.
        """
        filtered = []
        for candidate in candidates:
            if self.should_include(candidate):
                updated = DiscoveryCandidate(
                    domain=candidate.domain,
                    source=candidate.source,
                    discovered_at=candidate.discovered_at,
                    status=CandidateStatus.FILTERED if candidate.status != CandidateStatus.REJECTED else CandidateStatus.REJECTED,
                    validation_result=candidate.validation_result,
                    score=candidate.score,
                    confidence=candidate.confidence,
                    metadata=candidate.metadata,
                    parent_domain=candidate.parent_domain,
                )
                filtered.append(updated)
            else:
                updated = DiscoveryCandidate(
                    domain=candidate.domain,
                    source=candidate.source,
                    discovered_at=candidate.discovered_at,
                    status=CandidateStatus.REJECTED,
                    validation_result=candidate.validation_result,
                    score=candidate.score,
                    confidence=candidate.confidence,
                    metadata=candidate.metadata,
                    parent_domain=candidate.parent_domain,
                )
                filtered.append(updated)
        return tuple(filtered)

    def add_rule(self, rule: FilterRule) -> None:
        """Add a filter rule.

        Args:
            rule: Rule to add.
        """
        self._rules.append(rule)
        self._sort_rules()

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a filter rule.

        Args:
            rule_name: Name of rule to remove.

        Returns:
            True if rule was removed.
        """
        for i, rule in enumerate(self._rules):
            if rule.name == rule_name:
                self._rules.pop(i)
                return True
        return False

    def clear_rules(self) -> None:
        """Clear all filter rules."""
        self._rules.clear()

    def set_score_threshold(self, threshold: float) -> None:
        """Set the score threshold.

        Args:
            threshold: Minimum score to include.
        """
        if threshold < 0.0 or threshold > 1.0:
            raise FilterError("Score threshold must be between 0.0 and 1.0")
        self._score_threshold = threshold
        self._exclude_scores_below = threshold

    def get_score_threshold(self) -> float:
        """Get the current score threshold.

        Returns:
            Current threshold.
        """
        return self._score_threshold

    def get_rules(self) -> tuple[FilterRule, ...]:
        """Get current filter rules.

        Returns:
            Tuple of current rules.
        """
        return tuple(self._rules)

    def _sort_rules(self) -> None:
        """Sort rules by priority."""
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def _matches_rule(self, domain: str, pattern: str) -> bool:
        """Check if domain matches a pattern.

        Args:
            domain: Domain string.
            pattern: Pattern to match.

        Returns:
            True if domain matches pattern.
        """
        # Support glob patterns
        if "*" in pattern or "?" in pattern:
            return self._matches_glob(domain, pattern.lower())

        # Support regex patterns (starting with ^ or ending with $)
        if pattern.startswith("^") or pattern.endswith("$") or "/" in pattern:
            try:
                return bool(re.search(pattern, domain, re.IGNORECASE))
            except re.error:
                # Fall back to literal match
                return pattern.lower() in domain

        # Literal match
        return pattern.lower() in domain

    def _matches_glob(self, text: str, pattern: str) -> bool:
        """Match text against a glob pattern.

        Args:
            text: Text to match.
            pattern: Glob pattern.

        Returns:
            True if text matches pattern.
        """
        # Convert glob to regex
        regex_pattern = re.escape(pattern)
        regex_pattern = regex_pattern.replace(r"\*", ".*")
        regex_pattern = regex_pattern.replace(r"\?", ".")
        regex_pattern = f"^{regex_pattern}$"

        try:
            return bool(re.match(regex_pattern, text, re.IGNORECASE))
        except re.error:
            return False


class ExclusionFilter(DomainFilter):
    """Filter that only applies exclusion rules.

    Use this when you want to exclude specific domains
    but include everything else.
    """

    def should_include(self, candidate: DiscoveryCandidate) -> bool:
        """Check if candidate should be included.

        Only exclusion rules are applied.

        Args:
            candidate: Candidate to check.

        Returns:
            True if candidate should be included.
        """
        # Check score threshold first
        if candidate.score is not None and candidate.score < self._exclude_scores_below:
            return False

        domain_str = candidate.domain.name.lower()

        # Only apply exclusion rules
        for rule in self._rules:
            if not rule.is_exclusion:
                continue
            if self._matches_rule(domain_str, rule.pattern):
                return False

        return True


class InclusionFilter(DomainFilter):
    """Filter that only applies inclusion rules.

    Use this when you want to include only specific domains
    and exclude everything else.
    """

    def should_include(self, candidate: DiscoveryCandidate) -> bool:
        """Check if candidate should be included.

        Only inclusion rules are applied.

        Args:
            candidate: Candidate to check.

        Returns:
            True if candidate should be included.
        """
        # Check score threshold first
        if candidate.score is not None and candidate.score < self._exclude_scores_below:
            return False

        domain_str = candidate.domain.name.lower()

        # Only apply inclusion rules if any exist
        inclusion_rules = [r for r in self._rules if not r.is_exclusion]
        if inclusion_rules:
            for rule in inclusion_rules:
                if self._matches_rule(domain_str, rule.pattern):
                    return True
            return False

        # No inclusion rules - include by default
        return True
