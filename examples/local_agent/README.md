# Local-model agent — drive Pearl with Ollama

A minimal agent loop that points a **local model** (running under
[Ollama](https://ollama.com)) at the Epiphan Pearl MCP server's tools. You type a
request in plain language; the model calls the right tools to control your Pearl.

Nothing leaves your machine — the model runs locally and the tools talk to your Pearl
over your LAN. No cloud API keys, no per-token cost.

## How it works

```
you ──▶ agent.py ──▶ Ollama (local model)
                        │  emits tool calls
                        ▼
                 FastMCP in-memory client
                        │  dispatches to the 130 Pearl tools
                        ▼
                 your Pearl device(s)
```

- The MCP server is loaded **in-process** (FastMCP's in-memory `Client`) — no subprocess.
- Tool schemas are handed to Ollama's **OpenAI-compatible** endpoint
  (`/v1/chat/completions`) verbatim as `function` tools.
- The loop runs: model → tool call(s) → dispatch → results → model → … → final answer.

## Setup

1. Install the server (from the repo root):

   ```bash
   pip install -e ".[dev]"          # or: pip install -e ".[local-agent]"
   ```

2. Install and start Ollama, then pull a model:

   ```bash
   ollama pull qwen2.5:14b
   ollama serve                     # if not already running
   ```

3. Point at your Pearl via the usual env vars (`PEARL_DEVICES`, `PEARL_USERNAME`,
   `PEARL_PASSWORD`) — same as the main README.

## Usage

```bash
# No Ollama, no hardware — just show what the model would be given (wiring check):
python examples/local_agent/agent.py --dry-run --profile smoke "start recording"

# Real run:
python examples/local_agent/agent.py --profile core "what's the status of my pearl?"
```

Flags:

| Flag | Default | Notes |
|------|---------|-------|
| `--profile` | `core` | Which tool subset to expose: `smoke`, `core`, or `all`. |
| `--model` | `qwen2.5:14b` | Any Ollama model that supports tool calling. |
| `--ollama-url` | `http://localhost:11434` | Ollama base URL. |
| `--max-iters` | `8` | Max tool-calling rounds before giving up. |
| `--dry-run` | off | Print the exposed tools + prompt; don't contact Ollama. |

## Tool profiles — why they matter

Handing a local model all **130** tool schemas blows the context window and wrecks
tool-calling accuracy on smaller models. `tool_profiles.py` defines subsets:

- **`smoke`** (~5 tools) — status/list/start/stop. For constrained hardware and small
  models. Proves connectivity and single-tool dispatch; not meant for real work.
- **`core`** (~20 tools) — recording, streaming, layouts, fleet status, single-touch.
  The everyday driving set.
- **`all`** (130) — everything. Only worth it on capable hardware with a strong
  tool-calling model.

## Model & hardware guidance

Tool-calling reliability is the whole game here, and it drops fast on small models.

| Machine | Recommended | Profile | Reality |
|---------|-------------|---------|---------|
| **24 GB (e.g. M4)** | `qwen2.5:14b` | `core` / `all` | The real driver. Reliable tool calls with usable context. Verified working end-to-end. |
| **8 GB (e.g. M1)** | `qwen2.5:3b` | `smoke` only | Connectivity/one-tool proof box. Expect flaky tool-calling — don't rely on it for real ops. |

Model notes:

- **Qwen2.5** (instruct/coder) is currently the most reliable local tool-caller — the default.
- **DeepSeek-R1** works but its reasoning traces can fight structured tool output; if
  you use it, prefer the `smoke`/`core` profiles and expect occasional malformed calls.
- **GLM-4 9B** is workable on the 24 GB box but more variable than Qwen.

Pull alternates with e.g. `ollama pull deepseek-r1:14b`, then pass `--model deepseek-r1:14b`.

## Limitations

- This is an **example harness**, not a production agent — no streaming output, no
  conversation memory across invocations, no ret/guardrails beyond `--max-iters`.
- Destructive tools (reboot, delete, etc.) are reachable in the `all` profile. The
  system prompt tells the model to prefer read-only tools, but treat a local model's
  judgement accordingly — start with `smoke`/`core`.
