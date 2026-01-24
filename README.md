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
- 🔍 **AI Video Analysis** - Scene understanding, OCR, quality checks, change detection via vision LLMs

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

# AI Analysis (optional - enables AI-powered tools)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### AI Configuration (Optional)

To enable AI-powered video analysis tools, add OpenRouter credentials:

```bash
# Required for AI features
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional: Override default models
LLM_VISION_MODEL=google/gemini-2.0-flash-001      # Scene analysis
LLM_OCR_MODEL=qwen/qwen2.5-vl-72b-instruct        # Text extraction
LLM_QUALITY_MODEL=google/gemini-2.0-flash-001     # Quality checks
LLM_TEXT_MODEL=deepseek/deepseek-chat-v3-0324     # Reasoning

# Optional: Testing without API
LLM_MOCK_MODE=true  # Returns mock responses
```

**Supported Vision Models** (via [OpenRouter](https://openrouter.ai)):
- Google Gemini Flash - Fast, cost-effective (default)
- Qwen VL 72B - Best for OCR/text extraction
- Claude Sonnet - Premium quality reasoning
- DeepSeek VL - Scientific/technical content

> **Note**: AI features work without `OPENROUTER_API_KEY` in mock mode (`LLM_MOCK_MODE=true`), useful for testing.

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
| `get_fleet_status` | Get status of entire fleet with health scores |
| `fleet_health_report` | AI-summarized fleet health with recommendations |

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
| `get_stream_status` | Get current stream state and duration |

### Layout & Channels
| Tool | Description |
|------|-------------|
| `switch_layout` | Change active layout/scene |
| `list_layouts` | List available layouts for a channel |
| `add_bookmark` | Add timestamp bookmark to recording |

### Scheduling & Batch Control
| Tool | Description |
|------|-------------|
| `get_scheduled_events` | Get CMS scheduled events (Kaltura/Panopto/Opencast) |
| `single_touch_start` | Start all recorders and streams at once |
| `single_touch_stop` | Stop all recorders and streams at once |

### AI-Powered Analysis
| Tool | Description |
|------|-------------|
| `analyze_channel_scene` | AI vision analysis of channel content (scene description, content detection, presenter detection) |
| `extract_text_from_preview` | OCR text extraction from slides, graphics, and lower thirds |
| `detect_layout_changes` | Monitor channel for scene transitions and slide advances |
| `check_video_quality` | AI assessment of lighting, focus, framing, and production quality |
| `clear_change_detection_cache` | Reset change detection baseline |

### AI Predictive Maintenance
| Tool | Description |
|------|-------------|
| `predict_storage_full` | Estimate hours until storage is full based on recording bitrate |
| `get_device_health_score` | Aggregate health score (0-100) with category breakdown |
| `fleet_health_report` | AI-summarized fleet health with prioritized recommendations |

#### Health Score Thresholds

| Score | Status | Action |
|-------|--------|--------|
| 80-100 | Healthy | No action needed |
| 60-79 | Minor Issues | Review when convenient |
| 40-59 | Needs Attention | Address issues soon |
| 0-39 | Unhealthy | Immediate attention required |

**Scoring breakdown (0-100):**
- **Storage (50 pts max)**: 50 = healthy, 30 = >75% used, 10 = >90% used
- **Recording (50 pts max)**: 50 = accessible, 25 = degraded

Fleet-level metrics:
- `average_health`: Mean health score of online devices
- `unhealthy_devices`: Count of devices with score < 60

#### AI Analysis Types

The `analyze_channel_scene` tool supports multiple analysis modes:

- **scene_description** - General description of what's on screen
- **content_detection** - Classify content type (educational, corporate, etc.)
- **quality_check** - Technical quality assessment
- **text_extraction** - OCR to extract visible text
- **presenter_detection** - Detect and describe presenters in frame

#### Example AI Usage

```
You: What's happening on channel 1?
Claude: [Calls analyze_channel_scene] The channel shows a corporate presentation
        with a presenter on the left third of frame. A slide titled "Q4 Results"
        is visible with bullet points and a bar chart.

You: Is the video quality okay?
Claude: [Calls check_video_quality] Quality assessment:
        - Lighting: Good, even illumination
        - Focus: Sharp
        - Framing: Presenter has adequate headroom
        Overall: Excellent production quality

You: What text is on the slide?
Claude: [Calls extract_text_from_preview] Extracted text:
        Title: Q4 Results Summary
        - Revenue: $4.2M (+15% YoY)
        - New customers: 847
        - NPS Score: 72

You: How's the device health?
Claude: [Calls get_device_health_score] Health Score: 85/100
        - Storage: 50/50 (healthy, 65% free)
        - Recording: 35/50 (degraded - check input signal)
        Recommendation: Device has minor issues - review when convenient

You: How long until storage fills up?
Claude: [Calls predict_storage_full] At current 8 Mbps bitrate:
        - 127.3 hours until full (~5 days)
        - 847 GB free of 1 TB
        Storage capacity is sufficient.
```

## AI Tools Deep Dive

### Tool Reference

#### `analyze_channel_scene`

General-purpose AI vision analysis of channel content.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device_id` | string | `"default"` | Pearl device identifier |
| `channel` | string | `"1"` | Channel ID (e.g., "1", "2") |
| `analysis_type` | string | `"scene_description"` | Type of analysis (see below) |

**Returns:**
```json
{
  "success": true,
  "analysis": "Scene shows a presenter at a podium...",
  "analysis_type": "scene_description",
  "model_used": "google/gemini-2.0-flash-001",
  "timestamp": "2025-01-23T10:30:00.000Z",
  "image_hash": "a1b2c3d4...",
  "device_id": "default",
  "channel": "1"
}
```

#### `extract_text_from_preview`

OCR-optimized text extraction for slides, graphics, and lower thirds.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device_id` | string | `"default"` | Pearl device identifier |
| `channel` | string | `"1"` | Channel ID |

**Returns:** `{ "success": true, "text": "Extracted text...", "model_used": "...", ... }`

**Best for:** Presentation slides, whiteboards, title cards, lower-third graphics.

#### `detect_layout_changes`

Monitors a channel for scene transitions and content changes.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device_id` | string | `"default"` | Pearl device identifier |
| `channel` | string | `"1"` | Channel ID |
| `sensitivity` | string | `"medium"` | Detection sensitivity: `"low"`, `"medium"`, `"high"` |

**Sensitivity levels:**
- `low` - Only major scene changes (camera switches, black frames)
- `medium` - Slide advances, presenter movement, graphics changes
- `high` - Any visible change including subtle movements

**Returns:** `{ "success": true, "changed": true/false, "change_type": "...", "message": "..." }`

**Use case:** Automated recording triggers, event logging, slide counting.

#### `check_video_quality`

Technical quality assessment for production monitoring.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device_id` | string | `"default"` | Pearl device identifier |
| `channel` | string | `"1"` | Channel ID |

**Returns:** `{ "success": true, "quality_report": "Detailed assessment...", ... }`

**Checks:** Lighting, focus, framing, exposure, color balance, artifacts.

#### `clear_change_detection_cache`

Resets the change detection baseline.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device_id` | string | `None` | Device to clear (None = all devices) |
| `channel` | string | `None` | Channel to clear (None = all channels) |

**Use when:** Starting new sessions, after intentional scene changes, resetting monitoring.

### Analysis Types Reference

| Type | Use Case | Default Model |
|------|----------|---------------|
| `scene_description` | General understanding of what's on screen | Gemini Flash |
| `content_detection` | Classify content (educational, corporate, entertainment) | Gemini Flash |
| `quality_check` | Technical quality assessment | Gemini Flash |
| `text_extraction` | OCR for slides, graphics, captions | Qwen VL 72B |
| `presenter_detection` | Find and describe people in frame | Gemini Flash |

### Model Selection

Models are selected automatically based on task, but can be overridden:

| Environment Variable | Purpose | Default |
|---------------------|---------|---------|
| `LLM_VISION_MODEL` | General scene analysis | `google/gemini-2.0-flash-001` |
| `LLM_OCR_MODEL` | Text extraction (OCR) | `qwen/qwen2.5-vl-72b-instruct` |
| `LLM_QUALITY_MODEL` | Quality assessment | `google/gemini-2.0-flash-001` |
| `LLM_TEXT_MODEL` | Reasoning/planning | `deepseek/deepseek-chat-v3-0324` |

**Model recommendations:**
- **Gemini Flash** - Fast, cost-effective, good general vision
- **Qwen VL 72B** - Superior OCR and text extraction
- **Claude Sonnet** - Premium reasoning for complex analysis
- **DeepSeek VL** - Technical/scientific content

### Troubleshooting

#### Mock Mode (No API Key)

When `OPENROUTER_API_KEY` is not set, AI tools automatically use mock mode:
- Returns realistic sample responses
- Useful for development and testing
- No API costs incurred

Enable explicitly: `LLM_MOCK_MODE=true`

#### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "API key not configured" | Missing `OPENROUTER_API_KEY` | Add key to `.env` file |
| Empty analysis results | Invalid image from Pearl | Check Pearl preview is working |
| Slow responses | Large images or complex analysis | Use faster models (Gemini Flash) |
| Rate limiting | Too many requests | Add delays between calls |

#### Cost Optimization

- **Default models are cost-optimized** - Gemini Flash is ~$0.10/1M tokens
- **OCR uses Qwen** - Better accuracy reduces retries
- **Change detection uses hashing** - Only calls AI when changes detected
- **Preview images are 720p** - Balances quality with token usage

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
├── test_client.py       # PearlClient API tests
├── test_server.py       # MCP tool tests
├── test_llm.py          # LLM provider and analyzer tests
└── test_ai_tools.py     # AI-powered tool tests
```

**197 tests** with **92% coverage**. All tests use mocked HTTP responses - no real Pearl hardware or API keys required.

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
