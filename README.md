# Epiphan Pearl MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

MCP (Model Context Protocol) server for controlling Epiphan Pearl video capture devices through AI assistants like Claude.

> **First AI-native control interface for professional video capture hardware.**

## Features

- 🎬 **Recording Control** - Start, stop, and monitor recordings
- 📡 **Streaming Control** - Manage live streams to RTMP, SRT destinations
- 🎨 **Layout Switching** - Change scenes and video layouts
- 🏢 **Fleet Management** - Control multiple Pearl devices from one interface
- 🤖 **Natural Language** - "Start recording in Room 201" just works

## Quick Start

### Installation

```bash
pip install epiphan-mcp
```

Or from source:

```bash
git clone https://github.com/tmkipper/epiphan-mcp-server.git
cd epiphan-mcp-server
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file:

```bash
# Single device
PEARL_DEVICES=192.168.1.100
PEARL_USERNAME=admin
PEARL_PASSWORD=your_password

# Multiple devices (comma-separated)
PEARL_DEVICES=192.168.1.100,192.168.1.101,192.168.1.102
```

### Usage with Claude Code

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "epiphan-pearl": {
      "command": "python",
      "args": ["-m", "epiphan_mcp"],
      "env": {
        "PEARL_DEVICES": "192.168.1.100",
        "PEARL_USERNAME": "admin",
        "PEARL_PASSWORD": "your_password"
      }
    }
  }
}
```

Then in Claude Code:

```
You: What's the status of my Pearl device?
Claude: [Calls get_device_status] Your Pearl at 192.168.1.100 is online with
        847GB free storage. Currently not recording.

You: Start recording
Claude: [Calls start_recording] Recording started on recorder 1.

You: What's the status of all classroom devices?
Claude: [Calls get_fleet_status] Fleet "classroom-pearls" has 12 devices:
        - 11 online, 1 offline (Room 305)
        - 3 currently recording
        - 1 alert: Room 201 storage at 85%
```

## Available Tools

### Device Status
| Tool | Description |
|------|-------------|
| `get_device_status` | Get health, storage, and activity of a device |
| `list_devices` | List all configured devices |
| `get_fleet_status` | Get status of entire fleet |

### Recording
| Tool | Description |
|------|-------------|
| `start_recording` | Start recording on a device |
| `stop_recording` | Stop recording on a device |
| `get_recording_status` | Get current recording state |
| `batch_start_recording` | Start recording on multiple devices |
| `batch_stop_recording` | Stop recording on multiple devices |

### Streaming
| Tool | Description |
|------|-------------|
| `start_stream` | Start streaming to configured destination |
| `stop_stream` | Stop streaming |

### Layout
| Tool | Description |
|------|-------------|
| `switch_layout` | Change active layout/scene |

## Supported Devices

- Pearl Nano
- Pearl Nexus
- Pearl Mini
- Pearl-2

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage report
pytest --cov=src/epiphan_mcp --cov-report=term-missing

# Run tests verbosely
pytest -v

# Type checking
mypy src/

# Linting
ruff check src/
ruff format src/
```

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures, mock configurations
├── fixtures/
│   └── responses.py     # Mock API v2.0 responses
├── test_client.py       # PearlClient API tests (46 tests)
└── test_server.py       # MCP tool tests (33 tests)
```

All tests use mocked HTTP responses via `respx` - no real Pearl hardware required.

## API Reference

This server wraps Epiphan Pearl's REST API. For full API documentation:
- [Pearl REST API Swagger](https://epiphan-video.github.io/pearl_api_swagger_ui/)
- [Pearl API Guide](https://www.epiphan.com/userguides/pearl-api/)

Based on patterns from [harvard-dce/epipearl](https://github.com/harvard-dce/epipearl).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read the [contributing guidelines](CONTRIBUTING.md) first.

## Acknowledgments

- [Epiphan Video](https://www.epiphan.com/) for the Pearl product line and API
- [Harvard DCE](https://github.com/harvard-dce/epipearl) for the original Python client
- [Anthropic](https://anthropic.com/) for the MCP specification

---

**Built with ❤️ for the AV community**
