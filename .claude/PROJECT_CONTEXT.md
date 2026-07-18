# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-07-18 (end of day)

## Status
Full handover-prep pass for Vadim + Epiphan engineers, done end-to-end: confidentiality
audit (this repo + epiphan-openav-bridge + silkroute), repo hygiene, test-coverage gaps
closed, CI hardened, and a code-review pass with its findings fixed. **4 commits on
`main`, all local — NOT yet pushed to `origin/main`** (currently 4 ahead). Suite at
**1,414 passed / 7 skipped**, mypy strict + ruff clean, coverage gate live at 80%
(measured 85%). No secrets/strategy leaks found in a final grep re-sweep across all
three repos.

## Next Session's Focus
1. [ ] **Push to origin** — `git push`, 4 unpublished commits (`d91c314..5dbf75d`).
   Nothing from today is visible to anyone else until this happens.
2. [ ] **Hardware validation — the single biggest remaining gap.** No `.env` has ever
   existed here; nothing in this repo (or the Lane-A spike, or `scripts/validate_ec20.py`
   /`validate_cms.py`) has ever touched a real Pearl, EC20, or OpenAV device. This is the
   actual gap between "130 tools, tests pass" and proof they work. Also the blocker for
   the Vadim live demo. Needs: `cp .env.example .env` + real Pearl creds, then
   `pytest -m integration` (7 tests) + `run.py --live` (Lane-A spike).
3. [ ] **PyPI publish decision** — still not live (`QUICKSTART.md`/`server.json` both say
   "not yet published"). Publish v1.3.0 or keep docs honest as-is.
4. [ ] **`server.json` MCP-registry validity** — no `$schema`, non-reverse-DNS `name`,
   missing `packages`/`remotes` block. Only matters if official-registry submission is
   still a live goal.
5. [ ] **`fastmcp<3` ceiling** — blocks fastmcp 3.4.4, which likely carries the fixed
   transitive deps for the remaining pip-audit CVEs (pyjwt/starlette/python-multipart,
   all via `mcp`). Bumping past `<3` is a real major-version upgrade needing its own
   compatibility pass against `server.py` — don't do it silently.
6. [ ] **gtm-brain-skill rename** (separate repo: `skills/archived/gtm-brain-skill`) —
   Tim wants it rebuilt under a ProAV-specific name, not sales/BDR. Source is archived,
   not deleted; Aura creds untouched in `skills/.env`.
7. [ ] Deferred, no urgency: full research report on `epiphan-pi-strategic-report.md`
   for Victor and George (memory: `strategic-report-followup.md`).

## Done (This Session)
- [x] **Neo4j/context-graph review + direction decision**: graph investment is
  ProAV/fleet-vertical (`docs/proav-ontology.md` written, pins Device/Incident/Fix/
  Technician/Venue/Integration/Vertical schema), not sales — gtm-brain-skill archived
  pending a ProAV-specific rename
- [x] **Confidentiality audit** across epiphan-mcp-server + epiphan-openav-bridge +
  silkroute: removed `docs/SPRINT_REPORT.md` (named "Epiphan themselves" as biggest
  competitive threat), removed tracked pointers to `epiphan-pi-strategic-report.md` in
  both sibling repos' `PROJECT_CONTEXT.md`, removed "before sharing with Vadim"
  narrative-framing section from silkroute's demo guide. Final grep re-sweep clean.
- [x] **Repo hygiene**: fixed `github.com/tmkipper` → `ScientiaCapital` drift everywhere
  (README/CHANGELOG/QUICKSTART/server.json/pyproject/llm headers); version bumped to
  1.3.0 (was under-versioned vs the already-advertised 130-tool/Echo360 count); added
  `SECURITY.md`; removed dead `autoresearch/` experiment harness; marked stale
  `docs/PRD.md`/`PRP.md` SUPERSEDED
- [x] **Test coverage gaps closed**: `tools/fleet_intelligence.py` (was wrongly reported
  as 0% by an earlier sweep — really just untested branches: storage/health/risk-level
  logic, fleet-status-failure path), `tools/schedule.py`'s
  create/pause/resume_event (zero coverage before), `switch_layout`'s error branches,
  `integrations/_pagination.py`. New: `tests/test_fleet_intelligence.py`,
  `tests/test_pagination.py`.
- [x] **CI hardened**: coverage gate `--cov-fail-under=80` (verified live, passes at
  85%), `tests/` now linted+format-checked (not just `src/`), non-blocking `pip-audit`
  step, unconditional `build` job on every PR (not just tags), weekly Dependabot.
- [x] **Code-review pass + fixes**: 9 unexplained `type: ignore` in `tools/kaltura.py`
  eliminated via a `TypedDict` on `_get_kaltura_config()`; the 2 remaining
  `ks`-nullability ignores in `integrations/kaltura.py` replaced with real
  `assert self._session is not None` (mypy narrowing, not suppression); triplicated
  `max_wait=300.0` upload timeout collapsed into `integrations/_upload.
  DEFAULT_UPLOAD_MAX_WAIT_SECONDS`; LLM client timeout now configurable
  (`LLM_REQUEST_TIMEOUT`) instead of hardcoded; `pytest>=9.0.3`/`python-dotenv>=1.2.2`
  floor pins fix 2 of the pip-audit CVEs, CI comment corrected to explain the rest are
  blocked behind the `fastmcp<3` ceiling, not "no upstream fix"

## Blockers
**Not pushed** — `main` is 4 commits ahead of `origin/main`, push before anyone else
(Vadim, Epiphan engineers) can see today's work. Otherwise Tim-gated: hardware
validation needs real `.env`+credentials; PyPI publish is a go/no-go call; gtm-brain
rename needs a name from Tim.

## Tech Stack
Python 3.11+ | FastMCP | httpx (async) | Pydantic v2 | pydantic-settings | pytest + respx | ruff + mypy (strict)

## Links
- GitHub: https://github.com/ScientiaCapital/epiphan-mcp-server (4 commits unpushed locally)
- Sibling repos touched today (confidentiality fixes uncommitted there, by design —
  each has its own unrelated in-progress work): `../epiphan-openav-bridge`,
  `../silkroute`
- Pearl API docs: https://www.epiphan.com/userguides/pearl-api/
- Full plan/status doc for this session: `~/.claude/plans/where-we-at-withthe-radiant-pudding.md`

---

Next session: push first, then hardware validation is the highest-leverage next step
(unblocks both the Vadim demo and the "does this actually work" question). Everything
else (PyPI, registry, fastmcp bump, gtm-brain rename) is a deliberate go/no-go call for
Tim, not blocked work.

_Updated at end of day 2026-07-18._
