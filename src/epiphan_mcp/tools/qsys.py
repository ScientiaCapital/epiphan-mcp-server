"""Q-SYS integration MCP tools.

These tools enable AI assistants to control Pearl devices through Q-SYS Core
processors, providing a unified AV control interface for complex installations.

Q-SYS is QSC's software-based audio, video, and control platform used in
professional AV installations. When configured with Pearl plugins, it can
control Epiphan Pearl devices alongside other AV equipment.

Environment Variables Required:
    QSYS_CORE_IP: Q-SYS Core processor IP address
    QSYS_PORT: TCP port (default 1710)
    QSYS_PIN: Optional PIN for authentication
"""

import os
from typing import Any

from fastmcp import FastMCP

from epiphan_mcp.integrations.qsys import (
    QSysAuthError,
    QSysClient,
    QSysConnectionError,
    QSysRPCError,
)


def _get_qsys_config() -> dict[str, Any]:
    """Get Q-SYS configuration from environment."""
    host = os.environ.get("QSYS_CORE_IP")

    if not host:
        raise ValueError(
            "Missing Q-SYS configuration. Set QSYS_CORE_IP environment variable."
        )

    return {
        "host": host,
        "port": int(os.environ.get("QSYS_PORT", "1710")),
        "pin": os.environ.get("QSYS_PIN", ""),
    }


async def list_qsys_components(name_filter: str = "Pearl") -> dict[str, Any]:
    """List Q-SYS components, optionally filtered by name.

    Discovers components in the Q-SYS design that match the filter.
    Use this to find Pearl-related components like recorders and layout controls.

    Args:
        name_filter: Filter components containing this string (default "Pearl").
                     Use empty string to list all components.

    Returns:
        Dict with components list and count.

    Example:
        "List all Q-SYS components"
        "Find Pearl components in Q-SYS"
        "Show Q-SYS recording components"
    """
    try:
        config = _get_qsys_config()
    except ValueError as e:
        return {"error": str(e), "components": []}

    try:
        async with QSysClient(**config) as client:
            components = await client.discover_components(name_filter=name_filter)
            return {
                "components": components,
                "count": len(components),
                "filter": name_filter or "all",
                "qsys_host": config["host"],
            }
    except QSysConnectionError as e:
        return {"error": f"Connection failed: {e}", "components": []}
    except QSysAuthError as e:
        return {"error": f"Authentication failed: {e}", "components": []}
    except QSysRPCError as e:
        return {"error": f"RPC error: {e}", "components": []}


async def qsys_get_pearl_status(component_name: str = "Pearl_Recorder") -> dict[str, Any]:
    """Get Pearl recording/streaming status through Q-SYS.

    Retrieves the current state of a Pearl device controlled by Q-SYS.

    Args:
        component_name: Name of the Pearl component in Q-SYS design.
                        Common names: "Pearl_Recorder", "Pearl_1", etc.

    Returns:
        Status dict with is_recording, is_streaming, current_layout.

    Example:
        "Get Pearl status from Q-SYS"
        "Is Pearl recording through Q-SYS?"
        "Check Q-SYS Pearl_Recorder status"
    """
    if not component_name:
        return {"error": "component_name is required"}

    try:
        config = _get_qsys_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with QSysClient(**config) as client:
            status = await client.get_pearl_status(component_name)
            return {
                "status": status,
                "component": component_name,
                "qsys_host": config["host"],
            }
    except QSysConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except QSysAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except QSysRPCError as e:
        return {"error": f"RPC error: {e}"}


async def qsys_start_recording(component_name: str = "Pearl_Recorder") -> dict[str, Any]:
    """Start recording on Pearl through Q-SYS.

    Triggers recording start via the Q-SYS Pearl component. This is useful
    when Pearl is integrated into a larger Q-SYS controlled AV system.

    Args:
        component_name: Name of the Pearl component in Q-SYS design.

    Returns:
        Confirmation of recording start.

    Example:
        "Start Pearl recording through Q-SYS"
        "Q-SYS: start recording on Pearl_Recorder"
    """
    if not component_name:
        return {"error": "component_name is required"}

    try:
        config = _get_qsys_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with QSysClient(**config) as client:
            result = await client.start_recording(component_name)
            return {
                "success": True,
                "message": f"Recording started on {component_name}",
                "component": component_name,
                "qsys_host": config["host"],
                "result": result,
            }
    except QSysConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except QSysAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except QSysRPCError as e:
        return {"error": f"RPC error: {e}"}


async def qsys_stop_recording(component_name: str = "Pearl_Recorder") -> dict[str, Any]:
    """Stop recording on Pearl through Q-SYS.

    Triggers recording stop via the Q-SYS Pearl component.

    Args:
        component_name: Name of the Pearl component in Q-SYS design.

    Returns:
        Confirmation of recording stop.

    Example:
        "Stop Pearl recording through Q-SYS"
        "Q-SYS: stop recording on Pearl_Recorder"
    """
    if not component_name:
        return {"error": "component_name is required"}

    try:
        config = _get_qsys_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with QSysClient(**config) as client:
            result = await client.stop_recording(component_name)
            return {
                "success": True,
                "message": f"Recording stopped on {component_name}",
                "component": component_name,
                "qsys_host": config["host"],
                "result": result,
            }
    except QSysConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except QSysAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except QSysRPCError as e:
        return {"error": f"RPC error: {e}"}


async def qsys_switch_layout(
    layout_id: str,
    component_name: str = "Pearl_Layout",
) -> dict[str, Any]:
    """Switch Pearl layout through Q-SYS.

    Changes the active layout/scene on a Pearl device via Q-SYS control.
    The layout component must be configured in the Q-SYS design.

    Args:
        layout_id: Layout ID or index to switch to.
        component_name: Name of the Pearl layout component in Q-SYS.

    Returns:
        Confirmation of layout switch.

    Example:
        "Switch to layout 2 through Q-SYS"
        "Q-SYS: change Pearl layout to fullscreen"
    """
    if not layout_id:
        return {"error": "layout_id is required"}

    if not component_name:
        return {"error": "component_name is required"}

    try:
        config = _get_qsys_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with QSysClient(**config) as client:
            result = await client.switch_layout(layout_id, component_name)
            return {
                "success": True,
                "message": f"Layout switched to {layout_id} on {component_name}",
                "layout_id": layout_id,
                "component": component_name,
                "qsys_host": config["host"],
                "result": result,
            }
    except QSysConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except QSysAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except QSysRPCError as e:
        return {"error": f"RPC error: {e}"}


# Tool registry for MCP server registration
QSYS_TOOLS = [
    list_qsys_components,
    qsys_get_pearl_status,
    qsys_start_recording,
    qsys_stop_recording,
    qsys_switch_layout,
]


def register(server: FastMCP) -> None:
    """Register Q-SYS MCP tools."""
    server.tool()(list_qsys_components)
    server.tool()(qsys_get_pearl_status)
    server.tool()(qsys_start_recording)
    server.tool()(qsys_stop_recording)
    server.tool()(qsys_switch_layout)
