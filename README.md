# Epiphan Pearl MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-1309_passing-brightgreen.svg)](tests/)
[![Tools](https://img.shields.io/badge/MCP_tools-130-blue.svg)](src/epiphan_mcp/server.py)
[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](CHANGELOG.md)

MCP (Model Context Protocol) server for controlling Epiphan Pearl video capture devices through AI assistants like Claude.

> **Pearl Copilot: First AI-native control interface for professional video capture hardware.**

## Why Pearl Copilot?

| Traditional AV Control | Pearl Copilot |
|------------------------|---------------|
| Proprietary vendor apps | Open MCP standard |
| Button-clicking workflows | Natural language commands |
| Manual monitoring | AI-powered predictive maintenance |
| Single-device focus | Fleet-wide orchestration |
| Reactive troubleshooting | Proactive issue detection |

## Integrations

Pearl Copilot connects **11 systems** through a unified AI interface:

| Integration | Tools | Description |
|-------------|-------|-------------|
| **Pearl REST API** | 49 | Core device control — recording, streaming, layouts, system |
| **Device Discovery** | 2 | Auto-detect recorders/channels with session-scoped cache |
| **Panopto CMS** | 9 | Lecture capture — folders, sessions, S3 upload |
| **Kaltura CMS** | 9 | Video platform — categories, media, chunked upload |
| **Opencast CMS** | 9 | Open-source CMS — series, events, Dublin Core ingest |
| **YuJa CMS** | 6 | Enterprise video platform — videos, channels, signed-URL upload |
| **Echo360 CMS** | 6 | EchoVideo platform — courses, sections, media, Capture Intake upload |
| **Q-SYS AV** | 5 | Room control — JSON-RPC over TCP to Q-SYS Core |
| **YouTube Live** | 4 | Live streaming — broadcasts, RTMP credentials |
| **EC20 PTZ Camera** | 10 | Camera control — pan/tilt/zoom, presets, AI tracking |
| **Epiphan Cloud** | 12 | Fleet management — devices, commands, presets via go.epiphan.cloud |
| **AI Analysis** | 9 | Vision LLMs — scene analysis, OCR, quality checks |
| **Total** | **130** | |

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
# Pearl device(s) — comma-separated for multiple
PEARL_DEVICES=192.168.1.100
PEARL_USERNAME=admin
PEARL_PASSWORD=your_password

# Multiple devices
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

## Available Tools (113)

### Device & System (11 tools)

| Tool | Description |
|------|-------------|
| `get_device_status` | Get health, storage, and activity of a device |
| `list_devices` | List all configured devices |
| `get_fleet_status` | Get status of entire fleet with health scores |
| `fleet_health_report` | AI-summarized fleet health with recommendations |
| `get_system_info` | Hardware model, firmware, uptime, storage, CPU, temperature |
| `reboot_device` | Reboot device (requires `confirm=True`) |
| `shutdown_device` | Shutdown device (requires `confirm=True`) |
| `predict_storage_full` | Estimate hours until storage is full |
| `get_device_health_score` | Aggregate health score (0-100) |
| `single_touch_start` | Start all recorders and streams at once |
| `single_touch_stop` | Stop all recorders and streams at once |

### Recording (7 tools)

| Tool | Description |
|------|-------------|
| `start_recording` | Start recording on a device |
| `stop_recording` | Stop recording on a device |
| `get_recording_status` | Get current recording state |
| `batch_start_recording` | Start recording on multiple devices |
| `batch_stop_recording` | Stop recording on multiple devices |
| `list_recorders` | Discover available recorders |
| `list_archive_files` | Browse recorded files with pagination |

### Streaming & Publishers (9 tools)

| Tool | Description |
|------|-------------|
| `start_stream` | Start streaming to configured destination |
| `stop_stream` | Stop streaming |
| `get_stream_status` | Get current stream state and duration |
| `create_publisher` | Create RTMP/SRT/HLS streaming destination |
| `delete_publisher` | Remove stream from channel |
| `get_publisher_settings` | View stream configuration |
| `update_publisher_settings` | Modify stream settings |
| `list_publisher_types` | Available streaming protocols |
| `rename_publisher` | Change stream display name |

### Layout & Channels (6 tools)

| Tool | Description |
|------|-------------|
| `switch_layout` | Change active layout/scene |
| `list_layouts` | List available layouts for a channel |
| `list_channels` | List all video processing pipelines |
| `list_publishers` | List stream destinations on a channel |
| `get_channel_preview` | Live preview snapshot (base64) |
| `add_bookmark` | Add timestamp bookmark to recording |

### Input/Output Management (5 tools)

| Tool | Description |
|------|-------------|
| `create_network_input` | Add SRT/RTSP/NDI sources |
| `get_input_settings` | View input configuration |
| `update_input_settings` | Modify input config |
| `list_outputs` | Available HDMI/SDI output ports |
| `set_output_source` | Configure output routing |

### Event Scheduling (5 tools)

| Tool | Description |
|------|-------------|
| `get_scheduled_events` | Get CMS scheduled events |
| `create_scheduled_event` | Create ad-hoc recording event |
| `pause_event` | Pause active event |
| `resume_event` | Resume paused event |
| `get_input_preview` | Live preview from input source (base64) |

### AI-Powered Analysis (9 tools)

| Tool | Description |
|------|-------------|
| `analyze_channel_scene` | AI vision analysis of channel content |
| `extract_text_from_preview` | OCR text extraction from slides and graphics |
| `detect_layout_changes` | Monitor for scene transitions and slide advances |
| `check_video_quality` | AI assessment of lighting, focus, framing |
| `clear_change_detection_cache` | Reset change detection baseline |
| `detect_recording_issues` | AI detection of recording problems |
| `predict_storage_full` | Estimate hours until storage is full |
| `get_device_health_score` | Aggregate health score (0-100) |
| `fleet_health_report` | AI-summarized fleet health |

### Panopto CMS (9 tools)

| Tool | Description |
|------|-------------|
| `list_panopto_folders` | Browse folder hierarchy |
| `get_panopto_folder` | Get folder details |
| `create_panopto_folder` | Create new folders |
| `list_panopto_sessions` | List recordings |
| `get_panopto_session` | Get session details |
| `create_panopto_session` | Create recording placeholder |
| `upload_to_panopto` | Full S3-based upload workflow |
| `get_panopto_upload_status` | Check processing status |
| `delete_panopto_session` | Remove session |

### Kaltura CMS (9 tools)

| Tool | Description |
|------|-------------|
| `list_kaltura_categories` | Browse content folders |
| `get_kaltura_category` | Get folder details |
| `create_kaltura_category` | Create new category |
| `list_kaltura_media` | List video entries |
| `get_kaltura_media` | Get media details |
| `create_kaltura_media` | Create media placeholder |
| `upload_to_kaltura` | Chunked upload workflow (10MB chunks) |
| `schedule_kaltura_event` | Create scheduled events for Pearl auto-record |
| `get_kaltura_upload_status` | Check processing status |

### Opencast CMS (9 tools)

| Tool | Description |
|------|-------------|
| `list_opencast_series` | Browse series (courses/channels) |
| `get_opencast_series` | Get series details |
| `create_opencast_series` | Create new series |
| `list_opencast_events` | List recordings |
| `get_opencast_event` | Get event details |
| `ingest_to_opencast` | Upload video with Dublin Core metadata |
| `get_opencast_ingest_status` | Check processing workflow |
| `schedule_opencast_capture` | Schedule Pearl auto-record |
| `delete_opencast_event` | Remove event |

### Q-SYS AV Control (5 tools)

| Tool | Description |
|------|-------------|
| `list_qsys_components` | Discover Pearl components in Q-SYS design |
| `qsys_get_pearl_status` | Get recording/streaming state via Q-SYS |
| `qsys_start_recording` | Start recording through Q-SYS Core |
| `qsys_stop_recording` | Stop recording through Q-SYS Core |
| `qsys_switch_layout` | Change Pearl layout via Q-SYS |

### YouTube Live (4 tools)

| Tool | Description |
|------|-------------|
| `create_youtube_broadcast` | Create broadcast + stream, returns RTMP credentials |
| `get_youtube_broadcast_status` | Check broadcast/stream health |
| `list_youtube_broadcasts` | List user's broadcasts |
| `end_youtube_broadcast` | Transition broadcast to complete |

### EC20 PTZ Camera (10 tools)

| Tool | Description |
|------|-------------|
| `ec20_get_status` | Camera status, PTZ position, tracking state |
| `ec20_pan_tilt` | Absolute pan/tilt positioning |
| `ec20_zoom` | Zoom level control (1-36: optical + digital) |
| `ec20_goto_preset` | Recall saved camera preset |
| `ec20_save_preset` | Save current position as preset |
| `ec20_home` | Return to home position |
| `ec20_enable_tracking` | Enable AI tracking (presenter/zone/body) |
| `ec20_disable_tracking` | Disable AI tracking |
| `ec20_list_presets` | List all saved presets |
| `ec20_get_preview` | Get preview image (base64) |

### Epiphan Cloud (12 tools)

| Tool | Description |
|------|-------------|
| `cloud_get_user` | Current authenticated user profile |
| `cloud_list_devices` | List all paired devices |
| `cloud_get_device` | Device details and telemetry |
| `cloud_pair_device` | Pair new device via pairing code |
| `cloud_unpair_device` | Unpair device from cloud |
| `cloud_delete_device` | Delete device record |
| `cloud_rename_device` | Rename device |
| `cloud_run_command` | Run task on single device (recording, streaming, setprop) |
| `cloud_batch_command` | Run task on multiple devices simultaneously |
| `cloud_get_settings` | Get device configuration |
| `cloud_get_preview` | Get device preview (base64 JPEG) |
| `cloud_apply_preset` | Apply cloud/local preset to device |

## Environment Variables

### Pearl (Required)

```bash
PEARL_DEVICES=192.168.1.100,192.168.1.101
PEARL_USERNAME=admin
PEARL_PASSWORD=your_password
PEARL_USE_HTTPS=false
PEARL_TIMEOUT=30.0
PEARL_FLEET_NAME=classroom-pearls
```

### EC20 PTZ Camera (Optional)

```bash
EC20_DEVICES=192.168.1.50,192.168.1.51
EC20_USERNAME=admin
EC20_PASSWORD=your_ec20_password
EC20_USE_HTTPS=false
EC20_TIMEOUT=30.0
```

### Epiphan Cloud (Optional)

```bash
EPIPHAN_CLOUD_API_URL=https://go.epiphan.cloud/api/v2
EPIPHAN_CLOUD_API_TOKEN=your_bearer_token
```

### Panopto CMS (Optional)

```bash
PANOPTO_HOST=panopto.university.edu
PANOPTO_CLIENT_ID=your-client-id
PANOPTO_USERNAME=service@university.edu
PANOPTO_PASSWORD=your-password
PANOPTO_CLIENT_SECRET=your-client-secret  # For confidential clients
```

### Kaltura CMS (Optional)

```bash
KALTURA_SERVICE_URL=https://www.kaltura.com
KALTURA_PARTNER_ID=your_partner_id
KALTURA_APP_TOKEN_ID=your_token_id
KALTURA_APP_TOKEN=your_app_token
```

### Opencast CMS (Optional)

```bash
OPENCAST_HOST=https://opencast.university.edu
OPENCAST_USERNAME=admin
OPENCAST_PASSWORD=your_password
```

### Q-SYS AV Control (Optional)

```bash
QSYS_CORE_IP=192.168.1.200
QSYS_PORT=1710
QSYS_PIN=your_pin  # Optional
```

### YouTube Live (Optional)

```bash
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret
YOUTUBE_REFRESH_TOKEN=your_refresh_token
```

### AI Analysis (Optional)

```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
LLM_VISION_MODEL=google/gemini-2.0-flash-001
LLM_OCR_MODEL=qwen/qwen2.5-vl-72b-instruct
LLM_TEXT_MODEL=deepseek/deepseek-chat-v3-0324
LLM_MOCK_MODE=true  # For testing without API key
```

## Supported Devices

All Pearl models share the same REST API v2.0:

| Model | Form Factor | Best For |
|-------|-------------|----------|
| **Pearl Nano** | Portable, PoE+ | Field production, SRT contribution |
| **Pearl Mini** | Desktop, touchscreen | Lecture capture, small events |
| **Pearl Nexus** | 1RU rackmount | Classroom installations |
| **Pearl-2** | Desktop/rackmount | Multi-camera production |

## Platform Support

Pearl Copilot works with any MCP-compatible AI tool:

| Platform | Status | Integration |
|----------|--------|-------------|
| **Claude Code** | Ready | Native MCP |
| **Claude Desktop** | Ready | Native MCP |
| **Cursor** | Ready | MCP server |
| **Windsurf** | Ready | MCP server |
| **[SilkRoute](https://github.com/ScientiaCapital/silkroute)** (self-hosted demo) | Ready | Native MCP via `mcp_bridge` — see SilkRoute's ["Try the AV demo"](https://github.com/ScientiaCapital/silkroute#try-the-av-demo) |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage report
pytest --cov=src/epiphan_mcp --cov-report=term-missing

# Type checking
mypy src/

# Linting
ruff check src/
ruff format src/
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures, mock configurations
├── fixtures/
│   └── responses.py         # Mock API v2.0 responses
├── test_client.py           # PearlClient API tests
├── test_server.py           # MCP tool tests
├── test_llm.py              # LLM provider and analyzer tests
├── test_ai_tools.py         # AI-powered tool tests
├── test_panopto.py          # Panopto CMS integration tests
├── test_kaltura.py          # Kaltura CMS integration tests
├── test_opencast.py         # Opencast CMS integration tests
├── test_qsys.py             # Q-SYS AV control tests
├── test_youtube.py          # YouTube Live tests
├── test_ec20.py             # EC20 PTZ camera tests
├── test_cloud.py            # Epiphan Cloud tests
└── test_integration.py      # Integration tests (real hardware)
```

**754 tests** with **~95% coverage**. All tests use mocked HTTP responses — no real Pearl hardware or API keys required.

## API Reference

This server wraps Epiphan Pearl's REST API. For full API documentation:
- [Pearl REST API Swagger](https://epiphan-video.github.io/pearl_api_swagger_ui/)
- [Pearl API Guide](https://www.epiphan.com/userguides/pearl-api/)

Based on patterns from [harvard-dce/epipearl](https://github.com/harvard-dce/epipearl).

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Epiphan Video](https://www.epiphan.com/) for the Pearl product line and API
- [Harvard DCE](https://github.com/harvard-dce/epipearl) for the original Python client
- [Anthropic](https://anthropic.com/) for the MCP specification

---

**Built for the AV community**
