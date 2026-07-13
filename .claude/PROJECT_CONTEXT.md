# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-07-12 (polish-day close)

## Status
**Tech-debt/polish day complete** — 7 commits (`9d6739b..eb3a11b`), all pushed, suite green at every commit (**1,311 passed / 7 skipped**, mypy strict + ruff clean, gitleaks clean). Six parallel audit agents swept all 19k src lines; every finding fixed or backlogged with justification. Net **-349 lines** (1,282 added / 1,631 deleted) — the codebase got smaller and safer. Earlier the same day: **v1.2.0 released**, **Echo360 integration shipped** (130 tools / 11 integrations), and the **GTM Canvas wedge** delivered real LMS data (113 Canvas / 35 Blackboard / 43 Moodle / 17 Brightspace across 344 warm Higher-Ed domains) plus a validated negative: Apollo/Clay tech-stack cannot detect LMS.

## Today's Focus
1. [x] v1.2.0 release (tag + push)
2. [x] Echo360 integration (client + 6 tools + 38 tests)
3. [x] GTM Canvas/Blackboard wedge (probe v1–v3, contacts found)
4. [x] Polish day: bugs/leaks fixed, audit drift reconciled, dead code deleted, fleet split, docs de-staled, consistency pass

## Done (This Session — polish day)
- [x] `fix(core)`: null-fallback bug (explicit JSON null → "None" string / TypeError crash), fleet LLM provider client leak, qsys socket+task leak on bad PIN, retry jitter — all with regression tests
- [x] `fix(audit)`: log_operation on every destructive/outbound tool (cloud command tools had fleet-wide RTMP-redirect power with zero trail); SENSITIVE_OPERATIONS reconciled; drift-guard meta-test; rtmp.start URL SSRF-validated; integration hosts format-checked
- [x] `refactor(dead-code)`: -651 lines, ~20 grep-verified-unreferenced models/methods
- [x] `refactor(fleet)`: fleet.py (1,210) → fleet.py + fleet_intelligence.py, single test patch-point preserved
- [x] `docs`: TECHNICAL_ROADMAP v0.8→v1.2 reality; CONTRIBUTING remote+tree fixed; 13 stale docstrings; "AI-powered" claim removed; GTM v3 correction in backlog
- [x] `refactor(consistency)`: 401/403→AuthError everywhere; `_resolve_host()` + `require_env()` dedup; 12× test fixture → 1; discovery log level
- [x] `refactor(upload)`: shared `stream_file()` (was byte-identical ×3)
- [x] Process fix: `.claude/gtm/` gitignored after a near-miss staging of the local-only customer-data report (caught pre-push, amended out, verified absent from history)

## Blockers
None

## Tomorrow (carried priorities)
1. **GTM wedge follow-ups**: human login-page glance for 78 Learn-portal + 57 Unknown domains (validated as the ONLY reliable resolver — not paid enrichment); Apollo/Clay credits go to unmasking the 100 found decision-maker contacts when top-10 Canvas accounts move to outreach
2. **YuJa + Echo360 live-endpoint validation** (both MEDIUM, same root cause — vendor docs gated behind login)
3. **PyPI publish decision**: confirmed NOT live; either publish or keep docs honest (README already fixed)
4. **Deferred-by-design** (BACKLOG.md): retry-on-POST idempotency (behavior change), Echo360 pagination flag, blocking upload reads
5. Reply to Vadim re: fleet-timeout fix (still unconfirmed sent)

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

Tomorrow: GTM login-page pass + YuJa/Echo360 live validation | main session | Observer notes: 0 CRITICAL/BLOCKER; top flags are the 2 MEDIUM unvalidated-endpoint smells (YuJa/Echo360) + deferred retry-on-POST idempotency

_Updated at polish-day close. 2026-07-12._
