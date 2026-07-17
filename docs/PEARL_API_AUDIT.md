# Pearl API Audit — client.py vs official OpenAPI spec

Audited `src/epiphan_mcp/client.py` against the official Pearl v2.0 OpenAPI spec
([vendored copy](api/pearl_openapi_v2.0.yml), source:
https://epiphan-video.github.io/pearl_api_swagger_ui/). Date: 2026-07-16.

**Result: 35 of 40 REST calls matched the spec exactly. 5 diverged — all now fixed.**

The 5 survived because the test suite mocked whatever path the code used (respx),
so wrong paths still passed — the classic "green tests, wrong endpoint" trap. Fixes
match the documented spec but are **not yet verified against real hardware**; run the
client against a live Pearl to confirm.

## Findings & fixes

| # | Method | Was (wrong) | Now (spec) | Notes |
|---|--------|-------------|-----------|-------|
| 1 | `get_storages` | `GET /storages` | `GET /system/storages` + per-storage `GET /system/storages/{stid}/status` | Spec list returns only `{id}`; capacity (`state,total,free`) is a separate call. |
| 2 | `get_system_status` | `GET /device` | `GET /system/ident` (name) + `GET /system/firmware` (product_name=model, version) + storages | No `/device` in spec; identity is split across endpoints. Serial isn't exposed by these — best-effort. |
| 3 | `single_touch_start` / `single_touch_stop` | `POST /singletouch/control/start` / `/stop` | `GET /system/singletouchcontrol` → per-object `GET .../{stcid}/state` → `POST .../{stcid}/control/toggle` | API models single-touch as a per-object **toggle**, not global start/stop. `_set_single_touch(desired)` reads each object's state and toggles only those not already in the target state. |
| 4 | `get_layouts` | `GET /channels/{cid}/layouts` | *(flagged, unchanged)* | **No spec endpoint** enumerates all layouts — only `active_layout` (via `GET /channels`) and `PUT /channels/{cid}/layouts/active` exist. May be undocumented-but-real; flagged in the method docstring. |

Findings 1-3 were rewritten to the documented endpoints (with test mocks updated to
the spec shapes). Finding 4 has no documented replacement, so it carries a
`SPEC MISMATCH (unverified)` marker instead.

## Still to verify on real hardware

- Confirm the rewritten storage/system-info/single-touch flows return the expected
  shapes on a live Pearl (esp. `/system/storages/{stid}/status` field names and the
  single-touch `state.status` boolean semantics).
- Determine whether `GET /channels/{cid}/layouts` is a real (undocumented) endpoint
  or whether layout enumeration must be derived from `GET /channels` + config.

## Reproduce this audit

```bash
python - <<'PY'
import re, yaml, pathlib
spec = yaml.safe_load(open("docs/api/pearl_openapi_v2.0.yml"))
norm = lambda p: re.sub(r"\{[^}]+\}", "{}", p)
spec_set = {(m.upper(), norm(p)) for p, ops in spec["paths"].items()
            for m in ops if m in ("get","post","put","patch","delete")}
src = pathlib.Path("src/epiphan_mcp/client.py").read_text()
for m in re.finditer(r'self\._(get|post|put|patch|delete)\(\s*f?"([^"]+)"', src):
    key = (m.group(1).upper(), norm(m.group(2)))
    if key not in spec_set:
        print("MISMATCH", *key)
PY
```
