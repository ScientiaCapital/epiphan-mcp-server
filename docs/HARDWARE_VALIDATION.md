# Hardware & live-system validation checklist

Some integrations have endpoints that can only be confirmed against real hardware or
a live tenant. Everything here has been implemented and unit-tested with mocks; this
doc is the one-command path to confirm each against the real thing. See
[EXTERNAL_RESOURCES.md](EXTERNAL_RESOURCES.md) for the authoritative API sources.

## 1. EC20 PTZ camera — endpoint paths (highest priority)

Epiphan publishes no REST endpoint reference, so `integrations/ec20.py` paths are
best-effort placeholders. Confirmed capability facts (presets 0-11, Presenter/Zone
modes, MJPEG preview, HTTP:80) are already baked in; the paths are not.

```bash
export EC20_PASSWORD=...            # and EC20_USERNAME if not 'admin'
python scripts/validate_ec20.py --host <camera-ip>               # read-only probes
python scripts/validate_ec20.py --host <camera-ip> --destructive # moves the camera
```

- **PASS** on a probe → that path is correct.
- **FAIL/ERR** → capture the real path from the camera web UI (`http://<camera-ip>`)
  browser dev-tools (Network tab while using the control), then update
  `integrations/ec20.py` and re-run.
- Also confirm: presets really are 0-11; tracking modes are exactly Presenter/Zone;
  whether PTZ is relative+speed (spec) vs the absolute model currently coded; whether
  HTTPS is truly disabled (port 80 only).
- Fallback: request the REST reference from support@epiphan.com.

## 2. YuJa — list/channel endpoints

`/services` base + `authToken` header are confirmed; the list/channel paths are not.

```bash
export YUJA_HOST=<tenant>.yuja.com YUJA_AUTH_TOKEN=...
python scripts/validate_cms.py --yuja
```

- Confirm `GET /services/media/videos` returns account-wide videos, or whether it
  needs `/user/{id}` or `/group/{id}` scoping.
- Confirm `GET /services/channels` exists (**highest risk** — unconfirmed in public docs).
- Authoritative source: YuJa API guide §5.2.x (login-gated).

## 3. Echo360 — /courses collection

`/public/api/v1/sections` is confirmed in docs; `/courses` is inferred.

```bash
export ECHO360_HOST=echo360.org ECHO360_CLIENT_ID=... ECHO360_CLIENT_SECRET=...
python scripts/validate_cms.py --echo360
```

- Confirm `GET /public/api/v1/courses` against the per-institution Swagger UI at
  `https://<host>/api-documentation`.
- Confirm the `courseId` filter param name on `/sections`.

## 4. Pearl core — spec fixes (see PEARL_API_AUDIT.md)

The storage/system-info/single-touch methods were corrected to the official spec but
not yet run against real hardware. Point the server at a real Pearl and exercise:

```bash
export PEARL_DEVICES=<pearl-ip> PEARL_USERNAME=admin PEARL_PASSWORD=...
pytest -m integration
```

Then confirm via any MCP client: `get_system_info`, `get_storage_report`,
`single_touch_start` / `single_touch_stop`, and `list_layouts`. See
[PEARL_API_AUDIT.md](PEARL_API_AUDIT.md) for the specific shapes to verify.

## 5. Local-model agent on constrained hardware (8 GB)

```bash
ollama pull qwen2.5:3b
python examples/local_agent/agent.py --check                        # fast self-test
python examples/local_agent/agent.py --profile smoke --model qwen2.5:3b "what's my pearl's status?"
```

Expect the `smoke` profile to connect and drive one or two tools; small models are
flaky at multi-tool calls. See [`examples/local_agent/README.md`](../examples/local_agent/README.md).
