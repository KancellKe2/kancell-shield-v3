"""Unit tests for result normalizers."""

import pytest

from src.search.normalizer import (
    DeduplicatingNormalizer,
    ResultNormalizerImpl,
    StrictResultNormalizer,
)
from src.search.models import SearchResult


class TestResultNormalizerImpl:
    """Tests for ResultNormalizerImpl."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.normalizer = ResultNormalizerImpl()

    def test_normalize_results(self) -> None:
        """Test normalizing results."""
        results = [
            SearchResult(
                url="https://Example.COM/",
                title="  Test Title  ",
                snippet="Test snippet",
                provider="test",
            )
        ]

        normalized = self.normalizer.normalize(results, "test")

        assert len(normalized) == 1
        assert normalized[0].url == "https://example.com"
        assert normalized[0].title == "Test Title"

    def test_clean_url(self) -> None:
        """Test URL cleaning."""
        results = [
            SearchResult(
                url="HTTP://example.COM/path/",
                title="Test",
                snippet="Snippet",
                provider="test",
            )
        ]

        normalized = self.normalizer.normalize(results, "test")
        assert normalized[0].url == "https://example.com/path"

    def test_clean_title(self) -> None:
        """Test title cleaning."""
        results = [
            SearchResult(
                url="https://example.com",
                title="  Multiple   Spaces   Here  ",
                snippet="Test",
                provider="test",
            )
        ]

        normalized = self.normalizer.normalize(results, "test")
        assert "Multiple   Spaces   Here" not in normalized[0].title
        assert normalized[0].title == "Multiple Spaces Here"

    def test_calculate_confidence(self) -> None:
        """Test confidence calculation."""
        result = SearchResult(
            url="https://example.com",
            title="Malware test results",
            snippet="Information about malware",
            provider="test",
        )

        confidence = self.normalizer.calculate_confidence(
            result,
            ["malware", "test"]
        )

        assert 0.0 <= confidence <= 1.0
        # With keyword match, should be higher than base
        assert confidence > 0.5

    def test_confidence_with_provider_weight(self) -> None:
        """Test confidence with provider weights."""
        normalizer = ResultNormalizerImpl(
            provider_weights={"trusted": 0.3, "untrusted": 0.1}
        )

        trusted_result = SearchResult(
            url="https://example.com",
            title="Test",
            snippet="Test",
            provider="trusted",
        )

        untrusted_result = SearchResult(
            url="https://other.com",
            title="Test",
            snippet="Test",
            provider="untrusted",
        )

        trusted_conf = normalizer.calculate_confidence(trusted_result, [])
        untrusted_conf = normalizer.calculate_confidence(untrusted_result, [])

        assert trusted_conf > untrusted_conf

    def test_keyword_match_score(self) -> None:
        """Test keyword matching in confidence."""
        result = SearchResult(
            url="https://example.com",
            title="This is about malware and phishing",
            snippet="Malware is bad",
            provider="test",
        )

        # All keywords match
        all_match = self.normalizer.calculate_confidence(
            result, ["malware", "phishing"]
        )

        # No keywords match
        none_match = self.normalizer.calculate_confidence(
            result, ["xyz123", "abc456"]
        )

        assert all_match > none_match

    def test_position_score(self) -> None:
        """Test position-based scoring."""
        r1 = SearchResult(
            url="https://a.com",
            title="Test",
            snippet="Test",
            provider="test",
            position=0,
        )
        r2 = SearchResult(
            url="https://b.com",
            title="Test",
            snippet="Test",
            provider="test",
            position=10,
        )

        c1 = self.normalizer.calculate_confidence(r1, [])
        c2 = self.normalizer.calculate_confidence(r2, [])

        assert c1 > c2


class TestStrictResultNormalizer:
    """Tests for StrictResultNormalizer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.normalizer = StrictResultNormalizer()

    def test_removes_html_tags(self) -> None:
        """Test HTML tag removal."""
        results = [
            SearchResult(
                url="https://example.com",
                title="<b>Bold</b> Title",
                snippet="<p>Paragraph</p>",
                provider="test",
            )
        ]

        normalized = self.normalizer.normalize(results, "test")
        assert "<b>" not in normalized[0].title
        assert "<p>" not in normalized[0].snippet

    def test_decodes_html_entities(self) -> None:
        """Test HTML entity decoding."""
        results = [
            SearchResult(
                url="https://example.com",
                title="AT&amp;T &lt;Company&gt;",
                snippet="Test &quot;quoted&quot;",
                provider="test",
            )
        ]

        normalized = self.normalizer.normalize(results, "test")
        assert "&amp;" not in normalized[0].title
        assert "&lt;" not in normalized[0].title

    def test_removes_tracking_params(self) -> None:
        """Test tracking parameter removal."""
        results = [
            SearchResult(
                url="https://example.com/page?utm_source=test&fbclid=123",
                title="Test",
                snippet="Test",
                provider="test",
            )
        ]

        normalized = self.normalizer.normalize(results, "test")
        assert "utm_source" not in normalized[0].url
        assert "fbclid" not in normalized[0].url


class TestDeduplicatingNormalizer:
    """Tests for DeduplicatingNormalizer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.normalizer = DeduplicatingNormalizer()

    def test_deduplicates_by_url(self) -> None:
        """Test deduplication by URL."""
        results = [
            SearchResult(url="https://example.com", title="A", snippet="A", provider="p1"),
            SearchResult(url="https://example.com", title="B", snippet="B", provider="p2"),
            SearchResult(url="https://other.com", title="C", snippet="C", provider="p1"),
        ]

        normalized = self.normalizer.normalize(results, "test")
        assert len(normalized) == 2

    def test_normalizes_urls_for_comparison(self) -> None:
        """Test URL normalization for comparison."""
        results = [
            SearchResult(url="https://EXAMPLE.COM/", title="A", snippet="A", provider="p1"),
            SearchResult(url="http://example.com", title="B", snippet="B", provider="p2"),
            SearchResult(url="https://www.example.com/", title="C", snippet="C", provider="p1"),
        ]

        normalized = self.normalizer.normalize(results, "test")
        assert len(normalized) == 1

    def test_reset_clears_seen_urls(self) -> None:
        """Test reset clears deduplication state."""
        results = [
            SearchResult(url="https://example.com", title="A", snippet="A", provider="p1"),
        ]

        self.normalizer.normalize(results, "test")
        assert len(self.normalizer._seen_urls) == 1

        self.normalizer.reset()
        assert len(self.normalizer._seen_urls) == 0
