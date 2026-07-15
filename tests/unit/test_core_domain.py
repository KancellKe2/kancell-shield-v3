"""Unit tests for Core Domain Model."""

import pytest
from datetime import datetime, timezone

from src.core import (
    # Value Objects
    Domain,
    Hostname,
    URL,
    ConfidenceScore,
    Priority,
    Timestamp,
    # Identifiers
    ProviderId,
    CandidateId,
    TaskId,
    BatchId,
    EventId,
    SourceId,
    RuleId,
    # Enums
    PriorityLevel,
    DiscoveryStatus,
    ProviderStatus,
    CandidateStatus,
    ScoreLevel,
    # Exceptions
    ValidationError,
    DomainValidationError,
    URLValidationError,
    ScoreValidationError,
    PriorityValidationError,
    IdentifierError,
    # Types
    is_valid_domain,
    is_valid_url,
    is_valid_score,
    is_valid_priority,
    is_terminal_status,
    is_active_status,
)

from src.core.constants import (
    MIN_SCORE,
    MAX_SCORE,
    DEFAULT_SCORE,
    HIGH_SCORE_THRESHOLD,
    MIN_PRIORITY,
    MAX_PRIORITY,
    DEFAULT_PRIORITY,
    HIGH_RISK_TLDS,
    LOW_RISK_TLDS,
    RESERVED_TLDS,
)


class TestDomain:
    """Tests for Domain value object."""

    def test_create_valid_domain(self) -> None:
        """Test creating a valid domain."""
        domain = Domain(name="example.com")
        assert str(domain) == "example.com"
        assert domain.name == "example.com"
        assert domain.tld == "com"
        assert domain.registrable_domain == "example.com"

    def test_create_domain_with_subdomain(self) -> None:
        """Test creating domain with subdomain."""
        domain = Domain(name="example.com", subdomain="www")
        assert str(domain) == "www.example.com"
        assert domain.subdomain == "www"
        assert domain.full_domain == "www.example.com"
        assert domain.registrable_domain == "example.com"

    def test_create_invalid_empty_domain(self) -> None:
        """Test creating domain with empty name."""
        with pytest.raises(ValueError):
            Domain(name="")

    def test_create_invalid_too_long_domain(self) -> None:
        """Test creating domain that's too long."""
        long_name = "a" * 250 + ".com"
        with pytest.raises(ValueError):
            Domain(name=long_name)

    def test_create_invalid_format(self) -> None:
        """Test creating domain with invalid format."""
        with pytest.raises(ValueError):
            Domain(name="not-a-domain")

    def test_domain_tld(self) -> None:
        """Test TLD extraction."""
        domain = Domain(name="example.co.uk")
        assert domain.tld == "uk"
        assert domain.registrable_domain == "co.uk"

    def test_domain_immutability(self) -> None:
        """Test domain is immutable."""
        domain = Domain(name="example.com")
        with pytest.raises(Exception):  # FrozenInstanceError
            domain.name = "other.com"  # type: ignore

    def test_domain_hash(self) -> None:
        """Test domain is hashable."""
        d1 = Domain(name="example.com")
        d2 = Domain(name="example.com")
        assert hash(d1) == hash(d2)

    def test_domain_equality(self) -> None:
        """Test domain equality."""
        d1 = Domain(name="example.com")
        d2 = Domain(name="example.com")
        d3 = Domain(name="other.com")
        assert d1 == d2
        assert d1 != d3


class TestHostname:
    """Tests for Hostname value object."""

    def test_create_valid_hostname(self) -> None:
        """Test creating a valid hostname."""
        host = Hostname(value="server1.example.com")
        assert str(host) == "server1.example.com"
        assert host.value == "server1.example.com"

    def test_create_hostname_with_port(self) -> None:
        """Test creating hostname with port."""
        host = Hostname(value="server1.example.com", port=8080)
        assert str(host) == "server1.example.com:8080"
        assert host.port == 8080

    def test_create_invalid_empty_hostname(self) -> None:
        """Test creating hostname with empty value."""
        with pytest.raises(ValueError):
            Hostname(value="")

    def test_create_invalid_too_long_hostname(self) -> None:
        """Test creating hostname that's too long."""
        # 254 character hostname should fail
        long_value = "a" * 254
        with pytest.raises(ValueError):
            Hostname(value=long_value)

    def test_create_invalid_port(self) -> None:
        """Test creating hostname with invalid port."""
        with pytest.raises(ValueError):
            Hostname(value="example.com", port=70000)

    def test_hostname_immutability(self) -> None:
        """Test hostname is immutable."""
        host = Hostname(value="example.com")
        with pytest.raises(Exception):
            host.value = "other.com"  # type: ignore


class TestURL:
    """Tests for URL value object."""

    def test_create_valid_url(self) -> None:
        """Test creating a valid URL."""
        url = URL(scheme="https", host="example.com")
        assert str(url) == "https://example.com"
        assert url.scheme == "https"
        assert url.host == "example.com"

    def test_create_url_with_path(self) -> None:
        """Test creating URL with path."""
        url = URL(scheme="https", host="example.com", path="/api/v1")
        assert str(url) == "https://example.com/api/v1"
        assert url.path == "/api/v1"

    def test_create_url_with_port(self) -> None:
        """Test creating URL with port."""
        url = URL(scheme="https", host="example.com", port=8443)
        assert str(url) == "https://example.com:8443"

    def test_create_url_with_query(self) -> None:
        """Test creating URL with query."""
        url = URL(scheme="https", host="example.com", query="foo=bar")
        assert "foo=bar" in str(url)
        assert url.query == "foo=bar"

    def test_create_invalid_empty_scheme(self) -> None:
        """Test creating URL with empty scheme."""
        with pytest.raises(ValueError):
            URL(scheme="", host="example.com")

    def test_create_invalid_scheme(self) -> None:
        """Test creating URL with invalid scheme."""
        with pytest.raises(ValueError):
            URL(scheme="invalid", host="example.com")

    def test_create_invalid_empty_host(self) -> None:
        """Test creating URL with empty host."""
        with pytest.raises(ValueError):
            URL(scheme="https", host="")

    def test_url_domain_property(self) -> None:
        """Test URL domain extraction."""
        url = URL(scheme="https", host="server.example.com:8080")
        assert url.domain == "server.example.com"


class TestConfidenceScore:
    """Tests for ConfidenceScore value object."""

    def test_create_valid_score(self) -> None:
        """Test creating a valid score."""
        score = ConfidenceScore(value=0.85)
        assert score.value == 0.85
        assert score.percentage == 85

    def test_create_score_boundaries(self) -> None:
        """Test creating score at boundaries."""
        score_min = ConfidenceScore(value=0.0)
        score_max = ConfidenceScore(value=1.0)
        assert score_min.value == 0.0
        assert score_max.value == 1.0

    def test_create_invalid_negative_score(self) -> None:
        """Test creating score with negative value."""
        with pytest.raises(ValueError):
            ConfidenceScore(value=-0.1)

    def test_create_invalid_over_max_score(self) -> None:
        """Test creating score over maximum."""
        with pytest.raises(ValueError):
            ConfidenceScore(value=1.5)

    def test_score_is_high_confidence(self) -> None:
        """Test high confidence property."""
        high = ConfidenceScore(value=0.9)
        low = ConfidenceScore(value=0.5)
        assert high.is_high_confidence is True
        assert low.is_high_confidence is False

    def test_score_is_low_confidence(self) -> None:
        """Test low confidence property."""
        high = ConfidenceScore(value=0.9)
        low = ConfidenceScore(value=0.1)
        assert low.is_low_confidence is True
        assert high.is_low_confidence is False

    def test_score_immutability(self) -> None:
        """Test score is immutable."""
        score = ConfidenceScore(value=0.5)
        with pytest.raises(Exception):
            score.value = 0.8  # type: ignore


class TestPriority:
    """Tests for Priority value object."""

    def test_create_valid_priority(self) -> None:
        """Test creating a valid priority."""
        priority = Priority(value=50, level="high")
        assert priority.value == 50
        assert priority.level == "high"

    def test_create_priority_boundaries(self) -> None:
        """Test creating priority at boundaries."""
        p_min = Priority(value=MIN_PRIORITY)
        p_max = Priority(value=MAX_PRIORITY)
        assert p_min.value == MIN_PRIORITY
        assert p_max.value == MAX_PRIORITY

    def test_create_invalid_under_min_priority(self) -> None:
        """Test creating priority under minimum."""
        with pytest.raises(ValueError):
            Priority(value=MIN_PRIORITY - 1)

    def test_create_invalid_over_max_priority(self) -> None:
        """Test creating priority over maximum."""
        with pytest.raises(ValueError):
            Priority(value=MAX_PRIORITY + 1)

    def test_priority_is_high(self) -> None:
        """Test high priority property."""
        high = Priority(value=50)
        low = Priority(value=0)
        assert high.is_high is True
        assert low.is_high is False

    def test_priority_is_low(self) -> None:
        """Test low priority property."""
        high = Priority(value=0)
        low = Priority(value=-50)
        assert low.is_low is True
        assert high.is_low is False

    def test_priority_immutability(self) -> None:
        """Test priority is immutable."""
        priority = Priority(value=0)
        with pytest.raises(Exception):
            priority.value = 50  # type: ignore


class TestTimestamp:
    """Tests for Timestamp value object."""

    def test_create_from_datetime(self) -> None:
        """Test creating timestamp from datetime."""
        now = datetime.now(timezone.utc)
        ts = Timestamp(value=now)
        assert ts.value == now

    def test_create_now(self) -> None:
        """Test creating current timestamp."""
        ts = Timestamp.now()
        assert ts.value is not None

    def test_create_from_iso(self) -> None:
        """Test creating timestamp from ISO string."""
        iso = "2024-01-15T10:30:00+00:00"
        ts = Timestamp.from_iso(iso)
        assert ts.iso_format is not None

    def test_timestamp_iso_format(self) -> None:
        """Test ISO format property."""
        now = datetime.now(timezone.utc)
        ts = Timestamp(value=now)
        assert "T" in ts.iso_format

    def test_timestamp_unix(self) -> None:
        """Test Unix timestamp property."""
        now = datetime.now(timezone.utc)
        ts = Timestamp(value=now)
        assert ts.unix_timestamp > 0


class TestIdentifiers:
    """Tests for identifier value objects."""

    def test_create_provider_id(self) -> None:
        """Test creating provider ID."""
        pid = ProviderId(value="provider-1")
        assert str(pid) == "provider-1"

    def test_create_invalid_empty_provider_id(self) -> None:
        """Test creating empty provider ID."""
        with pytest.raises(ValueError):
            ProviderId(value="")

    def test_create_candidate_id(self) -> None:
        """Test creating candidate ID."""
        cid = CandidateId(value="candidate-1")
        assert str(cid) == "candidate-1"

    def test_create_task_id(self) -> None:
        """Test creating task ID."""
        tid = TaskId(value="task-1")
        assert str(tid) == "task-1"

    def test_create_batch_id(self) -> None:
        """Test creating batch ID."""
        bid = BatchId(value="batch-1")
        assert str(bid) == "batch-1"

    def test_create_event_id(self) -> None:
        """Test creating event ID."""
        eid = EventId(value="event-1")
        assert str(eid) == "event-1"

    def test_create_source_id(self) -> None:
        """Test creating source ID."""
        sid = SourceId(value="source-1")
        assert str(sid) == "source-1"

    def test_create_rule_id(self) -> None:
        """Test creating rule ID."""
        rid = RuleId(value="rule-1")
        assert str(rid) == "rule-1"

    def test_identifier_immutability(self) -> None:
        """Test identifiers are immutable."""
        pid = ProviderId(value="provider-1")
        with pytest.raises(Exception):
            pid.value = "other"  # type: ignore

    def test_identifier_hash(self) -> None:
        """Test identifiers are hashable."""
        p1 = ProviderId(value="provider-1")
        p2 = ProviderId(value="provider-1")
        assert hash(p1) == hash(p2)


class TestPriorityLevel:
    """Tests for PriorityLevel enum."""

    def test_from_value(self) -> None:
        """Test creating from value."""
        assert PriorityLevel.from_value("high") == PriorityLevel.HIGH
        assert PriorityLevel.from_value("invalid") == PriorityLevel.NORMAL

    def test_sort_order(self) -> None:
        """Test sort order property."""
        assert PriorityLevel.CRITICAL.sort_order > PriorityLevel.HIGH.sort_order
        assert PriorityLevel.LOW.sort_order < PriorityLevel.NORMAL.sort_order


class TestDiscoveryStatus:
    """Tests for DiscoveryStatus enum."""

    def test_is_terminal(self) -> None:
        """Test terminal status detection."""
        assert DiscoveryStatus.COMPLETED.is_terminal is True
        assert DiscoveryStatus.FAILED.is_terminal is True
        assert DiscoveryStatus.RUNNING.is_terminal is False

    def test_is_active(self) -> None:
        """Test active status detection."""
        assert DiscoveryStatus.RUNNING.is_active is True
        assert DiscoveryStatus.PAUSED.is_active is True
        assert DiscoveryStatus.STOPPED.is_active is False


class TestProviderStatus:
    """Tests for ProviderStatus enum."""

    def test_is_available(self) -> None:
        """Test available status detection."""
        assert ProviderStatus.HEALTHY.is_available is True
        assert ProviderStatus.DEGRADED.is_available is True
        assert ProviderStatus.UNHEALTHY.is_available is False


class TestCandidateStatus:
    """Tests for CandidateStatus enum."""

    def test_is_terminal(self) -> None:
        """Test terminal status detection."""
        assert CandidateStatus.REJECTED.is_terminal is True
        assert CandidateStatus.DUPLICATE.is_terminal is True
        assert CandidateStatus.VALIDATED.is_terminal is False

    def test_is_valid(self) -> None:
        """Test valid status detection."""
        assert CandidateStatus.VALIDATED.is_valid is True
        assert CandidateStatus.SCORED.is_valid is True
        assert CandidateStatus.REJECTED.is_valid is False


class TestScoreLevel:
    """Tests for ScoreLevel enum."""

    def test_from_score(self) -> None:
        """Test creating from score."""
        assert ScoreLevel.from_score(0.1) == ScoreLevel.LOW
        assert ScoreLevel.from_score(0.3) == ScoreLevel.MEDIUM
        assert ScoreLevel.from_score(0.6) == ScoreLevel.HIGH
        assert ScoreLevel.from_score(0.9) == ScoreLevel.CRITICAL
        assert ScoreLevel.from_score(-0.1) == ScoreLevel.UNKNOWN

    def test_risk_weight(self) -> None:
        """Test risk weight property."""
        assert ScoreLevel.HIGH.risk_weight == 0.75
        assert ScoreLevel.LOW.risk_weight == 0.25


class TestTypeGuards:
    """Tests for type guard functions."""

    def test_is_valid_domain(self) -> None:
        """Test domain validation guard."""
        assert is_valid_domain(Domain(name="example.com")) is True
        assert is_valid_domain("not-a-domain") is False

    def test_is_valid_url(self) -> None:
        """Test URL validation guard."""
        url = URL(scheme="https", host="example.com")
        assert is_valid_url(url) is True
        assert is_valid_url("not-a-url") is False

    def test_is_valid_score(self) -> None:
        """Test score validation guard."""
        assert is_valid_score(0.5) is True
        assert is_valid_score(1.5) is False
        assert is_valid_score(-0.1) is False

    def test_is_valid_priority(self) -> None:
        """Test priority validation guard."""
        assert is_valid_priority(0) is True
        assert is_valid_priority(50) is True
        assert is_valid_priority(-150) is False

    def test_is_terminal_status(self) -> None:
        """Test terminal status guard."""
        assert is_terminal_status(DiscoveryStatus.COMPLETED) is True
        assert is_terminal_status(DiscoveryStatus.RUNNING) is False

    def test_is_active_status(self) -> None:
        """Test active status guard."""
        assert is_active_status(DiscoveryStatus.RUNNING) is True
        assert is_active_status(DiscoveryStatus.STOPPED) is False


class TestConstants:
    """Tests for constants."""

    def test_score_boundaries(self) -> None:
        """Test score boundary constants."""
        assert MIN_SCORE == 0.0
        assert MAX_SCORE == 1.0
        assert DEFAULT_SCORE == 0.5
        assert HIGH_SCORE_THRESHOLD >= 0.75

    def test_priority_boundaries(self) -> None:
        """Test priority boundary constants."""
        assert MIN_PRIORITY <= -100
        assert MAX_PRIORITY >= 100
        assert DEFAULT_PRIORITY == 0

    def test_tld_sets(self) -> None:
        """Test TLD sets are defined."""
        assert "com" not in HIGH_RISK_TLDS
        assert "xyz" in HIGH_RISK_TLDS
        assert "com" in LOW_RISK_TLDS
        assert "local" in RESERVED_TLDS


class TestExceptions:
    """Tests for exception classes."""

    def test_validation_error(self) -> None:
        """Test ValidationError."""
        error = ValidationError("Invalid input", field="name", value="")
        assert error.message == "Invalid input"
        assert error.field == "name"
        assert error.code == "VALIDATION_ERROR"

    def test_domain_validation_error(self) -> None:
        """Test DomainValidationError."""
        error = DomainValidationError("Invalid domain", domain="bad")
        assert error.domain == "bad"
        assert error.code == "VALIDATION_ERROR"

    def test_url_validation_error(self) -> None:
        """Test URLValidationError."""
        error = URLValidationError("Invalid URL", url="bad")
        assert error.url == "bad"

    def test_score_validation_error(self) -> None:
        """Test ScoreValidationError."""
        error = ScoreValidationError("Invalid score", score=2.0)
        assert error.score == 2.0

    def test_priority_validation_error(self) -> None:
        """Test PriorityValidationError."""
        error = PriorityValidationError("Invalid priority", priority=200)
        assert error.priority == 200

    def test_identifier_error(self) -> None:
        """Test IdentifierError."""
        error = IdentifierError("Invalid ID", identifier_type="TaskId", value="")
        assert error.identifier_type == "TaskId"
        assert error.code == "IDENTIFIER_ERROR"
