# Kancell Shield v3 Architecture

## Overview

This document provides a high-level overview of the Kancell Shield v3 architecture.

## Project Structure

```
kancell-shield-v3/
├── .github/workflows/     # CI/CD pipelines
├── src/                   # Main source code
├── tests/
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── config/                # Configuration files
└── data/                  # Data files
```

## Technology Stack

- **Language:** Python 3.12+
- **Testing:** pytest
- **Linting:** ruff
- **Formatting:** black
- **Type Checking:** mypy

## Design Principles

1. **Simplicity:** Keep the codebase simple and maintainable
2. **Modularity:** Separate concerns into distinct modules
3. **Testability:** Write testable code with clear interfaces
4. **Documentation:** Document all public APIs and key decisions
