# Epiphan Pearl MCP Server

## Project Overview

MCP (Model Context Protocol) server that wraps Epiphan Pearl's REST API, enabling AI assistants like Claude to control Pearl video capture devices through natural language.

**Goal**: First-to-market AI-native control for professional AV hardware.

---

## Critical Rules

### LLM Rules (NO OPENAI)
- **NO OpenAI** models or APIs anywhere in this project
- Use Anthropic Claude for any AI features
- Use local/edge models if needed for processing

### API Keys
- **NEVER hardcode** API keys or credentials
- All secrets go in `.env` file only
- Use `python-dotenv` for environment loading

### Code Style
- Python 3.11+ with type hints everywhere
- Async-first (asyncio, httpx)
- FastMCP for MCP server implementation
- Pydantic for data validation
- pytest for testing

---

## Architecture

```
epiphan-mcp-server/
├── src/
│   └── epiphan_mcp/
│       ├── __init__.py
│       ├── server.py          # FastMCP server definition
│       ├── client.py          # Pearl REST API client
│       ├── tools/             # MCP tool implementations
│       │   ├── __init__.py
│       │   ├── device.py      # Device discovery & status
│       │   ├── recording.py   # Recording control
│       │   ├── streaming.py   # Streaming control
│       │   └── fleet.py       # Fleet management
│       ├── models.py          # Pydantic models
│       └── config.py          # Configuration
├── tests/
│   ├── conftest.py
│   ├── test_client.py
│   └── test_tools/
├── examples/
│   └── basic_usage.py
├── docs/
│   ├── PRD.md                 # Product Requirements
│   └── PRP.md                 # Project Plan
├── .env.example
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

---

## Pearl API Reference

### Base URL
```
http://<pearl-ip>/api
https://<pearl-ip>/api  (if HTTPS enabled)
```

### Authentication
- HTTP Basic Auth or API key
- Credentials stored in `.env`

### Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/admin/channel{n}/status` | GET | Channel status |
| `/admin/channel{n}/recording/start` | POST | Start recording |
| `/admin/channel{n}/recording/stop` | POST | Stop recording |
| `/admin/channel{n}/streaming/start` | POST | Start streaming |
| `/admin/channel{n}/streaming/stop` | POST | Stop streaming |
| `/admin/channel{n}/layout/set` | POST | Change layout |
| `/admin/sources` | GET | List input sources |
| `/admin/sysstat` | GET | System status |
| `/admin/mediafiles` | GET | List recordings |

### Full API Documentation
- [Epiphan Pearl API Guide (PDF)](https://www.epiphan.com/userguides/pdfs/Epiphan-Pearl-API-Guide.pdf)
- [Pearl API User Guide](https://www.epiphan.com/userguides/pearl-api/Content/startHere/startHere-about-apiGuide.htm)

---

## MCP Tools to Implement

### Phase 1: Core Tools (MVP)
```python
# Device Discovery & Status
@mcp.tool()
async def list_devices() -> list[Device]: ...

@mcp.tool()
async def get_device_status(device_id: str) -> DeviceStatus: ...

# Recording Control
@mcp.tool()
async def start_recording(device_id: str, channel: int = 1) -> RecordingResult: ...

@mcp.tool()
async def stop_recording(device_id: str, channel: int = 1) -> RecordingResult: ...

@mcp.tool()
async def get_recording_status(device_id: str) -> RecordingStatus: ...
```

### Phase 2: Streaming & Layout
```python
# Streaming Control
@mcp.tool()
async def start_stream(device_id: str, channel: int = 1) -> StreamResult: ...

@mcp.tool()
async def stop_stream(device_id: str, channel: int = 1) -> StreamResult: ...

# Layout Control
@mcp.tool()
async def list_layouts(device_id: str) -> list[Layout]: ...

@mcp.tool()
async def switch_layout(device_id: str, layout_id: str) -> LayoutResult: ...
```

### Phase 3: Fleet Management
```python
# Fleet Operations
@mcp.tool()
async def get_fleet_status() -> FleetStatus: ...

@mcp.tool()
async def batch_start_recording(device_ids: list[str]) -> BatchResult: ...

@mcp.tool()
async def get_fleet_alerts() -> list[Alert]: ...
```

---

## Development Commands

```bash
# Setup
cd /Users/tmkipper/Desktop/tk_projects/epiphan-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run MCP server (stdio mode for Claude)
python -m epiphan_mcp

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
ruff format src/
```

---

## Testing Strategy

### Without Real Hardware
- Mock Pearl API responses using `respx` or `pytest-httpx`
- Use recorded API responses as fixtures
- Test tool logic independently from API

### With Real Hardware (Integration)
- Set `PEARL_TEST_IP` in `.env`
- Mark integration tests with `@pytest.mark.integration`
- Run with `pytest -m integration`

---

## Environment Variables

```bash
# .env.example

# Pearl device(s) - comma-separated for multiple
PEARL_DEVICES=192.168.1.100,192.168.1.101

# Authentication
PEARL_USERNAME=admin
PEARL_PASSWORD=your_password

# Optional: API key auth instead of basic auth
# PEARL_API_KEY=your_api_key

# Fleet management (optional)
PEARL_FLEET_NAME=classroom-pearls

# Testing
PEARL_TEST_IP=192.168.1.100
```

---

## Related Resources

### Epiphan Documentation
- [Pearl API Guide](https://www.epiphan.com/userguides/pearl-api/)
- [Pearl-2 User Guide](https://www.epiphan.com/userguides/pearl-2/)
- [Pearl Mini User Guide](https://www.epiphan.com/userguides/pearl-mini/)

### MCP Resources
- [MCP Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Claude MCP Integration](https://docs.anthropic.com/en/docs/agents-and-tools/mcp)

### Tim's Related Projects
- `research-hub` - Research agents (this project's origin)
- `epiphan-bdr-playbook` - Sales playbook with Blue Ocean analysis
- `netzero-expert` - MCP server orchestration reference (18 servers)

---

## Commit Conventions

```
feat: Add new feature
fix: Bug fix
docs: Documentation only
refactor: Code change that neither fixes a bug nor adds a feature
test: Adding missing tests
chore: Changes to build process or auxiliary tools
```

---

## Success Criteria

### MVP (Week 1)
- [ ] Connect to single Pearl device
- [ ] Get device status
- [ ] Start/stop recording
- [ ] Works with Claude Code

### v0.2 (Week 2)
- [ ] Multi-device support
- [ ] Streaming control
- [ ] Layout switching
- [ ] Fleet status

### v1.0 (Month 1)
- [ ] Full fleet management
- [ ] Batch operations
- [ ] Alert monitoring
- [ ] Published to PyPI
- [ ] GitHub Actions CI
