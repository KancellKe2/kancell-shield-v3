"""Unit tests for keyword engine exceptions."""

import pytest

from src.keyword.exceptions import (
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


class TestKeywordEngineExceptions:
    """Tests for keyword engine exception hierarchy."""

    def test_keyword_engine_error_is_base(self) -> None:
        """Test KeywordEngineError is base exception."""
        error = KeywordEngineError("test")
        assert isinstance(error, Exception)

    def test_template_error_inheritance(self) -> None:
        """Test TemplateError inherits from base."""
        error = TemplateError("template error")
        assert isinstance(error, KeywordEngineError)

    def test_normalization_error_inheritance(self) -> None:
        """Test NormalizationError inherits from base."""
        error = NormalizationError("normalization error")
        assert isinstance(error, KeywordEngineError)

    def test_deduplication_error_inheritance(self) -> None:
        """Test DeduplicationError inherits from base."""
        error = DeduplicationError("deduplication error")
        assert isinstance(error, KeywordEngineError)

    def test_configuration_error_inheritance(self) -> None:
        """Test ConfigurationError inherits from base."""
        error = ConfigurationError("configuration error")
        assert isinstance(error, KeywordEngineError)

    def test_validation_error_inheritance(self) -> None:
        """Test ValidationError inherits from base."""
        error = ValidationError("validation error")
        assert isinstance(error, KeywordEngineError)

    def test_generation_error_inheritance(self) -> None:
        """Test GenerationError inherits from base."""
        error = GenerationError("generation error")
        assert isinstance(error, KeywordEngineError)

    def test_provider_error_inheritance(self) -> None:
        """Test ProviderError inherits from base."""
        error = ProviderError("provider error")
        assert isinstance(error, KeywordEngineError)

    def test_combination_error_inheritance(self) -> None:
        """Test CombinationError inherits from base."""
        error = CombinationError("combination error")
        assert isinstance(error, KeywordEngineError)

    def test_exception_message(self) -> None:
        """Test exception messages are preserved."""
        message = "specific error message"
        error = KeywordEngineError(message)
        assert str(error) == message

    def test_exception_chaining(self) -> None:
        """Test exception chaining works."""
        cause = ValueError("cause")
        error = GenerationError("effect")
        error.__cause__ = cause
        assert error.__cause__ is cause
