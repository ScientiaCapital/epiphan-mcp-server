# Epiphan Pearl MCP Server

MCP (Model Context Protocol) server wrapping Epiphan Pearl's REST API v2.0, enabling AI assistants to control Pearl video capture devices through natural language. 113 MCP tools across 9 integrations.

## Stack

- **Language**: Python 3.11+
- **MCP Framework**: FastMCP
- **HTTP**: httpx (async)
- **Validation**: Pydantic v2
- **Config**: pydantic-settings
- **Testing**: pytest + respx (618 tests)
- **Linting**: ruff, mypy (strict)
- **Build**: hatchling (`pip install -e ".[dev]"`)

## Directory Structure

```
src/epiphan_mcp/
├── server.py         # FastMCP server (113 MCP tools)
├── client.py         # Pearl REST API v2.0 client
├── models.py         # Pydantic models
├── config.py         # pydantic-settings config
├── integrations/     # Panopto, Kaltura, Opencast, Q-SYS, YouTube, EC20, Cloud
└── tools/            # MCP tool implementations
tests/                # 618 tests (unit + integration)
```

## Key Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run MCP server (stdio mode for Claude)
python -m epiphan_mcp

# Tests, type check, lint
pytest
mypy src/
ruff check src/
```

## Environment Variables

```bash
PEARL_DEVICES=192.168.1.100,192.168.1.101   # comma-separated
PEARL_USERNAME=admin
PEARL_PASSWORD=your_password
PEARL_USE_HTTPS=false
PEARL_TIMEOUT=30.0
PEARL_TEST_IP=192.168.1.100   # for integration tests
EC20_DEVICES=192.168.1.50
EC20_USERNAME=admin
EC20_PASSWORD=your_ec20_password
```

## Rules

- **No OpenAI** — Epiphan is an OpenAI customer, not a technology partner
- Type hints required everywhere; async-first (asyncio + httpx.AsyncClient)
- All secrets in `.env` only — never hardcoded
- Integration tests (require hardware): `pytest -m integration`

## Pearl REST API

- Base URL: `http://<pearl-ip>/api/v2.0`
- Auth: HTTP Basic Auth (required since firmware 4.14.2)
- Swagger: https://epiphan-video.github.io/pearl_api_swagger_ui/
- Full guide: https://www.epiphan.com/userguides/pearl-api/
