# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-07-13 (end of day)

## Status
Clean close, everything pushed (origin/main @ 18d6e96). Full `/begin`→`/end` day: start-day observer audit found 2 WARNINGs + 2 RISKs + smells; every unblocked finding was fixed and merged same-day across two parallel branches. Suite at **1,334 passed / 7 skipped**, mypy strict + ruff clean, gitleaks 0 leaks. GTM: HubSpot noise-cleanup scoped and verified — awaiting Tim's go before any CRM write.

## Tomorrow's Focus (sprint-ready)
1. [ ] **GTM — HubSpot cleanup (Tim gate, then 10 min)**: confirm the 6 junk records / 5 domains (berkley.edu ×2 incl. fake "Berkeley Law", boston.edu ≠ BU, i2itech.com, laregents.edu, victorchang.edu.au, taboradelaide.edu.au — IDs in memory `lms-detection-for-gtm.md`), pick mechanism (industry patch vs `[AI]` review list), then execute. **Do NOT touch the other ~39 "Not-LMS" domains — they're real universities, LMS just not visible to the probe.**
2. [ ] **GTM — 13 SSO-only domains**: Tim's 5-second glance (list in wedge report v4 residual table); after that, Apollo/Clay credits go to unmasking the 100 decision-maker contacts when top-10 Canvas accounts move to outreach
3. [ ] **Vadim draft**: verify recipient (draft r2770306474456285798 addressed to vkalinsky@epiphan.com, inferred) + send, or move text to Slack
4. [ ] **PyPI publish decision**: still NOT live; publish v1.2.x or keep docs honest
5. [ ] **Live-endpoint validation** (all blocked on credentials/hardware): YuJa + Echo360 collection endpoints (MEDIUM), EC20 placeholder paths (MEDIUM, `ec20.py:15`)
6. [ ] `.env` still missing locally (`cp .env.example .env` + credentials before any live-hardware work)
7. [ ] Optional code (LOW): Opencast multipart still reads on the event loop — streaming multipart or multi-step ingest, ~1-2h

## Done (This Session)
- [x] **feat(cms)**: Panopto + YuJa list tools surface `truncated` flag — same silent-pagination bug class Echo360 got fixed for; extraction generalized into shared `integrations/_pagination.extract_page` (Echo360 delegates); Panopto `TotalNumberOfResults` in heuristics; 8 TDD tests
- [x] **test(kaltura)**: first-ever coverage of the 5-step streamed upload workflow (chunk order, resume/resumeAt, finalChunk) — teammate branch
- [x] **docs(retry) + test**: busy-retry on POST/PATCH pinned as deliberate (busy = pre-execution reject) with comment + regression test
- [x] **chore(deps)**: `httpx<1`, `pydantic<3`, `pydantic-settings<3` caps; author email fixed
- [x] **GTM**: HubSpot cleanup scoped — corrected "46 noise domains" to **7 actual noise / 39 real universities**; 6 HubSpot records verified by ID; tallinn.ee has no company record; saved to memory
- [x] Vadim reply drafted in Gmail (both fleet fixes)
- [x] End-day: observers dispositioned + archived + reset, BACKLOG updated (2 stale items closed), gitleaks clean, metrics logged, main pushed

## Blockers
None. (Tim-gated: HubSpot write confirmation, SSO glance, PyPI decision, vendor credentials.)

## Tech Stack
Python 3.11+ | FastMCP | httpx (async) | Pydantic v2 | pydantic-settings | pytest + respx | ruff + mypy (strict)

## Links
- GitHub: https://github.com/ScientiaCapital/epiphan-mcp-server
- GTM wedge report (LOCAL ONLY, gitignored — contains customer/deal data): `.claude/gtm/canvas-wedge-2026-07-12.md`
- Pearl API docs: https://www.epiphan.com/userguides/pearl-api/

---

Tomorrow: HubSpot cleanup execute (post-confirm) + SSO glance + Vadim send + PyPI decision | main session | Est: 1-2h agent time, GTM-heavy, code work optional | Observer notes: 0 CRITICAL/BLOCKER open; top flags are the 2 MEDIUM unvalidated-endpoint items (YuJa/Echo360) + EC20 placeholders — all credential/hardware-gated

_Updated at end of day 2026-07-13._
