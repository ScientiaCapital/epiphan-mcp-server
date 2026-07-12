"""Contract meta-tests for MCP tool schemas.

These tests assert the *MCP-visible* schema (what an LLM client actually sees),
not just the Python type hints:

- Every parameter of a converted tool must carry a non-empty ``description`` in
  its input JSON schema.
- Every converted tool must expose an ``output_schema`` whose top-level
  properties are all described.

Modules that have not been converted yet are listed in ``NOT_YET_CONVERTED``.
This allowlist shrinks by one module per Phase-2 conversion commit; when it is
empty every tool in the server is required to have a fully described schema.

The final section is a wire-compatibility check: for a few converted fleet
tools it confirms that every key the tool returned *before* the typed-return
conversion is still present in ``structured_content`` with the same value, and
that the only new keys are the documented additive ones (Optional/defaulted
fields). This guards PyPI consumers against silent key removals or renames.
"""

import asyncio

import pytest
import respx
from httpx import Response

from epiphan_mcp.config import Settings
from epiphan_mcp.server import mcp

from .fixtures.responses import (
    CONTROL_SUCCESS_RESPONSE,
    DEVICE_RESPONSE,
    RECORDER_STATUS_STOPPED,
    STORAGE_RESPONSE,
)

# Tool modules not yet converted to typed params + typed returns.
# Remove a module from this set in the same commit that converts it.
NOT_YET_CONVERTED = {
    "ai_tools",
    "cloud",
    "device",
    "discovery",
    "ec20",
    "inputs",
    "kaltura",
    "layout",
    "maintenance",
    "opencast",
    "panopto",
    "publishers",
    "qsys",
    "recording",
    "schedule",
    "storage",
    "streaming",
    "system",
    "youtube",
}

# Fetched once at collection time; get_tools() is async but self-contained.
_TOOLS = asyncio.run(mcp.get_tools())


def _module_of(tool) -> str:
    """Short tool-module name, e.g. 'fleet' for epiphan_mcp.tools.fleet."""
    return tool.fn.__module__.rsplit(".", 1)[-1]


_ALL_TOOLS = sorted(_TOOLS.items())
_CONVERTED_TOOLS = [
    (name, tool)
    for name, tool in _ALL_TOOLS
    if _module_of(tool) not in NOT_YET_CONVERTED
]


def test_allowlist_names_are_real_modules():
    """Every allowlisted name must correspond to an actual tool module."""
    real_modules = {_module_of(t) for t in _TOOLS.values()}
    unknown = NOT_YET_CONVERTED - real_modules
    assert not unknown, f"NOT_YET_CONVERTED lists unknown modules: {unknown}"


def test_fleet_is_converted():
    """Fleet was converted in Phase 1, so it must not be on the allowlist."""
    assert "fleet" not in NOT_YET_CONVERTED


def test_some_tools_are_converted():
    """Guard against the parametrized lists silently becoming empty."""
    assert _CONVERTED_TOOLS, "no converted tools found — schema contract not exercised"


@pytest.mark.parametrize(
    "name,tool", _CONVERTED_TOOLS, ids=[n for n, _ in _CONVERTED_TOOLS]
)
def test_converted_tool_params_have_descriptions(name, tool):
    """Every input parameter of a converted tool has a non-empty description."""
    properties = (tool.parameters or {}).get("properties", {})
    for param_name, schema in properties.items():
        assert schema.get("description"), (
            f"{name}: parameter '{param_name}' has no description in its input schema"
        )


@pytest.mark.parametrize(
    "name,tool", _CONVERTED_TOOLS, ids=[n for n, _ in _CONVERTED_TOOLS]
)
def test_converted_tool_has_described_output_schema(name, tool):
    """Every converted tool exposes an output schema with described properties."""
    schema = tool.output_schema
    assert schema, f"{name}: converted tool has no output_schema"
    properties = schema.get("properties")
    assert properties, f"{name}: output_schema has no properties"
    for prop_name, prop_schema in properties.items():
        assert prop_schema.get("description"), (
            f"{name}: output field '{prop_name}' has no description"
        )


# ============================================================
# Wire-compatibility: structured_content keys/values preserved
# ============================================================
#
# Key sets captured from the fleet tools BEFORE the typed-return conversion
# (read off the original dict-returning code). The conversion may ADD keys
# (Optional fields), but must never drop, rename, or change the value of a
# pre-existing key.

_PRE_CONVERSION_KEYS = {
    # (tool, case): (expected pre-conversion keys, allowed additive keys)
    ("get_fleet_status", "normal"): (
        {
            "success",
            "fleet_name",
            "total_devices",
            "online_devices",
            "recording_devices",
            "average_health",
            "unhealthy_devices",
            "alerts_count",
            "devices",
            "alerts",
        },
        {"message"},
    ),
    ("batch_start_recording", "normal"): (
        {"success", "total_devices", "successful", "failed", "results"},
        {"error"},
    ),
    ("batch_start_recording", "no_devices"): (
        {"success", "error"},
        {"total_devices", "successful", "failed", "results"},
    ),
}


def _settings(devices: str) -> Settings:
    return Settings(
        devices=devices,
        username="admin",
        password="testpass",
        use_https=False,
        timeout=5.0,
        verify_ssl=False,
        fleet_name="wire-test",
    )


def _assert_wire_compatible(tool_name: str, case: str, structured: dict):
    pre_keys, additive = _PRE_CONVERSION_KEYS[(tool_name, case)]
    sc_keys = set(structured)
    missing = pre_keys - sc_keys
    assert not missing, f"{tool_name} ({case}) dropped pre-conversion keys: {missing}"
    extra = sc_keys - pre_keys
    assert extra <= additive, (
        f"{tool_name} ({case}) added unexpected keys: {extra - additive}"
    )


async def test_wire_compat_get_fleet_status_normal(monkeypatch):
    """get_fleet_status still returns all its original keys/values (plus message)."""
    from epiphan_mcp.tools import fleet

    host = "192.168.1.100"
    monkeypatch.setattr(fleet, "get_settings", lambda: _settings(host))
    api = f"http://{host}/api/v2.0"

    with respx.mock(assert_all_called=False) as router:
        router.get(f"{api}/device").mock(return_value=Response(200, json=DEVICE_RESPONSE))
        router.get(f"{api}/storages").mock(return_value=Response(200, json=STORAGE_RESPONSE))
        router.get(f"{api}/recorders/recorder-1/status").mock(
            return_value=Response(200, json=RECORDER_STATUS_STOPPED)
        )
        result = await _TOOLS["get_fleet_status"].run({})

    sc = result.structured_content
    _assert_wire_compatible("get_fleet_status", "normal", sc)
    # Values on the original keys are preserved.
    assert sc["success"] is True
    assert sc["total_devices"] == 1
    assert sc["online_devices"] == 1
    assert sc["devices"][0]["host"] == host
    # The single additive key is the documented Optional -> null.
    assert sc["message"] is None


async def test_wire_compat_batch_start_normal(monkeypatch):
    """batch_start_recording preserves its original keys/values (plus error=null)."""
    from epiphan_mcp.tools import fleet

    host = "192.168.1.100"
    monkeypatch.setattr(fleet, "get_settings", lambda: _settings(host))
    api = f"http://{host}/api/v2.0"

    with respx.mock(assert_all_called=False) as router:
        router.post(f"{api}/recorders/recorder-1/control/start").mock(
            return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
        )
        result = await _TOOLS["batch_start_recording"].run({"device_ids": "all"})

    sc = result.structured_content
    _assert_wire_compatible("batch_start_recording", "normal", sc)
    assert sc["success"] is True
    assert sc["total_devices"] == 1
    assert sc["successful"] == 1
    assert sc["failed"] == 0
    assert sc["error"] is None


async def test_wire_compat_batch_start_no_devices(monkeypatch):
    """The {success: False, error} error convention is preserved on the model."""
    from epiphan_mcp.tools import fleet

    monkeypatch.setattr(fleet, "get_settings", lambda: _settings(""))
    result = await _TOOLS["batch_start_recording"].run({"device_ids": "all"})

    sc = result.structured_content
    _assert_wire_compatible("batch_start_recording", "no_devices", sc)
    assert sc["success"] is False
    assert sc["error"] == "No devices specified"
