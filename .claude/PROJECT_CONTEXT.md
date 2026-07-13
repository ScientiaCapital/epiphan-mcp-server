# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-07-12

## Status
**Echo360 (EchoVideo) integration shipped** — client + 6 tools (OAuth2 client-credentials with single-use refresh-token rotation, regional base URLs, Capture Intake signed-URL upload), following the YuJa convention. **v1.2.0 tagged and released** (21/21 typed schemas + YuJa). Server now registers **130 tools across 11 integrations**. Full suite **1,309 passed / 7 skipped**, mypy strict clean, ruff clean. **GTM Canvas/Blackboard wedge v1 shipped**: a free DNS/HTTPS subdomain probe (no CRM/tech-scraper can see LMS subdomains) classified 344 warm Higher-Ed domains — 112 Canvas / 44 Moodle / 25 Blackboard / 2 Brightspace / 141 Unknown. `BACKLOG.md` given a full cleanup pass — every stale "gap"/"unexposed method" table verified against current code and resolved or removed.

## Today's Focus
1. [x] Ship v1.2.0 (tag + push) for yesterday's 21/21 schemas + YuJa
2. [x] Build Echo360 integration (client + 6 tools + 38 tests)
3. [x] GTM Canvas/Blackboard wedge — subdomain probe (real data, not deferred this time)
4. [x] Full BACKLOG.md cleanup pass (verified against code, not just re-dated)
5. [ ] GTM wedge v2 — Apollo/Clay enrichment for 141 Unknown-LMS domains (approved, carried to tomorrow)

## Done (This Session)
- [x] `chore(release)`: v1.2.0 tagged + pushed — pyproject.toml/server.json synced, tools_count/integrations corrected in server.json
- [x] `feat(echo360)`: Echo360 client (`integrations/echo360.py`) + 6 tools + `tests/test_echo360.py` (38 tests); OAuth2 client-credentials with single-use refresh-token rotation (novel vs. Panopto/YuJa auth); 429 rate-limit surfacing; registered in server (130 tools / 11 integrations)
- [x] Docs: README/CLAUDE.md/CHANGELOG/.env.example synced to 130 tools, 11 integrations, 1,316 test count in dev docs; CHANGELOG `[Unreleased]` properly promoted to `[1.2.0]`
- [x] GTM: ran subdomain-probe LMS detection (documented as reusable method in project memory `lms-detection-for-gtm`); real counts across 344 institutional domains; top-10 outreach list with deal counts
- [x] Security sweep: gitleaks clean across 99 commits, manual secret-pattern scan clean
- [x] Observer audit: 1 new SMELL (Echo360 unvalidated endpoints, same class as YuJa's) — no BLOCKER/CRITICAL/RISK
- [x] BACKLOG.md: verified every "gap"/"unexposed method" entry against `tools/__init__.py` — all resolved, tables collapsed; fixed README's misleading `pip install epiphan-mcp` (confirmed NOT on PyPI via `pip index versions`)
- [x] Portfolio metrics captured (see below)

## Blockers
None

## Tomorrow
(1) **GTM wedge v2**: Apollo tech-stack + Clay company enrichment on the 141 Unknown-LMS domains (Tim-approved credits; use `epiphan-ai-mcp-guide-skill` toolset) — try an extended-pattern subdomain probe first (free, likely converts 50%+ on its own). (2) **Validate YuJa + Echo360 endpoints** against live instances (both MEDIUM, both same root cause — vendor gates full API docs behind login). (3) **PyPI publish status** — confirmed NOT live this session; either actually publish or stop implying it in docs. (4) Reply to Vadim re: fleet-timeout fix (carried item, unconfirmed sent).

## Tech Stack
Python 3.11+ | FastMCP | httpx (async) | Pydantic v2 | pydantic-settings | pytest + respx | ruff + mypy (strict)

## Links
- GitHub: https://github.com/ScientiaCapital/epiphan-mcp-server
- silkroute (MCP client): https://github.com/ScientiaCapital/silkroute
- Pearl API docs: https://www.epiphan.com/userguides/pearl-api/
- YuJa API: https://support.yuja.com/hc/en-us/articles/360049580714-YuJa-API
- Echo360 API/SDK docs: https://support.echo360.com/hc/en-us/articles/360038693311-EchoVideo-API-and-SDK-Documentation
- GTM wedge report (local only, not pushed): `.claude/gtm/canvas-wedge-2026-07-12.md`

---

## Portfolio Capture — 2026-07-12

### Output (this session)
- Commits: 4 (`acd08ec` release, `50fca6e` Echo360, `a473b63` end-day sync, plus README PyPI fix pending commit)
- Lines shipped (Echo360 commit): 1,729 insertions / 15 deletions — backend 983 (client + tools + registration), tests 693, docs 59
- Features: 1 (Echo360 integration, 6 tools) | Fixes: 0 (no bugs this session; Panopto fix was yesterday) | Chores: 2 (release, end-day sync)
- Full calendar-day total (git log, includes prior sessions): 40 commits, 22 feat, 2 fix

### Quality
- Observer CRITICALs/BLOCKERs resolved: 0 (none existed)
- New SMELL logged: Echo360 endpoint paths unverified against live Swagger (consistent with, not worse than, the existing YuJa smell)
- Tech debt prevented: wire contract pinned for Echo360 at build time (would have silently broken MCP clients on a future field rename); PyPI install instructions caught before a user hit a real `pip install` failure

### Cost
- Session-day spend: $339.77 | MTD: $457.97 (98/mo budget note: Tim confirmed this is an Epiphan Video company account — budget figures are not a constraint, see project memory)

### GTME Value
- GTM motion enabled: Canvas/Blackboard LMS wedge gives sales a data-backed target list (112 warm Canvas accounts with active deals) where none existed — HubSpot literally cannot answer "which LMS does this school run," and this closes that gap for free
- Operational leverage: subdomain-probe method is reusable and documented in project memory — next Higher-Ed prospecting pass doesn't require re-deriving the approach
- Portfolio positioning: 11th CMS/AV integration in 5 months (Panopto→Kaltura→Opencast→Q-SYS→YouTube→EC20→Cloud→YuJa→Echo360) demonstrates sustained integration-breadth velocity, now the broadest surface of any AV-hardware MCP server
- Skill demonstrated: revops data-quality diagnosis (identifying a CRM blind spot) + free-tooling problem-solving (subdomain probe) instead of defaulting to paid enrichment

## Portfolio metrics ledger
- Appended to `~/.claude/portfolio/daily-metrics.jsonl` (note: this file accumulates one entry per script run today, not deduped per calendar day — the last entry, `{commits:40, features:22, fixes:2, cost:339.77}`, is the cumulative full-day figure)

---

Tomorrow: GTM wedge v2 (Apollo/Clay enrichment, 141 Unknowns) + YuJa/Echo360 live-instance validation | main session | Observer notes: 2 MEDIUM unvalidated-endpoint smells (YuJa + Echo360, same root cause) — top unresolved flag

_Updated at end-of-day close. 2026-07-12._
