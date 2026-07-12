# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-07-12

## Status
Typed-schema conversion now **16/21 modules** done and pushed. This session added the model-field wire-compat guard, converted the full CMS/AV batch (qsys, youtube, opencast, panopto, kaltura), cleared all pre-existing ruff debt in tests/, and passed an independent DA verification. Full suite **1042 passed / 7 skipped**, mypy strict clean, ruff clean (src + tests). `NOT_YET_CONVERTED` down to 5. All work committed and pushed (origin/main 0/0).

## Today's Focus
1. [x] Harden wire-compat guard + convert CMS/AV batch
2. [ ] Convert last 5 modules (ai_tools, cloud, ec20, publishers, schedule)
3. [ ] Build YuJa integration (first new video-CMS), then Echo360

## Done (This Session)
- [x] `test(schemas)`: model-field wire-compat guard (25 models) + `resolution` docstring fix + guard comment accuracy
- [x] `feat(qsys/youtube/opencast/panopto/kaltura)`: typed params + return models for all 5 CMS/AV integration modules (~40 tools, ~36 result models); integration no-`success` convention preserved
- [x] `style`: cleared pre-existing ruff debt in tests/ (SIM117×15, N806×9, F841×5, E402) — `ruff check tests/` now clean
- [x] `chore(observers)`: recorded typed-schema audit (0 CRITICAL/BLOCKER)
- [x] DA verification: PASS (1042 passed, no dropped/renamed keys, lint-safety confirmed)
- [x] Researched Echo360/YuJa/Canvas/Moodle APIs (see task notes) — YuJa chosen as first build

## Blockers
None

## Tomorrow
Tomorrow (in priority order): (1) Convert last 5 modules to typed schemas via the established recipe — ai_tools, cloud, ec20, publishers, schedule — finishes the surface at 21/21 and empties NOT_YET_CONVERTED. (2) Build **YuJa** integration first (decided): direct platform REST API, mirror src/epiphan_mcp/integrations/panopto.py (async httpx client + token dataclass + exception hierarchy); YuJa uses a static `authToken` header + 2-step signed-URL PUT upload; Epiphan's own docs specify the minimum token perms. Then Echo360 (GA summer 2026, dual OAuth2+Basic auth — confirm internal API spec/sandbox first). Canvas/Moodle = lighter publish-to-LMS tools later. (3) GTM wedge (task #16, time-sensitive): Canvas-breach LMS-migration wave — pull Higher-Ed accounts (HubSpot/Apollo), flag Canvas/Blackboard shops for outreach. Open Qs: internal Echo360 spec? Canvas Studio vs Files? Moodle version targeting?

## Tech Stack
Python 3.11+ | FastMCP | httpx (async) | Pydantic v2 | pydantic-settings | pytest + respx | ruff + mypy (strict)

## Links
- GitHub: https://github.com/ScientiaCapital/epiphan-mcp-server
- silkroute (MCP client): https://github.com/ScientiaCapital/silkroute
- Pearl API docs: https://www.epiphan.com/userguides/pearl-api/

---

_Updated at CMS/AV batch checkpoint. 2026-07-12._
