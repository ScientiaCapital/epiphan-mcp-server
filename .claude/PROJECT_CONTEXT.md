# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-07-12

## Status
Both of Vadim's critiques (timeout, typed schemas) fixed, merged, and pushed. Reply sent to Vadim. Now also a verified, documented MCP client target — silkroute's new `mcp_bridge` drives this server over stdio end-to-end (README compatibility table updated). 15 tool modules still need the typed-schema conversion (recipe established, not blocking).

## Done (This Session)
- [x] `fix(fleet)`: dedicated `PEARL_FLEET_TIMEOUT_PER_DEVICE` (default 5s) — real cause of the "lacks parallel execution" critique was the 30s timeout, not missing concurrency
- [x] Typed Pydantic params/returns for fleet, device, system, recording, storage tool modules
- [x] `tests/test_tool_schemas.py` contract meta-test with shrinking `NOT_YET_CONVERTED` allowlist
- [x] Reply sent to Vadim (2026-07-12) — confirmed by Tim, closes the loop with live numbers (5.1s vs 30.1s, 5.9x)
- [x] README updated: SilkRoute added to the MCP-client compatibility table, linking to its "Try the AV demo" section
- [x] No source changes needed to support the AV demo — `PEARL_DEVICES` already accepted the mock server's host:port, proving the server's existing design was already flexible enough

## Blockers
None

## Tomorrow
Tomorrow: convert remaining 15 modules to typed schemas via the established recipe (ai_tools, cloud, discovery, ec20, inputs, kaltura, layout, maintenance, opencast, panopto, publishers, qsys, schedule, streaming, youtube) — ~1-2h each | Consider running a live end-to-end check against Vadim's real 15-device fleet once he re-tests | Observer notes: none run this session — reviewed inline instead

## Tech Stack
Python 3.11+ | FastMCP | httpx (async) | Pydantic v2 | pydantic-settings | pytest + respx | ruff + mypy (strict)

## Links
- GitHub: https://github.com/ScientiaCapital/epiphan-mcp-server
- silkroute (MCP client): https://github.com/ScientiaCapital/silkroute
- Pearl API docs: https://www.epiphan.com/userguides/pearl-api/

---

_Updated by AV demo cross-repo session. 2026-07-12._
