# Keyword Engine Architecture

## Purpose

The Keyword Engine is a design-time component responsible for generating search keywords used in discovering malicious domains. It provides a flexible, extensible system for creating, combining, and managing keyword patterns that will be consumed by downstream search and discovery systems.

The engine operates as a pure keyword generator without any knowledge of search execution, domain validation, or threat classification.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Keyword Engine                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │   Models    │  │ Interfaces  │  │  Configuration      │   │
│  │ (Data Types)│  │ (Contracts) │  │  (Templates/Settings)│   │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Keyword Generation                     │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐   │
│  │  │ Base    │  │ Category│  │ Template│  │ Language │   │
│  │  │ Keywords│──▶│ Handler │──▶│ Engine  │──▶│ Processor│   │
│  │  └─────────┘  └─────────┘  └─────────┘  └──────────┘   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. Configuration Load
   └── Load templates, base keywords, language rules

2. Category Selection
   └── Select keyword categories to use

3. Template Processing
   └── Apply templates to base keywords

4. Combination Generation
   └── Generate combinations and permutations

5. Language Processing
   └── Apply language-specific transformations

6. Normalization
   └── Normalize, deduplicate, and validate output

7. Export
   └── Return final keyword set to caller
```

## Component Responsibilities

### Models (`models.py`)

The data layer containing immutable data structures:

| Model | Purpose |
|-------|---------|
| `Keyword` | Represents a single keyword with metadata |
| `KeywordCategory` | Enum for keyword classification types |
| `KeywordTemplate` | Defines patterns for keyword generation |
| `LanguageCode` | Enum for supported languages |
| `KeywordSet` | Collection of keywords with deduplication metadata |
| `GenerationConfig` | Configuration for keyword generation process |
| `NormalizationRule` | Defines normalization transformations |

### Interfaces (`interfaces.py`)

Abstract contracts defining the engine's capabilities:

| Interface | Purpose |
|-----------|---------|
| `KeywordProvider` | Supplies base keywords from a source |
| `CategoryHandler` | Processes keywords by category |
| `TemplateEngine` | Applies templates to generate new keywords |
| `LanguageProcessor` | Handles language-specific transformations |
| `DeduplicationStrategy` | Defines how duplicates are identified |
| `NormalizationStrategy` | Defines text normalization rules |
| `KeywordGenerator` | Main interface for generating keywords |

### Configuration

Configuration is externalized to allow runtime customization:

```python
# Example configuration structure
GenerationConfig:
  - enabled_categories: List[KeywordCategory]
  - languages: List[LanguageCode]
  - deduplication_strategy: DeduplicationStrategy
  - normalization_rules: List[NormalizationRule]
  - max_combinations: int
  - min_keyword_length: int
  - max_keyword_length: int
```

## Public Interfaces

### KeywordGenerator (Main Interface)

```python
class KeywordGenerator(Protocol):
    """Main interface for keyword generation."""
    
    def generate(
        self,
        config: GenerationConfig,
        templates: Sequence[KeywordTemplate]
    ) -> KeywordSet:
        """Generate keywords based on configuration and templates."""
        ...
```

### KeywordProvider

```python
class KeywordProvider(Protocol):
    """Interface for providing base keywords."""
    
    def get_keywords(
        self,
        categories: Sequence[KeywordCategory]
    ) -> Sequence[Keyword]:
        """Retrieve keywords for specified categories."""
        ...
```

### DeduplicationStrategy

```python
class DeduplicationStrategy(Protocol):
    """Interface for identifying duplicate keywords."""
    
    def is_duplicate(
        self,
        keyword: Keyword,
        existing: Sequence[Keyword]
    ) -> bool:
        """Check if keyword is a duplicate."""
        ...
```

### NormalizationStrategy

```python
class NormalizationStrategy(Protocol):
    """Interface for normalizing keywords."""
    
    def normalize(self, keyword: Keyword) -> Keyword:
        """Apply normalization to keyword."""
        ...
    
    def apply_rules(
        self,
        keyword: Keyword,
        rules: Sequence[NormalizationRule]
    ) -> Keyword:
        """Apply normalization rules in sequence."""
        ...
```

## Configuration

### Keyword Categories

| Category | Description | Example Keywords |
|----------|-------------|------------------|
| `MALWARE` | Malware-related terms | virus, trojan, ransomware |
| `PHISHING` | Phishing-related terms | login, verify, account |
| `SPAM` | Spam-related terms | free, winner, claim |
| `DGA` | Domain generation algorithm terms | random, generated |
| `TYPOSQUATTING` | Typosquatting-related terms | misspellings, common errors |

### Language Support

| Language | Code | Status |
|----------|------|--------|
| English | `en` | Primary |
| Spanish | `es` | Supported |
| German | `de` | Supported |
| French | `fr` | Supported |
| Chinese | `zh` | Supported |
| Russian | `ru` | Supported |

### Template Format

Templates use placeholder syntax for variable substitution:

```
"{base_keyword}_{category_suffix}"
"{language_prefix}_{base_keyword}"
"{base_keyword}_{number_range}"
```

## Deduplication Strategy

The engine supports multiple deduplication approaches:

1. **Exact Match**: Simple string comparison
2. **Case-Insensitive**: Normalize case before comparison
3. **Semantic**: Detect semantically equivalent keywords
4. **Pattern-Based**: Remove keywords matching existing patterns

## Normalization Strategy

Normalization rules are applied in sequence:

1. **Case Normalization**: Convert to lowercase
2. **Whitespace Trimming**: Remove leading/trailing spaces
3. **Special Character Handling**: Remove or replace special characters
4. **Unicode Normalization**: Standardize Unicode representation
5. **Length Validation**: Enforce min/max length constraints

## Extensibility

The engine is designed for extension:

### Adding New Categories

1. Add enum value to `KeywordCategory`
2. Implement `CategoryHandler` if special processing needed
3. Register category in configuration

### Adding New Languages

1. Add enum value to `LanguageCode`
2. Implement `LanguageProcessor` if special rules needed
3. Register language in configuration

### Adding New Deduplication Strategies

1. Implement `DeduplicationStrategy` protocol
2. Register in configuration
3. Configure priority order

### Adding New Normalization Rules

1. Define `NormalizationRule` in models
2. Implement rule application logic
3. Register in configuration

## Testing Strategy

### Unit Tests

| Test Type | Coverage |
|-----------|----------|
| Model creation | All models instantiate correctly |
| Default values | Default values are applied |
| Enum behavior | Enum values work as expected |
| Interface existence | All interfaces are defined |

### Test Categories

1. **Model Tests**: Verify data structures
2. **Interface Tests**: Verify protocol compliance
3. **Configuration Tests**: Verify configuration parsing
4. **Factory Tests**: Verify object creation

## Future Extensions

Potential future enhancements:

- **Weighted Keywords**: Assign priority scores to keywords
- **Temporal Keywords**: Time-based keyword generation
- **Contextual Expansion**: Expand keywords based on context
- **Custom Dictionaries**: Support user-provided keyword dictionaries
- **Keyword Validation**: Add validation rules for keyword quality
- **Export Formats**: Support multiple export formats (JSON, CSV, SQL)

## Non-Goals

This design explicitly excludes:

- Search engine integration
- Crawler implementation
- Domain validation
- Threat classification
- Database persistence
- HTTP request handling
- AI/ML components
- File system operations

These concerns will be handled by other components in the system architecture.
