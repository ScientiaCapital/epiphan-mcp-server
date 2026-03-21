"""MCP tools for Epiphan EC20 PTZ camera control.

This module provides MCP-compatible tools for controlling EC20 PTZ cameras,
enabling AI assistants to perform camera operations through natural language.

Tools:
    - ec20_get_status: Get camera status and current position
    - ec20_pan_tilt: Move camera to absolute pan/tilt position
    - ec20_zoom: Set camera zoom level
    - ec20_goto_preset: Move camera to saved preset
    - ec20_save_preset: Save current position as preset
    - ec20_home: Return camera to home position
    - ec20_enable_tracking: Enable AI tracking mode
    - ec20_disable_tracking: Disable AI tracking
    - ec20_list_presets: List all saved presets
    - ec20_get_preview: Get camera preview image

Example:
    ```python
    # Get camera status
    result = await ec20_get_status(camera_id="192.168.1.50")

    # Pan and tilt camera
    result = await ec20_pan_tilt(camera_id="default", pan=45.0, tilt=15.0)

    # Enable presenter tracking
    result = await ec20_enable_tracking(camera_id="default", mode="presenter")
    ```
"""

import base64
import logging
from typing import Any

from fastmcp import FastMCP

from epiphan_mcp.config import get_settings
from epiphan_mcp.integrations.ec20 import EC20Client, EC20APIError, EC20ConnectionError

logger = logging.getLogger(__name__)


def _get_ec20_client(camera_id: str = "default") -> tuple[EC20Client, str]:
    """Get EC20 client for camera ID.

    Args:
        camera_id: Camera identifier (default, IP, or index)

    Returns:
        Tuple of (EC20Client, resolved_host)

    Raises:
        ValueError: If camera_id cannot be resolved
    """
    settings = get_settings()
    host = settings.get_ec20_host(camera_id)

    client = EC20Client(
        host=host,
        username=settings.ec20_username,
        password=settings.ec20_password,
        use_https=settings.ec20_use_https,
        timeout=settings.ec20_timeout,
    )

    return client, host


async def ec20_get_status(camera_id: str = "default") -> dict[str, Any]:
    """Get EC20 camera status including PTZ position and tracking state.

    Args:
        camera_id: EC20 camera identifier. Can be:
            - "default" - first configured EC20 camera
            - IP address or hostname - used directly
            - Index like "0", "1" - nth configured camera

    Returns:
        Dict containing:
            - success: bool
            - camera_id: Resolved hostname/IP
            - status: Camera status data (model, firmware, position, tracking)
            - error: Error message if success=False

    Example:
        >>> result = await ec20_get_status(camera_id="192.168.1.50")
        >>> print(result["status"]["pan"])
        45.0
    """
    try:
        client, host = _get_ec20_client(camera_id)

        async with client:
            status = await client.get_status()

        return {
            "success": True,
            "camera_id": host,
            "camera": status,
        }

    except ValueError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": str(e),
        }
    except EC20ConnectionError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"Connection error: {e}",
        }
    except EC20APIError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"API error: {e}",
        }


async def ec20_pan_tilt(
    camera_id: str = "default",
    pan: float = 0.0,
    tilt: float = 0.0,
    speed: int = 50,
) -> dict[str, Any]:
    """Move EC20 camera to absolute pan/tilt position.

    Args:
        camera_id: EC20 camera identifier
        pan: Pan position in degrees (-162.5 to +162.5)
        tilt: Tilt position in degrees (-30 to +90 typical)
        speed: Movement speed (1-100, default 50)

    Returns:
        Dict containing:
            - success: bool
            - camera_id: Resolved hostname/IP
            - pan: New pan position
            - tilt: New tilt position
            - error: Error message if success=False

    Example:
        >>> result = await ec20_pan_tilt(pan=45.0, tilt=15.0, speed=75)
        >>> print(result["pan"], result["tilt"])
        45.0 15.0
    """
    try:
        client, host = _get_ec20_client(camera_id)

        async with client:
            pan_result = await client.pan(degrees=pan, speed=speed)
            tilt_result = await client.tilt(degrees=tilt, speed=speed)

        return {
            "success": True,
            "camera_id": host,
            "pan": pan,
            "tilt": tilt,
            "pan_result": pan_result,
            "tilt_result": tilt_result,
        }

    except ValueError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": str(e),
        }
    except EC20ConnectionError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"Connection error: {e}",
        }
    except EC20APIError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"API error: {e}",
        }


async def ec20_zoom(
    camera_id: str = "default",
    level: int = 1,
) -> dict[str, Any]:
    """Set EC20 camera zoom level.

    Args:
        camera_id: EC20 camera identifier
        level: Zoom level (1-36: 1-20 optical, 21-36 digital)

    Returns:
        Dict containing:
            - success: bool
            - camera_id: Resolved hostname/IP
            - zoom_level: New zoom level
            - error: Error message if success=False

    Example:
        >>> result = await ec20_zoom(level=10)
        >>> print(result["zoom_level"])
        10
    """
    try:
        client, host = _get_ec20_client(camera_id)

        async with client:
            zoom_result = await client.zoom(level=level)

        return {
            "success": True,
            "camera_id": host,
            "zoom_level": level,
            "result": zoom_result,
        }

    except ValueError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": str(e),
        }
    except EC20ConnectionError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"Connection error: {e}",
        }
    except EC20APIError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"API error: {e}",
        }


async def ec20_goto_preset(
    camera_id: str = "default",
    preset_id: int = 1,
) -> dict[str, Any]:
    """Move EC20 camera to a saved preset position.

    Args:
        camera_id: EC20 camera identifier
        preset_id: ID of preset to recall (1-255)

    Returns:
        Dict containing:
            - success: bool
            - camera_id: Resolved hostname/IP
            - preset_id: Preset ID recalled
            - error: Error message if success=False

    Example:
        >>> result = await ec20_goto_preset(preset_id=1)
        >>> print(result["preset_id"])
        1
    """
    try:
        client, host = _get_ec20_client(camera_id)

        async with client:
            result = await client.goto_preset(preset_id=preset_id)

        return {
            "success": True,
            "camera_id": host,
            "preset_id": preset_id,
            "result": result,
        }

    except ValueError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": str(e),
        }
    except EC20ConnectionError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"Connection error: {e}",
        }
    except EC20APIError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"API error: {e}",
        }


async def ec20_save_preset(
    camera_id: str = "default",
    preset_id: int = 1,
    name: str = "",
) -> dict[str, Any]:
    """Save current EC20 camera position as a preset.

    Args:
        camera_id: EC20 camera identifier
        preset_id: ID for the preset (1-255)
        name: Name for the preset

    Returns:
        Dict containing:
            - success: bool
            - camera_id: Resolved hostname/IP
            - preset_id: Preset ID saved
            - name: Preset name
            - error: Error message if success=False

    Example:
        >>> result = await ec20_save_preset(preset_id=1, name="Podium")
        >>> print(result["name"])
        "Podium"
    """
    try:
        client, host = _get_ec20_client(camera_id)

        async with client:
            result = await client.save_preset(preset_id=preset_id, name=name)

        return {
            "success": True,
            "camera_id": host,
            "preset_id": preset_id,
            "name": name,
            "result": result,
        }

    except ValueError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": str(e),
        }
    except EC20ConnectionError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"Connection error: {e}",
        }
    except EC20APIError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"API error: {e}",
        }


async def ec20_home(camera_id: str = "default") -> dict[str, Any]:
    """Return EC20 camera to home position (pan=0, tilt=0, zoom=1).

    Args:
        camera_id: EC20 camera identifier

    Returns:
        Dict containing:
            - success: bool
            - camera_id: Resolved hostname/IP
            - result: Home operation result
            - error: Error message if success=False

    Example:
        >>> result = await ec20_home()
        >>> print(result["success"])
        True
    """
    try:
        client, host = _get_ec20_client(camera_id)

        async with client:
            result = await client.home()

        return {
            "success": True,
            "camera_id": host,
            "result": result,
        }

    except ValueError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": str(e),
        }
    except EC20ConnectionError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"Connection error: {e}",
        }
    except EC20APIError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"API error: {e}",
        }


async def ec20_enable_tracking(
    camera_id: str = "default",
    mode: str = "presenter",
) -> dict[str, Any]:
    """Enable AI tracking on EC20 camera.

    Args:
        camera_id: EC20 camera identifier
        mode: Tracking mode - "presenter", "zone", or "body"

    Returns:
        Dict containing:
            - success: bool
            - camera_id: Resolved hostname/IP
            - mode: Tracking mode enabled
            - result: Tracking operation result
            - error: Error message if success=False

    Example:
        >>> result = await ec20_enable_tracking(mode="presenter")
        >>> print(result["mode"])
        "presenter"
    """
    try:
        client, host = _get_ec20_client(camera_id)

        async with client:
            result = await client.enable_tracking(mode=mode)

        return {
            "success": True,
            "camera_id": host,
            "mode": mode,
            "result": result,
        }

    except ValueError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": str(e),
        }
    except EC20ConnectionError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"Connection error: {e}",
        }
    except EC20APIError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"API error: {e}",
        }


async def ec20_disable_tracking(camera_id: str = "default") -> dict[str, Any]:
    """Disable AI tracking on EC20 camera.

    Args:
        camera_id: EC20 camera identifier

    Returns:
        Dict containing:
            - success: bool
            - camera_id: Resolved hostname/IP
            - result: Tracking disabled result
            - error: Error message if success=False

    Example:
        >>> result = await ec20_disable_tracking()
        >>> print(result["success"])
        True
    """
    try:
        client, host = _get_ec20_client(camera_id)

        async with client:
            result = await client.disable_tracking()

        return {
            "success": True,
            "camera_id": host,
            "result": result,
        }

    except ValueError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": str(e),
        }
    except EC20ConnectionError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"Connection error: {e}",
        }
    except EC20APIError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"API error: {e}",
        }


async def ec20_list_presets(camera_id: str = "default") -> dict[str, Any]:
    """List all saved presets on EC20 camera.

    Args:
        camera_id: EC20 camera identifier

    Returns:
        Dict containing:
            - success: bool
            - camera_id: Resolved hostname/IP
            - presets: List of preset dicts with id, name, pan, tilt, zoom
            - error: Error message if success=False

    Example:
        >>> result = await ec20_list_presets()
        >>> for preset in result["presets"]:
        ...     print(f"{preset['id']}: {preset['name']}")
        1: Podium
        2: Whiteboard
    """
    try:
        client, host = _get_ec20_client(camera_id)

        async with client:
            presets = await client.get_presets()

        return {
            "success": True,
            "camera_id": host,
            "presets": presets,
        }

    except ValueError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": str(e),
        }
    except EC20ConnectionError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"Connection error: {e}",
        }
    except EC20APIError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"API error: {e}",
        }


async def ec20_get_preview(camera_id: str = "default") -> dict[str, Any]:
    """Get preview image from EC20 camera.

    Args:
        camera_id: EC20 camera identifier

    Returns:
        Dict containing:
            - success: bool
            - camera_id: Resolved hostname/IP
            - image_base64: Base64-encoded JPEG image
            - content_type: "image/jpeg"
            - error: Error message if success=False

    Example:
        >>> result = await ec20_get_preview()
        >>> import base64
        >>> image_bytes = base64.b64decode(result["image_base64"])
    """
    try:
        client, host = _get_ec20_client(camera_id)

        async with client:
            image_bytes = await client.get_preview()

        return {
            "success": True,
            "camera_id": host,
            "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
            "content_type": "image/jpeg",
        }

    except ValueError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": str(e),
        }
    except EC20ConnectionError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"Connection error: {e}",
        }
    except EC20APIError as e:
        return {
            "success": False,
            "camera_id": camera_id,
            "error": f"API error: {e}",
        }


def register(server: FastMCP) -> None:
    """Register EC20 MCP tools."""
    server.tool()(ec20_disable_tracking)
    server.tool()(ec20_enable_tracking)
    server.tool()(ec20_get_preview)
    server.tool()(ec20_get_status)
    server.tool()(ec20_goto_preset)
    server.tool()(ec20_home)
    server.tool()(ec20_list_presets)
    server.tool()(ec20_pan_tilt)
    server.tool()(ec20_save_preset)
    server.tool()(ec20_zoom)
