# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-02-09

## Status
MCP server for Epiphan Pearl video capture devices. v1.0.0 launch release — 113 MCP tools, 754 passing tests (7 skipped), 9 integrations (Pearl + Panopto + Kaltura + Opencast + Q-SYS + YouTube + EC20 + LLM + Cloud). Package published to PyPI.

## Done (This Session — 2026-02-09 Launch Sprint)
- Security audit fixes: host validation (`_validate_host()`), audit logging wired into destructive tools
- Configurable concurrency semaphore (was hardcoded at 10)
- URL validation for SSRF prevention on create_publisher/create_network_input
- Fleet tool extraction from server.py inline logic to tools/ module
- Edge case tests added (761 collected, 754 passing, up from 705)
- Launch artifacts: `server.json` for MCP Registry, README badge updates
- `tools/__init__.py` exports all 113 tools (was missing 15)

## Blockers
- EC20 REST API endpoints are placeholder (need device access to verify)

## Tech Stack
Python 3.11+ | FastMCP | httpx | Pydantic v2 | OpenRouter (multi-model gateway)

## Metrics
| Metric | Value |
|--------|-------|
| Tests | 754 passing (7 skipped) |
| Coverage | ~95% |
| MCP Tools | 113 total |
| Integrations | 9 (Pearl, Panopto, Kaltura, Opencast, Q-SYS, YouTube, EC20, LLM, Cloud) |
| Version | 1.0.0 |

## GitHub Topics
```
mcp, model-context-protocol, epiphan, pearl, video-capture, av-control,
streaming, recording, fleet-management, panopto, kaltura, opencast,
qsys, youtube-live, ptz-camera, ai-powered
```

## Next Session
1. Hardware: Connect Pearl Mini and EC20 to network
2. Verify EC20 REST API endpoints with real hardware
3. Demo video: Pearl Mini + EC20 + Cloud AI workflow
4. PyPI trusted publisher setup (if not done via CI tag)
5. Consider v1.1 features: WebSocket live events, dashboard UI
