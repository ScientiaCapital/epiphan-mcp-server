"""Layout and bookmark tools for Epiphan Pearl devices."""

import logging
from typing import Any

from fastmcp import FastMCP

from ..client import PearlAPIError
from .device import get_client
from .discovery import get_default_channel

logger = logging.getLogger(__name__)


async def list_layouts(device_id: str = "default", channel: int | None = None) -> dict[str, Any]:
    """
    List available layouts for a channel on an Epiphan Pearl device.

    Layouts define different arrangements of video sources (e.g., full screen,
    picture-in-picture, side-by-side).

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based). Auto-detected if not specified.

    Returns:
        List of available layouts including:
        - Layout ID and name
        - Which layout is currently active
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            layouts = await client.get_layouts(channel_id)
            active_layout = next(
                (layout["id"] for layout in layouts if layout.get("is_active")), None
            )
            return {
                "success": True,
                "device": client.host,
                "channel": channel_id,
                "total_layouts": len(layouts),
                "layouts": layouts,
                "active_layout": active_layout,
            }
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "channel": channel,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


async def switch_layout(
    device_id: str = "default", channel: int | None = None, layout_id: str = ""
) -> dict[str, Any]:
    """
    Switch the active layout/scene on an Epiphan Pearl channel.

    Layouts define how video sources are arranged and displayed.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based). Auto-detected if not specified.
        layout_id: Layout identifier to switch to.

    Returns:
        Confirmation of layout switch with device and channel details.
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    if not layout_id:
        return {
            "success": False,
            "error": "layout_id is required",
            "device": device_id,
            "channel": channel,
        }

    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.switch_layout(channel_id, layout_id)
            return result.model_dump()
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "channel": channel,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


async def add_bookmark(
    device_id: str = "default", channel: int | None = None, text: str = ""
) -> dict[str, Any]:
    """
    Add a bookmark to an active recording on an Epiphan Pearl device.

    Bookmarks mark important moments in a recording for easy navigation later.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based) with the active recording. Auto-detected if not specified.
        text: Optional bookmark text/label.

    Returns:
        Confirmation of bookmark creation with device and channel details.
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.add_bookmark(channel_id, text)
            return {
                "success": True,
                "device": client.host,
                "channel": channel_id,
                "text": text,
                "message": result.message,
            }
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "channel": channel,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


def register(server: FastMCP) -> None:
    """Register layout MCP tools."""
    server.tool()(add_bookmark)
    server.tool()(list_layouts)
    server.tool()(switch_layout)
