# Project Requirements Plan (PRP)
# Epiphan Pearl MCP Server

**Version**: 1.0
**Author**: Tim Kipper
**Date**: January 22, 2026
**Status**: SUPERSEDED — written at the 113-tool/674-test baseline; the project has
since grown to 130 tools / 1,376 tests. Kept for historical provenance only. See
`README.md` and `CLAUDE.md` for current scope.

---

## Project Overview

### Objective
Build an MCP (Model Context Protocol) server that wraps Epiphan Pearl's REST API, enabling AI assistants to control video capture hardware through natural language.

### Success Criteria
1. ✅ Connect to Pearl device and retrieve status
2. ✅ Start/stop recording via MCP tools
3. ✅ Works with Claude Code and Claude Desktop
4. ✅ Published to GitHub with documentation
5. ✅ At least 1 beta tester using in production

---

## Phase 1: MVP (Week 1-2)

### Goals
- Single device control
- Basic recording operations
- Works with Claude Code

### Deliverables

#### 1.1 Project Setup (Day 1)
- [x] Create repository structure
- [ ] Set up pyproject.toml with dependencies
- [ ] Configure development environment
- [ ] Create .env.example

#### 1.2 Pearl API Client (Days 2-3)
- [ ] Implement async HTTP client using httpx
- [ ] Add authentication (Basic Auth)
- [ ] Create Pydantic models for responses
- [ ] Implement core endpoints:
  - [ ] `GET /admin/sysstat` - System status
  - [ ] `GET /admin/channel{N}/get_params.cgi` - Channel params
  - [ ] `POST /admin/channelm{N}/set_params.cgi` - Recorder control
  - [ ] `GET /admin/sources` - Input sources

#### 1.3 MCP Server Foundation (Days 4-5)
- [ ] Set up FastMCP server
- [ ] Implement device tools:
  - [ ] `get_device_status` - Health, storage, uptime
  - [ ] `list_channels` - All channels and states
- [ ] Implement recording tools:
  - [ ] `start_recording` - Begin recording
  - [ ] `stop_recording` - Stop recording
  - [ ] `get_recording_status` - Current state

#### 1.4 Testing & Documentation (Days 6-7)
- [ ] Unit tests with mocked API responses
- [ ] Integration test script (optional hardware)
- [ ] README with quick start
- [ ] Example usage scripts

### Technical Specifications

```yaml
dependencies:
  runtime:
    - python: ">=3.11"
    - fastmcp: ">=0.1.0"
    - httpx: ">=0.25.0"
    - pydantic: ">=2.0.0"
    - python-dotenv: ">=1.0.0"

  development:
    - pytest: ">=7.0.0"
    - pytest-asyncio: ">=0.21.0"
    - respx: ">=0.20.0"  # HTTP mocking
    - mypy: ">=1.0.0"
    - ruff: ">=0.1.0"

file_structure:
  src/epiphan_mcp/:
    __init__.py: "Package init, version"
    __main__.py: "Entry point for python -m"
    server.py: "FastMCP server definition"
    client.py: "Pearl REST API client"
    config.py: "Configuration from env"
    models.py: "Pydantic models"
    tools/:
      __init__.py: "Tool exports"
      device.py: "Device status tools"
      recording.py: "Recording control tools"
```

### API Client Design

```python
# src/epiphan_mcp/client.py

from typing import Optional
import httpx
from pydantic import BaseModel

class PearlClient:
    """Async client for Epiphan Pearl REST API."""

    def __init__(
        self,
        host: str,
        username: str = "admin",
        password: str = "",
        use_https: bool = False,
        timeout: float = 30.0,
    ):
        self.base_url = f"{'https' if use_https else 'http'}://{host}"
        self.auth = (username, password)
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=self.auth,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def get_system_status(self) -> SystemStatus:
        """Get system status including storage and uptime."""
        response = await self._client.get("/admin/sysstat")
        response.raise_for_status()
        return SystemStatus.model_validate(response.json())

    async def get_channel_params(self, channel: int) -> ChannelParams:
        """Get parameters for a channel."""
        response = await self._client.get(
            f"/admin/channel{channel}/get_params.cgi",
            params={"rec_enabled": "", "publish_type": "", "framesize": ""}
        )
        response.raise_for_status()
        return ChannelParams.model_validate(response.json())

    async def set_recorder_params(
        self,
        recorder: int,
        params: dict
    ) -> RecorderResponse:
        """Set parameters for a recorder (channelm)."""
        response = await self._client.post(
            f"/admin/channelm{recorder}/set_params.cgi",
            params=params
        )
        response.raise_for_status()
        return RecorderResponse.model_validate(response.json())

    async def start_recording(self, recorder: int = 1) -> RecorderResponse:
        """Start recording on specified recorder."""
        return await self.set_recorder_params(recorder, {"rec_enabled": "on"})

    async def stop_recording(self, recorder: int = 1) -> RecorderResponse:
        """Stop recording on specified recorder."""
        return await self.set_recorder_params(recorder, {"rec_enabled": ""})
```

### MCP Server Design

```python
# src/epiphan_mcp/server.py

from fastmcp import FastMCP
from .client import PearlClient
from .config import settings

mcp = FastMCP("epiphan-pearl")

@mcp.tool()
async def get_device_status(device_id: str = "default") -> dict:
    """
    Get the current status of an Epiphan Pearl device.

    Args:
        device_id: Device identifier (IP or hostname). Use "default" for configured device.

    Returns:
        Device status including storage, uptime, and active operations.
    """
    host = settings.get_device_host(device_id)
    async with PearlClient(host, settings.username, settings.password) as client:
        status = await client.get_system_status()
        return status.model_dump()

@mcp.tool()
async def start_recording(
    device_id: str = "default",
    recorder: int = 1
) -> dict:
    """
    Start recording on an Epiphan Pearl device.

    Args:
        device_id: Device identifier (IP or hostname). Use "default" for configured device.
        recorder: Recorder number (1-based). Default is 1.

    Returns:
        Recording start confirmation with status.
    """
    host = settings.get_device_host(device_id)
    async with PearlClient(host, settings.username, settings.password) as client:
        result = await client.start_recording(recorder)
        return {
            "success": True,
            "device": host,
            "recorder": recorder,
            "status": "recording",
            "details": result.model_dump()
        }

@mcp.tool()
async def stop_recording(
    device_id: str = "default",
    recorder: int = 1
) -> dict:
    """
    Stop recording on an Epiphan Pearl device.

    Args:
        device_id: Device identifier (IP or hostname). Use "default" for configured device.
        recorder: Recorder number (1-based). Default is 1.

    Returns:
        Recording stop confirmation with status.
    """
    host = settings.get_device_host(device_id)
    async with PearlClient(host, settings.username, settings.password) as client:
        result = await client.stop_recording(recorder)
        return {
            "success": True,
            "device": host,
            "recorder": recorder,
            "status": "stopped",
            "details": result.model_dump()
        }
```

---

## Phase 2: Streaming & Layout (Week 3-4)

### Goals
- Streaming control (RTMP, SRT)
- Layout/scene switching
- Source management

### Deliverables

#### 2.1 Streaming Tools
- [ ] `start_stream` - Begin streaming to destination
- [ ] `stop_stream` - Stop streaming
- [ ] `get_stream_status` - Current stream health
- [ ] `configure_stream` - Set RTMP/SRT destination

#### 2.2 Layout Tools
- [ ] `list_layouts` - Available layouts
- [ ] `switch_layout` - Change active layout
- [ ] `get_current_layout` - Active layout info

#### 2.3 Source Tools
- [ ] `list_sources` - Input sources
- [ ] `get_source_status` - Source health/signal

---

## Phase 3: Fleet Management (Week 5-8)

### Goals
- Multi-device discovery
- Batch operations
- Monitoring and alerts

### Deliverables

#### 3.1 Device Discovery
- [ ] `discover_devices` - Network scan for Pearls
- [ ] `register_device` - Add device to fleet
- [ ] `list_fleet` - All registered devices

#### 3.2 Fleet Operations
- [ ] `get_fleet_status` - Status of all devices
- [ ] `batch_start_recording` - Start on multiple devices
- [ ] `batch_stop_recording` - Stop on multiple devices
- [ ] `batch_command` - Execute any command on fleet

#### 3.3 Monitoring
- [ ] `get_alerts` - Devices with issues
- [ ] `get_storage_report` - Storage across fleet
- [ ] `get_health_report` - Overall fleet health

---

## Phase 4: Intelligence & Integrations (Month 2-3)

### Goals
- Calendar integration for scheduling
- CMS integration (Panopto, Kaltura)
- Intelligent automation

### Deliverables

#### 4.1 Scheduling
- [ ] `schedule_recording` - Future recording
- [ ] `get_schedule` - Upcoming recordings
- [ ] `cancel_scheduled` - Cancel future recording

#### 4.2 CMS Integration
- [ ] `upload_to_panopto` - Push recording to Panopto
- [ ] `upload_to_kaltura` - Push to Kaltura
- [ ] `get_upload_status` - Upload progress

#### 4.3 Automation
- [ ] Webhook support for events
- [ ] Auto-recovery from failures
- [ ] Intelligent error reporting

---

## Technical Requirements

### Development Environment

```bash
# Required tools
python >= 3.11
git
uv (recommended) or pip

# Setup commands
cd /Users/tmkipper/Desktop/tk_projects/epiphan-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Testing Strategy

```yaml
unit_tests:
  framework: pytest
  mocking: respx (for httpx)
  coverage_target: 80%

integration_tests:
  marker: "@pytest.mark.integration"
  requires: "Real Pearl device or simulator"
  env_var: "PEARL_TEST_IP"

test_commands:
  unit: "pytest tests/ -v"
  integration: "pytest tests/ -v -m integration"
  coverage: "pytest --cov=src/epiphan_mcp"
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: ruff check src/
      - run: mypy src/
      - run: pytest tests/ -v

  publish:
    needs: test
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install build twine
      - run: python -m build
      - run: twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Pearl API changes | Medium | High | Abstract client, version pin |
| No hardware for testing | High | Medium | Use mocks, get loaner from Epiphan |
| Scope creep | Medium | Medium | Strict phase boundaries |
| Low adoption | Medium | Low | Focus on community, content |

---

## Definition of Done

### Per Feature
- [ ] Code complete with type hints
- [ ] Unit tests passing (80%+ coverage)
- [ ] Integration test (if applicable)
- [ ] Documentation updated
- [ ] PR reviewed and merged

### Per Phase
- [ ] All features complete
- [ ] README updated with new capabilities
- [ ] CHANGELOG entry added
- [ ] Version bumped
- [ ] GitHub release created

### For v1.0
- [ ] All Phase 1-3 features complete
- [ ] Full test coverage
- [ ] Published to PyPI
- [ ] 3+ beta testers validated
- [ ] Demo video created

---

## Timeline

```
Week 1-2:  Phase 1 MVP
           ├── Day 1-2: Project setup, client foundation
           ├── Day 3-5: MCP server, core tools
           └── Day 6-7: Testing, documentation, release v0.1.0

Week 3-4:  Phase 2 Streaming & Layout
           ├── Streaming tools
           ├── Layout tools
           └── Release v0.2.0

Week 5-8:  Phase 3 Fleet Management
           ├── Discovery and registration
           ├── Batch operations
           ├── Monitoring
           └── Release v0.3.0

Month 2-3: Phase 4 Intelligence
           ├── Scheduling
           ├── CMS integrations
           └── Release v1.0.0
```

---

## Appendix: Claude Code Prompt to Start

```
Open this project and help me build the Epiphan Pearl MCP Server:

/Users/tmkipper/Desktop/tk_projects/epiphan-mcp-server

Start by reading CLAUDE.md, then docs/PRD.md and docs/PRP.md to understand
the full context.

Begin with Phase 1 MVP:
1. Set up pyproject.toml with all dependencies
2. Create the Pearl API client (src/epiphan_mcp/client.py)
3. Implement the FastMCP server (src/epiphan_mcp/server.py)
4. Add the initial MCP tools: get_device_status, start_recording, stop_recording

Reference the Harvard DCE epipearl library for API patterns:
https://github.com/harvard-dce/epipearl

Use async/await throughout with httpx and Pydantic v2.
```

---

**Document Status**: Complete
**Owner**: Tim Kipper
