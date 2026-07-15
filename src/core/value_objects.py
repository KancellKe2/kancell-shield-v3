"""Immutable value objects for Kancell Shield v3.

Value objects are compared by their values, not identity.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import re


@dataclass(frozen=True)
class Domain:
    """Domain name value object.

    Represents a fully qualified domain name.
    """

    name: str
    subdomain: str | None = None

    # Regex patterns for validation
    _DOMAIN_PATTERN = re.compile(
        r"^(?:[a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$",
        re.IGNORECASE,
    )

    def __post_init__(self) -> None:
        """Validate the domain."""
        if not self.name:
            raise ValueError("Domain name cannot be empty")
        if len(self.name) > 253:
            raise ValueError("Domain name too long")

        # Validate format
        if not self._DOMAIN_PATTERN.match(self.full_domain):
            raise ValueError(f"Invalid domain format: {self.full_domain}")

    @property
    def full_domain(self) -> str:
        """Get full domain including subdomain.

        Returns:
            Full domain string.
        """
        if self.subdomain:
            return f"{self.subdomain}.{self.name}"
        return self.name

    @property
    def tld(self) -> str:
        """Get top-level domain.

        Returns:
            TLD string.
        """
        parts = self.name.lower().split(".")
        return parts[-1] if parts else ""

    @property
    def registrable_domain(self) -> str:
        """Get the registrable domain (without subdomain).

        Returns:
            Registrable domain string.
        """
        parts = self.name.lower().split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return self.name

    def __str__(self) -> str:
        """Return string representation."""
        return self.full_domain


@dataclass(frozen=True)
class Hostname:
    """Hostname value object.

    Represents a network hostname.
    """

    value: str
    port: int | None = None

    # Pattern for hostname validation
    _HOSTNAME_PATTERN = re.compile(
        r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$",
        re.IGNORECASE,
    )

    def __post_init__(self) -> None:
        """Validate the hostname."""
        if not self.value:
            raise ValueError("Hostname cannot be empty")
        if len(self.value) > 253:
            raise ValueError("Hostname too long")
        if not self._HOSTNAME_PATTERN.match(self.value):
            raise ValueError(f"Invalid hostname format: {self.value}")
        if self.port is not None and (self.port < 1 or self.port > 65535):
            raise ValueError(f"Invalid port: {self.port}")

    @property
    def full_hostname(self) -> str:
        """Get full hostname with port.

        Returns:
            Full hostname string.
        """
        if self.port:
            return f"{self.value}:{self.port}"
        return self.value

    def __str__(self) -> str:
        """Return string representation."""
        return self.full_hostname


@dataclass(frozen=True)
class URL:
    """URL value object.

    Represents a Uniform Resource Locator.
    """

    scheme: str
    host: str
    path: str = ""
    port: int | None = None
    query: str = ""
    fragment: str = ""

    # Valid URL schemes
    _VALID_SCHEMES = frozenset({"http", "https", "ftp", "ftps"})

    def __post_init__(self) -> None:
        """Validate the URL."""
        if not self.scheme:
            raise ValueError("URL scheme cannot be empty")
        if self.scheme.lower() not in self._VALID_SCHEMES:
            raise ValueError(f"Invalid URL scheme: {self.scheme}")
        if not self.host:
            raise ValueError("URL host cannot be empty")

    @property
    def full_url(self) -> str:
        """Get full URL string.

        Returns:
            Full URL string.
        """
        url = f"{self.scheme.lower()}://{self.host}"
        if self.port:
            url += f":{self.port}"
        if self.path:
            url += self.path
        if self.query:
            url += f"?{self.query}"
        if self.fragment:
            url += f"#{self.fragment}"
        return url

    @property
    def domain(self) -> str:
        """Extract domain from URL.

        Returns:
            Domain string.
        """
        return self.host.split(":")[0]

    def __str__(self) -> str:
        """Return string representation."""
        return self.full_url


@dataclass(frozen=True)
class ConfidenceScore:
    """Confidence score value object.

    Represents a confidence value between 0.0 and 1.0.
    """

    value: float

    def __post_init__(self) -> None:
        """Validate the score."""
        if self.value < 0.0 or self.value > 1.0:
            raise ValueError(f"ConfidenceScore must be between 0.0 and 1.0, got {self.value}")

    @property
    def percentage(self) -> int:
        """Get score as percentage.

        Returns:
            Integer percentage (0-100).
        """
        return int(self.value * 100)

    @property
    def is_high_confidence(self) -> bool:
        """Check if score indicates high confidence.

        Returns:
            True if score >= 0.8.
        """
        return self.value >= 0.8

    @property
    def is_low_confidence(self) -> bool:
        """Check if score indicates low confidence.

        Returns:
            True if score <= 0.2.
        """
        return self.value <= 0.2

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.percentage}%"


@dataclass(frozen=True)
class Priority:
    """Priority value object.

    Represents a priority value for ordering.
    """

    value: int
    level: str = "normal"

    # Priority bounds
    MIN = -100
    MAX = 100

    def __post_init__(self) -> None:
        """Validate the priority."""
        if self.value < self.MIN or self.value > self.MAX:
            raise ValueError(f"Priority must be between {self.MIN} and {self.MAX}")

    @property
    def is_high(self) -> bool:
        """Check if priority is high.

        Returns:
            True if value >= 50.
        """
        return self.value >= 50

    @property
    def is_low(self) -> bool:
        """Check if priority is low.

        Returns:
            True if value <= -50.
        """
        return self.value <= -50

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.level}:{self.value}"


@dataclass(frozen=True)
class Timestamp:
    """Timestamp value object.

    Represents a point in time.
    """

    value: datetime

    def __post_init__(self) -> None:
        """Validate the timestamp."""
        if self.value is None:
            raise ValueError("Timestamp cannot be None")

    @classmethod
    def now(cls) -> "Timestamp":
        """Create timestamp for current time.

        Returns:
            Timestamp for now.
        """
        return cls(value=datetime.now(timezone.utc))

    @classmethod
    def from_iso(cls, iso_string: str) -> "Timestamp":
        """Create timestamp from ISO format string.

        Args:
            iso_string: ISO format string.

        Returns:
            Timestamp instance.
        """
        return cls(value=datetime.fromisoformat(iso_string))

    @property
    def iso_format(self) -> str:
        """Get ISO format string.

        Returns:
            ISO format string.
        """
        return self.value.isoformat()

    @property
    def unix_timestamp(self) -> float:
        """Get Unix timestamp.

        Returns:
            Unix timestamp value.
        """
        return self.value.timestamp()

    def __str__(self) -> str:
        """Return string representation."""
        return self.iso_format
