# Quickstart — for reviewers & testers

The shortest path from `git clone` to driving a Pearl. ~5 minutes.

## 1. Install (from source — not on PyPI yet)

```bash
git clone https://github.com/tmkipper/epiphan-mcp-server.git
cd epiphan-mcp-server
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## 2. Sanity check — no hardware needed

Everything below runs against mocked HTTP, so it works before you touch a device.

```bash
pytest            # 1,376 tests (1,369 pass, 7 skip — the 7 need real hardware)
mypy src/         # strict type check, should be clean
ruff check src/   # lint, should be clean
```

## 3. Point at a real Pearl

```bash
cp .env.example .env
```

Edit `.env` — the only required values:

```bash
PEARL_DEVICES=192.168.1.100        # your Pearl's IP (comma-separated for several)
PEARL_USERNAME=admin
PEARL_PASSWORD=your_password
```

Run the 7 hardware integration tests (they skip unless `PEARL_DEVICES` is set):

```bash
pytest -m integration
```

## 4. Drive it from an AI assistant

Add to your MCP client (Claude Code / Claude Desktop / Cursor / Windsurf):

```json
{
  "mcpServers": {
    "epiphan-pearl": {
      "command": "python",
      "args": ["-m", "epiphan_mcp"],
      "env": {
        "PEARL_DEVICES": "192.168.1.100",
        "PEARL_USERNAME": "admin",
        "PEARL_PASSWORD": "your_password"
      }
    }
  }
}
```

Then ask: *"What's the status of my Pearl device?"* → it calls `get_device_status`.

Prefer a **local model** (Ollama, nothing leaves the machine)? See
[`examples/local_agent/`](examples/local_agent/).

## What to test first (be skeptical here)

Most integrations are unit-tested against mocks. These have **known-unverified live
endpoints** — exercise them first and expect to find issues:

| Area | Status | What to check |
|------|--------|---------------|
| **EC20 PTZ camera** (10 tools) | ⚠️ Endpoint paths are placeholders | Every call — the REST paths are guesses pending a real camera. See `src/epiphan_mcp/integrations/ec20.py`. |
| **YuJa** (list/channels) | ⚠️ Unverified | `list_yuja_videos`, `list_yuja_channels` against a live instance. Upload is validated. |
| **Echo360** (collections) | ⚠️ Unverified | `list_echo360_courses`, `list_echo360_sections`. Auth/upload/pagination validated. |

Solid areas (validated flows): Pearl core control, Epiphan Cloud, and the
Panopto / Kaltura / Opencast upload flows.

## Troubleshooting

- **`401 Unauthorized`** — Pearl firmware ≥ 4.14.2 requires HTTP Basic Auth. Check `PEARL_USERNAME` / `PEARL_PASSWORD`.
- **Can't reach device** — confirm the IP, and set `PEARL_USE_HTTPS=true` if your Pearl serves the API over HTTPS.
- **Integration tests all skipped** — that's expected until `PEARL_DEVICES` is exported.
