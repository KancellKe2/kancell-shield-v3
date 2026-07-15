"""Candidate validation for discovery."""

import re
from typing import Sequence

from .interfaces import CandidateValidator
from .models import (
    CandidateStatus,
    DiscoveryCandidate,
    Domain,
    ValidationResult,
)


# Reserved TLDs that should not be processed
RESERVED_TLDS = frozenset({
    "local",
    "localhost",
    "example",
    "invalid",
    "test",
})

# Reserved domain names
RESERVED_DOMAINS = frozenset({
    "example.com",
    "example.org",
    "example.net",
    "localhost.localdomain",
})

# Maximum domain length (per RFC 1035)
MAX_DOMAIN_LENGTH = 253

# Maximum label length (per RFC 1035)
MAX_LABEL_LENGTH = 63

# Minimum domain length (at least one char + TLD)
MIN_DOMAIN_LENGTH = 3


class DomainValidator(CandidateValidator):
    """Implementation of CandidateValidator.

    Performs syntax validation only - no network operations.
    """

    # RFC 1123 compliant label pattern
    _LABEL_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")

    # Full domain pattern
    _DOMAIN_PATTERN = re.compile(
        r"^(?:[a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$",
        re.IGNORECASE,
    )

    # Valid TLD pattern
    _TLD_PATTERN = re.compile(r"^[a-z]{2,}$", re.IGNORECASE)

    def __init__(
        self,
        min_length: int = MIN_DOMAIN_LENGTH,
        max_length: int = MAX_DOMAIN_LENGTH,
        allow_underscores: bool = False,
    ) -> None:
        """Initialize validator.

        Args:
            min_length: Minimum domain length.
            max_length: Maximum domain length.
            allow_underscores: Whether to allow underscores in domains.
        """
        self._min_length = min_length
        self._max_length = max_length
        self._allow_underscores = allow_underscores

    def validate(self, candidate: DiscoveryCandidate) -> ValidationResult:
        """Validate a candidate.

        Args:
            candidate: Candidate to validate.

        Returns:
            Validation result.
        """
        domain_str = candidate.domain.name
        length_result = self._validate_length(domain_str)
        if length_result != ValidationResult.VALID:
            return length_result

        format_result = self._validate_format(domain_str)
        if format_result != ValidationResult.VALID:
            return format_result

        tld_result = self._validate_tld(domain_str)
        if tld_result != ValidationResult.VALID:
            return tld_result

        reserved_result = self._validate_not_reserved(domain_str)
        if reserved_result != ValidationResult.VALID:
            return reserved_result

        return ValidationResult.VALID

    def validate_batch(
        self,
        candidates: Sequence[DiscoveryCandidate],
    ) -> tuple[DiscoveryCandidate, ...]:
        """Validate multiple candidates.

        Args:
            candidates: Candidates to validate.

        Returns:
            Validated candidates with updated status.
        """
        validated = []
        for candidate in candidates:
            result = self.validate(candidate)
            updated = DiscoveryCandidate(
                domain=candidate.domain,
                source=candidate.source,
                discovered_at=candidate.discovered_at,
                status=CandidateStatus.VALIDATED if result == ValidationResult.VALID else CandidateStatus.REJECTED,
                validation_result=result,
                score=candidate.score,
                confidence=candidate.confidence,
                metadata=candidate.metadata,
                parent_domain=candidate.parent_domain,
            )
            validated.append(updated)
        return tuple(validated)

    def is_valid_format(self, domain_string: str) -> bool:
        """Check if domain format is valid.

        Args:
            domain_string: Domain to check.

        Returns:
            True if format is valid.
        """
        return self._validate_format(domain_string) == ValidationResult.VALID

    def get_validation_errors(
        self,
        candidate: DiscoveryCandidate,
    ) -> tuple[ValidationResult, ...]:
        """Get all validation errors for a candidate.

        Args:
            candidate: Candidate to validate.

        Returns:
            Tuple of validation errors (empty if valid).
        """
        domain_str = candidate.domain.name
        errors = []

        length_result = self._validate_length(domain_str)
        if length_result != ValidationResult.VALID:
            errors.append(length_result)

        format_result = self._validate_format(domain_str)
        if format_result != ValidationResult.VALID:
            errors.append(format_result)

        tld_result = self._validate_tld(domain_str)
        if tld_result != ValidationResult.VALID:
            errors.append(tld_result)

        reserved_result = self._validate_not_reserved(domain_str)
        if reserved_result != ValidationResult.VALID:
            errors.append(reserved_result)

        return tuple(errors)

    def _validate_length(self, domain_str: str) -> ValidationResult:
        """Validate domain length.

        Args:
            domain_str: Domain string.

        Returns:
            Validation result.
        """
        length = len(domain_str)

        if length < self._min_length:
            return ValidationResult.TOO_SHORT

        if length > self._max_length:
            return ValidationResult.TOO_LONG

        return ValidationResult.VALID

    def _validate_format(self, domain_str: str) -> ValidationResult:
        """Validate domain format.

        Args:
            domain_str: Domain string.

        Returns:
            Validation result.
        """
        # Check against full pattern first
        if self._DOMAIN_PATTERN.match(domain_str):
            # Check each label
            labels = domain_str.lower().split(".")
            for label in labels:
                if not self._is_valid_label(label):
                    return ValidationResult.INVALID_SYNTAX
            return ValidationResult.VALID

        return ValidationResult.INVALID_FORMAT

    def _validate_tld(self, domain_str: str) -> ValidationResult:
        """Validate TLD.

        Args:
            domain_str: Domain string.

        Returns:
            Validation result.
        """
        parts = domain_str.lower().split(".")
        if not parts:
            return ValidationResult.INVALID_TLD

        tld = parts[-1]
        if not self._TLD_PATTERN.match(tld):
            return ValidationResult.INVALID_TLD

        if tld in RESERVED_TLDS:
            return ValidationResult.RESERVED_DOMAIN

        return ValidationResult.VALID

    def _validate_not_reserved(self, domain_str: str) -> ValidationResult:
        """Validate domain is not reserved.

        Args:
            domain_str: Domain string.

        Returns:
            Validation result.
        """
        if domain_str.lower() in RESERVED_DOMAINS:
            return ValidationResult.RESERVED_DOMAIN

        return ValidationResult.VALID

    def _is_valid_label(self, label: str) -> bool:
        """Check if a domain label is valid.

        Args:
            label: Label to check.

        Returns:
            True if valid.
        """
        if not label or len(label) > MAX_LABEL_LENGTH:
            return False

        if not label[0].isalnum() or not label[-1].isalnum():
            return False

        # Check for valid characters
        if self._allow_underscores:
            pattern = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
        else:
            pattern = self._LABEL_PATTERN

        return bool(pattern.match(label))
