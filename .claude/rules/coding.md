# Coding Rules — epiphan-mcp-server

## Stack
- **Language**: Python 3.11+
- **MCP Framework**: FastMCP
- **HTTP Client**: httpx (async)
- **Data Validation**: Pydantic v2
- **Config**: pydantic-settings
- **Testing**: pytest + respx (mock HTTP)
- **Linting**: ruff, mypy (strict)
- **Package**: hatchling build system, installed via `pip install -e ".[dev]"`

## Key Patterns
- All MCP tools are async functions decorated with `@mcp.tool()`
- Tool implementations live in `src/epiphan_mcp/tools/`
- External integrations (Panopto, Kaltura, Q-SYS, YouTube, EC20, Cloud) live in `src/epiphan_mcp/integrations/`
- Pearl REST API client is `src/epiphan_mcp/client.py`
- All config via `pydantic-settings` — never hardcode credentials
- Mock Pearl API in tests using `respx` or `pytest-httpx`
- Integration tests (require hardware) marked with `@pytest.mark.integration`

## Rules
- **No OpenAI** — Epiphan is an OpenAI *customer*, not a technology partner
- Type hints required on all functions
- Async-first: use `asyncio` / `httpx.AsyncClient` throughout
- All secrets in `.env` only — never in source

## Testing
- Unit tests: `pytest` (618 tests, no hardware needed)
- Integration tests: `pytest -m integration` (requires `PEARL_TEST_IP` in `.env`)
- Type check: `mypy src/`
- Lint: `ruff check src/`
