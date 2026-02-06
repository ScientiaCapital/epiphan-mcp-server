# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-02-05

## Status
MCP server for Epiphan Pearl video capture devices. Production-ready with 113 MCP tools, 674 tests, and 9 integrations (Pearl + Panopto + Kaltura + Opencast + Q-SYS + YouTube + EC20 + LLM + Cloud). Epiphan Cloud fleet management integration complete — 12 new tools for go.epiphan.cloud API.

## Done (This Session)
- Epiphan Cloud API client (integrations/cloud.py) — async httpx, Bearer token auth
- 12 Cloud MCP tool functions (tools/cloud.py) — fleet management
- Server registration of all 12 tools (113 total)
- 56 new Cloud tests (22 client + 34 tools), all passing
- Full suite: 674 passed, 7 skipped, 0 failures
- Security sweep: 0 secrets, 0 critical CVEs
- Code reviews: Batch 1 + 2 approved, no critical issues
- .env.example updated with Cloud config section
- CLAUDE.md updated with v1.5 Cloud section

## Cloud Tools Added (12)
- cloud_get_user — Current authenticated user profile
- cloud_list_devices — List all paired devices
- cloud_get_device — Device details + telemetry
- cloud_pair_device — Pair new device via pairing code
- cloud_unpair_device — Unpair device from cloud
- cloud_delete_device — Delete device record
- cloud_rename_device — Rename device
- cloud_run_command — Run task on single device (recording, streaming, setprop)
- cloud_batch_command — Run task on multiple devices simultaneously
- cloud_get_settings — Get device configuration
- cloud_get_preview — Get device preview (base64 JPEG)
- cloud_apply_preset — Apply cloud/local preset to device

## Blockers
- EC20 REST API endpoints are placeholder (need device access to verify)

## Tech Stack
Python 3.12+ | FastMCP | httpx | Pydantic v2 | OpenRouter (multi-model gateway)

## Metrics
| Metric | Value |
|--------|-------|
| Tests | 674 passing |
| Coverage | ~95% |
| MCP Tools | 113 total |
| Integrations | 9 (Pearl, Panopto, Kaltura, Opencast, Q-SYS, YouTube, EC20, LLM, Cloud) |

## Next Session
1. Push Cloud integration to remote (4 commits ahead)
2. Hardware: Connect Pearl Mini and EC20 to network
3. Verify EC20 REST API endpoints with real hardware
4. Launch readiness: CI/CD, PyPI publishing, v1.0 tag
5. Demo video: Pearl Mini + EC20 + Cloud AI workflow
