"""Custom exceptions for the Keyword Engine."""


class KeywordEngineError(Exception):
    """Base exception for Keyword Engine errors."""

    pass


class TemplateError(KeywordEngineError):
    """Raised when a template operation fails."""

    pass


class NormalizationError(KeywordEngineError):
    """Raised when a normalization operation fails."""

    pass


class DeduplicationError(KeywordEngineError):
    """Raised when a deduplication operation fails."""

    pass


class ConfigurationError(KeywordEngineError):
    """Raised when configuration is invalid."""

    pass


class ValidationError(KeywordEngineError):
    """Raised when keyword validation fails."""

    pass


class GenerationError(KeywordEngineError):
    """Raised when keyword generation fails."""

    pass


class ProviderError(KeywordEngineError):
    """Raised when a keyword provider operation fails."""

    pass


class CombinationError(KeywordEngineError):
    """Raised when keyword combination fails."""

    pass
