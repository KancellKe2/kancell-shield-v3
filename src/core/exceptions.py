"""Core exceptions for Kancell Shield v3.

Base exceptions for the application domain.
"""


class KancellShieldError(Exception):
    """Base exception for Kancell Shield errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize error.

        Args:
            message: Error message.
            code: Error code.
            details: Additional error details.
        """
        super().__init__(message)
        self.message = message
        self.code = code or "UNKNOWN_ERROR"
        self.details = details or {}


class ValidationError(KancellShieldError):
    """Validation error for invalid input."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: object | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message.
            field: Field that failed validation.
            value: Invalid value.
        """
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, "value": value},
        )
        self.field = field
        self.value = value


class DomainValidationError(ValidationError):
    """Validation error for invalid domain."""

    def __init__(
        self,
        message: str,
        domain: str | None = None,
    ) -> None:
        """Initialize domain validation error.

        Args:
            message: Error message.
            domain: Invalid domain string.
        """
        super().__init__(message=message, field="domain", value=domain)
        self.domain = domain


class URLValidationError(ValidationError):
    """Validation error for invalid URL."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
    ) -> None:
        """Initialize URL validation error.

        Args:
            message: Error message.
            url: Invalid URL string.
        """
        super().__init__(message=message, field="url", value=url)
        self.url = url


class ScoreValidationError(ValidationError):
    """Validation error for invalid score."""

    def __init__(
        self,
        message: str,
        score: float | None = None,
    ) -> None:
        """Initialize score validation error.

        Args:
            message: Error message.
            score: Invalid score value.
        """
        super().__init__(message=message, field="score", value=score)
        self.score = score


class PriorityValidationError(ValidationError):
    """Validation error for invalid priority."""

    def __init__(
        self,
        message: str,
        priority: int | None = None,
    ) -> None:
        """Initialize priority validation error.

        Args:
            message: Error message.
            priority: Invalid priority value.
        """
        super().__init__(message=message, field="priority", value=priority)
        self.priority = priority


class IdentifierError(KancellShieldError):
    """Error for invalid identifier."""

    def __init__(
        self,
        message: str,
        identifier_type: str | None = None,
        value: str | None = None,
    ) -> None:
        """Initialize identifier error.

        Args:
            message: Error message.
            identifier_type: Type of identifier.
            value: Invalid identifier value.
        """
        super().__init__(
            message=message,
            code="IDENTIFIER_ERROR",
            details={"type": identifier_type, "value": value},
        )
        self.identifier_type = identifier_type
        self.value = value


class ConfigurationError(KancellShieldError):
    """Configuration error."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Error message.
            config_key: Configuration key that failed.
        """
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            details={"config_key": config_key},
        )
        self.config_key = config_key


class StateError(KancellShieldError):
    """Error for invalid state transition."""

    def __init__(
        self,
        message: str,
        current_state: str | None = None,
        target_state: str | None = None,
    ) -> None:
        """Initialize state error.

        Args:
            message: Error message.
            current_state: Current state.
            target_state: Target state that failed.
        """
        super().__init__(
            message=message,
            code="STATE_ERROR",
            details={"current_state": current_state, "target_state": target_state},
        )
        self.current_state = current_state
        self.target_state = target_state


class ResourceError(KancellShieldError):
    """Error for resource limits."""

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        limit: int | None = None,
    ) -> None:
        """Initialize resource error.

        Args:
            message: Error message.
            resource_type: Type of resource.
            limit: Resource limit.
        """
        super().__init__(
            message=message,
            code="RESOURCE_ERROR",
            details={"resource_type": resource_type, "limit": limit},
        )
        self.resource_type = resource_type
        self.limit = limit
