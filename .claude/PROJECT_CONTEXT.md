# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-01-23

## Status
MCP server for Epiphan Pearl video capture devices. Phase 4 (AI-powered video analysis) implemented with OpenRouter integration supporting Claude, Gemini, DeepSeek, and Qwen models. 165 tests passing with 93% coverage.

## Today's Focus
1. [x] Security scan - secrets audit complete, no issues
2. [x] Dependency audit - pydantic CVE-2024-3772 noted (version already compliant)
3. [x] Code review - new AI tools reviewed, clean architecture
4. [x] Tests - 165 passed, 93% coverage
5. [ ] Commit uncommitted changes (7 modified + 5 new files)

## Done (This Session)
- Audited 7 modified files + 5 untracked files
- Verified no hardcoded secrets in codebase or git history
- Ran full test suite with coverage
- Created PROJECT_CONTEXT.md

## Blockers
None - ready for commit

## Tech Stack
Python 3.11+ | FastMCP | httpx | Pydantic v2 | OpenRouter (multi-model gateway)

## Recent Changes
- Added AI-powered analysis tools (5 new MCP tools)
- LLM integration via OpenRouter (not OpenAI - per project rules)
- New modules: `src/epiphan_mcp/llm/` and `src/epiphan_mcp/tools/ai_tools.py`
- Comprehensive tests for all new functionality

## Next Session
- Consider increasing test coverage for OpenRouter error paths (currently 68%)
- Pin pydantic to `>=2.4.0` for CVE mitigation
- Document new AI tools in README.md
