"""Result normalizer implementation for normalizing search results."""

import re
import unicodedata
from typing import Sequence

from .interfaces import ResultNormalizer
from .models import SearchResult


class ResultNormalizerImpl(ResultNormalizer):
    """Implementation of result normalizer.

    Normalizes search results by cleaning titles, snippets, and URLs,
    and calculates confidence scores based on various factors.
    """

    BASE_SCORE = 0.5
    PROVIDER_WEIGHT_RANGE = (0.1, 0.3)
    KEYWORD_MATCH_RANGE = (0.0, 0.2)
    POSITION_RANGE = (0.0, 0.1)

    def __init__(
        self,
        provider_weights: dict[str, float] | None = None,
        min_confidence: float = 0.0,
    ) -> None:
        """Initialize the result normalizer.

        Args:
            provider_weights: Weight per provider (0.0-1.0).
            min_confidence: Minimum confidence threshold.
        """
        self._provider_weights = provider_weights or {}
        self._min_confidence = min_confidence

    def normalize(
        self,
        results: Sequence[SearchResult],
        provider: str,
    ) -> Sequence[SearchResult]:
        """Normalize search results.

        Args:
            results: Raw results from provider.
            provider: Source provider name.

        Returns:
            Normalized results with cleaned fields.
        """
        normalized: list[SearchResult] = []

        for result in results:
            cleaned_url = self._clean_url(result.url)
            cleaned_title = self._clean_title(result.title)
            cleaned_snippet = self._clean_snippet(result.snippet)

            # Create normalized result
            normalized_result = SearchResult(
                url=cleaned_url,
                title=cleaned_title,
                snippet=cleaned_snippet,
                provider=provider,
                confidence=result.confidence,
                keywords=result.keywords,
                discovered_at=result.discovered_at,
                position=result.position,
                metadata=result.metadata,
            )
            normalized.append(normalized_result)

        return normalized

    def calculate_confidence(
        self,
        result: SearchResult,
        keywords: Sequence[str],
    ) -> float:
        """Calculate confidence score for result.

        Args:
            result: Search result to score.
            keywords: Keywords that matched.

        Returns:
            Confidence score between 0 and 1.
        """
        score = self.BASE_SCORE

        # Provider weight modifier
        provider_weight = self._provider_weights.get(
            result.provider,
            0.1,  # Default weight
        )
        score += provider_weight

        # Keyword match modifier
        keyword_score = self._calculate_keyword_score(result, keywords)
        score += keyword_score

        # Position modifier
        position_score = self._calculate_position_score(result.position)
        score += position_score

        # Clamp to valid range
        return max(self._min_confidence, min(1.0, score))

    def _clean_url(self, url: str) -> str:
        """Clean and normalize URL.

        Args:
            url: Raw URL.

        Returns:
            Cleaned URL.
        """
        # Strip tracking parameters
        url = url.strip()

        # Normalize protocol
        url = url.lower()
        if url.startswith("http://"):
            url = "https://" + url[7:]
        elif not url.startswith("https://"):
            url = "https://" + url

        # Remove trailing slashes (except for root)
        if url.count("/") > 2:
            url = url.rstrip("/")

        return url

    def _clean_title(self, title: str) -> str:
        """Clean and normalize title.

        Args:
            title: Raw title.

        Returns:
            Cleaned title.
        """
        # Strip whitespace
        title = title.strip()

        # Normalize whitespace
        title = re.sub(r"\s+", " ", title)

        # Remove special characters that might cause issues
        title = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", title)

        # Normalize unicode
        title = unicodedata.normalize("NFKC", title)

        return title

    def _clean_snippet(self, snippet: str) -> str:
        """Clean and normalize snippet.

        Args:
            snippet: Raw snippet.

        Returns:
            Cleaned snippet.
        """
        # Strip whitespace
        snippet = snippet.strip()

        # Normalize whitespace
        snippet = re.sub(r"\s+", " ", snippet)

        # Remove control characters
        snippet = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", snippet)

        # Normalize unicode
        snippet = unicodedata.normalize("NFKC", snippet)

        # Truncate if too long
        max_length = 500
        if len(snippet) > max_length:
            snippet = snippet[:max_length].rsplit(" ", 1)[0] + "..."

        return snippet

    def _calculate_keyword_score(
        self,
        result: SearchResult,
        keywords: Sequence[str],
    ) -> float:
        """Calculate keyword match score.

        Args:
            result: Search result.
            keywords: Keywords to match.

        Returns:
            Score between KEYWORD_MATCH_RANGE.
        """
        if not keywords:
            return 0.0

        result_text = f"{result.title} {result.snippet}".lower()
        matches = 0

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in result_text:
                matches += 1

        match_ratio = matches / len(keywords)
        min_score, max_score = self.KEYWORD_MATCH_RANGE
        return min_score + (match_ratio * (max_score - min_score))

    def _calculate_position_score(self, position: int) -> float:
        """Calculate position-based score.

        Args:
            position: Result position (0-indexed).

        Returns:
            Score between POSITION_RANGE.
        """
        min_score, max_score = self.POSITION_RANGE

        if position <= 0:
            return max_score

        # Higher positions get higher scores
        # Position 1 gets max_score, decreasing for later positions
        score = max_score / (1 + (position * 0.1))
        return max(min_score, score)


class StrictResultNormalizer(ResultNormalizerImpl):
    """Strict result normalizer with aggressive cleaning.

    Applies additional normalization including HTML tag removal
    and more aggressive URL cleaning.
    """

    def _clean_title(self, title: str) -> str:
        """Clean title with HTML removal.

        Args:
            title: Raw title.

        Returns:
            Cleaned title.
        """
        # First apply base cleaning
        title = super()._clean_title(title)

        # Remove HTML tags
        title = re.sub(r"<[^>]+>", "", title)

        # Decode HTML entities
        title = title.replace("&amp;", "&")
        title = title.replace("&lt;", "<")
        title = title.replace("&gt;", ">")
        title = title.replace("&quot;", '"')
        title = title.replace("&#39;", "'")
        title = title.replace("&nbsp;", " ")

        return title

    def _clean_snippet(self, snippet: str) -> str:
        """Clean snippet with HTML removal.

        Args:
            snippet: Raw snippet.

        Returns:
            Cleaned snippet.
        """
        # First apply base cleaning
        snippet = super()._clean_snippet(snippet)

        # Remove HTML tags
        snippet = re.sub(r"<[^>]+>", "", snippet)

        # Decode HTML entities
        snippet = snippet.replace("&amp;", "&")
        snippet = snippet.replace("&lt;", "<")
        snippet = snippet.replace("&gt;", ">")
        snippet = snippet.replace("&quot;", '"')
        snippet = snippet.replace("&#39;", "'")
        snippet = snippet.replace("&nbsp;", " ")

        return snippet

    def _clean_url(self, url: str) -> str:
        """Clean URL with tracking parameter removal.

        Args:
            url: Raw URL.

        Returns:
            Cleaned URL.
        """
        # First apply base cleaning
        url = super()._clean_url(url)

        # Remove common tracking parameters
        tracking_params = [
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "ref",
            "source",
            "fbclid",
            "gclid",
        ]

        # Parse URL and remove tracking params
        if "?" in url:
            base, params = url.split("?", 1)
            param_list = params.split("&")
            clean_params = [
                p for p in param_list
                if not any(t in p.lower() for t in tracking_params)
            ]
            if clean_params:
                url = base + "?" + "&".join(clean_params)
            else:
                url = base

        return url


class DeduplicatingNormalizer(ResultNormalizerImpl):
    """Result normalizer with built-in deduplication."""

    def __init__(
        self,
        provider_weights: dict[str, float] | None = None,
        min_confidence: float = 0.0,
    ) -> None:
        """Initialize the deduplicating normalizer.

        Args:
            provider_weights: Weight per provider.
            min_confidence: Minimum confidence threshold.
        """
        super().__init__(provider_weights, min_confidence)
        self._seen_urls: set[str] = set()

    def normalize(
        self,
        results: Sequence[SearchResult],
        provider: str,
    ) -> Sequence[SearchResult]:
        """Normalize and deduplicate search results.

        Args:
            results: Raw results from provider.
            provider: Source provider name.

        Returns:
            Normalized and deduplicated results.
        """
        normalized = super().normalize(results, provider)
        unique: list[SearchResult] = []
        duplicate_count = 0

        for result in normalized:
            clean_url = self._normalize_url_for_comparison(result.url)

            if clean_url not in self._seen_urls:
                self._seen_urls.add(clean_url)
                unique.append(result)
            else:
                duplicate_count += 1

        return unique

    def _normalize_url_for_comparison(self, url: str) -> str:
        """Normalize URL for duplicate comparison.

        Args:
            url: URL to normalize.

        Returns:
            Normalized URL for comparison.
        """
        url = url.lower()
        url = url.strip()

        # Remove protocol
        url = re.sub(r"^https?://", "", url)

        # Remove trailing slash
        url = url.rstrip("/")

        # Remove www prefix
        url = re.sub(r"^www\.", "", url)

        # Remove common tracking parameters
        tracking_patterns = [
            r"\?utm_[^&]+",
            r"&utm_[^&]+",
            r"\?ref=[^&]+",
            r"&ref=[^&]+",
        ]
        for pattern in tracking_patterns:
            url = re.sub(pattern, "", url)

        # Remove trailing characters
        url = url.rstrip("?&")

        return url

    def reset(self) -> None:
        """Reset seen URLs for fresh deduplication."""
        self._seen_urls.clear()
