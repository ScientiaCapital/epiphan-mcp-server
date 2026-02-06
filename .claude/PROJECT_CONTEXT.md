# epiphan-mcp-server

**Branch**: feat/expose-pearl-discovery-tools | **Updated**: 2026-02-05

## Status
MCP server for Epiphan Pearl video capture devices. Production-ready with 101 MCP tools, 618 tests, and 8 integrations (Pearl + Panopto + Kaltura + Opencast + Q-SYS + YouTube + LLM + EC20). Pearl discovery & system tools complete — all client methods now exposed as MCP tools.

## Today's Focus
1. [x] TDD: Write failing tests for 9 new Pearl discovery/system tools (39 tests)
2. [x] Implement list_recorders, list_archive_files
3. [x] Implement list_channels, list_publishers, get_channel_preview
4. [x] Implement get_input_preview
5. [x] Implement reboot_device, shutdown_device, get_system_info
6. [x] Register all 9 tools in server.py (101 total)
7. [x] Update test_tools_imports.py assertions (92 → 101)
8. [x] Full test suite: 618 passed, 0 failures
9. [x] Security sweep: 0 secrets, 0 critical CVEs
10. [x] Doc updates: CLAUDE.md, CHANGELOG.md, BACKLOG.md

## Done (This Session)
- ✅ 9 new Pearl discovery & system MCP tools implemented
- ✅ 39 new tests (618 total, all passing)
- ✅ Security sweep: 0 critical issues
- ✅ Lint clean (ruff auto-fixed import sorting)
- ✅ All docs updated

## Blockers
- EC20 REST API endpoints are placeholder (need device access to verify actual endpoints)
- Epiphan Edge cloud management launching Spring 2026

## Tech Stack
Python 3.12+ | FastMCP | httpx | Pydantic v2 | OpenRouter (multi-model gateway)

## Metrics
| Metric | Value |
|--------|-------|
| Tests | 618 passing |
| Coverage | ~95% |
| MCP Tools | 101 total |
| Integrations | 8 (Pearl, Panopto, Kaltura, Opencast, Q-SYS, YouTube, LLM, EC20) |

## New Tools Added (9)
- list_recorders - Discover available recorders on a device
- list_archive_files - Browse recorded files with pagination
- list_channels - List all video processing pipelines
- list_publishers - List stream destinations on a channel
- get_channel_preview - Live preview snapshot from channel (base64)
- get_input_preview - Live preview from input source (base64)
- reboot_device - Reboot with `confirm=True` safety gate
- shutdown_device - Shutdown with `confirm=True` safety gate
- get_system_info - Hardware model, firmware, uptime, storage, CPU, temperature

## Next Session
1. Merge feat/expose-pearl-discovery-tools → main
2. Hardware: Connect Pearl Mini and EC20 to network
3. Verify EC20 REST API endpoints with real hardware
4. Launch readiness: CI/CD, PyPI publishing, v1.0 tag
5. Demo video: Pearl Mini + EC20 AI workflow
