"""Normalizer implementation for keyword normalization."""

import re
import unicodedata
from typing import Sequence

from .exceptions import NormalizationError
from .interfaces import NormalizationStrategy
from .models import (
    Keyword,
    KeywordCategory,
    LanguageCode,
    NormalizationMode,
    NormalizationResult,
    NormalizationRule,
)


class KeywordNormalizer(NormalizationStrategy):
    """Implementation of keyword normalization.

    Applies normalization rules to keywords including case normalization,
    whitespace trimming, special character handling, and Unicode normalization.
    """

    DEFAULT_SPECIAL_CHARS_PATTERN = re.compile(r"[^\w\s\-]")
    DEFAULT_WHITESPACE_PATTERN = re.compile(r"\s+")

    def __init__(
        self,
        mode: NormalizationMode = NormalizationMode.LOWERCASE,
        rules: Sequence[NormalizationRule] | None = None,
    ) -> None:
        """Initialize the normalizer.

        Args:
            mode: The normalization mode to use.
            rules: Optional sequence of normalization rules.
        """
        self._mode = mode
        self._rules = list(rules) if rules else []

    def normalize(self, keyword: Keyword) -> Keyword:
        """Apply normalization to a keyword.

        Args:
            keyword: The keyword to normalize.

        Returns:
            Normalized keyword with updated text.

        Raises:
            NormalizationError: If normalization fails.
        """
        try:
            original_text = keyword.text
            normalized_text = original_text
            rules_applied: list[str] = []

            # Apply built-in mode-based normalization
            if self._mode == NormalizationMode.LOWERCASE:
                new_text = normalized_text.lower()
                if new_text != normalized_text:
                    normalized_text = new_text
                    rules_applied.append("lowercase")

            elif self._mode == NormalizationMode.TRIM:
                new_text = normalized_text.strip()
                if new_text != normalized_text:
                    normalized_text = new_text
                    rules_applied.append("trim")

            elif self._mode == NormalizationMode.UNICODE:
                new_text = unicodedata.normalize("NFKC", normalized_text)
                if new_text != normalized_text:
                    normalized_text = new_text
                    rules_applied.append("unicode_nfkc")

            elif self._mode == NormalizationMode.SPECIAL_CHARS:
                new_text = self.DEFAULT_SPECIAL_CHARS_PATTERN.sub("", normalized_text)
                if new_text != normalized_text:
                    normalized_text = new_text
                    rules_applied.append("remove_special_chars")

            # Apply custom rules
            for rule in self._rules:
                if not rule.enabled:
                    continue
                try:
                    pattern = re.compile(rule.pattern)
                    new_text = pattern.sub(rule.replacement, normalized_text)
                    if new_text != normalized_text:
                        normalized_text = new_text
                        rules_applied.append(rule.name)
                except re.error as e:
                    raise NormalizationError(
                        f"Invalid regex pattern in rule '{rule.name}': {e}"
                    ) from e

            # Return updated keyword if text changed
            if normalized_text != original_text:
                return Keyword(
                    text=normalized_text,
                    category=keyword.category,
                    language=keyword.language,
                    weight=keyword.weight,
                    tags=keyword.tags,
                )

            return keyword

        except Exception as e:
            raise NormalizationError(f"Failed to normalize keyword: {e}") from e

    def apply_rules(
        self,
        keyword: Keyword,
        rules: Sequence[NormalizationRule],
    ) -> Keyword:
        """Apply normalization rules in sequence.

        Args:
            keyword: The keyword to normalize.
            rules: The normalization rules to apply.

        Returns:
            Normalized keyword.

        Raises:
            NormalizationError: If rule application fails.
        """
        result = keyword
        for rule in sorted(rules, key=lambda r: r.priority):
            if not rule.enabled:
                continue
            result = self._apply_single_rule(result, rule)
        return result

    def _apply_single_rule(
        self,
        keyword: Keyword,
        rule: NormalizationRule,
    ) -> Keyword:
        """Apply a single normalization rule.

        Args:
            keyword: The keyword to normalize.
            rule: The rule to apply.

        Returns:
            Normalized keyword.

        Raises:
            NormalizationError: If rule application fails.
        """
        try:
            pattern = re.compile(rule.pattern)
            new_text = pattern.sub(rule.replacement, keyword.text)

            if new_text != keyword.text:
                return Keyword(
                    text=new_text,
                    category=keyword.category,
                    language=keyword.language,
                    weight=keyword.weight,
                    tags=keyword.tags,
                )

            return keyword

        except re.error as e:
            raise NormalizationError(
                f"Invalid regex pattern in rule '{rule.name}': {e}"
            ) from e

    def get_mode(self) -> NormalizationMode:
        """Get the normalization mode used by this strategy.

        Returns:
            The NormalizationMode enum value.
        """
        return self._mode

    def normalize_batch(
        self,
        keywords: Sequence[Keyword],
    ) -> list[NormalizationResult]:
        """Normalize a batch of keywords.

        Args:
            keywords: Keywords to normalize.

        Returns:
            List of normalization results.
        """
        results: list[NormalizationResult] = []

        for keyword in keywords:
            original = keyword.text
            normalized_keyword = self.normalize(keyword)
            results.append(
                NormalizationResult(
                    original_keyword=original,
                    normalized_keyword=normalized_keyword.text,
                    rules_applied=tuple(),
                    changed=original != normalized_keyword.text,
                )
            )

        return results


class LengthEnforcingNormalizer(KeywordNormalizer):
    """A normalizer that also enforces keyword length constraints."""

    def __init__(
        self,
        min_length: int = 2,
        max_length: int = 64,
        **kwargs: object,
    ) -> None:
        """Initialize the length-enforcing normalizer.

        Args:
            min_length: Minimum keyword length.
            max_length: Maximum keyword length.
            **kwargs: Additional arguments for parent class.
        """
        super().__init__(**kwargs)
        self._min_length = min_length
        self._max_length = max_length

    def normalize(self, keyword: Keyword) -> Keyword:
        """Apply normalization and enforce length constraints.

        Args:
            keyword: The keyword to normalize.

        Returns:
            Normalized keyword within length constraints.
        """
        normalized = super().normalize(keyword)

        text = normalized.text
        if len(text) < self._min_length:
            # Pad with spaces (will be trimmed later)
            text = text.ljust(self._min_length)
        elif len(text) > self._max_length:
            text = text[: self._max_length]

        if text != normalized.text:
            return Keyword(
                text=text.strip(),
                category=normalized.category,
                language=normalized.language,
                weight=normalized.weight,
                tags=normalized.tags,
            )

        return normalized

    def is_valid_length(self, text: str) -> bool:
        """Check if text is within valid length range.

        Args:
            text: Text to check.

        Returns:
            True if within range.
        """
        return self._min_length <= len(text) <= self._max_length


class StrictNormalizer(KeywordNormalizer):
    """A stricter normalizer that applies all normalization modes."""

    def normalize(self, keyword: Keyword) -> Keyword:
        """Apply all normalization modes in sequence.

        Args:
            keyword: The keyword to normalize.

        Returns:
            Fully normalized keyword.
        """
        result = keyword

        # Apply Unicode normalization first
        result = self._normalize_unicode(result)

        # Apply lowercase
        result = self._normalize_case(result)

        # Apply whitespace normalization
        result = self._normalize_whitespace(result)

        # Apply special character removal
        result = self._normalize_special_chars(result)

        # Apply custom rules
        result = self.apply_rules(result, self._rules)

        return result

    def _normalize_unicode(self, keyword: Keyword) -> Keyword:
        """Normalize Unicode representation."""
        normalized = unicodedata.normalize("NFKC", keyword.text)
        if normalized != keyword.text:
            return Keyword(
                text=normalized,
                category=keyword.category,
                language=keyword.language,
                weight=keyword.weight,
                tags=keyword.tags,
            )
        return keyword

    def _normalize_case(self, keyword: Keyword) -> Keyword:
        """Normalize case to lowercase."""
        lowered = keyword.text.lower()
        if lowered != keyword.text:
            return Keyword(
                text=lowered,
                category=keyword.category,
                language=keyword.language,
                weight=keyword.weight,
                tags=keyword.tags,
            )
        return keyword

    def _normalize_whitespace(self, keyword: Keyword) -> Keyword:
        """Normalize whitespace."""
        normalized = self.DEFAULT_WHITESPACE_PATTERN.sub(" ", keyword.text).strip()
        if normalized != keyword.text:
            return Keyword(
                text=normalized,
                category=keyword.category,
                language=keyword.language,
                weight=keyword.weight,
                tags=keyword.tags,
            )
        return keyword

    def _normalize_special_chars(self, keyword: Keyword) -> Keyword:
        """Remove special characters."""
        normalized = self.DEFAULT_SPECIAL_CHARS_PATTERN.sub("", keyword.text)
        if normalized != keyword.text:
            return Keyword(
                text=normalized,
                category=keyword.category,
                language=keyword.language,
                weight=keyword.weight,
                tags=keyword.tags,
            )
        return keyword
