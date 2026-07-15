"""Unit tests for template engine."""

import pytest

from src.keyword.models import (
    Keyword,
    KeywordCategory,
    KeywordTemplate,
    LanguageCode,
)
from src.keyword.template_engine import (
    KeywordTemplateEngine,
    SimpleTemplateEngine,
)
from src.keyword.exceptions import TemplateError


class TestKeywordTemplateEngine:
    """Tests for KeywordTemplateEngine."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.engine = KeywordTemplateEngine()

    def test_apply_template_with_base_placeholder(self) -> None:
        """Test template with {base} placeholder."""
        template = KeywordTemplate(
            name="base_template",
            pattern="{base}_keyword",
        )
        keywords = [
            Keyword(text="virus", category=KeywordCategory.MALWARE),
            Keyword(text="phish", category=KeywordCategory.PHISHING),
        ]

        results = self.engine.apply_template(template, keywords)

        assert len(results) == 2
        assert "virus_keyword" in results
        assert "phish_keyword" in results

    def test_apply_template_with_category_placeholder(self) -> None:
        """Test template with {category} placeholder."""
        template = KeywordTemplate(
            name="category_template",
            pattern="{base}_{category}",
        )
        keywords = [
            Keyword(text="test", category=KeywordCategory.MALWARE),
        ]

        results = self.engine.apply_template(template, keywords)

        assert "test_malware" in results

    def test_apply_template_with_language_placeholder(self) -> None:
        """Test template with {language} placeholder."""
        template = KeywordTemplate(
            name="language_template",
            pattern="{language}_{base}",
        )
        keywords = [
            Keyword(
                text="virus",
                category=KeywordCategory.MALWARE,
                language=LanguageCode.EN,
            ),
        ]

        results = self.engine.apply_template(template, keywords)

        assert "en_virus" in results

    def test_apply_template_with_disabled_template(self) -> None:
        """Test disabled template returns empty."""
        template = KeywordTemplate(
            name="disabled_template",
            pattern="{base}_keyword",
            enabled=False,
        )
        keywords = [
            Keyword(text="virus", category=KeywordCategory.MALWARE),
        ]

        results = self.engine.apply_template(template, keywords)

        assert len(results) == 0

    def test_apply_template_with_category_filter(self) -> None:
        """Test template with category filter."""
        template = KeywordTemplate(
            name="filtered_template",
            pattern="{base}",
            categories=frozenset({KeywordCategory.MALWARE}),
        )
        keywords = [
            Keyword(text="virus", category=KeywordCategory.MALWARE),
            Keyword(text="login", category=KeywordCategory.PHISHING),
        ]

        results = self.engine.apply_template(template, keywords)

        assert len(results) == 1
        assert "virus" in results

    def test_apply_template_with_language_filter(self) -> None:
        """Test template with language filter."""
        template = KeywordTemplate(
            name="language_filtered",
            pattern="{base}",
            languages=frozenset({LanguageCode.EN}),
        )
        keywords = [
            Keyword(text="virus", category=KeywordCategory.MALWARE, language=LanguageCode.EN),
            Keyword(text="virus", category=KeywordCategory.MALWARE, language=LanguageCode.ES),
        ]

        results = self.engine.apply_template(template, keywords)

        assert len(results) == 1

    def test_validate_template_valid(self) -> None:
        """Test validation of valid template."""
        template = KeywordTemplate(
            name="valid_template",
            pattern="{base}_{category}",
        )

        result = self.engine.validate_template(template)

        assert result is True

    def test_validate_template_invalid_placeholder(self) -> None:
        """Test validation fails with invalid placeholder."""
        template = KeywordTemplate(
            name="invalid",
            pattern="{invalid}",
        )

        with pytest.raises(TemplateError, match="Invalid placeholder"):
            self.engine.validate_template(template)

    def test_generate_combinations(self) -> None:
        """Test generating combinations from multiple templates."""
        templates = [
            KeywordTemplate(name="t1", pattern="{base}_v1"),
            KeywordTemplate(name="t2", pattern="{base}_v2"),
        ]
        keywords = [
            Keyword(text="test", category=KeywordCategory.MALWARE),
        ]

        results = self.engine.generate_combinations(templates, keywords)

        assert "test_v1" in results
        assert "test_v2" in results

    def test_generate_combinations_with_max_limit(self) -> None:
        """Test max combinations limit."""
        templates = [
            KeywordTemplate(name="t1", pattern="{base}"),
        ]
        keywords = [
            Keyword(text=f"keyword{i}", category=KeywordCategory.MALWARE)
            for i in range(100)
        ]

        results = self.engine.generate_combinations(templates, keywords, max_combinations=10)

        assert len(results) == 10


class TestSimpleTemplateEngine:
    """Tests for SimpleTemplateEngine."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.engine = SimpleTemplateEngine()

    def test_apply_template_basic(self) -> None:
        """Test basic template application."""
        template = KeywordTemplate(
            name="simple",
            pattern="{base}_suffix",
        )
        keywords = [
            Keyword(text="test", category=KeywordCategory.MALWARE),
        ]

        results = self.engine.apply_template(template, keywords)

        assert "test_suffix" in results

    def test_validate_template_with_base(self) -> None:
        """Test validation with base placeholder."""
        template = KeywordTemplate(
            name="valid",
            pattern="{base}",
        )

        result = self.engine.validate_template(template)

        assert result is True
