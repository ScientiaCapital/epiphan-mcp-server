#!/usr/bin/env python
"""Drive the Epiphan Pearl MCP server with a local Ollama model.

A minimal agent loop: it connects to the MCP server **in-process** (no subprocess),
exposes a curated subset of the 130 Pearl tools to a local model running under
Ollama, and lets the model call those tools to control your Pearl devices.

Nothing leaves your machine — the model runs locally via Ollama and the tools talk
to your Pearl over your LAN.

Examples
--------
    # No Ollama, no hardware needed — just show what the model would be given:
    python examples/local_agent/agent.py --dry-run --profile smoke "start recording"

    # Real run on a capable machine (Ollama serving qwen2.5:14b):
    python examples/local_agent/agent.py --profile core "what's the status of my pearl?"

See this folder's README for model choices and hardware guidance.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

import httpx
from fastmcp import Client
from tool_profiles import PROFILES, select

# The MCP side uses FastMCP's in-memory client against the imported server object.
from epiphan_mcp.server import mcp

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:14b"
DEFAULT_MAX_ITERS = 8

SYSTEM_PROMPT = (
    "You control Epiphan Pearl video capture devices through the provided tools. "
    "When the user asks you to do or check something, call the appropriate tool "
    "rather than guessing. Prefer read-only status tools before destructive ones. "
    "After tools return, answer the user concisely in plain language. "
    "If no tool fits, say so plainly."
)


def mcp_tools_to_openai(tools: list[Any]) -> list[dict[str, Any]]:
    """Convert MCP tool definitions to OpenAI/Ollama function-tool schemas."""
    converted: list[dict[str, Any]] = []
    for tool in tools:
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": (tool.description or "").strip(),
                    "parameters": tool.inputSchema
                    or {"type": "object", "properties": {}},
                },
            }
        )
    return converted


def extract_tool_result(result: Any) -> str:
    """Pull a JSON-serializable string out of a FastMCP CallToolResult."""
    # Structured data first (dict/list), then text content blocks, then repr.
    data = getattr(result, "data", None)
    if data is not None:
        try:
            return json.dumps(data, default=str)
        except TypeError:
            return str(data)
    content = getattr(result, "content", None)
    if content:
        texts = [getattr(block, "text", None) for block in content]
        joined = "\n".join(t for t in texts if t)
        if joined:
            return joined
    return str(result)


async def call_ollama(
    client: httpx.AsyncClient,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    """Call Ollama's OpenAI-compatible chat endpoint and return the message dict."""
    resp = await client.post(
        "/v1/chat/completions",
        json={
            "model": model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "stream": False,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    message: dict[str, Any] = data["choices"][0]["message"]
    return message


async def run_agent(
    query: str,
    profile: str,
    model: str,
    ollama_url: str,
    max_iters: int,
    dry_run: bool,
) -> int:
    async with Client(mcp) as mcp_client:
        all_tools = await mcp_client.list_tools()
        available_names = [t.name for t in all_tools]

        wanted = select(profile, available_names)
        if wanted is None:
            selected = all_tools
        else:
            selected = [t for t in all_tools if t.name in set(wanted)]
            missing = set(PROFILES[profile] or []) - set(available_names)
            if missing:
                print(
                    f"[warn] profile '{profile}' names not registered on server: "
                    f"{', '.join(sorted(missing))}",
                    file=sys.stderr,
                )

        openai_tools = mcp_tools_to_openai(selected)

        if dry_run:
            print(f"Profile '{profile}' exposes {len(openai_tools)} of "
                  f"{len(all_tools)} tools:\n")
            for t in openai_tools:
                fn = t["function"]
                params = list((fn["parameters"].get("properties") or {}).keys())
                summary = (fn["description"].splitlines() or [""])[0][:70]
                print(f"  • {fn['name']}({', '.join(params)}) — {summary}")
            print("\n--- system prompt ---")
            print(SYSTEM_PROMPT)
            print(f"\n--- user query ---\n{query}")
            print("\n[dry-run] Not contacting Ollama. Wiring OK.")
            return 0

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        async with httpx.AsyncClient(base_url=ollama_url, timeout=120.0) as http:
            for _iteration in range(max_iters):
                try:
                    message = await call_ollama(http, model, messages, openai_tools)
                except httpx.ConnectError:
                    print(
                        f"[error] Could not reach Ollama at {ollama_url}. "
                        "Is `ollama serve` running?",
                        file=sys.stderr,
                    )
                    return 2

                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    print(message.get("content", "").strip() or "(no answer)")
                    return 0

                # Record the assistant turn, then execute each requested tool.
                messages.append(message)
                for call in tool_calls:
                    fn = call["function"]
                    name = fn["name"]
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    print(f"[tool] {name}({json.dumps(args)})", file=sys.stderr)
                    try:
                        result = await mcp_client.call_tool(name, args)
                        content = extract_tool_result(result)
                    except Exception as exc:  # surface tool errors to the model
                        content = json.dumps({"error": str(exc)})
                        print(f"[tool-error] {name}: {exc}", file=sys.stderr)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id", name),
                            "content": content,
                        }
                    )

            print(
                f"[warn] hit max iterations ({max_iters}) without a final answer.",
                file=sys.stderr,
            )
            return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Drive the Epiphan Pearl MCP server with a local Ollama model.",
    )
    parser.add_argument("query", help="What you want the agent to do.")
    parser.add_argument(
        "--profile",
        default="core",
        choices=sorted(PROFILES),
        help="Which tool subset to expose (default: core).",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})."
    )
    parser.add_argument(
        "--ollama-url",
        default=DEFAULT_OLLAMA_URL,
        help=f"Ollama base URL (default: {DEFAULT_OLLAMA_URL}).",
    )
    parser.add_argument(
        "--max-iters",
        type=int,
        default=DEFAULT_MAX_ITERS,
        help=f"Max tool-calling rounds (default: {DEFAULT_MAX_ITERS}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the tools/prompt the model would receive; don't call Ollama.",
    )
    args = parser.parse_args()

    return asyncio.run(
        run_agent(
            query=args.query,
            profile=args.profile,
            model=args.model,
            ollama_url=args.ollama_url,
            max_iters=args.max_iters,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
