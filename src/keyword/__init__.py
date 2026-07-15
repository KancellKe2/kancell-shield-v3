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

from .exceptions import (
    CombinationError,
    ConfigurationError,
    DeduplicationError,
    GenerationError,
    KeywordEngineError,
    NormalizationError,
    ProviderError,
    TemplateError,
    ValidationError,
)

from .template_engine import (
    KeywordTemplateEngine,
    SimpleTemplateEngine,
)

from .normalizer import (
    KeywordNormalizer,
    LengthEnforcingNormalizer,
    StrictNormalizer,
)

from .deduplicator import (
    CaseInsensitiveDeduplicator,
    ChainedDeduplicator,
    ExactMatchDeduplicator,
    KeywordDeduplicator,
    PatternDeduplicator,
)

from .generator import (
    BasicKeywordGenerator,
    DefaultKeywordProvider,
    KeywordGeneratorImpl,
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
    # Exceptions
    "CombinationError",
    "ConfigurationError",
    "DeduplicationError",
    "GenerationError",
    "KeywordEngineError",
    "NormalizationError",
    "ProviderError",
    "TemplateError",
    "ValidationError",
    # Implementations
    "KeywordTemplateEngine",
    "SimpleTemplateEngine",
    "KeywordNormalizer",
    "LengthEnforcingNormalizer",
    "StrictNormalizer",
    "KeywordDeduplicator",
    "CaseInsensitiveDeduplicator",
    "ExactMatchDeduplicator",
    "PatternDeduplicator",
    "ChainedDeduplicator",
    "KeywordGeneratorImpl",
    "BasicKeywordGenerator",
    "DefaultKeywordProvider",
]
