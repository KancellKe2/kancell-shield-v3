"""Unit tests for deduplicator."""

import pytest

from src.keyword.models import (
    Keyword,
    KeywordCategory,
    DeduplicationMode,
)
from src.keyword.deduplicator import (
    CaseInsensitiveDeduplicator,
    ChainedDeduplicator,
    ExactMatchDeduplicator,
    KeywordDeduplicator,
    PatternDeduplicator,
)


class TestKeywordDeduplicator:
    """Tests for KeywordDeduplicator with exact match mode."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.deduplicator = KeywordDeduplicator(mode=DeduplicationMode.EXACT)

    def test_is_duplicate_exact_match(self) -> None:
        """Test exact duplicate detection."""
        existing = [
            Keyword(text="virus", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="virus", category=KeywordCategory.MALWARE)

        result = self.deduplicator.is_duplicate(keyword, existing)

        assert result is True

    def test_is_not_duplicate_different_text(self) -> None:
        """Test different keywords are not duplicates."""
        existing = [
            Keyword(text="virus", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="phish", category=KeywordCategory.PHISHING)

        result = self.deduplicator.is_duplicate(keyword, existing)

        assert result is False

    def test_is_not_duplicate_empty_existing(self) -> None:
        """Test keyword with no existing is not duplicate."""
        keyword = Keyword(text="virus", category=KeywordCategory.MALWARE)

        result = self.deduplicator.is_duplicate(keyword, [])

        assert result is False

    def test_get_mode(self) -> None:
        """Test getting deduplication mode."""
        mode = self.deduplicator.get_mode()

        assert mode == DeduplicationMode.EXACT

    def test_deduplicate_batch(self) -> None:
        """Test batch deduplication."""
        keywords = [
            Keyword(text="virus", category=KeywordCategory.MALWARE),
            Keyword(text="virus", category=KeywordCategory.MALWARE),
            Keyword(text="phish", category=KeywordCategory.PHISHING),
        ]

        unique, result = self.deduplicator.deduplicate_batch(keywords)

        assert len(unique) == 2
        assert result.original_count == 3
        assert result.duplicate_count == 1
        assert result.remaining_count == 2


class TestCaseInsensitiveDeduplicator:
    """Tests for CaseInsensitiveDeduplicator."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.deduplicator = CaseInsensitiveDeduplicator()

    def test_is_duplicate_case_insensitive(self) -> None:
        """Test case-insensitive duplicate detection."""
        existing = [
            Keyword(text="VIRUS", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="virus", category=KeywordCategory.MALWARE)

        result = self.deduplicator.is_duplicate(keyword, existing)

        assert result is True

    def test_is_not_duplicate_different_case(self) -> None:
        """Test different case keywords are not duplicates in exact mode."""
        deduplicator = KeywordDeduplicator(mode=DeduplicationMode.EXACT)
        existing = [
            Keyword(text="VIRUS", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="virus", category=KeywordCategory.MALWARE)

        result = deduplicator.is_duplicate(keyword, existing)

        assert result is False

    def test_get_mode(self) -> None:
        """Test getting deduplication mode."""
        mode = self.deduplicator.get_mode()

        assert mode == DeduplicationMode.CASE_INSENSITIVE


class TestPatternDeduplicator:
    """Tests for PatternDeduplicator."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.deduplicator = PatternDeduplicator()

    def test_is_duplicate_substring(self) -> None:
        """Test substring detection."""
        existing = [
            Keyword(text="malware", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="mal", category=KeywordCategory.MALWARE)

        result = self.deduplicator.is_duplicate(keyword, existing)

        assert result is True

    def test_is_duplicate_superstring(self) -> None:
        """Test superstring detection."""
        existing = [
            Keyword(text="mal", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="malware", category=KeywordCategory.MALWARE)

        result = self.deduplicator.is_duplicate(keyword, existing)

        assert result is True

    def test_is_not_duplicate_unrelated(self) -> None:
        """Test unrelated keywords are not duplicates."""
        existing = [
            Keyword(text="apple", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="zebra", category=KeywordCategory.MALWARE)

        result = self.deduplicator.is_duplicate(keyword, existing)

        assert result is False


class TestExactMatchDeduplicator:
    """Tests for ExactMatchDeduplicator."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.deduplicator = ExactMatchDeduplicator()

    def test_is_duplicate_exact(self) -> None:
        """Test exact duplicate detection."""
        existing = [
            Keyword(text="virus", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="virus", category=KeywordCategory.MALWARE)

        result = self.deduplicator.is_duplicate(keyword, existing)

        assert result is True

    def test_is_not_duplicate_case_difference(self) -> None:
        """Test case difference is not duplicate."""
        existing = [
            Keyword(text="VIRUS", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="virus", category=KeywordCategory.MALWARE)

        result = self.deduplicator.is_duplicate(keyword, existing)

        assert result is False


class TestChainedDeduplicator:
    """Tests for ChainedDeduplicator."""

    def test_is_duplicate_first_strategy(self) -> None:
        """Test first strategy in chain."""
        chain = ChainedDeduplicator([
            CaseInsensitiveDeduplicator(),
        ])
        existing = [
            Keyword(text="VIRUS", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="virus", category=KeywordCategory.MALWARE)

        result = chain.is_duplicate(keyword, existing)

        assert result is True

    def test_is_duplicate_second_strategy(self) -> None:
        """Test second strategy catches duplicate."""
        chain = ChainedDeduplicator([
            ExactMatchDeduplicator(),  # Won't catch
            CaseInsensitiveDeduplicator(),  # Will catch
        ])
        existing = [
            Keyword(text="VIRUS", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="virus", category=KeywordCategory.MALWARE)

        result = chain.is_duplicate(keyword, existing)

        assert result is True

    def test_is_not_duplicate_no_match(self) -> None:
        """Test no strategy finds duplicate."""
        chain = ChainedDeduplicator([
            ExactMatchDeduplicator(),
        ])
        existing = [
            Keyword(text="VIRUS", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="phish", category=KeywordCategory.PHISHING)

        result = chain.is_duplicate(keyword, existing)

        assert result is False

    def test_get_mode_first_strategy(self) -> None:
        """Test getting mode from first strategy."""
        chain = ChainedDeduplicator([
            CaseInsensitiveDeduplicator(),
            ExactMatchDeduplicator(),
        ])

        mode = chain.get_mode()

        assert mode == DeduplicationMode.CASE_INSENSITIVE

    def test_empty_chain(self) -> None:
        """Test empty chain returns exact mode."""
        chain = ChainedDeduplicator([])

        mode = chain.get_mode()

        assert mode == DeduplicationMode.EXACT


class TestEdgeCases:
    """Tests for edge cases in deduplication."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.deduplicator = KeywordDeduplicator()

    def test_special_characters(self) -> None:
        """Test special characters handling."""
        existing = [
            Keyword(text="virus@", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="virus@", category=KeywordCategory.MALWARE)

        result = self.deduplicator.is_duplicate(keyword, existing)

        assert result is True

    def test_whitespace_difference(self) -> None:
        """Test whitespace handling."""
        existing = [
            Keyword(text="virus", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="virus ", category=KeywordCategory.MALWARE)

        result = self.deduplicator.is_duplicate(keyword, existing)

        assert result is False

    def test_unicode_characters(self) -> None:
        """Test Unicode character handling."""
        existing = [
            Keyword(text="вирус", category=KeywordCategory.MALWARE),
        ]
        keyword = Keyword(text="вирус", category=KeywordCategory.MALWARE)

        result = self.deduplicator.is_duplicate(keyword, existing)

        assert result is True

    def test_large_batch_deduplication(self) -> None:
        """Test deduplication with large batch."""
        keywords = [
            Keyword(text=f"keyword{i}", category=KeywordCategory.MALWARE)
            for i in range(100)
        ]
        # Add duplicates
        keywords.extend([
            Keyword(text=f"keyword{i}", category=KeywordCategory.MALWARE)
            for i in range(50)
        ])

        unique, result = self.deduplicator.deduplicate_batch(keywords)

        assert len(unique) == 100
        assert result.original_count == 150
        assert result.duplicate_count == 50
        assert result.remaining_count == 100
