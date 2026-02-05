# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-02-05

## Status
MCP server for Epiphan Pearl video capture devices. Production-ready with 92 MCP tools, 579 tests, and 8 integrations (Pearl + Panopto + Kaltura + Opencast + Q-SYS + YouTube + EC20). EC20 PTZ camera integration complete with 10 new tools. Ready for hardware testing with Pearl Mini + EC20.

## Today's Focus
1. [x] Update docs - clean stale items from BACKLOG.md, TECHNICAL_ROADMAP.md
2. [x] TDD: Write failing tests for EC20 client (21 tests)
3. [x] TDD: Implement EC20 client to pass tests
4. [x] TDD: Write failing tests for EC20 MCP tools (10 tests)
5. [x] TDD: Implement EC20 MCP tools to pass tests
6. [x] Register EC20 tools in server.py (10 new tools)
7. [x] Update CLAUDE.md and docs with EC20 integration
8. [ ] Hardware: Connect Pearl Mini to network, test existing tools
9. [ ] Hardware: Connect EC20 via NDI, verify REST API endpoints
10. [ ] Integration test: Recording + PTZ workflow end-to-end

## Done (This Session)
- ✅ EC20 PTZ integration complete (10 new MCP tools)
- ✅ 38 new tests for EC20 client, config, and tools
- ✅ All 579 tests passing
- ✅ Security sweep: 0 critical issues
- ✅ Git pushed: commit 69505e9
- ✅ End-of-day lockdown completed

## Blockers
- EC20 REST API endpoints are placeholder (need device access to verify actual endpoints)
- Epiphan Edge cloud management launching Spring 2026

## Tech Stack
Python 3.12+ | FastMCP | httpx | Pydantic v2 | OpenRouter (multi-model gateway)

## Metrics
| Metric | Value |
|--------|-------|
| Tests | 579 passing |
| Coverage | ~95% |
| MCP Tools | 92 total |
| Integrations | 8 (Pearl, Panopto, Kaltura, Opencast, Q-SYS, YouTube, LLM, EC20) |

## Hardware Available
- Pearl Mini (demo unit)
- EC20 PTZ Camera (demo unit, launched Dec 2025)

## EC20 Tools Added (10)
- ec20_get_status - Camera status, PTZ position, tracking state
- ec20_pan_tilt - Absolute pan/tilt positioning
- ec20_zoom - Zoom level control (1-36)
- ec20_goto_preset - Recall saved preset
- ec20_save_preset - Save current position as preset
- ec20_home - Return to home position
- ec20_enable_tracking - Enable AI tracking (presenter/zone/body)
- ec20_disable_tracking - Disable AI tracking
- ec20_list_presets - List all saved presets
- ec20_get_preview - Get preview image

## Next Session
1. Hardware: Connect Pearl Mini and EC20 to network
2. Verify EC20 REST API endpoints with real hardware
3. Update placeholder endpoints in ec20.py
4. End-to-end test: Recording + PTZ workflow
5. PyPI publish when ready
