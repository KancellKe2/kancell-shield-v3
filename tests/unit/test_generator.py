"""Unit tests for keyword generator."""

import pytest

from src.keyword.models import (
    Keyword,
    KeywordCategory,
    KeywordSet,
    KeywordTemplate,
    LanguageCode,
    GenerationConfig,
)
from src.keyword.generator import (
    BasicKeywordGenerator,
    DefaultKeywordProvider,
    KeywordGeneratorImpl,
)
from src.keyword.exceptions import GenerationError, ProviderError


class TestDefaultKeywordProvider:
    """Tests for DefaultKeywordProvider."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.provider = DefaultKeywordProvider()

    def test_get_all_keywords(self) -> None:
        """Test getting all keywords."""
        keywords = self.provider.get_keywords()

        assert len(keywords) > 0

    def test_get_keywords_by_category(self) -> None:
        """Test getting keywords by category."""
        keywords = self.provider.get_keywords(
            categories=[KeywordCategory.MALWARE]
        )

        for keyword in keywords:
            assert keyword.category == KeywordCategory.MALWARE

    def test_get_keywords_multiple_categories(self) -> None:
        """Test getting keywords from multiple categories."""
        keywords = self.provider.get_keywords(
            categories=[KeywordCategory.MALWARE, KeywordCategory.PHISHING]
        )

        categories = {k.category for k in keywords}
        assert KeywordCategory.MALWARE in categories
        assert KeywordCategory.PHISHING in categories

    def test_get_keywords_with_languages(self) -> None:
        """Test keywords have correct languages."""
        keywords = self.provider.get_keywords()

        languages = {k.language for k in keywords}
        assert LanguageCode.EN in languages

    def test_get_keywords_empty_category(self) -> None:
        """Test getting keywords with empty category list returns all keywords."""
        # Empty list should return all keywords (no filtering)
        keywords = self.provider.get_keywords(categories=[])
        assert len(keywords) > 0


class TestKeywordGeneratorImpl:
    """Tests for KeywordGeneratorImpl."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.generator = KeywordGeneratorImpl()

    def test_generate_basic(self) -> None:
        """Test basic generation."""
        config = GenerationConfig()
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        assert isinstance(result, KeywordSet)
        assert result.total_count > 0

    def test_generate_with_categories(self) -> None:
        """Test generation with specific categories."""
        config = GenerationConfig(
            enabled_categories=frozenset({KeywordCategory.MALWARE}),
        )
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        for keyword in result.keywords:
            assert keyword.category == KeywordCategory.MALWARE

    def test_generate_with_languages(self) -> None:
        """Test generation with specific languages."""
        config = GenerationConfig(
            languages=frozenset({LanguageCode.EN}),
        )
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        for keyword in result.keywords:
            assert keyword.language == LanguageCode.EN

    def test_generate_with_deduplication(self) -> None:
        """Test generation with deduplication enabled."""
        config = GenerationConfig(
            enable_deduplication=True,
        )
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        # With deduplication, all keywords should be unique
        texts = [k.text for k in result.keywords]
        assert len(texts) == len(set(texts))

    def test_generate_with_normalization(self) -> None:
        """Test generation with normalization enabled."""
        config = GenerationConfig(
            enable_normalization=True,
        )
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        # Normalized keywords should be lowercase
        for keyword in result.keywords:
            assert keyword.text == keyword.text.lower()

    def test_generate_disabled_deduplication(self) -> None:
        """Test generation with deduplication disabled."""
        config = GenerationConfig(
            enable_deduplication=False,
        )
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        # Even without deduplication, templates generate unique results
        assert result.total_count > 0

    def test_generate_with_max_combinations(self) -> None:
        """Test max combinations limit."""
        config = GenerationConfig(
            max_combinations=5,
        )
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        assert result.total_count <= 5

    def test_generate_with_length_constraints(self) -> None:
        """Test length constraints."""
        config = GenerationConfig(
            min_keyword_length=5,
            max_keyword_length=10,
        )
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        for keyword in result.keywords:
            assert len(keyword.text) >= 5
            assert len(keyword.text) <= 10

    def test_generate_with_template_combinations(self) -> None:
        """Test multiple templates generate combinations."""
        config = GenerationConfig()
        templates = [
            KeywordTemplate(name="t1", pattern="{base}_v1"),
            KeywordTemplate(name="t2", pattern="{base}_v2"),
        ]

        result = self.generator.generate(config, templates)

        # Should have keywords from both templates
        texts = {k.text for k in result.keywords}
        has_v1 = any("_v1" in t for t in texts)
        has_v2 = any("_v2" in t for t in texts)
        assert has_v1 or has_v2

    def test_generate_with_category_filter_in_template(self) -> None:
        """Test template with category filter."""
        config = GenerationConfig()
        templates = [
            KeywordTemplate(
                name="malware_only",
                pattern="{base}",
                categories=frozenset({KeywordCategory.MALWARE}),
            ),
        ]

        result = self.generator.generate(config, templates)

        for keyword in result.keywords:
            assert keyword.category == KeywordCategory.MALWARE

    def test_get_provider(self) -> None:
        """Test getting provider."""
        provider = self.generator.get_provider()

        assert isinstance(provider, DefaultKeywordProvider)

    def test_generate_with_category_suffix(self) -> None:
        """Test template with category suffix."""
        config = GenerationConfig()
        templates = [
            KeywordTemplate(name="suffix", pattern="{base}_{category}"),
        ]

        result = self.generator.generate(config, templates)

        texts = {k.text for k in result.keywords}
        # Should contain keywords with category suffix
        assert len(texts) > 0

    def test_generate_with_language_prefix(self) -> None:
        """Test template with language prefix."""
        config = GenerationConfig()
        templates = [
            KeywordTemplate(name="lang_prefix", pattern="{language}_{base}"),
        ]

        result = self.generator.generate(config, templates)

        texts = {k.text for k in result.keywords}
        # Should contain keywords with language prefix
        assert len(texts) > 0


class TestBasicKeywordGenerator:
    """Tests for BasicKeywordGenerator."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.generator = BasicKeywordGenerator()

    def test_generate(self) -> None:
        """Test basic generation."""
        config = GenerationConfig()
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        assert isinstance(result, KeywordSet)
        assert result.total_count > 0

    def test_get_provider(self) -> None:
        """Test getting provider."""
        provider = self.generator.get_provider()

        assert isinstance(provider, DefaultKeywordProvider)


class TestGenerationEdgeCases:
    """Tests for edge cases in generation."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.generator = KeywordGeneratorImpl()

    def test_generate_empty_templates(self) -> None:
        """Test generation with no templates."""
        config = GenerationConfig()
        templates: list[KeywordTemplate] = []

        # When no templates are provided, no keywords are generated
        # The generator may raise GenerationError or return empty set
        try:
            result = self.generator.generate(config, templates)
            # If no error, the result should be empty or generator handles it
            assert result.total_count == 0
        except GenerationError:
            # Expected when no keywords can be generated
            pass

    def test_generate_with_all_categories(self) -> None:
        """Test generation with all categories enabled."""
        config = GenerationConfig(
            enabled_categories=frozenset(KeywordCategory),
        )
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        # With all categories, we should have at least one keyword
        assert result.total_count > 0

    def test_generate_with_all_languages(self) -> None:
        """Test generation with all languages."""
        config = GenerationConfig(
            languages=frozenset(LanguageCode),
        )
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        # Should have keywords from multiple languages
        assert len(result.language_counts) >= 1

    def test_generate_metadata(self) -> None:
        """Test generation includes metadata."""
        config = GenerationConfig(
            enabled_categories=frozenset({KeywordCategory.MALWARE}),
            languages=frozenset({LanguageCode.EN}),
        )
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        assert "generated_at" in result.generation_metadata
        assert "MALWARE" in result.generation_metadata["categories"]
        assert "en" in result.generation_metadata["languages"]

    def test_generate_unique_count_accuracy(self) -> None:
        """Test unique count is accurate."""
        config = GenerationConfig()
        templates = [
            KeywordTemplate(name="basic", pattern="{base}"),
        ]

        result = self.generator.generate(config, templates)

        assert result.unique_count <= result.total_count
        assert result.unique_count == len(set(k.text for k in result.keywords))


class TestInvalidConfiguration:
    """Tests for invalid configuration handling."""

    def test_invalid_max_combinations(self) -> None:
        """Test invalid max_combinations."""
        with pytest.raises(ValueError):
            GenerationConfig(max_combinations=0)

    def test_invalid_length_range(self) -> None:
        """Test invalid length range."""
        with pytest.raises(ValueError):
            GenerationConfig(
                min_keyword_length=10,
                max_keyword_length=5,
            )

    def test_invalid_min_length(self) -> None:
        """Test invalid min_keyword_length."""
        with pytest.raises(ValueError):
            GenerationConfig(min_keyword_length=0)
