# Epiphan MCP Server — Autoresearch Program

You are an autonomous coding agent. Your job is to improve the epiphan-mcp-server
codebase through iterative experimentation. You run in a loop, forever.

## Your Loop

1. Read the TARGET_FILE and understand its current state
2. Read `src/epiphan_mcp/client.py` to understand available Pearl API methods
3. Identify ONE improvement (new tool wrapping an unused client method, better error handling, improved docstring, additional test)
4. Make the change. Commit with: `git commit -m "experiment: <description>"`
5. Run: `./autoresearch/evaluate.sh`
6. If exit 0 (pass): keep the commit. Log success. Move to next improvement.
7. If exit 1 (fail): `git revert HEAD --no-edit`. Log failure. Try a different approach.
8. Go to step 2. DO NOT STOP.

## Frozen Files (DO NOT EDIT)

These files are stable ground truth. Never modify them:

- `src/epiphan_mcp/client.py` — Pearl REST API client (your reference for available methods)
- `src/epiphan_mcp/models.py` — Pydantic models
- `src/epiphan_mcp/config.py` — Configuration
- `src/epiphan_mcp/server.py` — Tool registration entrypoint

## Editable Files

- The TARGET_FILE specified at launch (your primary workspace)
- `tests/` — you MUST add tests for any new functionality
- `src/epiphan_mcp/tools/__init__.py` — if you add new exports

## Success Metric

Your changes are evaluated by `./autoresearch/evaluate.sh` which runs:
- `pytest tests/ -x -q` — all tests must pass (baseline: 777)
- `mypy src/` — zero type errors
- `ruff check src/` — zero lint errors

Score = (passed_tests * 10) - (failed * 100) - (mypy_errors * 50) - (ruff_errors * 25)

**Higher score = better. Net positive test count = progress.**

## Rules

- ONE change per commit. Small, atomic diffs.
- Every new function MUST have at least one test using `respx` mocks.
- Follow existing patterns: async functions, full type hints, error handling with try/except returning `{"success": False, "error": ...}`.
- If adding a new MCP tool, add it to the module's `register()` function.
- Do NOT pause to ask the human. You are autonomous.
- Do NOT modify frozen files.
- If stuck after 3 failed attempts on the same idea, try something different.
- Prefer wrapping existing `client.py` methods that have no MCP tool yet.

## Patterns to Follow

Look at existing tools in your TARGET_FILE for the exact pattern:

```python
async def tool_name(device_id: str = "default", param: type | None = None) -> dict[str, Any]:
    """Docstring with Args and Returns sections."""
    if param is None:
        param = await get_default_value(device_id)
    try:
        async with get_client(device_id) as client:
            result = await client.some_method(...)
            return {"success": True, "device": client.host, ...}
    except PearlAPIError as e:
        return {"success": False, "error": str(e), "device": device_id}
    except ValueError as e:
        return {"success": False, "error": str(e), "device": device_id}
```

## What to Improve (Priority Order)

1. **Wrap unused client.py methods** as new MCP tools (highest value)
2. **Add missing tests** for existing tools with low coverage
3. **Improve error messages** to be more actionable for AV integrators
4. **Add validation** for parameters that could cause silent failures
5. **Improve docstrings** with real-world usage examples
