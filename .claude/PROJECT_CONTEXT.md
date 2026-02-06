# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-02-06

## Status
MCP server for Epiphan Pearl video capture devices. v1.0.0 launch release — 113 MCP tools, 674+ tests, 9 integrations (Pearl + Panopto + Kaltura + Opencast + Q-SYS + YouTube + EC20 + LLM + Cloud). Package published to PyPI.

## Done (This Session)
- (session start — clear)

## Blockers
- EC20 REST API endpoints are placeholder (need device access to verify)

## Tech Stack
Python 3.11+ | FastMCP | httpx | Pydantic v2 | OpenRouter (multi-model gateway)

## Metrics
| Metric | Value |
|--------|-------|
| Tests | 674 passing |
| Coverage | ~95% |
| MCP Tools | 113 total |
| Integrations | 9 (Pearl, Panopto, Kaltura, Opencast, Q-SYS, YouTube, EC20, LLM, Cloud) |
| Version | 1.0.0 |

## Next Session
1. Hardware: Connect Pearl Mini and EC20 to network
2. Verify EC20 REST API endpoints with real hardware
3. Demo video: Pearl Mini + EC20 + Cloud AI workflow
4. PyPI trusted publisher setup (if not done via CI tag)
5. Consider v1.1 features: WebSocket live events, dashboard UI
