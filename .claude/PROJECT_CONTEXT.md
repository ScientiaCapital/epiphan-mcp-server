# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-07-12 (second session — sprint start)

## Status
Second session of 2026-07-12, starting from a clean main (in sync with origin, suite green at 1,311 passed / 7 skipped). Earlier today: v1.2.0 released, Echo360 shipped (130 tools / 11 integrations), GTM Canvas wedge v1–v3 (113 Canvas confirmed), full polish day (7 commits, −349 net lines, 6-agent audit). This session: clear the three deferred-by-design backlog code items + automate the GTM login-page pass for the 135 unresolved domains.

## Today's Focus
1. [x] Retry-on-POST idempotency fix (`fix/retry-idempotency`) — POST/PATCH retry only on connect-phase errors
2. [x] Echo360 pagination `truncated` flag (`fix/echo360-pagination-flag`)
3. [x] Non-blocking upload reads via `asyncio.to_thread` (`fix/nonblocking-upload-reads`)
4. [x] Pin `fastmcp<3` in pyproject.toml (folded into last branch)
5. [x] GTM login-page pass (automated): resolved 40/135, residual classified → v4 section in wedge report

## Done (This Session)
- [x] `fix(client)`: POST/PATCH retry restricted to connect-phase failures (ReadTimeout after send no longer duplicates side effects); busy-retry preserved; 4 tests
- [x] `fix(fleet)` **found during verification**: unreachable devices were reported online whenever jittered retries beat the fleet timeout — `get_system_status` now re-raises transport errors; deterministic test; test_fleet.py 36s → 6s (flake introduced by yesterday's jitter fix, killed for good)
- [x] `feat(echo360)`: list tools expose `truncated` flag from envelope pagination hints; page fetching still deferred to live-Swagger validation
- [x] `fix(upload)`: `stream_file()` reads via `asyncio.to_thread` (event-loop-responsiveness test proves it); Kaltura chunk loop dedup'd onto `stream_file`; Opencast limitation documented; `fastmcp<3` pinned
- [x] GTM v4 pass: 3-stage automated login-page glance (httpx markers/SSO-redirects → Playwright render → AI screenshot review of 88 shots; classifier spot-check 5/5). 40/135 resolved (Canvas 18, Moodle 12, Brightspace 4, Blackboard 3, Sakai 1, OLAT 1, iSpring 1); residual 95 fully classified (46 Not-LMS/CRM noise, 13 SSO-only for human glance, 36 blank/unreachable). Appended to wedge report (local-only)
- Suite: 1,311 → **1,324 passed** / 7 skipped, mypy strict + ruff clean at every merge

## Blockers
None

## Tomorrow (carried priorities)
1. **GTM**: Tim's 5-second glance on the 13 SSO-only domains (list in wedge report v4 residual table); Apollo/Clay credits go to unmasking the 100 decision-maker contacts when top-10 Canvas accounts move to outreach; HubSpot segmentation cleanup now has 46 confirmed Not-LMS/noise domains as input
2. **YuJa + Echo360 live-endpoint validation** (both MEDIUM, vendor docs gated behind login)
3. **PyPI publish decision**: confirmed NOT live; either publish or keep docs honest (README already fixed)
4. Reply to Vadim re: fleet-timeout fix (still unconfirmed sent) — note the NEW fleet fix (offline-detection race) is also worth mentioning to him
5. `.env` still missing locally (`cp .env.example .env` + credentials before any live-hardware work)

## Tech Stack
Python 3.11+ | FastMCP | httpx (async) | Pydantic v2 | pydantic-settings | pytest + respx | ruff + mypy (strict)

## Links
- GitHub: https://github.com/ScientiaCapital/epiphan-mcp-server
- GTM wedge report (LOCAL ONLY, gitignored — contains customer/deal data): `.claude/gtm/canvas-wedge-2026-07-12.md`
- Pearl API docs: https://www.epiphan.com/userguides/pearl-api/
- Echo360 API/SDK docs: https://support.echo360.com/hc/en-us/articles/360038693311-EchoVideo-API-and-SDK-Documentation

---

## Portfolio Capture — 2026-07-12 (full day)

### Output
- Commits: 49 across the calendar day (22 feat, 4 fix); polish session alone: 7 commits, 48 files, 1,282+/1,631- (src 965+/1,395-, tests 210+/168-)
- Features: v1.2.0 release, Echo360 integration (6 tools), GTM wedge v1-v3
- Fixes: 2 resource leaks, 1 systemic null bug, audit-policy drift, retry jitter

### Quality
- 6-agent audit: 2 High leaks + 2 High audit gaps + 1 systemic bug found and fixed same-day; drift-guard meta-test prevents recurrence
- Tech debt removed: 651 dead lines, 12× fixture dup, 3× stream helper dup, 2× config dup
- Honest-docs pass: roadmap/CONTRIBUTING/README no longer claim untrue things (incl. PyPI)

### GTME Value
- GTM: data-backed Canvas wedge list (113 confirmed Canvas warm accounts, top-10 with deal counts, 100 masked decision-maker contacts) + a validated negative worth real money — paid enrichment can't detect LMS, the free probe can
- Skill demonstrated: revops data-quality diagnosis, security-relevant audit reconciliation, large-scale verified refactoring

---

Tomorrow: 13 SSO-only domains human glance (5 min) + YuJa/Echo360 live validation + PyPI decision + Vadim reply | main session | Est: 2-3h, live-validation blocked on vendor credentials + `.env` | Observer notes: 0 CRITICAL/BLOCKER; top flags remain the 2 MEDIUM unvalidated-endpoint smells (YuJa/Echo360) — retry-idempotency/pagination/upload-reads all cleared this session

_Updated at second-session close. 2026-07-13._
