# Epiphan Pearl MCP Server

## Project Overview

MCP (Model Context Protocol) server that wraps Epiphan Pearl's **REST API v2.0**, enabling AI assistants like Claude to control Pearl video capture devices through natural language.

**Goal**: First-to-market AI-native control for professional AV hardware.

---

## Critical Rules

### LLM Rules (NO OPENAI)
- **NO OpenAI** models or APIs anywhere in this project
- Use Anthropic Claude for any AI features
- Use local/edge models if needed for processing

**Note**: OpenAI is an Epiphan customer (used Pearl for "12 Days of OpenAI" streaming), not a technology partner. Epiphan products do not use OpenAI APIs.

### API Keys
- **NEVER hardcode** API keys or credentials
- All secrets go in `.env` file only
- Use `pydantic-settings` for environment loading

### Code Style
- Python 3.11+ with type hints everywhere
- Async-first (asyncio, httpx)
- FastMCP for MCP server implementation
- Pydantic v2 for data validation
- pytest for testing

---

## Architecture

```
epiphan-mcp-server/
├── src/
│   └── epiphan_mcp/
│       ├── __init__.py
│       ├── __main__.py       # Entry point
│       ├── server.py         # FastMCP server definition
│       ├── client.py         # Pearl REST API v2.0 client
│       ├── models.py         # Pydantic models
│       └── config.py         # Configuration (pydantic-settings)
├── tests/
│   ├── conftest.py
│   └── test_client.py
├── docs/
│   ├── PRD.md               # Product Requirements + GTM
│   └── PRP.md               # Project Plan
├── .env.example
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

---

## Pearl REST API v2.0 Reference

### Base URL
```
http://<pearl-ip>/api/v2.0
https://<pearl-ip>/api/v2.0  (if HTTPS enabled)
```

### Authentication
- **HTTP Basic Auth** with admin account (required since firmware 4.14.2)
- All API calls require authentication

### Response Format
All JSON responses include a top-level `status` field:
- `"ok"` - Success, result in `result` field
- `"error"` - Error, details in `message` field
- `"busy"` - Resource busy, retry later

### API Categories

| Category | Description |
|----------|-------------|
| **Recorders** | Recording control and status |
| **Channels** | Channel configuration and layouts |
| **Publishers** | Streaming control (RTMP, SRT, etc.) |
| **Inputs** | Video/audio input sources |
| **Events** | Scheduled recording (Kaltura/Panopto/Opencast) |
| **System** | Device control, firmware, storage |
| **AFU** | Automatic File Upload |
| **Single Touch** | Batch start/stop all |

### Key Endpoints

#### Recorders
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/recorders` | GET | List all recorders |
| `/recorders/status` | GET | Status of all recorders |
| `/recorders/control/start` | POST | Start all recorders |
| `/recorders/control/stop` | POST | Stop all recorders |
| `/recorders/{rid}/control/start` | POST | Start specific recorder |
| `/recorders/{rid}/control/stop` | POST | Stop specific recorder |
| `/recorders/{rid}/status` | GET | Get recorder status |
| `/recorders/{rid}/archive/files` | GET | List recorded files |

#### Channels
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/channels` | GET | List all channels |
| `/channels/{cid}/preview` | GET | Get preview image (binary) |
| `/channels/{cid}/layouts/active` | PUT | Switch layout |
| `/channels/{cid}/bookmarks` | POST | Add bookmark to recording |

#### Publishers (Streaming)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/channels/{cid}/publishers` | GET | List publishers (streams) |
| `/channels/{cid}/publishers/control/start` | POST | Start all streams |
| `/channels/{cid}/publishers/control/stop` | POST | Stop all streams |
| `/channels/{cid}/publishers/{pid}/control/start` | POST | Start specific stream |
| `/channels/{cid}/publishers/{pid}/control/stop` | POST | Stop specific stream |
| `/channels/{cid}/publishers/{pid}/status` | GET | Get stream status |

#### Events (CMS Integration)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/schedule/events` | GET | List scheduled events |
| `/schedule/events` | POST | Create ad-hoc event |
| `/schedule/events/{id}/control/start` | POST | Force start event |
| `/schedule/events/{id}/control/stop` | POST | Force stop event |

#### System
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/device` | GET | Device identity info |
| `/storages` | GET | Storage information |
| `/inputs` | GET | List input sources |
| `/system/control/reboot` | POST | Reboot device |
| `/system/control/shutdown` | POST | Shutdown device |

#### Single Touch Control
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/singletouch/control/start` | POST | Start all recorders + streams |
| `/singletouch/control/stop` | POST | Stop all recorders + streams |

### Full API Documentation
- **OpenAPI Spec**: https://epiphan-video.github.io/pearl_api_swagger_ui/api/v2.0/openapi.yml
- **Swagger UI**: https://epiphan-video.github.io/pearl_api_swagger_ui/
- **API Guide**: https://www.epiphan.com/userguides/pearl-api/Default.htm

---

## MCP Tools Implemented

### Device & System
```python
@mcp.tool()
async def get_device_status(device_id: str) -> dict: ...

@mcp.tool()
async def list_devices() -> dict: ...

@mcp.tool()
async def get_fleet_status() -> dict: ...
```

### Recording Control
```python
@mcp.tool()
async def start_recording(device_id: str, recorder: str) -> dict: ...

@mcp.tool()
async def stop_recording(device_id: str, recorder: str) -> dict: ...

@mcp.tool()
async def get_recording_status(device_id: str, recorder: str) -> dict: ...

@mcp.tool()
async def batch_start_recording(device_ids: str = "all") -> dict: ...

@mcp.tool()
async def batch_stop_recording(device_ids: str = "all") -> dict: ...
```

### Streaming Control
```python
@mcp.tool()
async def start_stream(device_id: str, channel: str, publisher: str) -> dict: ...

@mcp.tool()
async def stop_stream(device_id: str, channel: str, publisher: str) -> dict: ...
```

### Layout Control
```python
@mcp.tool()
async def switch_layout(device_id: str, channel: str, layout_id: str) -> dict: ...
```

### Publisher Management (NEW - 2026-01-27)
```python
@mcp.tool()
async def create_publisher(device_id: str, channel: int, name: str, publisher_type: str, ...) -> dict: ...

@mcp.tool()
async def delete_publisher(device_id: str, channel: int, publisher: str) -> dict: ...

@mcp.tool()
async def get_publisher_settings(device_id: str, channel: int, publisher: str) -> dict: ...

@mcp.tool()
async def update_publisher_settings(device_id: str, channel: int, publisher: str, ...) -> dict: ...

@mcp.tool()
async def list_publisher_types(device_id: str, channel: int) -> dict: ...

@mcp.tool()
async def rename_publisher(device_id: str, channel: int, publisher: str, name: str) -> dict: ...
```

### Input/Output Management (NEW - 2026-01-27)
```python
@mcp.tool()
async def create_network_input(device_id: str, name: str, input_type: str, ...) -> dict: ...

@mcp.tool()
async def get_input_settings(device_id: str, input_id: str) -> dict: ...

@mcp.tool()
async def update_input_settings(device_id: str, input_id: str, ...) -> dict: ...

@mcp.tool()
async def list_outputs(device_id: str) -> dict: ...

@mcp.tool()
async def set_output_source(device_id: str, output_id: str, source_channel: int) -> dict: ...
```

### Event Control (NEW - 2026-01-27)
```python
@mcp.tool()
async def create_scheduled_event(device_id: str, name: str, ...) -> dict: ...

@mcp.tool()
async def pause_event(device_id: str, event_id: str) -> dict: ...

@mcp.tool()
async def resume_event(device_id: str, event_id: str) -> dict: ...
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

# Authentication (REQUIRED since firmware 4.14.2)
PEARL_USERNAME=admin
PEARL_PASSWORD=your_password

# Connection settings
PEARL_USE_HTTPS=false
PEARL_TIMEOUT=30.0
PEARL_VERIFY_SSL=true

# Fleet management (optional)
PEARL_FLEET_NAME=classroom-pearls

# Testing
PEARL_TEST_IP=192.168.1.100
```

---

## Related Resources

### Epiphan Documentation
- [Pearl REST API v2.0 Swagger](https://epiphan-video.github.io/pearl_api_swagger_ui/)
- [Pearl System API Guide](https://www.epiphan.com/userguides/pearl-api/)
- [Firmware Release Notes](https://www.epiphan.com/userguides/pearl-2/Content/startHere/releaseNotes/whatsNew-details.htm)

### MCP Resources
- [MCP Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Claude MCP Integration](https://docs.anthropic.com/en/docs/agents-and-tools/mcp)

### Reference Implementations
- [harvard-dce/epipearl](https://github.com/harvard-dce/epipearl) - Python client reference

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
- [x] Connect to single Pearl device via v2.0 API
- [x] Get device status
- [x] Start/stop recording
- [x] Works with Claude Code

### v0.2 (Week 2)
- [x] Multi-device support
- [x] Streaming control (publishers)
- [x] Layout switching
- [x] Fleet status

### v1.0 (Month 1)
- [x] Full fleet management
- [x] Batch operations
- [x] CMS event control (Kaltura/Panopto/Opencast)
- [x] AFU status monitoring
- [ ] Published to PyPI
- [x] GitHub Actions CI

### v1.1 (API Expansion - 2026-01-27)
- [x] DELETE/PATCH HTTP methods
- [x] Publisher CRUD (6 tools)
- [x] Input/Output management (5 tools)
- [x] Event control: create/pause/resume (3 tools)
- [x] Security: audit logging, concurrency limits, image validation
- [x] **46 total MCP tools** (was 32)
