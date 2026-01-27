# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-01-27

### Added

- **Publisher Management** (6 new tools)
  - `create_publisher`: Create RTMP/SRT/HLS streaming destinations
  - `delete_publisher`: Remove stream from channel
  - `get_publisher_settings`: View stream configuration
  - `update_publisher_settings`: Modify stream settings (PATCH semantics)
  - `list_publisher_types`: Available streaming protocols
  - `rename_publisher`: Change stream display name

- **Input/Output Management** (5 new tools)
  - `create_network_input`: Add SRT/RTSP/NDI sources
  - `get_input_settings`: View input configuration
  - `update_input_settings`: Modify input config
  - `list_outputs`: Available HDMI/SDI output ports
  - `set_output_source`: Configure output routing

- **Event Control** (3 new tools)
  - `create_scheduled_event`: Create ad-hoc recording events
  - `pause_event`: Pause active event
  - `resume_event`: Resume paused event

- **Security Hardening**
  - Audit logging module (`src/epiphan_mcp/audit.py`)
  - Fleet operation concurrency limits (Semaphore(10))
  - Image size validation for AI tools (10MB max)

- **HTTP Methods**
  - `_delete()` and `_patch()` methods with retry logic

### Changed

- **API Coverage**: 61% → 96% (31/51 → 49/51 endpoints)
- **MCP Tools**: 32 → 46 total
- **Tests**: 338 → 361+ passing

---

## [0.5.0] - 2025-01-24

### Added

- **Fleet Health Monitoring**
  - `fleet_health_report`: AI-summarized fleet health with recommendations
  - Per-device `health_score` (0-100) in fleet status
  - Per-device `health_issues` list for quick triage
  - Fleet-level `average_health` aggregate metric
  - Fleet-level `unhealthy_devices` count (score < 60)
- Health scoring based on storage usage and recorder accessibility

### Changed

- Enhanced `get_fleet_status` to include health metrics
- Added 7 new tests for health features (322 total tests)

## [0.4.0] - 2025-01-23

### Added

- **AI-Powered Video Analysis** via OpenRouter integration
  - `analyze_video_scene`: Vision LLM scene analysis with customizable prompts
  - `extract_text_from_video`: OCR text extraction from slides/presentations
  - `check_video_quality`: Automated quality monitoring (lighting, focus, framing)
  - `detect_scene_change`: Slide advance and scene transition detection
- **Fleet Management**
  - `get_fleet_status`: Aggregate status across all configured devices
  - `batch_start_recording`: Start recording on multiple devices
  - `batch_stop_recording`: Stop recording on multiple devices
- **Recording Control**
  - `start_recording`: Start recording on specific device/recorder
  - `stop_recording`: Stop recording on specific device/recorder
  - `get_recording_status`: Get current recording state and duration
- **Streaming Control**
  - `start_stream`: Start RTMP/SRT streaming
  - `stop_stream`: Stop streaming
- **Layout Control**
  - `switch_layout`: Switch active layout on a channel
- **Device Management**
  - `get_device_status`: Comprehensive device status
  - `list_devices`: List all configured Pearl devices
- GitHub Actions CI/CD pipeline with PyPI publishing
- Comprehensive test suite (165 tests, 93% coverage)

### Changed

- Updated to Pearl REST API v2.0 endpoints
- Modern async-first architecture with httpx
- Pydantic v2 for configuration and validation

### Security

- Pydantic >= 2.4.0 requirement (CVE-2024-3772 fix)
- HTTP Basic Auth for all API calls (required since firmware 4.14.2)
- No hardcoded credentials - all via environment variables

## [0.1.0] - 2025-01-22

### Added

- Initial project setup
- Basic MCP server structure with FastMCP
- Pearl REST API client foundation
- Configuration via pydantic-settings

[0.4.0]: https://github.com/tmkipper/epiphan-mcp-server/compare/v0.1.0...v0.4.0
[0.1.0]: https://github.com/tmkipper/epiphan-mcp-server/releases/tag/v0.1.0
