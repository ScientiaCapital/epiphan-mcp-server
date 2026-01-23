# Contributing to Epiphan MCP Server

Thank you for your interest in contributing to the Epiphan MCP Server project! This document provides guidelines for contributing.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- An Epiphan Pearl device (optional, for integration testing)

### Getting Started

1. **Clone the repository**

   ```bash
   git clone https://github.com/tmkipper/epiphan-mcp-server.git
   cd epiphan-mcp-server
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**

   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your Pearl device settings
   ```

## Code Style

This project uses:

- **ruff** for linting and formatting
- **mypy** for type checking
- **Python 3.11+** type hints throughout

### Running Checks

```bash
# Format code
ruff format src/ tests/

# Run linter
ruff check src/ tests/

# Type checking
mypy src/

# Run all checks before committing
ruff format src/ tests/ && ruff check src/ tests/ && mypy src/
```

## Testing

### Running Tests

```bash
# Run all unit tests
pytest

# Run with coverage
pytest --cov=src/epiphan_mcp --cov-report=term-missing

# Run integration tests (requires real Pearl hardware)
pytest -m integration
```

### Writing Tests

- Use `pytest` and `pytest-asyncio` for async tests
- Mock HTTP responses using `respx`
- Place test fixtures in `tests/fixtures/`
- Name test files `test_*.py`
- Name test functions `test_*`

## Pull Request Process

1. **Fork the repository** and create your branch from `main`

2. **Make your changes**
   - Follow the code style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Run the test suite**

   ```bash
   pytest
   ```

4. **Ensure code quality**

   ```bash
   ruff format src/ tests/
   ruff check src/ tests/
   mypy src/
   ```

5. **Create a Pull Request**
   - Provide a clear description of the changes
   - Reference any related issues
   - Ensure CI checks pass

## Commit Message Convention

Use conventional commit messages:

```
feat: Add new feature
fix: Bug fix
docs: Documentation only
refactor: Code change that neither fixes a bug nor adds a feature
test: Adding missing tests
chore: Changes to build process or auxiliary tools
```

Examples:

```
feat: Add batch streaming control
fix: Handle timeout in get_device_status
docs: Update API reference in README
test: Add tests for layout switching
```

## Architecture Overview

```
src/epiphan_mcp/
├── __init__.py       # Package initialization
├── __main__.py       # CLI entry point
├── server.py         # FastMCP server and tool definitions
├── client.py         # Pearl REST API v2.0 client
├── models.py         # Pydantic models
├── config.py         # Configuration handling
└── tools/            # AI-powered tools (optional features)
```

### Key Components

- **PearlClient**: Async HTTP client wrapping Pearl REST API v2.0
- **FastMCP server**: MCP protocol implementation for Claude integration
- **Pydantic models**: Type-safe API response handling

## Important Notes

### No OpenAI

This project does not use OpenAI APIs. Use Anthropic Claude for AI features.

### API Keys

Never commit API keys or credentials. Use `.env` files and `pydantic-settings`.

### Testing Without Hardware

All unit tests run without real Pearl hardware using mocked HTTP responses.

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones

Thank you for contributing!
