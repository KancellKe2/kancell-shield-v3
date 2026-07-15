"""Keyword Engine for Kancell Shield v3.

This module provides the keyword generation capabilities for
discovering and identifying malicious domains.
"""

from .models import (
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

from .interfaces import (
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

__all__ = [
    # Models
    "DeduplicationMode",
    "DeduplicationResult",
    "GenerationConfig",
    "Keyword",
    "KeywordCategory",
    "KeywordSet",
    "KeywordTemplate",
    "LanguageCode",
    "NormalizationMode",
    "NormalizationResult",
    "NormalizationRule",
    # Interfaces
    "CategoryHandler",
    "CombinationStrategy",
    "DeduplicationStrategy",
    "KeywordExporter",
    "KeywordGenerator",
    "KeywordProvider",
    "KeywordValidator",
    "LanguageProcessor",
    "NormalizationStrategy",
    "TemplateEngine",
]
