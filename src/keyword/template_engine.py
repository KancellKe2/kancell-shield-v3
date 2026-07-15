"""Template engine implementation for keyword generation."""

import re
from typing import Sequence

from .exceptions import TemplateError
from .interfaces import TemplateEngine as ITemplateEngine
from .models import Keyword, KeywordCategory, KeywordTemplate, LanguageCode


class KeywordTemplateEngine(ITemplateEngine):
    """Implementation of template engine for applying keyword templates.

    This engine applies templates to generate new keyword strings by
    substituting placeholders with actual values.
    """

    PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")

    def __init__(self) -> None:
        """Initialize the template engine."""
        self._template_cache: dict[str, re.Pattern[str]] = {}

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

        Raises:
            TemplateError: If template application fails.
        """
        if not template.enabled:
            return []

        generated: list[str] = []
        placeholders = self._extract_placeholders(template.pattern)

        for keyword in base_keywords:
            # Filter by category if template has category restrictions
            if template.categories and keyword.category not in template.categories:
                continue

            # Filter by language if template has language restrictions
            if template.languages and keyword.language not in template.languages:
                continue

            try:
                result = self._substitute_placeholders(
                    pattern=template.pattern,
                    placeholders=placeholders,
                    keyword=keyword,
                    category=keyword.category,
                    language=keyword.language,
                )
                if result:
                    generated.append(result)
            except Exception as e:
                raise TemplateError(
                    f"Failed to apply template '{template.name}': {e}"
                ) from e

        return generated

    def validate_template(self, template: KeywordTemplate) -> bool:
        """Validate that a template is well-formed.

        Args:
            template: The template to validate.

        Returns:
            True if the template is valid.

        Raises:
            TemplateError: If the template is invalid.
        """
        if not template.name:
            raise TemplateError("Template name cannot be empty")

        if not template.pattern:
            raise TemplateError("Template pattern cannot be empty")

        placeholders = self._extract_placeholders(template.pattern)

        valid_placeholders = {"base", "category", "language"}
        for placeholder in placeholders:
            if placeholder not in valid_placeholders:
                raise TemplateError(
                    f"Invalid placeholder '{placeholder}' in template. "
                    f"Valid placeholders: {valid_placeholders}"
                )

        return True

    def _extract_placeholders(self, pattern: str) -> list[str]:
        """Extract placeholder names from a pattern.

        Args:
            pattern: The template pattern.

        Returns:
            List of placeholder names.
        """
        matches = self.PLACEHOLDER_PATTERN.findall(pattern)
        return matches

    def _substitute_placeholders(
        self,
        pattern: str,
        placeholders: list[str],
        keyword: Keyword,
        category: KeywordCategory,
        language: LanguageCode,
    ) -> str:
        """Substitute placeholders in a pattern.

        Args:
            pattern: The template pattern.
            placeholders: List of placeholder names.
            keyword: The keyword to use for substitution.
            category: The category to use for substitution.
            language: The language to use for substitution.

        Returns:
            The substituted string.
        """
        result = pattern

        for placeholder in placeholders:
            if placeholder == "base":
                result = result.replace("{base}", keyword.text)
            elif placeholder == "category":
                result = result.replace("{category}", category.name.lower())
            elif placeholder == "language":
                result = result.replace("{language}", language.value)

        return result

    def generate_combinations(
        self,
        templates: Sequence[KeywordTemplate],
        base_keywords: Sequence[Keyword],
        max_combinations: int = 1000,
    ) -> list[str]:
        """Generate keyword combinations from multiple templates.

        Args:
            templates: Templates to apply.
            base_keywords: Base keywords to use.
            max_combinations: Maximum number of combinations to generate.

        Returns:
            List of generated keyword strings.

        Raises:
            TemplateError: If combination generation fails.
        """
        results: list[str] = []
        seen: set[str] = set()

        for template in templates:
            if not template.enabled:
                continue

            generated = self.apply_template(template, base_keywords)

            for keyword_str in generated:
                # Enforce uniqueness
                lower_str = keyword_str.lower()
                if lower_str not in seen:
                    seen.add(lower_str)
                    results.append(keyword_str)

                    if len(results) >= max_combinations:
                        return results

        return results


class SimpleTemplateEngine(ITemplateEngine):
    """A simpler template engine that only supports base keyword substitution."""

    def __init__(self) -> None:
        """Initialize the simple template engine."""
        pass

    def apply_template(
        self,
        template: KeywordTemplate,
        base_keywords: Sequence[Keyword],
    ) -> Sequence[str]:
        """Apply a template with only base keyword substitution.

        Args:
            template: The template to apply.
            base_keywords: The base keywords to use.

        Returns:
            Generated keyword strings.
        """
        if not template.enabled:
            return []

        results: list[str] = []
        for keyword in base_keywords:
            result = template.pattern.replace("{base}", keyword.text)
            results.append(result)

        return results

    def validate_template(self, template: KeywordTemplate) -> bool:
        """Validate template has base placeholder.

        Args:
            template: The template to validate.

        Returns:
            True if valid.
        """
        return "{base}" in template.pattern
