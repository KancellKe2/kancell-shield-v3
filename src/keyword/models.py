"""Data models for the Keyword Engine.

This module contains only dataclasses, enums, and immutable models.
No algorithms or business logic should be placed here.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import FrozenSet, Sequence


class KeywordCategory(Enum):
    """Categories for classifying keywords by threat type."""

    MALWARE = auto()
    PHISHING = auto()
    SPAM = auto()
    DGA = auto()
    TYPOSQUATTING = auto()
    CLOUD_HOSTING = auto()
    DEFACEMENT = auto()
    CREDENTIAL_THEFT = auto()


class LanguageCode(Enum):
    """Supported languages for keyword generation."""

    EN = "en"
    ES = "es"
    DE = "de"
    FR = "fr"
    ZH = "zh"
    RU = "ru"
    JA = "ja"
    KO = "ko"
    PT = "pt"
    AR = "ar"


@dataclass(frozen=True)
class Keyword:
    """Represents a single keyword with associated metadata.

    This is an immutable data class.
    """

    text: str
    category: KeywordCategory
    language: LanguageCode = LanguageCode.EN
    weight: float = 1.0
    tags: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate keyword data after initialization."""
        if not self.text:
            raise ValueError("Keyword text cannot be empty")
        if self.weight < 0.0 or self.weight > 1.0:
            raise ValueError("Weight must be between 0.0 and 1.0")


@dataclass(frozen=True)
class NormalizationRule:
    """Defines a normalization transformation rule.

    This is an immutable data class.
    """

    name: str
    description: str
    pattern: str
    replacement: str
    priority: int = 0
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate rule data after initialization."""
        if not self.name:
            raise ValueError("Rule name cannot be empty")
        if not self.pattern:
            raise ValueError("Rule pattern cannot be empty")


@dataclass(frozen=True)
class KeywordTemplate:
    """Defines a template for keyword generation.

    Templates use placeholder syntax: {base}, {category}, {language}
    Example: "{base}_{category}" generates "malware_virus"

    This is an immutable data class.
    """

    name: str
    pattern: str
    description: str = ""
    categories: FrozenSet[KeywordCategory] = field(default_factory=frozenset)
    languages: FrozenSet[LanguageCode] = field(default_factory=frozenset)
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate template data after initialization."""
        if not self.name:
            raise ValueError("Template name cannot be empty")
        if not self.pattern:
            raise ValueError("Template pattern cannot be empty")
        if "{" not in self.pattern or "}" not in self.pattern:
            raise ValueError("Template pattern must contain placeholders")


@dataclass(frozen=True)
class GenerationConfig:
    """Configuration for the keyword generation process.

    This is an immutable data class.
    """

    enabled_categories: FrozenSet[KeywordCategory] = field(
        default_factory=lambda: frozenset({KeywordCategory.MALWARE})
    )
    languages: FrozenSet[LanguageCode] = field(
        default_factory=lambda: frozenset({LanguageCode.EN})
    )
    max_combinations: int = 1000
    min_keyword_length: int = 2
    max_keyword_length: int = 64
    enable_deduplication: bool = True
    enable_normalization: bool = True
    normalization_rules: FrozenSet[str] = field(default_factory=frozenset)
    custom_templates: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.max_combinations < 1:
            raise ValueError("max_combinations must be at least 1")
        if self.min_keyword_length < 1:
            raise ValueError("min_keyword_length must be at least 1")
        if self.max_keyword_length < self.min_keyword_length:
            raise ValueError("max_keyword_length must be >= min_keyword_length")


@dataclass(frozen=True)
class KeywordSet:
    """A collection of keywords with metadata.

    This is an immutable data class.
    """

    keywords: tuple[Keyword, ...]
    total_count: int
    unique_count: int
    category_counts: dict[KeywordCategory, int] = field(default_factory=dict)
    language_counts: dict[LanguageCode, int] = field(default_factory=dict)
    generation_metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate keyword set after initialization."""
        if not self.keywords:
            raise ValueError("KeywordSet must contain at least one keyword")

    def filter_by_category(
        self, categories: Sequence[KeywordCategory]
    ) -> "KeywordSet":
        """Return a new KeywordSet filtered by categories."""
        filtered = tuple(k for k in self.keywords if k.category in categories)
        return self._create_filtered_set(filtered, categories)

    def filter_by_language(
        self, languages: Sequence[LanguageCode]
    ) -> "KeywordSet":
        """Return a new KeywordSet filtered by languages."""
        filtered = tuple(k for k in self.keywords if k.language in languages)
        return self._create_filtered_set(filtered, languages)

    def _create_filtered_set(
        self, keywords: tuple[Keyword, ...], _: Sequence[object]
    ) -> "KeywordSet":
        """Helper to create a filtered KeywordSet."""
        category_counts: dict[KeywordCategory, int] = {}
        language_counts: dict[LanguageCode, int] = {}
        for k in keywords:
            category_counts[k.category] = category_counts.get(k.category, 0) + 1
            language_counts[k.language] = language_counts.get(k.language, 0) + 1
        return KeywordSet(
            keywords=keywords,
            total_count=len(keywords),
            unique_count=len(set(k.text for k in keywords)),
            category_counts=category_counts,
            language_counts=language_counts,
            generation_metadata=self.generation_metadata,
        )


@dataclass(frozen=True)
class DeduplicationResult:
    """Result of deduplication operation.

    This is an immutable data class.
    """

    original_count: int
    duplicate_count: int
    remaining_count: int
    duplicates: tuple[str, ...] = field(default_factory=tuple)
    strategy_used: str = "default"


@dataclass(frozen=True)
class NormalizationResult:
    """Result of normalization operation.

    This is an immutable data class.
    """

    original_keyword: str
    normalized_keyword: str
    rules_applied: tuple[str, ...] = field(default_factory=tuple)
    changed: bool = False


class DeduplicationMode(Enum):
    """Modes for deduplication strategies."""

    EXACT = auto()
    CASE_INSENSITIVE = auto()
    SEMANTIC = auto()
    PATTERN_BASED = auto()


class NormalizationMode(Enum):
    """Modes for normalization strategies."""

    LOWERCASE = auto()
    TRIM = auto()
    UNICODE = auto()
    SPECIAL_CHARS = auto()
    LENGTH = auto()
    CUSTOM = auto()
