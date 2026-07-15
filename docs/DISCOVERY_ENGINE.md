# Discovery Engine Architecture

## Purpose

The Discovery Engine is responsible for finding new domain candidates to evaluate for malicious activity. It provides a pluggable architecture for different discovery strategies while maintaining a consistent interface for candidate processing.

The engine takes seed domains or keywords and discovers related domains through various discovery sources. Candidates are validated, filtered, and scored before being passed to downstream evaluation.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Discovery Engine                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │     Models       │  │    Interfaces    │  │    Configuration    │  │
│  │  (Data Types)    │  │   (Contracts)    │  │    (Settings)       │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Discovery Orchestration                          │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │   │
│  │  │Scheduler│──▶│Pipeline │──▶│Collector│──▶│ Validator│──▶│Scorer │ │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                       Source Layer                                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────┐  │   │
│  │  │ Passive  │  │  Active  │  │  WHOIS   │  │   DNS    │  │... │  │   │
│  │  │ Sources  │  │  Sources │  │  Lookup  │  │ Lookup   │  │    │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. Task Creation
   └── Receive discovery task with seed domains/keywords
   └── Validate task configuration
   └── Initialize discovery state

2. Source Scheduling
   └── Select discovery sources based on configuration
   └── Prioritize sources by expected yield
   └── Respect source rate limits

3. Discovery Pipeline
   └── Execute discovery across selected sources
   └── Collect raw candidates
   └── Handle source failures gracefully

4. Candidate Collection
   └── Aggregate candidates from all sources
   └── Deduplicate candidates
   └── Track candidate origins

5. Validation
   └── Apply format validation
   └── Check domain syntax
   └── Verify DNS feasibility

6. Scoring
   └── Calculate relevance scores
   └── Apply source weights
   └── Rank candidates by score

7. Filtering
   └── Apply inclusion/exclusion filters
   └── Remove known benign domains
   └── Filter by score thresholds

8. Result Export
   └── Return validated DiscoveryResult objects
   └── Include statistics and metadata
```

## Component Responsibilities

### Models (`models.py`)

Immutable data structures for discovery operations:

| Model | Purpose |
|-------|---------|
| `DiscoveryTask` | Defines what to discover and how |
| `DiscoveryCandidate` | A discovered domain candidate |
| `DiscoverySource` | Information about the discovery source |
| `DiscoveryResult` | Aggregated discovery results |
| `DiscoveryStatistics` | Metrics about discovery operation |
| `DiscoveryConfiguration` | Runtime configuration |
| `DiscoveryProgress` | Progress tracking for long operations |
| `DiscoveryBatch` | Batch of candidates for processing |

### Interfaces (`interfaces.py`)

Protocol definitions for discovery components:

| Interface | Purpose |
|-----------|---------|
| `DiscoveryEngine` | Main orchestration interface |
| `DiscoveryScheduler` | Schedules discovery tasks |
| `DiscoveryPipeline` | Executes discovery workflow |
| `DiscoveryCollector` | Collects candidates from sources |
| `CandidateValidator` | Validates candidate format |
| `CandidateScorer` | Scores candidates |
| `CandidateFilter` | Filters candidates |
| `DiscoveryState` | Manages discovery state |

## Discovery Sources

Sources represent different methods of discovering domains:

### Passive Sources
- DNS cache snooping results
- Passive DNS databases
- Certificate transparency logs
- Historical DNS records

### Active Sources (Architecture only, no implementation)
- WHOIS lookups
- DNS enumeration
- Subdomain enumeration

## Candidate Lifecycle

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Discovered │───▶│   Validated  │───▶│   Scored    │───▶│   Filtered   │
│             │    │             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │                  │
      ▼                  ▼                  ▼                  ▼
  Raw domain         Format OK         Score > 0        Passes filters
  from source        Syntax valid       Relevance > 0     Not excluded
```

## State Management

Discovery state tracks the progress and results of discovery operations:

- **Pending**: Task created but not started
- **Running**: Discovery in progress
- **Paused**: Discovery paused (rate limit hit)
- **Completed**: Discovery finished successfully
- **Failed**: Discovery failed with error
- **Cancelled**: Discovery cancelled by user

## Configuration Options

| Option | Description |
|--------|-------------|
| `max_candidates` | Maximum candidates to discover |
| `timeout` | Discovery timeout in seconds |
| `retry_count` | Number of retries per source |
| `batch_size` | Candidates per batch |
| `score_threshold` | Minimum score to include |
| `sources` | Enabled discovery sources |

## Error Handling

The architecture supports graceful degradation:

1. **Source Failures**: Continue with remaining sources
2. **Validation Failures**: Log and skip invalid candidates
3. **Timeout Errors**: Retry or skip based on configuration
4. **Rate Limits**: Pause and resume when limits clear

## Thread Safety

The architecture is designed for single-threaded operation. Thread safety is handled at the implementation layer if needed, but the core interfaces do not assume concurrency.
