# Search Engine Architecture

## Purpose

The Search Engine is a runtime component responsible for executing search queries against multiple search providers to discover potentially malicious domains. It provides an abstraction layer that allows the system to query various search services while handling provider failures, rate limiting, and result aggregation.

The engine consumes keywords from the Keyword Engine and transforms them into search queries, returning normalized results for downstream processing.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Search Engine                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │   Models    │  │ Interfaces  │  │   Configuration     │   │
│  │ (Data Types)│  │ (Contracts) │  │   (Settings/Config)  │   │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Search Orchestration                    │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐   │
│  │  │ Provider│  │  Query  │  │ Result  │  │  Rate    │   │
│  │  │ Manager │──▶│ Builder │──▶│Normalizer│──▶│ Limiter │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └──────────┘   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Provider Layer                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐   │
│  │  │ Provider │  │ Provider │  │ Provider │  │ ...    │   │
│  │  │     A    │  │     B    │  │     C    │  │        │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └────────┘   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. Query Construction
   └── Receive keywords from Keyword Engine
   └── Build search queries from keywords
   └── Apply query templates and modifiers

2. Provider Selection
   └── Check provider health states
   └── Apply provider priorities
   └── Respect rate limits

3. Search Execution
   └── Route query to selected provider(s)
   └── Apply timeout configuration
   └── Handle retries if configured

4. Result Collection
   └── Aggregate results from all providers
   └── Normalize result formats
   └── Apply deduplication

5. Scoring and Ranking
   └── Calculate confidence scores
   └── Apply provider weights
   └── Sort by relevance

6. Result Export
   └── Return normalized SearchResult objects
   └── Include metadata and scores
```

## Component Responsibilities

### Models (`models.py`)

The data layer containing immutable data structures:

| Model | Purpose |
|-------|---------|
| `SearchQuery` | Represents a single search query with metadata |
| `SearchResult` | Represents a search result with URL, title, snippet |
| `ProviderConfig` | Configuration for a search provider |
| `SearchConfig` | Global search engine configuration |
| `ProviderHealth` | Health state and metrics for a provider |
| `RateLimitInfo` | Rate limiting state for a provider |
| `RetryConfig` | Configuration for retry behavior |
| `PaginationState` | Pagination tracking for result sets |

### Interfaces (`interfaces.py`)

Abstract contracts defining the engine's capabilities:

| Interface | Purpose |
|-----------|---------|
| `SearchProvider` | Protocol for search provider implementations |
| `ProviderRegistry` | Registry for managing provider instances |
| `RateLimiter` | Rate limiting strategy abstraction |
| `RetryStrategy` | Retry behavior abstraction |
| `ResultNormalizer` | Result format normalization |
| `QueryBuilder` | Build queries from keywords |
| `SearchEngine` | Main search orchestration interface |
| `HealthChecker` | Provider health checking |

## Public Interfaces

### SearchProvider (Protocol)

```python
class SearchProvider(Protocol):
    """Protocol for search provider implementations."""
    
    @property
    def name(self) -> str:
        """Provider identifier."""
        ...
    
    @property
    def priority(self) -> int:
        """Provider priority (higher = more preferred)."""
        ...
    
    async def search(
        self,
        query: SearchQuery,
        timeout: float
    ) -> Sequence[SearchResult]:
        """Execute a search query."""
        ...
    
    def is_healthy(self) -> bool:
        """Check if provider is healthy."""
        ...
    
    def get_rate_limit_info(self) -> RateLimitInfo:
        """Get current rate limit state."""
        ...
```

### SearchEngine (Protocol)

```python
class SearchEngine(Protocol):
    """Main interface for search orchestration."""
    
    async def search(
        self,
        keywords: Sequence[str],
        config: SearchConfig
    ) -> SearchResultSet:
        """Execute search for keywords across providers."""
        ...
    
    async def search_batch(
        self,
        keywords: Sequence[str],
        config: SearchConfig
    ) -> Sequence[SearchResultSet]:
        """Execute batch search for multiple keywords."""
        ...
```

### RateLimiter (Protocol)

```python
class RateLimiter(Protocol):
    """Protocol for rate limiting strategies."""
    
    async def acquire(self, provider: str) -> bool:
        """Acquire permission to make a request."""
        ...
    
    def release(self, provider: str) -> None:
        """Release rate limit token."""
        ...
    
    def get_wait_time(self, provider: str) -> float:
        """Get estimated wait time in seconds."""
        ...
```

### RetryStrategy (Protocol)

```python
class RetryStrategy(Protocol):
    """Protocol for retry behavior."""
    
    def should_retry(
        self,
        attempt: int,
        error: Exception
    ) -> bool:
        """Determine if request should be retried."""
        ...
    
    def get_backoff_delay(self, attempt: int) -> float:
        """Calculate backoff delay in seconds."""
        ...
```

## Provider Lifecycle

### Provider States

| State | Description |
|-------|-------------|
| `HEALTHY` | Provider is fully operational |
| `DEGRADED` | Provider has limited capacity |
| `UNHEALTHY` | Provider is not responding |
| `DISABLED` | Provider manually disabled |
| `RATE_LIMITED` | Provider has hit rate limits |

### State Transitions

```
HEALTHY ──(failure)──▶ DEGRADED ──(more failures)──▶ UNHEALTHY
   │                       │                              │
   │                       │                              │
   │                       ▼                              │
   │                   (success)                         │
   │                       │                              │
   │◀──(recovery)──────────┘                              │
   │                                                      │
   │◀──(manual enable)───────────────────────────────────┘
   │
   └──(rate limit hit)──▶ RATE_LIMITED ──(cooldown)──▶ HEALTHY
   │
   └──(manual disable)──▶ DISABLED
```

### Health Checking

- Providers perform self-checks periodically
- Failed health checks trigger state transitions
- Recovery requires consecutive successful checks
- Health state affects query routing

## Configuration

### Search Configuration

```python
SearchConfig:
  - timeout: float (default: 30.0 seconds)
  - max_retries: int (default: 3)
  - retry_delay: float (default: 1.0 seconds)
  - max_results_per_query: int (default: 100)
  - provider_timeout: dict[str, float] (per-provider overrides)
  - rate_limit_requests: int (default: 10)
  - rate_limit_window: float (default: 60.0 seconds)
  - batch_size: int (default: 10)
  - enable_deduplication: bool (default: True)
  - confidence_threshold: float (default: 0.5)
```

### Provider Configuration

```python
ProviderConfig:
  - name: str
  - priority: int (default: 1)
  - enabled: bool (default: True)
  - timeout: float (optional override)
  - rate_limit: RateLimitConfig
  - retry_config: RetryConfig
  - custom_settings: dict[str, Any]
```

### Rate Limit Configuration

```python
RateLimitConfig:
  - requests_per_window: int
  - window_seconds: float
  - backoff_multiplier: float
  - max_backoff: float
```

### Retry Configuration

```python
RetryConfig:
  - max_attempts: int
  - initial_delay: float
  - max_delay: float
  - exponential_backoff: bool
  - retryable_errors: tuple[type[Exception], ...]
```

## Error Handling

### Error Categories

| Category | Handling |
|----------|----------|
| `TimeoutError` | Retry with backoff |
| `RateLimitError` | Wait and retry |
| `ProviderError` | Fallback to next provider |
| `ValidationError` | Skip invalid queries |
| `NetworkError` | Retry with exponential backoff |

### Error Recovery

1. **Transient Errors**: Automatic retry with backoff
2. **Rate Limits**: Automatic cooldown and retry
3. **Provider Failure**: Fallback to alternative provider
4. **Complete Failure**: Log and continue with remaining providers

### Error Propagation

- All errors are caught and logged
- Partial results are returned when possible
- Error summary included in result metadata

## Retry Strategy

### Backoff Algorithms

1. **Fixed Delay**: Constant wait between retries
   - Use case: Predictable rate limits

2. **Linear Backoff**: Increasing delay by fixed amount
   - Delay = initial_delay + (attempt * increment)

3. **Exponential Backoff**: Delay doubles each attempt
   - Delay = initial_delay * (2 ^ attempt)
   - Cap at max_delay

4. **Jittered Backoff**: Random variation to prevent thundering herd
   - Delay = base_delay * random(0.5, 1.5)

### Retry Conditions

| Error Type | Default Behavior |
|------------|------------------|
| Timeout | Retry |
| Rate Limit | Retry with longer backoff |
| Server Error (5xx) | Retry |
| Client Error (4xx) | Do not retry |
| Network Error | Retry |
| Validation Error | Do not retry |

## Rate Limiting Strategy

### Token Bucket Algorithm

- Each provider has a token bucket
- Tokens refill at configured rate
- Request consumes one token
- If no tokens, wait for refill

### Sliding Window Algorithm

- Track requests in time window
- Window slides as requests complete
- If window is full, wait for window to advance

### Provider-Specific Limits

| Provider | Requests/Min | Burst |
|----------|---------------|-------|
| Provider A | 60 | 10 |
| Provider B | 30 | 5 |
| Provider C | 120 | 20 |

### Global Limits

- Sum of all provider requests
- Prevents overwhelming network
- Configurable multiplier

## Query Batching

### Batch Configuration

- Keywords are grouped into batches
- Each batch processed concurrently
- Batch results aggregated
- Configurable batch size

### Batch Processing Flow

```
Keywords: [k1, k2, k3, k4, k5, k6, k7, k8, k9, k10]
Batch Size: 3

Batch 1: [k1, k2, k3] ──▶ Concurrent Execution
Batch 2: [k4, k5, k6] ──▶ Concurrent Execution
Batch 3: [k7, k8, k9] ──▶ Concurrent Execution
Batch 4: [k10] ──────────▶ Concurrent Execution

Results: Aggregated and deduplicated
```

## Result Normalization

### Normalized Fields

| Field | Type | Description |
|-------|------|-------------|
| `url` | str | Normalized URL |
| `title` | str | Cleaned title |
| `snippet` | str | Cleaned snippet |
| `provider` | str | Source provider |
| `confidence` | float | Confidence score (0-1) |
| `keywords` | tuple[str, ...] | Matching keywords |
| `timestamp` | datetime | Result timestamp |

### Confidence Scoring

```python
Base Score = 0.5

Modifiers:
  - Provider Weight: +0.1 to +0.3
  - Freshness: +0.0 to +0.2
  - Keyword Match: +0.0 to +0.2
  - Position Bonus: +0.0 to +0.1

Final Score = clamp(Base + Modifiers, 0.0, 1.0)
```

## Pagination

### Pagination Types

| Type | Description |
|------|-------------|
| `OFFSET` | Skip N results |
| `CURSOR` | Use cursor for next page |
| `PAGE` | Page number and size |

### Pagination State

```python
PaginationState:
  - type: PaginationType
  - offset: int
  - cursor: str | None
  - page: int
  - page_size: int
  - total_results: int | None
  - has_more: bool
```

## Future Extensions

Potential future enhancements:

- **Search Analytics**: Track and analyze search patterns
- **Provider Auto-Scaling**: Dynamically adjust provider usage
- **Smart Routing**: ML-based provider selection
- **Result Caching**: Cache frequent queries
- **Distributed Search**: Multi-node search coordination
- **Query Optimization**: Rewrite and expand queries
- **Custom Providers**: Plugin system for new providers

## Non-Goals

This design explicitly excludes:

- HTTP request implementation
- DNS resolution
- Crawler implementation
- Database persistence
- File system operations
- AI/ML components
- Discovery orchestration
- Pipeline management

These concerns will be handled by other components in the system architecture.
