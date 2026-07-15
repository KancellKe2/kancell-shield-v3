"""Protocol interfaces for the Keyword Engine.

This module contains only Protocol and ABC interface definitions.
No implementation should be placed here.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Sequence

from .models import (
    DeduplicationMode,
    DeduplicationResult,
    Keyword,
    KeywordCategory,
    KeywordSet,
    KeywordTemplate,
    LanguageCode,
    NormalizationMode,
    NormalizationResult,
    NormalizationRule,
    GenerationConfig,
)


class KeywordProvider(Protocol):
    """Protocol for providing base keywords from a source.

    Implementations may read from databases, files, APIs, or other sources.
    """

    def get_keywords(
        self,
        categories: Sequence[KeywordCategory] | None = None,
    ) -> Sequence[Keyword]:
        """Retrieve keywords for specified categories.

        Args:
            categories: Optional list of categories to filter by.
                       If None, returns all available keywords.

        Returns:
            Sequence of Keyword objects.
        """
        ...


class CategoryHandler(Protocol):
    """Protocol for processing keywords by category.

    Different categories may require different handling logic.
    """

    def handles_category(self, category: KeywordCategory) -> bool:
        """Check if this handler processes the given category.

        Args:
            category: The category to check.

        Returns:
            True if this handler processes the category.
        """
        ...

    def process(
        self,
        keywords: Sequence[Keyword],
        category: KeywordCategory,
    ) -> Sequence[Keyword]:
        """Process keywords for a specific category.

        Args:
            keywords: The keywords to process.
            category: The category being processed.

        Returns:
            Processed keywords.
        """
        ...


class TemplateEngine(Protocol):
    """Protocol for applying templates to generate new keywords."""

    def apply_template(
        self,
        template: KeywordTemplate,
        base_keywords: Sequence[Keyword],
    ) -> Sequence[str]:
        """Apply a template to generate keyword strings.

        Args:
            template: The template to apply.
            base_keywords: The base keywords to use with the template.

        Returns:
            Generated keyword strings.
        """
        ...

    def validate_template(self, template: KeywordTemplate) -> bool:
        """Validate that a template is well-formed.

        Args:
            template: The template to validate.

        Returns:
            True if the template is valid.
        """
        ...


class LanguageProcessor(Protocol):
    """Protocol for handling language-specific transformations."""

    def supports_language(self, language: LanguageCode) -> bool:
        """Check if this processor supports the given language.

        Args:
            language: The language to check.

        Returns:
            True if the language is supported.
        """
        ...

    def transform(
        self,
        keyword: Keyword,
        target_language: LanguageCode,
    ) -> Sequence[Keyword]:
        """Transform a keyword for a target language.

        Args:
            keyword: The keyword to transform.
            target_language: The target language.

        Returns:
            Transformed keywords.
        """
        ...

    def translate(
        self,
        text: str,
        source_language: LanguageCode,
        target_language: LanguageCode,
    ) -> str:
        """Translate keyword text from source to target language.

        Args:
            text: The text to translate.
            source_language: The source language.
            target_language: The target language.

        Returns:
            Translated text.
        """
        ...


class DeduplicationStrategy(Protocol):
    """Protocol for identifying duplicate keywords."""

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
        ...

    def get_mode(self) -> DeduplicationMode:
        """Get the deduplication mode used by this strategy.

        Returns:
            The DeduplicationMode enum value.
        """
        ...


class NormalizationStrategy(Protocol):
    """Protocol for normalizing keywords."""

    def normalize(self, keyword: Keyword) -> Keyword:
        """Apply normalization to a keyword.

        Args:
            keyword: The keyword to normalize.

        Returns:
            Normalized keyword.
        """
        ...

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
        """
        ...

    def get_mode(self) -> NormalizationMode:
        """Get the normalization mode used by this strategy.

        Returns:
            The NormalizationMode enum value.
        """
        ...


class KeywordGenerator(ABC):
    """Abstract base class for keyword generation.

    This is the main interface for generating keywords.
    """

    @abstractmethod
    def generate(
        self,
        config: GenerationConfig,
        templates: Sequence[KeywordTemplate],
    ) -> KeywordSet:
        """Generate keywords based on configuration and templates.

        Args:
            config: Generation configuration.
            templates: Templates to apply.

        Returns:
            Generated KeywordSet.
        """
        ...

    @abstractmethod
    def get_provider(self) -> KeywordProvider:
        """Get the keyword provider used by this generator.

        Returns:
            The KeywordProvider instance.
        """
        ...


class CombinationStrategy(ABC):
    """Abstract base class for combination strategies."""

    @abstractmethod
    def combine(
        self,
        keywords: Sequence[Keyword],
        templates: Sequence[KeywordTemplate],
    ) -> Sequence[str]:
        """Combine keywords using templates.

        Args:
            keywords: Base keywords.
            templates: Templates to apply.

        Returns:
            Combined keyword strings.
        """
        ...

    @abstractmethod
    def permute(
        self,
        keywords: Sequence[Keyword],
        max_length: int = 3,
    ) -> Sequence[str]:
        """Generate permutations of keywords.

        Args:
            keywords: Keywords to permute.
            max_length: Maximum number of keywords per permutation.

        Returns:
            Permuted keyword strings.
        """
        ...


class KeywordValidator(Protocol):
    """Protocol for validating keywords."""

    def is_valid(self, keyword: Keyword) -> bool:
        """Check if a keyword is valid.

        Args:
            keyword: The keyword to validate.

        Returns:
            True if the keyword is valid.
        """
        ...

    def validate_batch(
        self,
        keywords: Sequence[Keyword],
    ) -> tuple[Sequence[Keyword], Sequence[Keyword]]:
        """Validate a batch of keywords.

        Args:
            keywords: Keywords to validate.

        Returns:
            Tuple of (valid_keywords, invalid_keywords).
        """
        ...


class KeywordExporter(Protocol):
    """Protocol for exporting keywords to various formats."""

    def export_json(self, keyword_set: KeywordSet) -> str:
        """Export keywords as JSON.

        Args:
            keyword_set: Keywords to export.

        Returns:
            JSON string representation.
        """
        ...

    def export_csv(self, keyword_set: KeywordSet) -> str:
        """Export keywords as CSV.

        Args:
            keyword_set: Keywords to export.

        Returns:
            CSV string representation.
        """
        ...

    def export_text(self, keyword_set: KeywordSet) -> str:
        """Export keywords as plain text.

        Args:
            keyword_set: Keywords to export.

        Returns:
            Plain text representation.
        """
        ...
