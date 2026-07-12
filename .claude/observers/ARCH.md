# Observer: Architecture Report

**Date:** 2026-07-12
**Project:** epiphan-mcp-server
**Observer Model:** Claude Sonnet 5 (Observer Full)

**Session scope:** `git diff HEAD~7..HEAD` — typed-schema conversion of 5 tool
modules (discovery, layout, maintenance, streaming, inputs): `dict[str, Any]`
returns → typed Pydantic params (`params.py`) + typed return models
(`models.py`), plus test migrations from dict-indexing to attribute access,
plus 2 chore/docs commits (`BACKLOG.md`, `PROJECT_CONTEXT.md`). No feature
contract file exists under `.claude/contracts/` for this work — the task's
own contract-equivalent is `tests/test_tool_schemas.py`, treated as such
below.

---

## Blockers (stop work immediately)

_No blockers._ No dropped or renamed return-model keys were found across the
5 converted modules; every previously-emitted dict key has a corresponding
model field. No new API endpoints were added outside the stated scope.

---

## Risks (address this sprint)

`[WARNING]` — No feature contract exists in `.claude/contracts/` for this
work. Scope was inferred from commit messages/diff only. All 5 modified `src/`
tool modules (discovery, layout, maintenance, streaming, inputs), `models.py`,
and `params.py` match the stated "typed-schema conversion" scope exactly — no
unrelated modules were touched — but there is no durable, checked-in artifact
defining that scope other than the commit messages themselves.

`[WARNING]` — `tests/test_tool_schemas.py`'s wire-compatibility guard
(`_PRE_CONVERSION_KEYS`) does not yet include entries for any of the 5 tools
converted in this batch (only 2 Phase-1 fleet tools are covered). This is the
project's de facto contract-drift regression test, and it currently would not
catch a future key-drop/rename in discovery/layout/maintenance/streaming/
inputs. (Cross-referenced in QUALITY.md as a test gap; recorded here as the
architectural contract-enforcement gap it represents.)

---

## Smells (log to backlog)

`[INFO]` — Duplicate parameter-description pattern:
`ChannelPreviewResult.resolution` / `InputPreviewResult.resolution` field
descriptions ("present only when explicitly specified") no longer match
actual runtime behavior post-conversion (field is now always present, `null`
when unset). Not a contract violation (additive per the file's own
documented convention at `models.py:694-698`), but worth a one-line doc fix
so the schema an LLM client reads isn't misleading about key presence.

`[INFO]` — `PreviewResolution` / `ImageFormat` shared param types
(`params.py`) are correctly reused by both `streaming.get_channel_preview`
and `inputs.get_input_preview` rather than duplicated — good, no duplicate
logic introduced.

---

## Contract Compliance

No `.claude/contracts/` file exists for this feature; the closest thing to a
contract is `tests/test_tool_schemas.py`. Compliance assessed against that
file's own two requirements (every param/output field described) plus a
manual old-dict-vs-new-model key diff (since the wire-compat section of that
file doesn't cover this batch):

| Tool | Old dict keys (pre-conversion) | New model fields | Dropped/renamed? | Additive-only extras |
|---|---|---|---|---|
| `discover_device` | success, device, cached, recorders, channels, inputs, error | same 7 | No | — |
| `clear_discovery_cache` | success, cleared, entries_removed | same 3 | No | — |
| `list_layouts` | success, device, channel, total_layouts, layouts, active_layout, error | same 7 | No | — |
| `switch_layout` | success, message, device, details (+error/channel on error paths) | same, `extra="allow"` | No | — |
| `add_bookmark` | success, device, channel, text, message, error | same 6 | No | — |
| `predict_storage_full` | success, device, hours_until_full, storage_free_gb, storage_total_gb, storage_used_percent, is_recording, bitrate_mbps, warning, recommendation, error | same 11 | No | — |
| `get_device_health_score` | success, device, score, categories, issues, is_recording, recommendation, error | same 8 | No | — |
| `start_stream`/`stop_stream` | success, message, device, details (+error/channel on error) | same, `extra="allow"` | No | — |
| `get_stream_status` | success, device, channel, publisher, state, duration_seconds, bitrate_bps, bytes_sent, destination, error | same 10 | No | — |
| `list_channels` | success, device, total_channels, channels, error | same 5 | No | channels list now explicitly `model_dump()`-ed where source objects are Pydantic models |
| `list_publishers` | success, device, channel, total_publishers, publishers, error | same 6 | No | — |
| `get_channel_preview` | success, device, channel, format, preview_base64, size_bytes, (resolution only if set), error | same 8, `resolution` now always a key | No | `resolution` key presence changed from conditional to always-present-nullable (documented additive pattern; see Smells) |
| `create_network_input` | success, device, input, message, error | same 5 | No | — |
| `get_input_settings` | success, device, input_id, settings, error | same 5 | No | — |
| `update_input_settings` | success, message, device, details, input_id, error | same, `extra="allow"` | No | — |
| `list_outputs` | success, device, total_outputs, outputs, error | same 5 | No | — |
| `set_output_source` | success, message, device, details, output_id, error | same, `extra="allow"` | No | — |
| `get_input_preview` | success, device, input_id, format, preview_base64, size_bytes, (resolution only if set), error | same 8, `resolution` now always a key | No | same as `get_channel_preview` |

**Verdict: no BLOCKER-level contract drift.** All 17 converted tools are
additive-only; no key was dropped, renamed, or given a different value on
the same input.

---

## Devil's Advocate Challenges

| # | Target | Challenge | Verdict |
|---|---|---|---|
| 1 | `models.py` — 40+ new `*Result` classes | Does each tool need its own bespoke result model, or could a smaller number of generic shapes (e.g. one `OperationResult`-like class plus per-tool `data` payloads) cover this? | Accepted as-is: FastMCP derives the MCP output JSON schema from the return annotation, so per-tool models are what let each tool advertise its own field descriptions to the calling LLM (the stated point of this whole conversion). A generic wrapper would lose that. Not over-engineering given the stated goal. |
| 2 | `streaming.py`/`inputs.py` preview tools | `resolution` is now always emitted as `null` instead of omitted — was this an intentional wire-format change or an oversight of the dict→model conversion? | Not flagged as a defect (additive, matches the project's own stated convention), but the field descriptions are now inaccurate — logged in Smells/QUALITY.md. |
| 3 | `list_channels` in `streaming.py` | Why does only this one tool need `isinstance(c, BaseModel)` handling before constructing its result model, while every sibling tool assigns raw client-layer output directly? | Verified: `client.get_channels()` is the only one of the touched client methods that returns `list[ChannelInfo]` (Pydantic models); `get_outputs`/`get_publishers`/`get_layouts` return `list[dict[str, Any]]` already. The asymmetry is correct, not an inconsistency — confirmed by reading `client.py`. |
| 4 | 2 chore commits (`BACKLOG.md`, `PROJECT_CONTEXT.md`) bundled with 5 feature commits | Do state-handoff/backlog commits belong in the same reviewed batch as the typed-schema conversion? | Low risk — docs-only, no source/test files touched by those 2 commits. Not flagged as scope creep. |
| 5 | Test file layout — no `test_layout.py`/`test_maintenance.py` | Should coverage for `layout.py`/`maintenance.py` continue living inside the large `test_server.py` rather than dedicated files like the other 3 converted modules got? | Pre-existing structural choice, not introduced by this diff. Flagged as an [INFO] nicety in QUALITY.md, not a defect — worth a backlog item for consistency but not urgent. |

---

## Scope Creep Check

Files touched: `.claude/BACKLOG.md`, `.claude/PROJECT_CONTEXT.md`,
`src/epiphan_mcp/models.py`, `src/epiphan_mcp/tools/{discovery,inputs,layout,
maintenance,streaming,params}.py`, `tests/test_{discovery,inputs,server,
streaming,tool_schemas}.py`. No new API endpoints, no new tool functions, no
files in unexpected directories. **No scope creep found.**
