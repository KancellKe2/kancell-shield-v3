# Contributing to Kancell Shield v3

Thank you for your interest in contributing to Kancell Shield v3!

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Install dependencies: `pip install -r requirements.txt`
4. Make your changes
5. Run tests: `python -m pytest`
6. Submit a pull request

## Development Guidelines

- Follow the existing code style
- Write tests for new features
- Run linting checks before submitting
- Keep commits focused and atomic

## Code Style

This project uses:
- **black** for formatting
- **ruff** for linting
- **mypy** for type checking

Run all checks with:
```bash
python -m black .
python -m ruff check .
python -m mypy src
```

## Testing

All tests should pass before submitting a pull request:
```bash
python -m pytest
```

## Questions

If you have questions, please open an issue for discussion.
