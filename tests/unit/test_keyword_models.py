"""Unit tests for keyword models.

These tests verify model creation, default values, enum behavior,
and interface existence. No implementation tests are included.
"""

import pytest

from src.keyword.models import (
    DeduplicationMode,
    DeduplicationResult,
    GenerationConfig,
    Keyword,
    KeywordCategory,
    KeywordSet,
    KeywordTemplate,
    LanguageCode,
    NormalizationMode,
    NormalizationResult,
    NormalizationRule,
)
from src.keyword.interfaces import (
    CategoryHandler,
    CombinationStrategy,
    DeduplicationStrategy,
    KeywordExporter,
    KeywordGenerator,
    KeywordProvider,
    KeywordValidator,
    LanguageProcessor,
    NormalizationStrategy,
    TemplateEngine,
)


class TestKeywordCategory:
    """Tests for KeywordCategory enum."""

    def test_enum_values_exist(self) -> None:
        """Verify all expected category values exist."""
        assert KeywordCategory.MALWARE is not None
        assert KeywordCategory.PHISHING is not None
        assert KeywordCategory.SPAM is not None
        assert KeywordCategory.DGA is not None
        assert KeywordCategory.TYPOSQUATTING is not None
        assert KeywordCategory.CLOUD_HOSTING is not None
        assert KeywordCategory.DEFACEMENT is not None
        assert KeywordCategory.CREDENTIAL_THEFT is not None

    def test_enum_count(self) -> None:
        """Verify the number of enum values."""
        expected_count = 8
        actual_count = len(KeywordCategory)
        assert actual_count == expected_count


class TestLanguageCode:
    """Tests for LanguageCode enum."""

    def test_enum_values_exist(self) -> None:
        """Verify all expected language values exist."""
        assert LanguageCode.EN is not None
        assert LanguageCode.ES is not None
        assert LanguageCode.DE is not None
        assert LanguageCode.FR is not None
        assert LanguageCode.ZH is not None
        assert LanguageCode.RU is not None
        assert LanguageCode.JA is not None
        assert LanguageCode.KO is not None
        assert LanguageCode.PT is not None
        assert LanguageCode.AR is not None

    def test_language_codes_have_string_values(self) -> None:
        """Verify language codes have string values."""
        for lang in LanguageCode:
            assert isinstance(lang.value, str)
            assert len(lang.value) == 2


class TestKeyword:
    """Tests for Keyword dataclass."""

    def test_creation_with_required_fields(self) -> None:
        """Verify Keyword can be created with required fields."""
        keyword = Keyword(
            text="malware",
            category=KeywordCategory.MALWARE,
        )
        assert keyword.text == "malware"
        assert keyword.category == KeywordCategory.MALWARE
        assert keyword.language == LanguageCode.EN
        assert keyword.weight == 1.0
        assert keyword.tags == frozenset()

    def test_creation_with_all_fields(self) -> None:
        """Verify Keyword can be created with all fields."""
        keyword = Keyword(
            text="phishing",
            category=KeywordCategory.PHISHING,
            language=LanguageCode.ES,
            weight=0.8,
            tags=frozenset({"active", "high-priority"}),
        )
        assert keyword.text == "phishing"
        assert keyword.category == KeywordCategory.PHISHING
        assert keyword.language == LanguageCode.ES
        assert keyword.weight == 0.8
        assert keyword.tags == frozenset({"active", "high-priority"})

    def test_empty_text_raises_error(self) -> None:
        """Verify empty text raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Keyword(text="", category=KeywordCategory.MALWARE)

    def test_invalid_weight_raises_error(self) -> None:
        """Verify invalid weight raises ValueError."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            Keyword(text="test", category=KeywordCategory.MALWARE, weight=1.5)


class TestNormalizationRule:
    """Tests for NormalizationRule dataclass."""

    def test_creation_with_required_fields(self) -> None:
        """Verify NormalizationRule can be created with required fields."""
        rule = NormalizationRule(
            name="lowercase",
            description="Convert to lowercase",
            pattern="[A-Z]",
            replacement="a",
        )
        assert rule.name == "lowercase"
        assert rule.description == "Convert to lowercase"
        assert rule.pattern == "[A-Z]"
        assert rule.replacement == "a"
        assert rule.priority == 0
        assert rule.enabled is True

    def test_creation_with_all_fields(self) -> None:
        """Verify NormalizationRule can be created with all fields."""
        rule = NormalizationRule(
            name="trim",
            description="Trim whitespace",
            pattern=r"\s+",
            replacement=" ",
            priority=5,
            enabled=False,
        )
        assert rule.priority == 5
        assert rule.enabled is False

    def test_empty_name_raises_error(self) -> None:
        """Verify empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            NormalizationRule(
                name="",
                description="test",
                pattern="test",
                replacement="test",
            )

    def test_empty_pattern_raises_error(self) -> None:
        """Verify empty pattern raises ValueError."""
        with pytest.raises(ValueError, match="pattern cannot be empty"):
            NormalizationRule(
                name="test",
                description="test",
                pattern="",
                replacement="test",
            )


class TestKeywordTemplate:
    """Tests for KeywordTemplate dataclass."""

    def test_creation_with_required_fields(self) -> None:
        """Verify KeywordTemplate can be created with required fields."""
        template = KeywordTemplate(
            name="suffix_template",
            pattern="{base}_{category}",
        )
        assert template.name == "suffix_template"
        assert template.pattern == "{base}_{category}"
        assert template.description == ""
        assert template.enabled is True

    def test_creation_with_all_fields(self) -> None:
        """Verify KeywordTemplate can be created with all fields."""
        template = KeywordTemplate(
            name="full_template",
            pattern="{language}_{base}",
            description="Language prefix template",
            categories=frozenset({KeywordCategory.MALWARE}),
            languages=frozenset({LanguageCode.EN, LanguageCode.ES}),
            enabled=False,
        )
        assert template.description == "Language prefix template"
        assert KeywordCategory.MALWARE in template.categories
        assert LanguageCode.EN in template.languages
        assert LanguageCode.ES in template.languages
        assert template.enabled is False

    def test_missing_placeholders_raises_error(self) -> None:
        """Verify pattern without placeholders raises ValueError."""
        with pytest.raises(ValueError, match="must contain placeholders"):
            KeywordTemplate(
                name="invalid",
                pattern="no_placeholders",
            )


class TestGenerationConfig:
    """Tests for GenerationConfig dataclass."""

    def test_default_values(self) -> None:
        """Verify GenerationConfig has correct default values."""
        config = GenerationConfig()
        assert config.enabled_categories == frozenset({KeywordCategory.MALWARE})
        assert config.languages == frozenset({LanguageCode.EN})
        assert config.max_combinations == 1000
        assert config.min_keyword_length == 2
        assert config.max_keyword_length == 64
        assert config.enable_deduplication is True
        assert config.enable_normalization is True

    def test_custom_values(self) -> None:
        """Verify GenerationConfig can be customized."""
        config = GenerationConfig(
            enabled_categories=frozenset({
                KeywordCategory.MALWARE,
                KeywordCategory.PHISHING,
            }),
            languages=frozenset({LanguageCode.EN, LanguageCode.ZH}),
            max_combinations=500,
            min_keyword_length=3,
            max_keyword_length=100,
        )
        assert len(config.enabled_categories) == 2
        assert len(config.languages) == 2
        assert config.max_combinations == 500
        assert config.min_keyword_length == 3
        assert config.max_keyword_length == 100

    def test_invalid_max_combinations_raises_error(self) -> None:
        """Verify invalid max_combinations raises ValueError."""
        with pytest.raises(ValueError, match="must be at least 1"):
            GenerationConfig(max_combinations=0)

    def test_invalid_length_range_raises_error(self) -> None:
        """Verify invalid length range raises ValueError."""
        with pytest.raises(ValueError, match="must be >= min"):
            GenerationConfig(
                min_keyword_length=10,
                max_keyword_length=5,
            )


class TestKeywordSet:
    """Tests for KeywordSet dataclass."""

    def test_creation(self) -> None:
        """Verify KeywordSet can be created."""
        keywords = (
            Keyword(text="test1", category=KeywordCategory.MALWARE),
            Keyword(text="test2", category=KeywordCategory.PHISHING),
        )
        keyword_set = KeywordSet(
            keywords=keywords,
            total_count=2,
            unique_count=2,
        )
        assert len(keyword_set.keywords) == 2
        assert keyword_set.total_count == 2

    def test_empty_keywords_raises_error(self) -> None:
        """Verify empty keywords raises ValueError."""
        with pytest.raises(ValueError, match="at least one keyword"):
            KeywordSet(
                keywords=(),
                total_count=0,
                unique_count=0,
            )


class TestDeduplicationResult:
    """Tests for DeduplicationResult dataclass."""

    def test_creation(self) -> None:
        """Verify DeduplicationResult can be created."""
        result = DeduplicationResult(
            original_count=10,
            duplicate_count=3,
            remaining_count=7,
        )
        assert result.original_count == 10
        assert result.duplicate_count == 3
        assert result.remaining_count == 7
        assert result.strategy_used == "default"


class TestNormalizationResult:
    """Tests for NormalizationResult dataclass."""

    def test_creation(self) -> None:
        """Verify NormalizationResult can be created."""
        result = NormalizationResult(
            original_keyword="Test",
            normalized_keyword="test",
            rules_applied=tuple(["lowercase"]),
            changed=True,
        )
        assert result.original_keyword == "Test"
        assert result.normalized_keyword == "test"
        assert "lowercase" in result.rules_applied
        assert result.changed is True


class TestDeduplicationMode:
    """Tests for DeduplicationMode enum."""

    def test_enum_values_exist(self) -> None:
        """Verify all deduplication modes exist."""
        assert DeduplicationMode.EXACT is not None
        assert DeduplicationMode.CASE_INSENSITIVE is not None
        assert DeduplicationMode.SEMANTIC is not None
        assert DeduplicationMode.PATTERN_BASED is not None


class TestNormalizationMode:
    """Tests for NormalizationMode enum."""

    def test_enum_values_exist(self) -> None:
        """Verify all normalization modes exist."""
        assert NormalizationMode.LOWERCASE is not None
        assert NormalizationMode.TRIM is not None
        assert NormalizationMode.UNICODE is not None
        assert NormalizationMode.SPECIAL_CHARS is not None
        assert NormalizationMode.LENGTH is not None
        assert NormalizationMode.CUSTOM is not None


class TestKeywordValidation:
    """Tests for Keyword validation."""

    def test_empty_keyword_raises_error(self) -> None:
        """Verify empty text raises ValueError."""
        with pytest.raises(ValueError, match="Keyword text cannot be empty"):
            Keyword(text="", category=KeywordCategory.MALWARE)


class TestInterfacesExist:
    """Tests to verify all interfaces are defined."""

    def test_keyword_provider_interface_exists(self) -> None:
        """Verify KeywordProvider protocol exists."""
        assert KeywordProvider is not None

    def test_category_handler_interface_exists(self) -> None:
        """Verify CategoryHandler protocol exists."""
        assert CategoryHandler is not None

    def test_template_engine_interface_exists(self) -> None:
        """Verify TemplateEngine protocol exists."""
        assert TemplateEngine is not None

    def test_language_processor_interface_exists(self) -> None:
        """Verify LanguageProcessor protocol exists."""
        assert LanguageProcessor is not None

    def test_deduplication_strategy_interface_exists(self) -> None:
        """Verify DeduplicationStrategy protocol exists."""
        assert DeduplicationStrategy is not None

    def test_normalization_strategy_interface_exists(self) -> None:
        """Verify NormalizationStrategy protocol exists."""
        assert NormalizationStrategy is not None

    def test_keyword_generator_interface_exists(self) -> None:
        """Verify KeywordGenerator abstract class exists."""
        assert KeywordGenerator is not None

    def test_combination_strategy_interface_exists(self) -> None:
        """Verify CombinationStrategy abstract class exists."""
        assert CombinationStrategy is not None

    def test_keyword_validator_interface_exists(self) -> None:
        """Verify KeywordValidator protocol exists."""
        assert KeywordValidator is not None

    def test_keyword_exporter_interface_exists(self) -> None:
        """Verify KeywordExporter protocol exists."""
        assert KeywordExporter is not None
