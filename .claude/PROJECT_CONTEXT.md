# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-01-23

## Status
MCP server for Epiphan Pearl video capture devices. Sprint 2 complete - added 7 new MCP tools + 2 AI moat features (predictive maintenance). 197 tests passing with 92% coverage. Ready for launch preparation.

## Today's Focus
1. [x] Sprint 2 MCP Tools (get_stream_status, add_bookmark, single_touch_start/stop, get_scheduled_events, list_layouts)
2. [x] AI Moat Features (predict_storage_full, get_device_health_score)
3. [x] TDD implementation - all tools test-first
4. [x] Code review and quality checks
5. [x] Commit and push to main

## Done (This Session)
- Implemented 7 new MCP tools using TDD (31 new tests)
- Added predict_storage_full (AI predictive maintenance)
- Added get_device_health_score (AI health scoring 0-100)
- Fixed ruff and mypy linting issues
- Committed ee6caab: "feat: Add Sprint 2 MCP tools and AI predictive maintenance"
- Pushed to origin/main
- Security audit: no hardcoded secrets in code or git history
- All 197 tests passing, 92% coverage

## Blockers
None

## Tech Stack
Python 3.11+ | FastMCP | httpx | Pydantic v2 | OpenRouter (multi-model gateway)

## Metrics
| Metric | Value |
|--------|-------|
| Tests | 197 passing |
| Coverage | 92% |
| MCP Tools | 19 total |
| AI Tools | 6 (4 vision + 2 predictive) |

## Next Session
1. Update README.md with new tools documentation
2. Sprint 3: Additional moat features (if desired)
3. Consider PyPI publish when ready to exit stealth mode
4. Outreach to Epiphan Higher Ed accounts
