"""Core constants for Kancell Shield v3.

System-wide constant values.
"""


# Domain validation
MAX_DOMAIN_LENGTH = 253
MAX_LABEL_LENGTH = 63
MIN_DOMAIN_LENGTH = 3
MIN_DOMAIN_LABELS = 2
MIN_LABEL_LENGTH = 1

# URL validation
MAX_URL_LENGTH = 2048
MAX_HOST_LENGTH = 253
MAX_PORT = 65535

# Score thresholds
MIN_SCORE = 0.0
MAX_SCORE = 1.0
DEFAULT_SCORE = 0.5
HIGH_SCORE_THRESHOLD = 0.8
LOW_SCORE_THRESHOLD = 0.2

# Priority bounds
MIN_PRIORITY = -100
MAX_PRIORITY = 100
DEFAULT_PRIORITY = 0
HIGH_PRIORITY = 50
LOW_PRIORITY = -50

# Confidence levels
HIGH_CONFIDENCE = 0.8
MEDIUM_CONFIDENCE = 0.5
LOW_CONFIDENCE = 0.2

# Queue limits
DEFAULT_QUEUE_CAPACITY = 10000
MAX_QUEUE_CAPACITY = 100000

# Batch sizes
DEFAULT_BATCH_SIZE = 100
MAX_BATCH_SIZE = 1000
MIN_BATCH_SIZE = 1

# Timeout values (seconds)
DEFAULT_TIMEOUT = 30.0
MAX_TIMEOUT = 300.0
MIN_TIMEOUT = 1.0

# Retry values
DEFAULT_RETRY_COUNT = 3
MAX_RETRY_COUNT = 10
MIN_RETRY_COUNT = 0

# Rate limits
DEFAULT_RATE_LIMIT = 60  # requests per minute
MAX_RATE_LIMIT = 1000
MIN_RATE_LIMIT = 1

# Identifier lengths
MAX_PROVIDER_ID_LENGTH = 100
MAX_CANDIDATE_ID_LENGTH = 200
MAX_TASK_ID_LENGTH = 200
MAX_BATCH_ID_LENGTH = 200
MAX_EVENT_ID_LENGTH = 200
MAX_SOURCE_ID_LENGTH = 100
MAX_RULE_ID_LENGTH = 100

# Timestamp formats
ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
ISO_FORMAT_SHORT = "%Y-%m-%dT%H:%M:%SZ"

# Reserved TLDs (should not be processed)
RESERVED_TLDS = frozenset({
    "local",
    "localhost",
    "example",
    "invalid",
    "test",
    "onion",  # Tor hidden services need special handling
})

# High-risk TLDs (commonly used for malicious domains)
HIGH_RISK_TLDS = frozenset({
    "xyz",
    "top",
    "club",
    "online",
    "site",
    "buzz",
    "tk",
    "ml",
    "ga",
    "cf",
    "gq",
    "pw",
    "cc",
    "su",
    "racing",
    "win",
    "review",
    "country",
    "stream",
    "download",
    "trade",
    "accountant",
    "cricket",
    "science",
    "party",
    "gdn",
})

# Low-risk TLDs (commonly legitimate)
LOW_RISK_TLDS = frozenset({
    "com",
    "org",
    "net",
    "gov",
    "edu",
    "mil",
    "gov.uk",
    "org.uk",
    "com.au",
    "de",
    "fr",
    "jp",
    "cn",
})

# Status values (for serialization)
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_PAUSED = "paused"
STATUS_STOPPED = "stopped"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

# Priority level strings
PRIORITY_LOW = "low"
PRIORITY_NORMAL = "normal"
PRIORITY_HIGH = "high"
PRIORITY_CRITICAL = "critical"

# Event type prefixes
DISCOVERY_EVENT_PREFIX = "discovery"
CANDIDATE_EVENT_PREFIX = "candidate"
PROVIDER_EVENT_PREFIX = "provider"
PIPELINE_EVENT_PREFIX = "pipeline"
QUEUE_EVENT_PREFIX = "queue"
ERROR_EVENT_PREFIX = "error"

# Source types
SOURCE_TYPE_PASSIVE = "passive"
SOURCE_TYPE_ACTIVE = "active"
SOURCE_TYPE_DNS = "dns"
SOURCE_TYPE_CT = "certificate_transparency"
SOURCE_TYPE_WHOIS = "whois"
SOURCE_TYPE_PDNS = "passive_dns"
SOURCE_TYPE_CUSTOM = "custom"

# Default provider priorities
DEFAULT_PROVIDER_PRIORITIES = {
    SOURCE_TYPE_CT: 100,
    SOURCE_TYPE_PDNS: 90,
    SOURCE_TYPE_DNS: 80,
    SOURCE_TYPE_WHOIS: 70,
    SOURCE_TYPE_ACTIVE: 60,
    SOURCE_TYPE_PASSIVE: 50,
}

# Error codes
ERROR_VALIDATION = "VALIDATION_ERROR"
ERROR_CONFIGURATION = "CONFIGURATION_ERROR"
ERROR_TIMEOUT = "TIMEOUT_ERROR"
ERROR_RATE_LIMIT = "RATE_LIMIT_ERROR"
ERROR_NETWORK = "NETWORK_ERROR"
ERROR_PROVIDER = "PROVIDER_ERROR"
ERROR_STATE = "STATE_ERROR"
