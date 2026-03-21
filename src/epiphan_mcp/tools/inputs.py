"""Input and output management tools for Epiphan Pearl devices.

This module provides tools for managing network inputs (SRT, RTSP, NDI)
and hardware outputs (HDMI, SDI) on Pearl devices.
"""

import base64
import logging
from typing import Any

from fastmcp import FastMCP

from ..client import PearlAPIError
from ..validation import ValidationError, validate_streaming_url
from .device import get_client

logger = logging.getLogger(__name__)


async def create_network_input(
    device_id: str = "default",
    name: str = "",
    input_type: str = "srt",
    url: str | None = None,
    passphrase: str | None = None,
    latency: int | None = None,
) -> dict[str, Any]:
    """
    Create a new network input source (SRT, RTSP, or NDI).

    Network inputs allow Pearl to receive video from network sources
    instead of physical inputs like HDMI or SDI.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        name: Display name for the input.
        input_type: Input type - srt, rtsp, or ndi.
        url: Source URL (for SRT/RTSP inputs).
        passphrase: Encryption passphrase (for SRT inputs).
        latency: Buffer latency in milliseconds.

    Returns:
        Created input info including the assigned ID.
    """
    if not name:
        return {
            "success": False,
            "error": "Input name is required",
            "device": device_id,
        }

    if url:
        try:
            validate_streaming_url(url)
        except ValidationError as e:
            return {
                "success": False,
                "error": f"Invalid URL: {e}",
                "device": device_id,
            }

    try:
        async with get_client(device_id) as client:
            # Build settings dict
            settings: dict[str, Any] = {}
            if url:
                if input_type == "srt":
                    settings["srt_url"] = url
                elif input_type == "rtsp":
                    settings["rtsp_url"] = url
            if passphrase:
                settings["passphrase"] = passphrase
            if latency is not None:
                settings["latency"] = latency

            result = await client.create_input(
                name=name,
                input_type=input_type,
                settings=settings if settings else None,
            )
            return {
                "success": True,
                "device": client.host,
                "input": result,
                "message": f"Network input '{name}' created successfully",
            }
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


async def get_input_settings(
    device_id: str = "default",
    input_id: str = "",
) -> dict[str, Any]:
    """
    Get configuration settings for an input source.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        input_id: Input source ID (e.g., "srt-1", "hdmi-1").

    Returns:
        Input settings including URL, passphrase, latency, etc.
    """
    if not input_id:
        return {
            "success": False,
            "error": "Input ID is required",
            "device": device_id,
        }

    try:
        async with get_client(device_id) as client:
            settings = await client.get_input_settings(input_id)
            return {
                "success": True,
                "device": client.host,
                "input_id": input_id,
                "settings": settings,
            }
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "input_id": input_id,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


async def update_input_settings(
    device_id: str = "default",
    input_id: str = "",
    url: str | None = None,
    passphrase: str | None = None,
    latency: int | None = None,
) -> dict[str, Any]:
    """
    Update settings for an input source (partial update).

    Only provided settings will be changed; other settings remain unchanged.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        input_id: Input source ID.
        url: New source URL (for network inputs).
        passphrase: New encryption passphrase (for SRT inputs).
        latency: New buffer latency in milliseconds.

    Returns:
        Confirmation of settings update.
    """
    if not input_id:
        return {
            "success": False,
            "error": "Input ID is required",
            "device": device_id,
        }

    # Validate URL if provided (SSRF prevention)
    if url is not None:
        try:
            validate_streaming_url(url)
        except ValidationError as e:
            return {
                "success": False,
                "error": f"Invalid URL: {e}",
                "device": device_id,
            }

    # Build settings dict with only provided values
    settings: dict[str, Any] = {}
    if url is not None:
        settings["url"] = url
    if passphrase is not None:
        settings["passphrase"] = passphrase
    if latency is not None:
        settings["latency"] = latency

    if not settings:
        return {
            "success": False,
            "error": "No settings provided to update",
            "device": device_id,
        }

    try:
        async with get_client(device_id) as client:
            result = await client.update_input_settings(input_id, settings)
            return result.model_dump()
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "input_id": input_id,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


async def list_outputs(
    device_id: str = "default",
) -> dict[str, Any]:
    """
    List available output ports on a Pearl device.

    Output ports include HDMI and SDI outputs that can be configured
    to display channel content.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        List of output ports including:
        - Output ID and name
        - Output type (HDMI, SDI)
        - Current source channel
        - Resolution
    """
    try:
        async with get_client(device_id) as client:
            outputs = await client.get_outputs()
            return {
                "success": True,
                "device": client.host,
                "total_outputs": len(outputs),
                "outputs": outputs,
            }
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


async def set_output_source(
    device_id: str = "default",
    output_id: str = "",
    source_channel: int | None = None,
) -> dict[str, Any]:
    """
    Set the source channel for an output port.

    Configure which channel content is displayed on an HDMI or SDI output.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        output_id: Output ID (e.g., "hdmi-1", "sdi-1").
        source_channel: Channel number (1-based) to display, or None to disable.

    Returns:
        Confirmation of output configuration.
    """
    if not output_id:
        return {
            "success": False,
            "error": "Output ID is required",
            "device": device_id,
        }

    try:
        async with get_client(device_id) as client:
            channel_id = (
                f"channel-{source_channel}" if source_channel is not None else None
            )
            result = await client.set_output_source(output_id, channel_id)
            return result.model_dump()
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "output_id": output_id,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


async def get_input_preview(
    device_id: str = "default",
    input_id: str = "",
    resolution: str | None = None,
    format: str = "jpg",
) -> dict[str, Any]:
    """
    Get a live preview image from an input source.

    Captures a snapshot of an input source (HDMI, SDI, SRT, etc.) as a
    JPEG or PNG image. The image is returned as a base64-encoded string.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        input_id: Input source ID (e.g., "hdmi-1", "sdi-1", "srt-1").
        resolution: Optional resolution (e.g., "1920x1080", "640x360").
        format: Image format - "jpg" (default) or "png".

    Returns:
        Preview image as base64-encoded string with format and resolution metadata.
    """
    if not input_id:
        return {
            "success": False,
            "error": "Input ID is required",
            "device": device_id,
        }

    try:
        async with get_client(device_id) as client:
            image_bytes = await client.get_input_preview(
                input_id,
                resolution=resolution,
                format=format,
            )
            preview_b64 = base64.b64encode(image_bytes).decode("ascii")
            result: dict[str, Any] = {
                "success": True,
                "device": client.host,
                "input_id": input_id,
                "format": format,
                "preview_base64": preview_b64,
                "size_bytes": len(image_bytes),
            }
            if resolution:
                result["resolution"] = resolution
            return result
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "input_id": input_id,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


def register(server: FastMCP) -> None:
    """Register input/output MCP tools."""
    server.tool()(create_network_input)
    server.tool()(get_input_preview)
    server.tool()(get_input_settings)
    server.tool()(list_outputs)
    server.tool()(set_output_source)
    server.tool()(update_input_settings)
