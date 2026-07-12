# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-07-12

## Status
**Typed-schema conversion COMPLETE (21/21)** — `NOT_YET_CONVERTED` is empty; every tool in the server now enforces fully described input/output schemas via the contract meta-tests. **YuJa integration shipped** (first new video-CMS since the Kaltura batch): static authToken auth, signed-URL 2-step S3 upload, 6 tools, wire contract pinned in the guard. Server registers **124 tools across 10 integrations**. Bonus: fixed a latent Panopto S3-upload bug (sync file object through httpx.AsyncClient — every real upload would have failed) found via YuJa's transport-level tests. Full suite **1246 passed / 7 skipped**, mypy strict clean, ruff clean.

## Today's Focus
1. [x] Convert last 5 modules (schedule, publishers, ai_tools, cloud, ec20) — 21/21
2. [x] Build YuJa integration (client + 6 tools + 32 tests)
3. [ ] GTM wedge (deferred by scope decision — budget at 361% of monthly cap)

## Done (This Session)
- [x] `feat(schedule|publishers|ai_tools|cloud|ec20)`: typed params + return models for the final 42 tools (~33 new result models); all pre-conversion wire keys registered with the model-field guard; `NOT_YET_CONVERTED` emptied
- [x] `feat(yuja)`: YuJa client (`integrations/yuja.py`) + 6 tools + `tests/test_yuja.py`; audit logging on upload/delete; registered in server (124 tools)
- [x] `fix(panopto)`: S3 upload streamed as async byte iterator — sync-file `content=` raised RuntimeError on every real upload; regression test added
- [x] Drive-by: migrated stale dict-access assertions in hardware-gated integration tests (fleet_health_report, get_recording_status)
- [x] Docs: README/CLAUDE.md counts → 124 tools, 10 integrations, 1,253 tests
- [x] Observer record updated (0 CRITICAL/BLOCKER; 2 INFO logged)

## Blockers
None

## Tomorrow
(1) **GTM Canvas-breach wedge** (time-sensitive, deferred today): pull Higher-Ed accounts (HubSpot/Apollo), flag Canvas/Blackboard shops for lecture-capture outreach. (2) **Echo360 integration** — GA summer 2026, dual OAuth2+Basic auth; confirm internal API spec/sandbox first. (3) Validate YuJa endpoints against a live instance (list/channels paths designed from public docs; upload flow verified against YuJa's published examples) — YuJa help-center pages are fetch-blocked, so endpoint shapes for list/channels are best-effort. (4) Consider release: v1.2.0 tag for 21/21 schemas + YuJa.

## Tech Stack
Python 3.11+ | FastMCP | httpx (async) | Pydantic v2 | pydantic-settings | pytest + respx | ruff + mypy (strict)

## Links
- GitHub: https://github.com/ScientiaCapital/epiphan-mcp-server
- silkroute (MCP client): https://github.com/ScientiaCapital/silkroute
- Pearl API docs: https://www.epiphan.com/userguides/pearl-api/
- YuJa API: https://support.yuja.com/hc/en-us/articles/360049580714-YuJa-API

---

_Updated at 21/21 + YuJa milestone. 2026-07-12._
