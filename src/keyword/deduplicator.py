"""Deduplicator implementation for keyword deduplication."""

import re
from typing import Sequence

from .exceptions import DeduplicationError
from .interfaces import DeduplicationStrategy
from .models import (
    DeduplicationMode,
    DeduplicationResult,
    Keyword,
)


class KeywordDeduplicator(DeduplicationStrategy):
    """Implementation of keyword deduplication.

    Supports multiple deduplication modes including exact match,
    case-insensitive, and pattern-based deduplication.
    """

    def __init__(
        self,
        mode: DeduplicationMode = DeduplicationMode.EXACT,
    ) -> None:
        """Initialize the deduplicator.

        Args:
            mode: The deduplication mode to use.
        """
        self._mode = mode
        self._seen_exact: set[str] = set()
        self._seen_case_insensitive: dict[str, Keyword] = {}

    def is_duplicate(
        self,
        keyword: Keyword,
        existing: Sequence[Keyword],
    ) -> bool:
        """Check if a keyword is a duplicate of any in existing set.

        Args:
            keyword: The keyword to check.
            existing: Existing keywords to compare against.

        Returns:
            True if the keyword is a duplicate.
        """
        if self._mode == DeduplicationMode.EXACT:
            return self._is_duplicate_exact(keyword, existing)
        elif self._mode == DeduplicationMode.CASE_INSENSITIVE:
            return self._is_duplicate_case_insensitive(keyword, existing)
        elif self._mode == DeduplicationMode.PATTERN_BASED:
            return self._is_duplicate_pattern_based(keyword, existing)
        elif self._mode == DeduplicationMode.SEMANTIC:
            # For semantic, fall back to case-insensitive
            return self._is_duplicate_case_insensitive(keyword, existing)
        return False

    def _is_duplicate_exact(
        self,
        keyword: Keyword,
        existing: Sequence[Keyword],
    ) -> bool:
        """Check for exact duplicate.

        Args:
            keyword: The keyword to check.
            existing: Existing keywords.

        Returns:
            True if exact duplicate.
        """
        for existing_keyword in existing:
            if keyword.text == existing_keyword.text:
                return True
        return False

    def _is_duplicate_case_insensitive(
        self,
        keyword: Keyword,
        existing: Sequence[Keyword],
    ) -> bool:
        """Check for case-insensitive duplicate.

        Args:
            keyword: The keyword to check.
            existing: Existing keywords.

        Returns:
            True if case-insensitive duplicate.
        """
        lower_text = keyword.text.lower()
        for existing_keyword in existing:
            if lower_text == existing_keyword.text.lower():
                return True
        return False

    def _is_duplicate_pattern_based(
        self,
        keyword: Keyword,
        existing: Sequence[Keyword],
    ) -> bool:
        """Check for pattern-based duplicate.

        Args:
            keyword: The keyword to check.
            existing: Existing keywords.

        Returns:
            True if pattern duplicate.
        """
        keyword_lower = keyword.text.lower()

        for existing_keyword in existing:
            existing_lower = existing_keyword.text.lower()

            # Check if one is a substring of the other
            if keyword_lower in existing_lower or existing_lower in keyword_lower:
                return True

            # Check for common prefix/suffix patterns
            if self._has_common_pattern(keyword_lower, existing_lower):
                return True

        return False

    def _has_common_pattern(self, text1: str, text2: str) -> bool:
        """Check if two texts share a significant common pattern.

        Args:
            text1: First text.
            text2: Second text.

        Returns:
            True if significant common pattern exists.
        """
        if not text1 or not text2:
            return False

        # Check for common prefix
        common_prefix_len = 0
        for c1, c2 in zip(text1, text2):
            if c1 == c2:
                common_prefix_len += 1
            else:
                break

        # If more than 50% of shorter string is common, consider it a pattern
        min_len = min(len(text1), len(text2))
        if min_len > 0 and common_prefix_len >= min_len * 0.5:
            return True

        return False

    def get_mode(self) -> DeduplicationMode:
        """Get the deduplication mode used by this strategy.

        Returns:
            The DeduplicationMode enum value.
        """
        return self._mode

    def deduplicate_batch(
        self,
        keywords: Sequence[Keyword],
    ) -> tuple[Sequence[Keyword], DeduplicationResult]:
        """Deduplicate a batch of keywords.

        Args:
            keywords: Keywords to deduplicate.

        Returns:
            Tuple of (unique_keywords, deduplication_result).
        """
        original_count = len(keywords)
        unique_keywords: list[Keyword] = []
        duplicates: list[str] = []

        for keyword in keywords:
            if self.is_duplicate(keyword, unique_keywords):
                duplicates.append(keyword.text)
            else:
                unique_keywords.append(keyword)

        remaining_count = len(unique_keywords)
        duplicate_count = original_count - remaining_count

        return (
            unique_keywords,
            DeduplicationResult(
                original_count=original_count,
                duplicate_count=duplicate_count,
                remaining_count=remaining_count,
                duplicates=tuple(duplicates),
                strategy_used=self._mode.name,
            ),
        )


class ExactMatchDeduplicator(KeywordDeduplicator):
    """Deduplicator using exact string matching."""

    def __init__(self) -> None:
        """Initialize exact match deduplicator."""
        super().__init__(mode=DeduplicationMode.EXACT)


class CaseInsensitiveDeduplicator(KeywordDeduplicator):
    """Deduplicator using case-insensitive matching."""

    def __init__(self) -> None:
        """Initialize case-insensitive deduplicator."""
        super().__init__(mode=DeduplicationMode.CASE_INSENSITIVE)


class PatternDeduplicator(KeywordDeduplicator):
    """Deduplicator using pattern-based matching."""

    def __init__(self) -> None:
        """Initialize pattern-based deduplicator."""
        super().__init__(mode=DeduplicationMode.PATTERN_BASED)


class ChainedDeduplicator(DeduplicationStrategy):
    """Deduplicator that chains multiple deduplication strategies."""

    def __init__(self, strategies: Sequence[DeduplicationStrategy]) -> None:
        """Initialize with multiple strategies.

        Args:
            strategies: Strategies to chain.
        """
        self._strategies = list(strategies)

    def is_duplicate(
        self,
        keyword: Keyword,
        existing: Sequence[Keyword],
    ) -> bool:
        """Check using all strategies in chain.

        Args:
            keyword: The keyword to check.
            existing: Existing keywords.

        Returns:
            True if any strategy marks as duplicate.
        """
        for strategy in self._strategies:
            if strategy.is_duplicate(keyword, existing):
                return True
        return False

    def get_mode(self) -> DeduplicationMode:
        """Get the primary deduplication mode.

        Returns:
            Mode of first strategy.
        """
        if self._strategies:
            return self._strategies[0].get_mode()
        return DeduplicationMode.EXACT
