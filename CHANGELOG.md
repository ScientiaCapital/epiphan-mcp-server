# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.0] - 2026-02-05

### Added

- **Pearl Discovery & System Tools** (9 new tools)
  - `list_recorders`: Discover available recorders on a device
  - `list_archive_files`: Browse recorded files with pagination
  - `list_channels`: List all video processing pipelines
  - `list_publishers`: List stream destinations on a channel
  - `get_channel_preview`: Live preview snapshot from channel (base64)
  - `get_input_preview`: Live preview from input source (base64)
  - `reboot_device`: Reboot with `confirm=True` safety gate
  - `shutdown_device`: Shutdown with `confirm=True` safety gate
  - `get_system_info`: Hardware model, firmware, uptime, storage, CPU, temperature

### Changed

- Total MCP tools: 92 → 101 (+9)
- Tests: 579 → 618 (+39)

## [0.9.0] - 2026-02-05

### Added

- **EC20 PTZ Camera Integration** (10 new tools)
  - `ec20_get_status`: Camera status, PTZ position, tracking state
  - `ec20_pan_tilt`: Absolute pan/tilt positioning
  - `ec20_zoom`: Zoom level control (1-36: optical + digital)
  - `ec20_goto_preset`: Recall saved camera preset
  - `ec20_save_preset`: Save current position as preset
  - `ec20_home`: Return to home position
  - `ec20_enable_tracking`: Enable AI tracking (presenter/zone/body)
  - `ec20_disable_tracking`: Disable AI tracking
  - `ec20_list_presets`: List all saved presets
  - `ec20_get_preview`: Get preview image (base64)
  - REST API client for EC20 camera
  - Environment config: `EC20_DEVICES`, `EC20_USERNAME`, `EC20_PASSWORD`

### Changed

- Total MCP tools: 82 → 92 (+10)
- Total integrations: 7 → 8 (added EC20)
- Tests: 541 → 579 (+38)

## [0.8.0] - 2026-01-28

### Added

- **Q-SYS AV Control Integration** (5 new tools)
  - `list_qsys_components`: Discover Pearl components in Q-SYS design
  - `qsys_get_pearl_status`: Get recording/streaming state via Q-SYS
  - `qsys_start_recording`: Start recording through Q-SYS Core
  - `qsys_stop_recording`: Stop recording through Q-SYS Core
  - `qsys_switch_layout`: Change Pearl layout via Q-SYS
  - JSON-RPC 2.0 over TCP (port 1710) with null-terminated messages
  - Keep-alive mechanism (NoOp every 50s)
  - PIN authentication support
  - Environment config: `QSYS_CORE_IP`, `QSYS_PORT`, `QSYS_PIN`

- **Opencast CMS Integration** (9 new tools)
  - `list_opencast_series`: Browse series (courses/channels)
  - `get_opencast_series`: Get series details
  - `create_opencast_series`: Create new series
  - `list_opencast_events`: List recordings
  - `get_opencast_event`: Get event details
  - `ingest_to_opencast`: Upload video with Dublin Core metadata
  - `get_opencast_ingest_status`: Check processing workflow
  - `schedule_opencast_capture`: Schedule Pearl auto-record
  - `delete_opencast_event`: Remove event
  - HTTP Basic Auth, Dublin Core XML metadata
  - Environment config: `OPENCAST_HOST`, `OPENCAST_USERNAME`, `OPENCAST_PASSWORD`

- **YouTube Live Integration** (4 new tools)
  - `create_youtube_broadcast`: Create broadcast + stream, returns RTMP credentials for Pearl
  - `get_youtube_broadcast_status`: Check broadcast/stream health
  - `list_youtube_broadcasts`: List user's broadcasts
  - `end_youtube_broadcast`: Transition broadcast to complete
  - OAuth2 with automatic token refresh
  - Environment config: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`

### Changed

- Total MCP tools: 64 → 82 (+18)
- Total integrations: 4 → 7 (Pearl + Panopto + Kaltura + Opencast + Q-SYS + YouTube)
- Tests: 452 → 541

## [0.7.0] - 2026-01-27

### Added

- **Kaltura CMS Integration** (9 new tools)
  - `list_kaltura_categories`: Browse content folders
  - `get_kaltura_category`: Get folder details
  - `create_kaltura_category`: Create new category
  - `list_kaltura_media`: List video entries
  - `get_kaltura_media`: Get media details
  - `create_kaltura_media`: Create media placeholder
  - `upload_to_kaltura`: Chunked upload workflow (10MB chunks)
  - `schedule_kaltura_event`: Create scheduled events for Pearl auto-record
  - `get_kaltura_upload_status`: Check processing status
  - AppToken authentication (SHA256 hash flow)
  - Environment config: `KALTURA_PARTNER_ID`, `KALTURA_APP_TOKEN_ID`, `KALTURA_APP_TOKEN`

### Changed

- Total MCP tools: 55 → 64

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

- **Panopto CMS Integration** (9 new tools)
  - `list_panopto_folders`: Browse folder hierarchy
  - `get_panopto_folder`: Get folder details
  - `create_panopto_folder`: Create new folders
  - `list_panopto_sessions`: List recordings
  - `get_panopto_session`: Get session details
  - `create_panopto_session`: Create recording placeholder
  - `upload_to_panopto`: Full S3-based upload workflow
  - `get_panopto_upload_status`: Check processing status
  - `delete_panopto_session`: Remove session
  - OAuth2 Password Grant authentication
  - Environment config: `PANOPTO_HOST`, `PANOPTO_CLIENT_ID`, `PANOPTO_USERNAME`, `PANOPTO_PASSWORD`

- **Security Hardening**
  - Audit logging module (`src/epiphan_mcp/audit.py`)
  - Fleet operation concurrency limits (Semaphore(10))
  - Image size validation for AI tools (10MB max)

- **HTTP Methods**
  - `_delete()` and `_patch()` methods with retry logic

### Changed

- **API Coverage**: 61% → 96% (31/51 → 49/51 endpoints)
- **MCP Tools**: 32 → 55 total (46 Pearl + 9 Panopto CMS)
- **Tests**: 338 → 400 passing

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
