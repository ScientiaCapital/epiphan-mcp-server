"""FastMCP server for Epiphan Pearl devices.

This module creates the MCP server and registers all tools.
Tool implementations are organized in the tools/ subpackage.
"""

import logging

from fastmcp import FastMCP

from .tools import (
    ai_tools,
    cloud,
    device,
    discovery,
    ec20,
    fleet,
    inputs,
    kaltura,
    layout,
    maintenance,
    opencast,
    panopto,
    publishers,
    qsys,
    recording,
    schedule,
    storage,
    streaming,
    system,
    youtube,
    yuja,
)

logger = logging.getLogger(__name__)

# Create MCP server instance
mcp = FastMCP(
    "epiphan-pearl",
    instructions="Control Epiphan Pearl video capture devices through natural language",
)

# Register all tool modules
for _module in [
    device,
    recording,
    streaming,
    layout,
    storage,
    maintenance,
    fleet,
    ai_tools,
    schedule,
    publishers,
    inputs,
    system,
    discovery,
    panopto,
    kaltura,
    opencast,
    qsys,
    youtube,
    yuja,
    ec20,
    cloud,
]:
    _module.register(mcp)

# Re-export registered tools as module attributes for backward compatibility.
# Tests do: from epiphan_mcp.server import start_recording; await start_recording.fn(...)
globals().update(mcp._tool_manager._tools)
