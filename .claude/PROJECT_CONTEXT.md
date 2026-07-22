# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-07-22

## Status
First real hardware-validation pass — the gap flagged as "the single biggest remaining"
last session is now largely closed. The **EC20 integration was rewritten from a fictional
REST/Basic client to the real hardware API** (HTTP Digest + CGI, faithful directional PTZ),
discovered by inspecting the camera's own web-UI JS, and **validated live end-to-end** against
the unit (serial EP6601037): every PTZ/preset/home command returns `Result: "Success"`. A
silent-failure bug (device `Result:"Failed"` reported as success) was caught during live
validation and fixed. **3 commits on `main`, all pushed to `origin/main`** (`da61632`,
`329e91c`, `90c8879`). Suite **1425 passed / 7 deselected**, mypy strict + ruff clean.

The **Pearl Mini is located at `192.168.8.4`** but is in first-boot state — it forces
`/admin/passwords.cgi` and returns 403 on the REST API until an admin password is set. That's
a device action for Tim, and the only blocker on Pearl validation.

## Next Session's Focus
1. [ ] **Pearl Mini validation** (top priority; one step from done). Tim sets the admin password
   at `http://192.168.8.4/admin/passwords.cgi`, then: `cp .env.example .env` +
   `PEARL_DEVICES=192.168.8.4` / `PEARL_USERNAME=admin` / `PEARL_PASSWORD=<set>` →
   `pytest tests/test_integration.py -m integration -v` → `get_system_status` smoke.
   NOTE: verify the IP first — DHCP reshuffles addresses (see Network gotchas).
2. [ ] **EC20 AI-tracking grammar** — `set_ai_vip` is the right endpoint but needs a VIP-target
   arg (bare call → `{"Result":"Failed","Msg":"vip is null"}`). Capture the web-UI's actual
   `set_ai_vip` params (browser dev-tools while enabling tracking) to finish `enable_tracking`.
   Also: `get_target_status` 404s on this firmware (VX752A/SOC v3.0.30) — target-status read is
   absent here; `get_tracking_status` correctly surfaces that.
3. [ ] **EC20 `save_preset`** — never exercised live (would overwrite preset slot 0); the
   `posset&<id>` grammar is inferred, not hardware-confirmed. Confirm when a slot is expendable.
4. [ ] Carry-overs (deliberate go/no-go calls for Tim, not blocked work):
   PyPI publish decision (v1.3.0); `server.json` MCP-registry validity ($schema/reverse-DNS
   name/packages); `fastmcp<3` ceiling (blocks CVE-fixing transitive bumps — real major upgrade);
   gtm-brain-skill ProAV rename (separate repo, source archived).

## Done (This Session)
- [x] **EC20 root-caused + rewritten**: found via live curl + the camera's web-UI JS that the
  device uses **HTTP Digest** (not Basic) and a **CGI** API (`param.cgi`/`ptzctrl.cgi`/`vip`),
  not the fictional `/api/ptz/*` REST paths. Rewrote `integrations/ec20.py` to Digest + CGI +
  `key="value"` parsing (with password redaction) + faithful directional PTZ (move/stop, zoom
  in/out/stop, home, numeric presets 0-11, tracking); `get_preview` now honestly reports the
  WebSocket-only limitation instead of hitting a fabricated URL.
- [x] **Tool/model layer realigned**: `tools/ec20.py` kept the same 10 tool names (130-tool
  invariant intact) with directional params; `models.py` + `test_tool_schemas.py` wire keys
  updated; `tests/test_ec20.py` rewritten (client asserts real URLs + parsing; tool tests);
  `scripts/validate_ec20.py` repointed at real endpoints. All TDD (RED→GREEN).
- [x] **Live-validated the EC20** (read-only + destructive movement pass): `get_status` returns
  real device data; PTZ/preset-recall/home all `Success`; preview confirmed WebSocket-only.
- [x] **Fixed a silent failure** exposed live: `ptzctrl.cgi`/`vip` return HTTP 200 even on
  failure; added `_json_result()` to raise `EC20APIError` on `Result:"Failed"`. Tracking now
  honestly errors ("vip is null") instead of reporting success.
- [x] **Located the Pearl Mini** at `192.168.8.4` (in first-boot password-setup state) after a
  full-subnet signature scan; confirmed the EC20 lives at `192.168.8.5`/`.11` (DHCP-variable).

## Blockers
- **Pearl Mini**: admin password not set → REST API 403. Tim must set it via the device web UI
  (`http://192.168.8.4/admin/passwords.cgi`) before validation can proceed. Not a code issue.
- **EC20 AI tracking**: functional gap (needs the `set_ai_vip` target-arg grammar); everything
  else on the EC20 is validated and shipped.

## Network gotchas (saves hours next time)
- **DHCP reshuffles device IPs** — the EC20 appeared at both `.5` and `.11`; this Mac at `.7`/`.13`.
  Don't trust a static IP; re-discover each session.
- **Reach requires shared subnet** — a host only reaches devices on its own `/24`. The site
  router sends other subnets (e.g. `192.168.10.x`) straight to the internet (no inter-subnet
  routing). Get this Mac onto `192.168.8.x` (Wi-Fi) to reach the devices.
- **Discover by signature, not IP**: EC20 = Digest `GET /cgi-bin/param.cgi?get_device_conf` →
  "Epiphan EC20"; Pearl = `GET /api/v2.0/system/status` (JSON or 401 Basic) or `/admin/*.cgi`.
- Device creds: EC20 = Digest `admin`/`admin`; Pearl = Basic auth, password TBD by Tim at setup.

## Tech Stack
Python 3.11+ | FastMCP | httpx (async) | Pydantic v2 | pydantic-settings | pytest + respx | ruff + mypy (strict)

## Links
- GitHub: https://github.com/ScientiaCapital/epiphan-mcp-server (main == origin/main, clean)
- Pearl API docs: https://www.epiphan.com/userguides/pearl-api/
- Session plan/handoff: `~/.claude/plans/ok-we-have-all-frolicking-cocke.md`
- EC20 API reference (hard-won): auto-memory `ec20-rest-api-undocumented.md`

---

Next session: if Tim has set the Pearl password, Pearl validation is a ~10-minute close-out
(.env → integration tests). The EC20 — this session's main deliverable — is done, validated,
and pushed; only its AI-tracking grammar remains.

_Updated 2026-07-22._
