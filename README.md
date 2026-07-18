# Epiphan Pearl MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-1376-brightgreen.svg)](tests/)
[![Tools](https://img.shields.io/badge/MCP_tools-130-blue.svg)](src/epiphan_mcp/server.py)
[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](CHANGELOG.md)

MCP (Model Context Protocol) server for controlling Epiphan Pearl video capture devices through AI assistants like Claude.

> **Pearl Copilot: an AI-native control interface for professional video capture hardware.**

## Why Pearl Copilot?

| Traditional AV Control | Pearl Copilot |
|------------------------|---------------|
| Proprietary vendor apps | Open MCP standard |
| Button-clicking workflows | Natural language commands |
| Manual monitoring | Health scoring + predictive checks |
| Single-device focus | Fleet-wide orchestration |
| Reactive troubleshooting | Proactive issue detection |

## Integrations

Pearl Copilot exposes **130 tools** across **11 integration groups**:

| Integration | Tools | Live-validation status |
|-------------|-------|------------------------|
| **Pearl REST API** (core + discovery) | 54 | Unit-tested (mocked); hardware integration tests available — see below |
| **Epiphan Cloud** | 12 | Unit-tested (mocked) against `go.epiphan.cloud` API v2 |
| **AI Analysis** (vision) | 6 | Mock provider by default; OpenRouter optional — see note |
| **Panopto CMS** | 9 | Upload flow validated |
| **Kaltura CMS** | 9 | Upload flow validated |
| **Opencast CMS** | 9 | Ingest/upload flow validated |
| **YuJa CMS** | 6 | Upload validated; **list/channel paths unverified** |
| **Echo360 CMS** | 6 | Auth/upload/pagination validated; **collection paths unverified** |
| **Q-SYS AV** | 5 | Unit-tested (mocked); not yet run against a live Core |
| **YouTube Live** | 4 | Unit-tested (mocked); not yet run against a live account |
| **EC20 PTZ Camera** | 10 | ⚠️ **Endpoint paths are placeholders — not validated against a camera** |
| **Total** | **130** | |

### Integration maturity — read this before testing

All 130 tools have **unit tests against mocked HTTP responses** (1,376 tests total). What varies is whether the underlying endpoints have been exercised against a **real** live system. Test the known-unverified areas first:

- **EC20 (all 10 tools):** the REST endpoint paths are best-effort placeholders and have **not** been validated against real camera hardware. Expect these to need correction once a camera is on the bench. See the `TODO` in `src/epiphan_mcp/integrations/ec20.py`.
- **YuJa:** upload is validated; the list/channel endpoint paths come from public docs and are unconfirmed against a live instance.
- **Echo360:** auth, upload, and pagination are validated; the collection endpoints (`/courses`, `/sections`) are flagged unverified in the code.
- **Everything else** (Pearl core, Cloud, Q-SYS, YouTube, AI Analysis) is unit-tested with mocks — validate against your own hardware/accounts before relying on it.

## Quick Start

New here / just want to test it? See **[QUICKSTART.md](QUICKSTART.md)** for the shortest path.

### Installation

Not yet published to PyPI — **install from source**:

```bash
git clone https://github.com/tmkipper/epiphan-mcp-server.git
cd epiphan-mcp-server
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Configuration

Copy the example env file and fill in your device details:

```bash
cp .env.example .env
```

Minimum required config:

```bash
# Pearl device(s) — comma-separated for multiple
PEARL_DEVICES=192.168.1.100
PEARL_USERNAME=admin
PEARL_PASSWORD=your_password
```

### Usage with Claude Code (or any MCP client)

Add to your MCP client settings:

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

Then, in natural language:

```
You: What's the status of my Pearl device?
Assistant: [calls get_device_status] Your Pearl at 192.168.1.100 is online with
           847 GB free storage. Currently not recording.

You: Start recording
Assistant: [calls start_recording] Recording started on recorder 1.
```

### Drive it with a local model (Ollama)

You don't need a cloud assistant to drive the server. An in-repo harness at
**[`examples/local_agent/`](examples/local_agent/)** points a **local Ollama model**
(Qwen / DeepSeek / GLM) at these tools so a model running on your own machine can
control Pearl. See that folder's README for setup, model choices, and hardware
guidance (what runs on 8 GB vs 24 GB). No cloud API keys, nothing leaves the machine.

## Available Tools (130)

### Pearl — Device & System (5)

| Tool | Description |
|------|-------------|
| `get_device_status` | Current status of a device |
| `list_devices` | List all configured devices |
| `get_system_info` | Hardware model, firmware, uptime, storage, CPU, temperature |
| `reboot_device` | Reboot device (requires `confirm=True`) |
| `shutdown_device` | Shut down device (requires `confirm=True`) |

### Pearl — Device Discovery (2)

| Tool | Description |
|------|-------------|
| `pearl_discover_device` | Discover recorders, channels, and inputs on a device (cached 5 min) |
| `pearl_clear_discovery_cache` | Clear the device-discovery cache |

### Pearl — Recording (8)

| Tool | Description |
|------|-------------|
| `start_recording` | Start recording on a device |
| `stop_recording` | Stop recording on a device |
| `get_recording_status` | Current recording status |
| `get_all_recorder_status` | Recording status for all recorders at once |
| `start_all_recorders` | Start all recorders simultaneously |
| `stop_all_recorders` | Stop all recorders simultaneously |
| `list_recorders` | List all recorders on a device |
| `list_archive_files` | List recorded files in a recorder's archive |

### Pearl — Streaming & Publishers (12)

| Tool | Description |
|------|-------------|
| `start_stream` | Start streaming |
| `stop_stream` | Stop streaming |
| `get_stream_status` | Status of a specific stream/publisher |
| `list_channels` | List all channels (video pipelines) |
| `list_publishers` | List stream destinations on a channel |
| `get_channel_preview` | Live preview image from a channel (base64) |
| `create_publisher` | Create an RTMP/SRT/HLS streaming destination |
| `delete_publisher` | Delete a streaming destination |
| `get_publisher_settings` | View stream configuration |
| `update_publisher_settings` | Modify stream settings (partial update) |
| `list_publisher_types` | Available streaming protocols for a channel |
| `rename_publisher` | Rename a streaming destination |

### Pearl — Layout & Channels (3)

| Tool | Description |
|------|-------------|
| `switch_layout` | Switch the active layout/scene on a channel |
| `list_layouts` | List available layouts for a channel |
| `add_bookmark` | Add a bookmark to an active recording |

### Pearl — Inputs & Outputs (6)

| Tool | Description |
|------|-------------|
| `create_network_input` | Add an SRT/RTSP/NDI source |
| `get_input_settings` | View input configuration |
| `update_input_settings` | Modify input config (partial update) |
| `get_input_preview` | Live preview image from an input source (base64) |
| `list_outputs` | List available output ports |
| `set_output_source` | Set the source channel for an output port |

### Pearl — Scheduling & Single-Touch (6)

| Tool | Description |
|------|-------------|
| `get_scheduled_events` | Get scheduled events from CMS integration |
| `create_scheduled_event` | Create an ad-hoc recording event |
| `pause_event` | Pause an active event |
| `resume_event` | Resume a paused event |
| `single_touch_start` | Start all recorders and streams with one command |
| `single_touch_stop` | Stop all recorders and streams with one command |

### Pearl — Fleet & Health (12)

| Tool | Description |
|------|-------------|
| `get_fleet_status` | Status of all configured devices, in parallel |
| `batch_start_recording` | Start recording across many devices in parallel |
| `batch_stop_recording` | Stop recording across many devices in parallel |
| `fleet_health_report` | AI-summarized fleet health report |
| `get_device_health_score` | Aggregate device health score (0–100) |
| `predict_storage_full` | Estimate when storage will be full |
| `get_storage_report` | Detailed storage information |
| `get_afu_status` | Automatic File Upload (AFU) destination status |
| `list_inputs` | List available input sources |
| `predict_fleet_issues` | Predict fleet issues for the next 24/48/72 h |
| `suggest_maintenance_window` | Suggest an optimal maintenance window |
| `generate_shift_handoff` | End-of-shift handoff summary for AV teams |

### AI-Powered Analysis (6)

Vision/OCR over Pearl channel previews. Uses a **mock provider by default**; set an OpenRouter key for real analysis (see [AI Analysis config](#ai-analysis-optional)).

| Tool | Description |
|------|-------------|
| `analyze_channel_scene` | AI vision analysis of channel content |
| `extract_text_from_preview` | OCR text extraction from slides/graphics |
| `detect_layout_changes` | Detect scene transitions / slide advances |
| `check_video_quality` | AI assessment of lighting, focus, framing |
| `detect_recording_issues` | Detect quality issues during an active recording |
| `clear_change_detection_cache` | Reset the change-detection baseline |

### Panopto CMS (9)

| Tool | Description |
|------|-------------|
| `list_panopto_folders` | List folders |
| `get_panopto_folder` | Folder details |
| `create_panopto_folder` | Create a folder |
| `list_panopto_sessions` | List sessions (recordings) |
| `get_panopto_session` | Session details |
| `create_panopto_session` | Create a session (recording placeholder) |
| `upload_to_panopto` | Upload a video file (S3-based workflow) |
| `get_panopto_upload_status` | Check upload status |
| `delete_panopto_session` | Delete a session |

### Kaltura CMS (9)

| Tool | Description |
|------|-------------|
| `list_kaltura_categories` | List categories (folders) |
| `get_kaltura_category` | Category details |
| `create_kaltura_category` | Create a category |
| `list_kaltura_media` | List media entries |
| `get_kaltura_media` | Media details |
| `create_kaltura_media` | Create a media entry (placeholder) |
| `upload_to_kaltura` | Upload a video file (chunked) |
| `schedule_kaltura_event` | Schedule an event for Pearl auto-record |
| `get_kaltura_upload_status` | Check upload status |

### Opencast CMS (9)

| Tool | Description |
|------|-------------|
| `list_opencast_series` | List series (courses/channels) |
| `get_opencast_series` | Series details |
| `create_opencast_series` | Create a series |
| `list_opencast_events` | List events (recordings) |
| `get_opencast_event` | Event details |
| `ingest_to_opencast` | Ingest a video with Dublin Core metadata |
| `get_opencast_ingest_status` | Check ingest workflow status |
| `schedule_opencast_capture` | Schedule a capture for Pearl auto-record |
| `delete_opencast_event` | Delete an event |

### YuJa CMS (6)

| Tool | Description |
|------|-------------|
| `list_yuja_videos` | List videos |
| `get_yuja_video` | Video details and metadata |
| `list_yuja_channels` | List media channels |
| `upload_video_to_yuja` | Upload a video file |
| `get_yuja_upload_status` | Check upload session status |
| `delete_yuja_video` | Delete a video |

### Echo360 CMS (6)

| Tool | Description |
|------|-------------|
| `list_echo360_courses` | List courses |
| `list_echo360_sections` | List sections |
| `list_echo360_medias` | List media |
| `get_echo360_media` | Media item details |
| `upload_video_to_echo360` | Upload a video file (Capture Intake) |
| `get_echo360_upload_status` | Check capture upload status |

### Q-SYS AV Control (5)

| Tool | Description |
|------|-------------|
| `list_qsys_components` | Discover Pearl components in a Q-SYS design |
| `qsys_get_pearl_status` | Recording/streaming state via Q-SYS |
| `qsys_start_recording` | Start recording through the Q-SYS Core |
| `qsys_stop_recording` | Stop recording through the Q-SYS Core |
| `qsys_switch_layout` | Switch Pearl layout via Q-SYS |

### YouTube Live (4)

| Tool | Description |
|------|-------------|
| `create_youtube_broadcast` | Create a broadcast + stream, returns RTMP credentials |
| `get_youtube_broadcast_status` | Check broadcast/stream health |
| `list_youtube_broadcasts` | List the account's broadcasts |
| `end_youtube_broadcast` | Transition a broadcast to complete |

### EC20 PTZ Camera (10)  ⚠️ endpoint paths unverified

| Tool | Description |
|------|-------------|
| `ec20_get_status` | Camera status, PTZ position, tracking state |
| `ec20_pan_tilt` | Absolute pan/tilt positioning |
| `ec20_zoom` | Zoom level control |
| `ec20_goto_preset` | Recall a saved preset |
| `ec20_save_preset` | Save current position as a preset |
| `ec20_home` | Return to home position (pan=0, tilt=0, zoom=1) |
| `ec20_enable_tracking` | Enable AI tracking |
| `ec20_disable_tracking` | Disable AI tracking |
| `ec20_list_presets` | List all saved presets |
| `ec20_get_preview` | Preview image (base64) |

### Epiphan Cloud (12)

| Tool | Description |
|------|-------------|
| `cloud_get_user` | Current authenticated user profile |
| `cloud_list_devices` | List all paired devices |
| `cloud_get_device` | Device details |
| `cloud_pair_device` | Pair a new device |
| `cloud_unpair_device` | Unpair a device |
| `cloud_delete_device` | Delete a device record |
| `cloud_rename_device` | Rename a device |
| `cloud_run_command` | Run a command on a single device |
| `cloud_batch_command` | Run a command on multiple devices at once |
| `cloud_get_settings` | Get device settings |
| `cloud_get_preview` | Device preview image (base64 JPEG) |
| `cloud_apply_preset` | Apply a preset to a device |

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
EPIPHAN_CLOUD_TOKEN=your_bearer_token
EPIPHAN_CLOUD_HOST=go.epiphan.cloud   # optional; defaults to go.epiphan.cloud
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

The AI Analysis tools support three backends via `LLM_PROVIDER`:

- **`ollama`** — local models, no API key, nothing leaves the machine (recommended).
- **`openrouter`** — hosted cloud gateway (needs `OPENROUTER_API_KEY`).
- **`mock`** — fake responses; also the automatic fallback when no key is set.

**Local (Ollama)** — verified working with `qwen2.5vl:7b` (vision/OCR) and `qwen2.5:14b` (text):

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1   # default
LLM_VISION_MODEL=qwen2.5vl:7b               # ollama pull qwen2.5vl:7b
LLM_OCR_MODEL=qwen2.5vl:7b
LLM_TEXT_MODEL=qwen2.5:14b                  # ollama pull qwen2.5:14b
```

**Cloud (OpenRouter):**

```bash
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here
LLM_VISION_MODEL=google/gemini-2.0-flash-001
LLM_OCR_MODEL=qwen/qwen2.5-vl-72b-instruct
LLM_TEXT_MODEL=deepseek/deepseek-chat-v3-0324
```

> For the *model-drives-the-tools* use case (a local model calling the 130 tools),
> see [`examples/local_agent/`](examples/local_agent/).

## Supported Devices

All Pearl models share the same REST API v2.0:

| Model | Form Factor | Best For |
|-------|-------------|----------|
| **Pearl Nano** | Portable, PoE+ | Field production, SRT contribution |
| **Pearl Mini** | Desktop, touchscreen | Lecture capture, small events |
| **Pearl Nexus** | 1RU rackmount | Classroom installations |
| **Pearl-2** | Desktop/rackmount | Multi-camera production |

## Platform Support

Pearl Copilot is a standard stdio MCP server, so it works with any MCP-compatible client.

| Platform | Status | Integration |
|----------|--------|-------------|
| **Claude Code** | Verified | Native MCP |
| **Claude Desktop** | Verified | Native MCP |
| **Cursor** | Should work (standard MCP; not independently verified here) | MCP server |
| **Windsurf** | Should work (standard MCP; not independently verified here) | MCP server |
| **Local model via Ollama** | In this repo | [`examples/local_agent/`](examples/local_agent/) |
| **[SilkRoute](https://github.com/ScientiaCapital/silkroute)** (external, self-hosted demo) | External | Native MCP via that project's `mcp_bridge` |

## Development

```bash
pip install -e ".[dev]"

# Run tests (all mocked — no hardware or API keys needed)
pytest

# Coverage
pytest --cov=src/epiphan_mcp --cov-report=term-missing

# Type checking
mypy src/

# Linting
ruff check src/
ruff format src/
```

### Tests

**1,376 tests** (1,369 passing, 7 skipped). All unit tests use mocked HTTP responses — no
real Pearl hardware or API keys required. The 7 skipped tests are the real-hardware
integration tests in `tests/test_integration.py`; they run only when `PEARL_DEVICES` is set:

```bash
export PEARL_DEVICES=192.168.1.100
export PEARL_USERNAME=admin PEARL_PASSWORD=your_password
pytest -m integration
```

## API Reference

This server wraps Epiphan Pearl's REST API v2.0:
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
