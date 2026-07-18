"""MCP tools for Epiphan EC20 PTZ camera control.

The EC20 is a directional PTZ camera: pan/tilt and zoom are continuous motions
(a direction starts movement; a ``stop`` halts it), presets are numeric slots
0-11, and there is no absolute positioning or position query. These tools map
directly onto that real, hardware-verified control model.

Tools:
    - ec20_get_status: Get camera identity and system configuration
    - ec20_pan_tilt: Start/stop directional pan-tilt motion
    - ec20_zoom: Start/stop directional zoom motion
    - ec20_goto_preset: Recall a numeric preset (0-11)
    - ec20_save_preset: Save current position to a numeric preset (0-11)
    - ec20_home: Return camera to home position
    - ec20_enable_tracking: Enable AI tracking (presenter/zone)
    - ec20_disable_tracking: Disable AI tracking
    - ec20_list_presets: List the addressable preset slots (0-11)
    - ec20_get_preview: (Preview is a WebSocket MJPEG stream — reports unsupported)

Example:
    ```python
    await ec20_pan_tilt(camera_id="192.168.8.5", direction="left", pan_speed=12)
    await ec20_pan_tilt(camera_id="192.168.8.5", direction="stop")
    await ec20_goto_preset(camera_id="default", preset_id=3)
    ```
"""

import base64
import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from epiphan_mcp.config import get_settings
from epiphan_mcp.integrations.ec20 import (
    PRESET_ID_MAX,
    PRESET_ID_MIN,
    EC20APIError,
    EC20Client,
    EC20ConnectionError,
)
from epiphan_mcp.models import (
    EC20OperationResult,
    EC20PanTiltResult,
    EC20PresetListResult,
    EC20PresetRecallResult,
    EC20PresetSaveResult,
    EC20PreviewResult,
    EC20StatusResult,
    EC20TrackingResult,
    EC20ZoomResult,
)

logger = logging.getLogger(__name__)

_CameraId = Annotated[
    str,
    Field(
        description="EC20 camera identifier: 'default' for the first configured camera, "
        "an IP address or hostname, or a numeric index like '0' or '1'."
    ),
]
_Direction = Annotated[
    str,
    Field(description="Pan/tilt direction: 'up', 'down', 'left', 'right', or 'stop'."),
]
_PanSpeed = Annotated[
    int,
    Field(ge=1, description="Pan speed (typical 1-24). Ignored when direction is 'stop'."),
]
_TiltSpeed = Annotated[
    int,
    Field(ge=1, description="Tilt speed (typical 1-20). Ignored when direction is 'stop'."),
]
_ZoomDirection = Annotated[
    str,
    Field(description="Zoom direction: 'in', 'out', or 'stop'."),
]
_ZoomSpeed = Annotated[
    int,
    Field(ge=1, description="Zoom speed (typical 1-7). Ignored when direction is 'stop'."),
]
_PresetId = Annotated[
    int,
    Field(ge=PRESET_ID_MIN, le=PRESET_ID_MAX, description="Preset ID (0-11, per EC20 spec)."),
]
_TrackingMode = Annotated[
    str,
    Field(description="Tracking mode: 'presenter' (default) or 'zone'."),
]


def _get_ec20_client(camera_id: str = "default") -> tuple[EC20Client, str]:
    """Get EC20 client for a camera ID, plus the resolved host.

    Raises:
        ValueError: If camera_id cannot be resolved.
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


async def ec20_get_status(camera_id: _CameraId = "default") -> EC20StatusResult:
    """Get EC20 camera identity and system configuration.

    Returns real device fields (model, firmware, serial, work mode, NDI info).
    """
    try:
        client, host = _get_ec20_client(camera_id)
        async with client:
            status = await client.get_status()
        return EC20StatusResult(success=True, camera_id=host, camera=status)
    except ValueError as e:
        return EC20StatusResult(success=False, camera_id=camera_id, error=str(e))
    except EC20ConnectionError as e:
        return EC20StatusResult(success=False, camera_id=camera_id, error=f"Connection error: {e}")
    except EC20APIError as e:
        return EC20StatusResult(success=False, camera_id=camera_id, error=f"API error: {e}")


async def ec20_pan_tilt(
    camera_id: _CameraId = "default",
    direction: _Direction = "stop",
    pan_speed: _PanSpeed = 12,
    tilt_speed: _TiltSpeed = 12,
) -> EC20PanTiltResult:
    """Start or stop directional pan/tilt motion on the EC20.

    The camera moves continuously in ``direction`` until you call again with
    ``direction='stop'``. There is no absolute-position command.

    Example:
        >>> await ec20_pan_tilt(direction="left", pan_speed=12)   # start
        >>> await ec20_pan_tilt(direction="stop")                 # stop
    """
    try:
        client, host = _get_ec20_client(camera_id)
        async with client:
            if direction == "stop":
                result = await client.stop()
            else:
                result = await client.move(direction, pan_speed=pan_speed, tilt_speed=tilt_speed)
        return EC20PanTiltResult(
            success=True,
            camera_id=host,
            direction=direction,
            pan_speed=None if direction == "stop" else pan_speed,
            tilt_speed=None if direction == "stop" else tilt_speed,
            result=result,
        )
    except ValueError as e:
        return EC20PanTiltResult(success=False, camera_id=camera_id, error=str(e))
    except EC20ConnectionError as e:
        return EC20PanTiltResult(success=False, camera_id=camera_id, error=f"Connection error: {e}")
    except EC20APIError as e:
        return EC20PanTiltResult(success=False, camera_id=camera_id, error=f"API error: {e}")


async def ec20_zoom(
    camera_id: _CameraId = "default",
    direction: _ZoomDirection = "stop",
    speed: _ZoomSpeed = 5,
) -> EC20ZoomResult:
    """Start or stop directional zoom motion on the EC20.

    Zoom moves continuously ``in`` or ``out`` until you call with
    ``direction='stop'``. There is no absolute zoom-level command.

    Example:
        >>> await ec20_zoom(direction="in", speed=5)   # start zooming in
        >>> await ec20_zoom(direction="stop")          # stop
    """
    try:
        client, host = _get_ec20_client(camera_id)
        async with client:
            if direction == "stop":
                result = await client.zoom_stop()
            else:
                result = await client.zoom(direction, speed=speed)
        return EC20ZoomResult(
            success=True,
            camera_id=host,
            direction=direction,
            speed=None if direction == "stop" else speed,
            result=result,
        )
    except ValueError as e:
        return EC20ZoomResult(success=False, camera_id=camera_id, error=str(e))
    except EC20ConnectionError as e:
        return EC20ZoomResult(success=False, camera_id=camera_id, error=f"Connection error: {e}")
    except EC20APIError as e:
        return EC20ZoomResult(success=False, camera_id=camera_id, error=f"API error: {e}")


async def ec20_goto_preset(
    camera_id: _CameraId = "default",
    preset_id: _PresetId = 0,
) -> EC20PresetRecallResult:
    """Recall a saved EC20 preset position (0-11)."""
    try:
        client, host = _get_ec20_client(camera_id)
        async with client:
            result = await client.goto_preset(preset_id=preset_id)
        return EC20PresetRecallResult(
            success=True, camera_id=host, preset_id=preset_id, result=result
        )
    except ValueError as e:
        return EC20PresetRecallResult(success=False, camera_id=camera_id, error=str(e))
    except EC20ConnectionError as e:
        return EC20PresetRecallResult(
            success=False, camera_id=camera_id, error=f"Connection error: {e}"
        )
    except EC20APIError as e:
        return EC20PresetRecallResult(success=False, camera_id=camera_id, error=f"API error: {e}")


async def ec20_save_preset(
    camera_id: _CameraId = "default",
    preset_id: _PresetId = 0,
) -> EC20PresetSaveResult:
    """Save the current EC20 position to a numeric preset slot (0-11).

    The EC20 stores presets by number only — there is no name.
    """
    try:
        client, host = _get_ec20_client(camera_id)
        async with client:
            result = await client.save_preset(preset_id=preset_id)
        return EC20PresetSaveResult(
            success=True, camera_id=host, preset_id=preset_id, result=result
        )
    except ValueError as e:
        return EC20PresetSaveResult(success=False, camera_id=camera_id, error=str(e))
    except EC20ConnectionError as e:
        return EC20PresetSaveResult(
            success=False, camera_id=camera_id, error=f"Connection error: {e}"
        )
    except EC20APIError as e:
        return EC20PresetSaveResult(success=False, camera_id=camera_id, error=f"API error: {e}")


async def ec20_home(camera_id: _CameraId = "default") -> EC20OperationResult:
    """Return the EC20 camera to its home position."""
    try:
        client, host = _get_ec20_client(camera_id)
        async with client:
            result = await client.home()
        return EC20OperationResult(success=True, camera_id=host, result=result)
    except ValueError as e:
        return EC20OperationResult(success=False, camera_id=camera_id, error=str(e))
    except EC20ConnectionError as e:
        return EC20OperationResult(
            success=False, camera_id=camera_id, error=f"Connection error: {e}"
        )
    except EC20APIError as e:
        return EC20OperationResult(success=False, camera_id=camera_id, error=f"API error: {e}")


async def ec20_enable_tracking(
    camera_id: _CameraId = "default",
    mode: _TrackingMode = "presenter",
) -> EC20TrackingResult:
    """Enable AI tracking on the EC20 camera ('presenter' or 'zone')."""
    try:
        client, host = _get_ec20_client(camera_id)
        async with client:
            result = await client.enable_tracking(mode=mode)
        return EC20TrackingResult(success=True, camera_id=host, mode=mode, result=result)
    except ValueError as e:
        return EC20TrackingResult(success=False, camera_id=camera_id, error=str(e))
    except EC20ConnectionError as e:
        return EC20TrackingResult(
            success=False, camera_id=camera_id, error=f"Connection error: {e}"
        )
    except EC20APIError as e:
        return EC20TrackingResult(success=False, camera_id=camera_id, error=f"API error: {e}")


async def ec20_disable_tracking(camera_id: _CameraId = "default") -> EC20OperationResult:
    """Disable AI tracking on the EC20 camera."""
    try:
        client, host = _get_ec20_client(camera_id)
        async with client:
            result = await client.disable_tracking()
        return EC20OperationResult(success=True, camera_id=host, result=result)
    except ValueError as e:
        return EC20OperationResult(success=False, camera_id=camera_id, error=str(e))
    except EC20ConnectionError as e:
        return EC20OperationResult(
            success=False, camera_id=camera_id, error=f"Connection error: {e}"
        )
    except EC20APIError as e:
        return EC20OperationResult(success=False, camera_id=camera_id, error=f"API error: {e}")


async def ec20_list_presets(camera_id: _CameraId = "default") -> EC20PresetListResult:
    """List the addressable EC20 preset slots (0-11).

    The EC20 firmware has no command to report which slots are populated or
    their names, so this returns the valid slot ids you can recall/save.
    """
    try:
        _, host = _get_ec20_client(camera_id)
        presets = [{"id": pid} for pid in range(PRESET_ID_MIN, PRESET_ID_MAX + 1)]
        return EC20PresetListResult(success=True, camera_id=host, presets=presets)
    except ValueError as e:
        return EC20PresetListResult(success=False, camera_id=camera_id, error=str(e))


async def ec20_get_preview(camera_id: _CameraId = "default") -> EC20PreviewResult:
    """Get a preview image from the EC20 camera.

    Note: the EC20 exposes preview only as an MJPEG WebSocket stream
    (/ws/mjpeg); single-frame HTTP capture is not supported on current
    firmware, so this reports an error rather than a fabricated image.
    """
    try:
        client, host = _get_ec20_client(camera_id)
        async with client:
            image_bytes = await client.get_preview()
        return EC20PreviewResult(
            success=True,
            camera_id=host,
            image_base64=base64.b64encode(image_bytes).decode("utf-8"),
            content_type="image/jpeg",
        )
    except ValueError as e:
        return EC20PreviewResult(success=False, camera_id=camera_id, error=str(e))
    except EC20ConnectionError as e:
        return EC20PreviewResult(success=False, camera_id=camera_id, error=f"Connection error: {e}")
    except EC20APIError as e:
        return EC20PreviewResult(success=False, camera_id=camera_id, error=f"API error: {e}")


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
