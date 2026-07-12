# Observer: Code Quality Report

**Date:** 2026-07-12 (morning /begin audit + end-of-sprint addendum)
**Project:** epiphan-mcp-server
**Observer:** Inline read-only audit (plan-mode /begin) — Claude Fable 5

**Session scope (morning):** `git diff HEAD~5..HEAD` — CMS/AV typed-schema
batch (qsys, youtube, opencast, panopto, kaltura) + backlog sync. Findings:
0 CRITICAL, 0 new TODO/FIXME/HACK/XXX markers, 0 silent exception handlers.
Prior DA verification (1042 passed) accepted; heavy re-audit skipped.

**Sprint addendum (same day):** typed-schema conversion completed 21/21
(schedule, publishers, ai_tools, cloud, ec20) + YuJa integration shipped.
- `NOT_YET_CONVERTED` now empty — schema contract enforced server-wide.
- All new/converted result models registered in `_MODEL_MUST_KEEP_FIELDS`.
- `[INFO]` Drive-by fix: stale dict-access assertions in hardware-gated
  integration tests (`fleet_health_report`, `get_recording_status`) left
  from earlier conversions — would have raised TypeError on next
  `pytest -m integration` run. Fixed in the ai_tools commit.
- `[INFO]` Latent pattern found via YuJa tests: passing a sync file object
  as `content=` to `httpx.AsyncClient.put` raises at request time. YuJa
  uses an async chunk generator; `panopto.py:upload_file_to_s3` has the
  same sync-file pattern and its tests mock above the transport — worth a
  follow-up check against a live Panopto instance. Logged to backlog.
- Final: 1246 passed / 7 skipped, mypy strict clean, ruff clean.

---

# Observer: Code Quality Report

**Date:** 2026-07-12
**Project:** epiphan-mcp-server
**Observer Model:** Claude Sonnet 5 (Observer Full)

**Session scope:** `git diff HEAD~7..HEAD` — typed-schema conversion of 5 tool
modules (discovery, layout, maintenance, streaming, inputs), additions to
`src/epiphan_mcp/models.py` and `src/epiphan_mcp/tools/params.py`, matching
test migrations, and 2 chore/handoff commits. Reported baseline: 876 passed /
7 skipped, mypy strict clean, ruff clean, gitleaks clean (not independently
re-run here; this audit focuses on what static checks won't catch).

---

## Critical (must fix before merge)

_No findings._ No dropped/renamed keys, no silent failures, no unused
imports, and no new TODO/FIXME/HACK/XXX/TEMP markers were found in the diff.

---

## Warnings (fix or log to backlog)

`[WARNING]` — `tests/test_tool_schemas.py` (wire-compat section,
`_PRE_CONVERSION_KEYS` / `_assert_wire_compatible`) — the schema contract
test's wire-compatibility check only covers two Phase-1 fleet tools
(`get_fleet_status`, `batch_start_recording`). None of the 5 modules
converted in *this* batch (discovery, layout, maintenance, streaming, inputs)
have a corresponding `_PRE_CONVERSION_KEYS` entry, so a future edit to any of
these 5 modules that drops or renames a key would not be caught by this test
— only by the (weaker) "every output field has a description" test, which
doesn't check key survival. Manual diff review in this audit found no
dropped/renamed keys in the current batch, but the regression is currently
unguarded by CI going forward. — Suggested fix: add one `_PRE_CONVERSION_KEYS`
entry per converted tool (e.g. `list_layouts` normal+error,
`get_stream_status` normal+error, `create_network_input` normal+error),
mirroring the existing fleet-tool pattern.

---

## Info (nice to have)

`[INFO]` — `src/epiphan_mcp/tools/streaming.py:298-306` (`get_channel_preview`)
and `src/epiphan_mcp/tools/inputs.py:376-384` (`get_input_preview`) — the
`resolution` field is now unconditionally passed to the result model
(`resolution=resolution`), whereas the pre-conversion dict only set the
`"resolution"` key when the caller explicitly supplied a value
(`if resolution: result["resolution"] = ...`). The field description in
`models.py:1063-1065` / `models.py:1149-1151` still says *"present only when
explicitly specified"*, which is no longer literally true — the key is now
always present in `structured_content`, just `null` when not specified. This
is additive (no key ever disappears or renames), consistent with the
project's own documented convention (`models.py:694-698`), so it is not a
wire-compat break, just a stale doc string. — Suggested fix: reword to
"Requested resolution, or null when using the device default."

`[INFO]` — No new TODO/FIXME/HACK/XXX/TEMP markers introduced in any of the 5
converted tool modules, `models.py`, or `params.py`. Marker count delta: 0.

`[INFO]` — No empty `except` blocks, bare `except:`, or
`except Exception: pass` patterns introduced. Every touched exception handler
(`PearlAPIError`, `ValueError`, `ValidationError`) returns a typed
error-result model with `error=str(e)`; the one pre-existing bare
`except PearlAPIError:` in `maintenance.py:169` (unchanged by this diff)
degrades gracefully and appends a message to `issues`, it does not swallow
silently.

`[INFO]` — No unused imports found. Spot-checked all 5 modules; `Any` remains
needed in `discovery.py` and `inputs.py` for local `dict[str, Any]`
annotations, and `BaseModel` in `streaming.py` is used by the
`isinstance(c, BaseModel)` guard in `list_channels` (the one place a Pearl
client method returns Pydantic model instances rather than plain dicts, and
the only place in this diff that needed an explicit `model_dump()` bridge).

`[INFO]` — No new third-party dependencies added to `pyproject.toml` in this
diff.

`[INFO]` — Every touched tool function has at least one exercised unit test:
`discover_device`/`clear_discovery_cache` (`tests/test_discovery.py`);
`start_stream`/`stop_stream`/`get_stream_status`/`list_channels`/
`list_publishers`/`get_channel_preview` (`tests/test_streaming.py`);
`create_network_input`/`get_input_settings`/`update_input_settings`/
`list_outputs`/`set_output_source`/`get_input_preview`
(`tests/test_inputs.py`); `list_layouts`/`switch_layout`/`add_bookmark`/
`predict_storage_full`/`get_device_health_score` (`tests/test_server.py`).
The latter two tool modules have no dedicated `test_layout.py` /
`test_maintenance.py` files, but that predates this diff and is not a
coverage regression introduced by it.

---

## Code Quality Metrics

| Metric | Value |
|--------|-------|
| Files scanned (diff scope) | 14 (5 tool modules, models.py, params.py, 6 test files, 2 chore/docs files) |
| TODO/FIXME/HACK/XXX/TEMP markers (in diff) | 0 |
| Empty catch blocks / bare except / swallowed errors | 0 |
| Unused imports found | 0 |
| New dependencies added | 0 |
| Modified functions with zero test coverage | 0 |
| Critical findings | 0 |
| Warnings | 1 |
| Info items | 6 |

---

## Monitoring Runs

| Date | Session | Task | Files Checked | Findings | Status |
|------|---------|------|--------------|----------|--------|
| 2026-07-12 | Observer Full (point-in-time) | Audit typed-schema conversion, HEAD~7..HEAD | 5 tool modules, models.py, params.py, 6 test files | 1 WARNING, 6 INFO, 0 CRITICAL | CLEAN — conversion is wire-compat safe; one test-coverage gate gap logged |
