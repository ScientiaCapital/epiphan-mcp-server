"""FastMCP server for Epiphan Pearl devices."""

import logging
from typing import Any

from fastmcp import FastMCP

from .client import PearlClient, PearlAPIError
from .config import get_settings

logger = logging.getLogger(__name__)

# Create MCP server instance
mcp = FastMCP(
    "epiphan-pearl",
    description="Control Epiphan Pearl video capture devices through natural language",
)


def get_client(device_id: str = "default") -> PearlClient:
    """
    Get a PearlClient for the specified device.

    Args:
        device_id: Device identifier (IP, hostname, "default", or index)

    Returns:
        Configured PearlClient instance.
    """
    settings = get_settings()
    host = settings.get_device_host(device_id)
    return PearlClient.from_settings(host, settings)


# ============================================================
# Device Status Tools
# ============================================================


@mcp.tool()
async def get_device_status(device_id: str = "default") -> dict[str, Any]:
    """
    Get the current status of an Epiphan Pearl device.

    Use this to check device health, storage levels, uptime, and active operations.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device,
                   or specify an IP address, hostname, or device index.

    Returns:
        Device status including:
        - Storage usage and availability
        - System uptime
        - CPU and memory usage
        - Firmware version
        - Current recording/streaming state
    """
    try:
        async with get_client(device_id) as client:
            status = await client.get_system_status()
            recorder_status = await client.get_recorder_status(1)

            return {
                "success": True,
                "device": client.host,
                "status": {
                    "uptime_hours": status.uptime_hours,
                    "storage": status.storage.model_dump() if status.storage else None,
                    "firmware": status.firmware_version,
                    "model": status.model,
                    "recording": recorder_status.state.value,
                },
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


@mcp.tool()
async def list_devices() -> dict[str, Any]:
    """
    List all configured Epiphan Pearl devices.

    Returns the list of devices configured in the PEARL_DEVICES environment variable.

    Returns:
        List of device hostnames/IPs with their indices.
    """
    settings = get_settings()
    devices = settings.get_device_list()

    return {
        "success": True,
        "fleet_name": settings.fleet_name,
        "device_count": len(devices),
        "devices": [{"index": i, "host": host} for i, host in enumerate(devices)],
    }


# ============================================================
# Recording Tools
# ============================================================


@mcp.tool()
async def start_recording(device_id: str = "default", recorder: int = 1) -> dict[str, Any]:
    """
    Start recording on an Epiphan Pearl device.

    This begins recording video to the device's local storage.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device,
                   or specify an IP address, hostname, or device index.
        recorder: Recorder number (1-based). Most setups use recorder 1.
                  Use higher numbers for multi-recorder configurations.

    Returns:
        Confirmation of recording start with device and recorder details.
    """
    try:
        async with get_client(device_id) as client:
            result = await client.start_recording(recorder)
            return result.model_dump()
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "recorder": recorder,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


@mcp.tool()
async def stop_recording(device_id: str = "default", recorder: int = 1) -> dict[str, Any]:
    """
    Stop recording on an Epiphan Pearl device.

    This stops the active recording and finalizes the video file.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device,
                   or specify an IP address, hostname, or device index.
        recorder: Recorder number (1-based). Must match the recorder that's recording.

    Returns:
        Confirmation of recording stop with device and recorder details.
    """
    try:
        async with get_client(device_id) as client:
            result = await client.stop_recording(recorder)
            return result.model_dump()
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "recorder": recorder,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


@mcp.tool()
async def get_recording_status(device_id: str = "default", recorder: int = 1) -> dict[str, Any]:
    """
    Get the current recording status of an Epiphan Pearl device.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        recorder: Recorder number (1-based).

    Returns:
        Recording state (recording, stopped, paused, error) and details.
    """
    try:
        async with get_client(device_id) as client:
            status = await client.get_recorder_status(recorder)
            return {
                "success": True,
                "device": client.host,
                "recorder": recorder,
                "state": status.state.value,
                "duration_seconds": status.duration_seconds,
                "file_size_bytes": status.file_size_bytes,
                "filename": status.filename,
            }
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "recorder": recorder,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


# ============================================================
# Streaming Tools
# ============================================================


@mcp.tool()
async def start_stream(device_id: str = "default", channel: int = 1) -> dict[str, Any]:
    """
    Start streaming on an Epiphan Pearl device.

    This begins streaming video to the configured destination (RTMP, SRT, etc.).
    The stream destination must be configured on the device beforehand.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based) to start streaming.

    Returns:
        Confirmation of stream start with device and channel details.
    """
    try:
        async with get_client(device_id) as client:
            result = await client.start_stream(channel)
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


@mcp.tool()
async def stop_stream(device_id: str = "default", channel: int = 1) -> dict[str, Any]:
    """
    Stop streaming on an Epiphan Pearl device.

    This stops the active stream on the specified channel.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based) to stop streaming.

    Returns:
        Confirmation of stream stop with device and channel details.
    """
    try:
        async with get_client(device_id) as client:
            result = await client.stop_stream(channel)
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


# ============================================================
# Layout Tools
# ============================================================


@mcp.tool()
async def switch_layout(
    device_id: str = "default", channel: int = 1, layout_id: str = ""
) -> dict[str, Any]:
    """
    Switch the active layout/scene on an Epiphan Pearl channel.

    Layouts define how video sources are arranged and displayed.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based).
        layout_id: Layout identifier to switch to.

    Returns:
        Confirmation of layout switch with device and channel details.
    """
    if not layout_id:
        return {
            "success": False,
            "error": "layout_id is required",
            "device": device_id,
            "channel": channel,
        }

    try:
        async with get_client(device_id) as client:
            result = await client.switch_layout(channel, layout_id)
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


# ============================================================
# Fleet Management Tools (Phase 3)
# ============================================================


@mcp.tool()
async def get_fleet_status() -> dict[str, Any]:
    """
    Get status of all configured Epiphan Pearl devices.

    This provides a fleet-wide view of device health and activity.

    Returns:
        Summary of fleet status including:
        - Total devices configured
        - Devices online/offline
        - Devices currently recording
        - Devices currently streaming
        - Any alerts or issues
    """
    settings = get_settings()
    devices = settings.get_device_list()

    if not devices:
        return {
            "success": True,
            "fleet_name": settings.fleet_name,
            "total_devices": 0,
            "message": "No devices configured. Set PEARL_DEVICES environment variable.",
        }

    results = []
    online_count = 0
    recording_count = 0
    alerts = []

    for host in devices:
        try:
            async with PearlClient.from_settings(host, settings) as client:
                status = await client.get_system_status()
                recorder = await client.get_recorder_status(1)

                online_count += 1
                if recorder.state.value == "recording":
                    recording_count += 1

                # Check for alerts
                if status.storage and status.storage.percent_used > 80:
                    alerts.append({
                        "device": host,
                        "severity": "warning",
                        "message": f"Storage at {status.storage.percent_used:.1f}%",
                    })

                results.append({
                    "host": host,
                    "online": True,
                    "recording": recorder.state.value == "recording",
                    "storage_percent": status.storage.percent_used if status.storage else None,
                })

        except Exception as e:
            results.append({
                "host": host,
                "online": False,
                "error": str(e),
            })
            alerts.append({
                "device": host,
                "severity": "error",
                "message": f"Device offline: {e}",
            })

    return {
        "success": True,
        "fleet_name": settings.fleet_name,
        "total_devices": len(devices),
        "online_devices": online_count,
        "recording_devices": recording_count,
        "alerts_count": len(alerts),
        "devices": results,
        "alerts": alerts,
    }


@mcp.tool()
async def batch_start_recording(device_ids: str = "all") -> dict[str, Any]:
    """
    Start recording on multiple Epiphan Pearl devices.

    Args:
        device_ids: Comma-separated list of device IDs, or "all" for all devices.

    Returns:
        Results for each device.
    """
    settings = get_settings()

    if device_ids == "all":
        hosts = settings.get_device_list()
    else:
        hosts = [d.strip() for d in device_ids.split(",")]

    if not hosts:
        return {
            "success": False,
            "error": "No devices specified",
        }

    results = []
    success_count = 0

    for host in hosts:
        try:
            async with PearlClient.from_settings(host, settings) as client:
                await client.start_recording(1)
                results.append({"device": host, "success": True})
                success_count += 1
        except Exception as e:
            results.append({"device": host, "success": False, "error": str(e)})

    return {
        "success": success_count == len(hosts),
        "total_devices": len(hosts),
        "successful": success_count,
        "failed": len(hosts) - success_count,
        "results": results,
    }


@mcp.tool()
async def batch_stop_recording(device_ids: str = "all") -> dict[str, Any]:
    """
    Stop recording on multiple Epiphan Pearl devices.

    Args:
        device_ids: Comma-separated list of device IDs, or "all" for all devices.

    Returns:
        Results for each device.
    """
    settings = get_settings()

    if device_ids == "all":
        hosts = settings.get_device_list()
    else:
        hosts = [d.strip() for d in device_ids.split(",")]

    if not hosts:
        return {
            "success": False,
            "error": "No devices specified",
        }

    results = []
    success_count = 0

    for host in hosts:
        try:
            async with PearlClient.from_settings(host, settings) as client:
                await client.stop_recording(1)
                results.append({"device": host, "success": True})
                success_count += 1
        except Exception as e:
            results.append({"device": host, "success": False, "error": str(e)})

    return {
        "success": success_count == len(hosts),
        "total_devices": len(hosts),
        "successful": success_count,
        "failed": len(hosts) - success_count,
        "results": results,
    }
