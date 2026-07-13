# Observer: Architecture Report

_Start-day audit 2026-07-13._

## Findings

[RISK] — panopto.py / yuja.py list tools — Same silent-pagination bug class Echo360 fixed yesterday: `list_folders`/`list_sessions` (Panopto) and `list_videos`/`list_channels` (YuJa) send no paging params and expose no "more pages exist" signal; first page presented as complete — impact: incomplete results presented as complete to the LLM (sprint task #1: port `_extract_page` truncation pattern, consider shared helper)

[RISK] — integrations/ec20.py:15 — Sole TODO in src tree: every EC20 REST endpoint path is a best-effort placeholder pending validation against real hardware — impact: blocks EC20-specific feature work until paths confirmed; not a server-wide blocker

[SMELL] — pyproject.toml — `httpx>=0.25.0`, `pydantic>=2.4.0`, `pydantic-settings>=2.0.0` have no upper bounds while fastmcp was defensively capped `<3`; a future httpx 1.0 / pydantic 3 could break fresh installs — fix: add upper bounds (sprint task #3). Also author email is placeholder `tim@example.com`

[SMELL] — commit 4efcd83 — `fastmcp<3` pin bundled into unrelated upload fix commit; self-noted as carried-forward backlog item — not actionable (merged), noted for commit hygiene only

## Clean categories
- Typed-schema contract: intact — every tool module has `register(server)`; `NOT_YET_CONVERTED` empty; wire-compat guard active in tests/test_tool_schemas.py
- Scope creep: none beyond the pin-bundling smell above
- Upload streaming duplication: properly de-duplicated onto `_upload.stream_file` (Panopto/Kaltura/YuJa); Opencast divergence documented
- Dependencies: fastmcp<3 present; pydantic>=2.4.0 carries CVE-2024-3772 floor; requires-python>=3.11 consistent

## BLOCKERS
None — sprint gate open.
