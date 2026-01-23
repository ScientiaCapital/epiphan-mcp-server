"""FastMCP server for Epiphan Pearl devices."""

import logging
from typing import Any

from fastmcp import FastMCP

from .client import PearlAPIError, PearlClient
from .config import get_settings
from .tools.ai_tools import (
    analyze_channel_scene as _analyze_channel_scene,
)
from .tools.ai_tools import (
    check_video_quality as _check_video_quality,
)
from .tools.ai_tools import (
    clear_change_detection_cache as _clear_change_detection_cache,
)
from .tools.ai_tools import (
    detect_layout_changes as _detect_layout_changes,
)
from .tools.ai_tools import (
    extract_text_from_preview as _extract_text_from_preview,
)

logger = logging.getLogger(__name__)

# Create MCP server instance
mcp = FastMCP(
    "epiphan-pearl",
    instructions="Control Epiphan Pearl video capture devices through natural language",
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
            recorder_status = await client.get_recorder_status("recorder-1")

            return {
                "success": True,
                "device": client.host,
                "status": {
                    "uptime_hours": status.uptime_hours,
                    "storage": {
                        "total_gb": status.storage_total_gb,
                        "free_gb": status.storage_free_gb,
                        "used_percent": status.storage_used_percent,
                    },
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
# Input Source Tools
# ============================================================


@mcp.tool()
async def list_inputs(device_id: str = "default") -> dict[str, Any]:
    """
    List available input sources on an Epiphan Pearl device.

    Input sources include HDMI, SDI, USB, and network inputs that can be
    used in channel layouts.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        List of input sources including:
        - Input ID and name
        - Input type (HDMI, SDI, etc.)
        - Connection status
        - Resolution and format info
    """
    try:
        async with get_client(device_id) as client:
            inputs = await client.get_inputs()
            return {
                "success": True,
                "device": client.host,
                "total_inputs": len(inputs),
                "inputs": [inp.model_dump() for inp in inputs],
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


# ============================================================
# Storage Tools
# ============================================================


@mcp.tool()
async def get_storage_report(device_id: str = "default") -> dict[str, Any]:
    """
    Get detailed storage information from an Epiphan Pearl device.

    Provides comprehensive storage details for capacity planning and monitoring.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        Storage report including:
        - Storage ID and type
        - Total capacity in bytes and GB
        - Free space in bytes and GB
        - Used percentage
        - Mount point and status
    """
    try:
        async with get_client(device_id) as client:
            storages = await client.get_storages()
            storage_list = []
            total_bytes = 0
            free_bytes = 0

            for storage in storages:
                storage_data = storage.model_dump()
                storage_list.append(storage_data)
                total_bytes += storage.total_bytes or 0
                free_bytes += storage.free_bytes or 0

            used_bytes = total_bytes - free_bytes
            used_percent = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0

            return {
                "success": True,
                "device": client.host,
                "total_storages": len(storages),
                "storages": storage_list,
                "summary": {
                    "total_bytes": total_bytes,
                    "total_gb": round(total_bytes / (1024**3), 2),
                    "free_bytes": free_bytes,
                    "free_gb": round(free_bytes / (1024**3), 2),
                    "used_bytes": used_bytes,
                    "used_gb": round(used_bytes / (1024**3), 2),
                    "used_percent": round(used_percent, 1),
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
            # Convert int to string recorder ID (e.g., 1 -> "recorder-1")
            recorder_id = f"recorder-{recorder}" if isinstance(recorder, int) else str(recorder)
            result = await client.start_recording(recorder_id)
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
            recorder_id = f"recorder-{recorder}" if isinstance(recorder, int) else str(recorder)
            result = await client.stop_recording(recorder_id)
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
            recorder_id = f"recorder-{recorder}" if isinstance(recorder, int) else str(recorder)
            status = await client.get_recorder_status(recorder_id)
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
    Starts all publishers/streams on the specified channel.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based) to start streaming.

    Returns:
        Confirmation of stream start with device and channel details.
    """
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.start_all_publishers(channel_id)
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

    This stops all active streams on the specified channel.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based) to stop streaming.

    Returns:
        Confirmation of stream stop with device and channel details.
    """
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.stop_all_publishers(channel_id)
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
async def get_stream_status(
    device_id: str = "default", channel: int = 1, publisher: str = "publisher-1"
) -> dict[str, Any]:
    """
    Get the status of a specific stream/publisher on an Epiphan Pearl device.

    Use this to check if a stream is active, its duration, bitrate, and bytes sent.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based) containing the publisher.
        publisher: Publisher ID (e.g., "publisher-1").

    Returns:
        Stream status including:
        - state: Current state (streaming, stopped, etc.)
        - duration_seconds: How long the stream has been active
        - bitrate_bps: Current bitrate in bits per second
        - bytes_sent: Total bytes sent since stream started
        - destination: Stream destination URL
    """
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            status = await client.get_publisher_status(channel_id, publisher)
            return {
                "success": True,
                "device": client.host,
                "channel": channel_id,
                "publisher": publisher,
                "state": status.state.value,
                "duration_seconds": status.duration_seconds,
                "bitrate_bps": status.bitrate_actual or 0,
                "bytes_sent": status.bytes_sent or 0,
                "destination": status.destination or "",
            }
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "channel": channel,
            "publisher": publisher,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


# ============================================================
# Bookmark Tools
# ============================================================


@mcp.tool()
async def add_bookmark(
    device_id: str = "default", channel: int = 1, text: str = ""
) -> dict[str, Any]:
    """
    Add a bookmark to an active recording on an Epiphan Pearl device.

    Bookmarks mark important moments in a recording for easy navigation later.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based) with the active recording.
        text: Optional bookmark text/label.

    Returns:
        Confirmation of bookmark creation with device and channel details.
    """
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


# ============================================================
# Layout Tools
# ============================================================


@mcp.tool()
async def list_layouts(device_id: str = "default", channel: int = 1) -> dict[str, Any]:
    """
    List available layouts for a channel on an Epiphan Pearl device.

    Layouts define different arrangements of video sources (e.g., full screen,
    picture-in-picture, side-by-side).

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based).

    Returns:
        List of available layouts including:
        - Layout ID and name
        - Which layout is currently active
    """
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


# ============================================================
# Single Touch Tools
# ============================================================


@mcp.tool()
async def single_touch_start(device_id: str = "default") -> dict[str, Any]:
    """
    Start all recorders and streams on an Epiphan Pearl device with one command.

    This is a convenience function that starts everything at once - useful for
    beginning a recording session quickly.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        Confirmation that all recorders and streams have started.
    """
    try:
        async with get_client(device_id) as client:
            result = await client.single_touch_start()
            return {
                "success": True,
                "device": client.host,
                "message": result.message,
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
async def single_touch_stop(device_id: str = "default") -> dict[str, Any]:
    """
    Stop all recorders and streams on an Epiphan Pearl device with one command.

    This is a convenience function that stops everything at once - useful for
    ending a recording session quickly.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        Confirmation that all recorders and streams have stopped.
    """
    try:
        async with get_client(device_id) as client:
            result = await client.single_touch_stop()
            return {
                "success": True,
                "device": client.host,
                "message": result.message,
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


# ============================================================
# Scheduled Events Tools
# ============================================================


@mcp.tool()
async def get_scheduled_events(
    device_id: str = "default", limit: int = 100
) -> dict[str, Any]:
    """
    Get scheduled recording events from CMS integration (Kaltura/Panopto/Opencast).

    Use this to see upcoming scheduled recordings configured via a CMS.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        limit: Maximum number of events to return (default 100).

    Returns:
        List of scheduled events including:
        - Event name and ID
        - Start/end times
        - CMS type (Kaltura, Panopto, Opencast)
        - Current status
    """
    try:
        async with get_client(device_id) as client:
            events = await client.get_events(limit=limit)
            return {
                "success": True,
                "device": client.host,
                "total_events": len(events),
                "events": events,
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


# ============================================================
# Predictive Maintenance Tools
# ============================================================


@mcp.tool()
async def predict_storage_full(
    device_id: str = "default", recorder: int = 1, assumed_bitrate_mbps: float = 8.0
) -> dict[str, Any]:
    """
    Predict when device storage will be full based on current recording rate.

    This is a predictive maintenance tool that helps prevent storage issues
    by estimating time remaining before storage fills up.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        recorder: Recorder number (1-based) to check for active recording.
        assumed_bitrate_mbps: Assumed recording bitrate in Mbps if not actively recording.
                              Default 8.0 Mbps is typical for 1080p H.264.

    Returns:
        Storage prediction including:
        - hours_until_full: Estimated hours until storage is full
        - storage_free_gb: Current free storage in GB
        - storage_total_gb: Total storage capacity in GB
        - is_recording: Whether currently recording
        - bitrate_mbps: Actual or assumed recording bitrate
        - warning: True if storage is critically low (<10%)
    """
    try:
        async with get_client(device_id) as client:
            # Get storage info
            storage_status = await client.get_system_status()
            free_bytes = storage_status.storage_free_gb * 1024 * 1024 * 1024

            # Get recording status for bitrate
            recorder_id = f"recorder-{recorder}"
            recorder_status = await client.get_recorder_status(recorder_id)
            is_recording = recorder_status.state.value == "recording"

            # Use actual bitrate if recording, otherwise use assumed
            bitrate_bps: float = (
                recorder_status.bitrate
                if is_recording and recorder_status.bitrate
                else assumed_bitrate_mbps * 1_000_000
            )

            bitrate_mbps = bitrate_bps / 1_000_000
            bytes_per_hour = bitrate_bps / 8 * 3600  # bits/sec -> bytes/hour

            # Calculate hours until full
            hours_until_full = (
                free_bytes / bytes_per_hour if bytes_per_hour > 0 else float("inf")
            )

            # Determine warning status (>= 90% used or < 2 hours remaining)
            storage_used_percent = storage_status.storage_used_percent or 0
            warning = storage_used_percent >= 90 or hours_until_full < 2

            return {
                "success": True,
                "device": client.host,
                "hours_until_full": round(hours_until_full, 1),
                "storage_free_gb": round(storage_status.storage_free_gb, 1),
                "storage_total_gb": round(storage_status.storage_total_gb, 1),
                "storage_used_percent": round(storage_used_percent, 1),
                "is_recording": is_recording,
                "bitrate_mbps": round(bitrate_mbps, 1),
                "warning": warning,
                "recommendation": (
                    "Storage critically low - archive or delete recordings"
                    if warning
                    else "Storage capacity is sufficient"
                ),
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
async def get_device_health_score(device_id: str = "default") -> dict[str, Any]:
    """
    Calculate an overall health score for a Pearl device (0-100).

    This AI-powered tool aggregates multiple health indicators into a single
    score, making it easy to identify devices that need attention.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        Health assessment including:
        - score: Overall health score 0-100 (higher is better)
        - categories: Breakdown by category (storage, recording, etc.)
        - issues: List of any detected issues
        - is_recording: Whether device is currently recording
        - recommendation: Suggested action if any issues found
    """
    try:
        async with get_client(device_id) as client:
            issues: list[str] = []
            category_scores: dict[str, dict[str, Any]] = {}

            # Get device and storage info
            storage_status = await client.get_system_status()

            # Storage health (50 points max)
            storage_used_percent = storage_status.storage_used_percent or 0
            if storage_used_percent >= 90:
                storage_score = 10  # Critical
                storage_healthy = False
                issues.append(f"Storage critically low: {storage_used_percent:.0f}% used")
            elif storage_used_percent >= 75:
                storage_score = 30  # Warning
                storage_healthy = False
                issues.append(f"Storage running low: {storage_used_percent:.0f}% used")
            else:
                storage_score = 50  # Healthy
                storage_healthy = True

            category_scores["storage"] = {
                "score": storage_score,
                "max": 50,
                "healthy": storage_healthy,
                "used_percent": round(storage_used_percent, 1),
            }

            # Recording health (50 points max)
            try:
                recorder_status = await client.get_recorder_status("recorder-1")
                is_recording = recorder_status.state.value == "recording"
                recording_score = 50  # Healthy - device is responsive
                recording_healthy = True
            except PearlAPIError:
                is_recording = False
                recording_score = 25  # Degraded - couldn't check recorder
                recording_healthy = False
                issues.append("Could not check recorder status")

            category_scores["recording"] = {
                "score": recording_score,
                "max": 50,
                "healthy": recording_healthy,
                "is_recording": is_recording,
            }

            # Calculate total score
            total_score = sum(cat["score"] for cat in category_scores.values())

            # Generate recommendation
            if total_score >= 80:
                recommendation = "Device is healthy - no action needed"
            elif total_score >= 60:
                recommendation = "Device has minor issues - review when convenient"
            elif total_score >= 40:
                recommendation = "Device needs attention - address issues soon"
            else:
                recommendation = "Device is unhealthy - immediate attention required"

            return {
                "success": True,
                "device": client.host,
                "score": total_score,
                "categories": category_scores,
                "issues": issues,
                "is_recording": is_recording,
                "recommendation": recommendation,
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
                recorder = await client.get_recorder_status("recorder-1")

                online_count += 1
                if recorder.state.value == "recording":
                    recording_count += 1

                # Check for alerts (storage threshold: 80%)
                if status.storage_used_percent > 80:
                    alerts.append(
                        {
                            "device": host,
                            "severity": "warning",
                            "message": f"Storage at {status.storage_used_percent:.1f}%",
                        }
                    )

                results.append(
                    {
                        "host": host,
                        "online": True,
                        "recording": recorder.state.value == "recording",
                        "storage_percent": status.storage_used_percent,
                    }
                )

        except Exception as e:
            results.append(
                {
                    "host": host,
                    "online": False,
                    "error": str(e),
                }
            )
            alerts.append(
                {
                    "device": host,
                    "severity": "error",
                    "message": f"Device offline: {e}",
                }
            )

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
                await client.start_recording("recorder-1")
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
                await client.stop_recording("recorder-1")
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


# ============================================================
# AI-Powered Analysis Tools (Phase 4)
# ============================================================
# These tools use vision LLMs to analyze video content from Pearl channels.
# Requires OPENROUTER_API_KEY environment variable for real analysis.
# Falls back to mock responses if not configured.


@mcp.tool()
async def analyze_channel_scene(
    device_id: str = "default",
    channel: str = "1",
    analysis_type: str = "scene_description",
) -> dict[str, Any]:
    """
    Analyze the current scene on a Pearl channel using AI vision.

    Uses a vision-capable LLM to understand what's currently being captured,
    enabling intelligent automation and monitoring for video production.

    Args:
        device_id: Pearl device identifier. Use "default" for the first configured device.
        channel: Channel ID to analyze (e.g., "1", "2").
        analysis_type: Type of analysis to perform:
            - "scene_description": General description of what's on screen
            - "content_detection": Classify content type and subject matter
            - "quality_check": Technical quality assessment (lighting, focus, framing)
            - "text_extraction": OCR to extract visible text (slides, graphics)
            - "presenter_detection": Detect and describe presenters in frame

    Returns:
        Analysis results including AI description, model used, and metadata.

    Examples:
        >>> # Describe what's happening on channel 1
        >>> await analyze_channel_scene(channel="1", analysis_type="scene_description")

        >>> # Check video quality during a live event
        >>> await analyze_channel_scene(channel="1", analysis_type="quality_check")

        >>> # Extract text from presentation slides
        >>> await analyze_channel_scene(channel="1", analysis_type="text_extraction")
    """
    return await _analyze_channel_scene(
        device_id=device_id,
        channel=channel,
        analysis_type=analysis_type,  # type: ignore
    )


@mcp.tool()
async def extract_text_from_preview(
    device_id: str = "default",
    channel: str = "1",
) -> dict[str, Any]:
    """
    Extract visible text from a Pearl channel preview using AI OCR.

    Uses a vision LLM optimized for text recognition (Qwen VL) to read text
    from presentations, slides, lower thirds, and other on-screen graphics.

    Useful for:
    - Automated captioning and transcription
    - Content indexing and search
    - Slide detection and chapter markers
    - Compliance monitoring (detecting required disclosures)

    Args:
        device_id: Pearl device identifier.
        channel: Channel ID to analyze.

    Returns:
        Extracted text content organized by location/type.

    Example:
        >>> result = await extract_text_from_preview(channel="1")
        >>> print(result["text"])
        "Title: Introduction to Machine Learning
         Subtitle: Chapter 3 - Neural Networks
         Footer: Presented by Dr. Smith"
    """
    return await _extract_text_from_preview(device_id=device_id, channel=channel)


@mcp.tool()
async def detect_layout_changes(
    device_id: str = "default",
    channel: str = "1",
    sensitivity: str = "medium",
) -> dict[str, Any]:
    """
    Detect if the channel content has changed since last check.

    Monitors a channel for significant changes like scene transitions,
    slide advances, or presenter movement. Uses efficient image hashing
    for quick comparisons, with AI analysis to describe detected changes.

    Useful for:
    - Automated recording triggers on scene changes
    - Event logging and chapter markers
    - Slide advance detection for presentations
    - Production monitoring and alerts

    Args:
        device_id: Pearl device identifier.
        channel: Channel ID to monitor.
        sensitivity: Change detection sensitivity:
            - "low": Only detect major scene changes (cuts, transitions)
            - "medium": Detect slide changes, significant presenter movement
            - "high": Detect any visible changes (subtle movements)

    Returns:
        Change detection results including whether change occurred and description.

    Example:
        >>> # First call establishes baseline
        >>> result = await detect_layout_changes(channel="1")
        >>> print(result["changed"])  # False (first frame)

        >>> # Later call detects changes
        >>> result = await detect_layout_changes(channel="1")
        >>> if result["changed"]:
        ...     print(result["message"])  # "Slide advanced to new content"
    """
    return await _detect_layout_changes(
        device_id=device_id,
        channel=channel,
        sensitivity=sensitivity,  # type: ignore
    )


@mcp.tool()
async def check_video_quality(
    device_id: str = "default",
    channel: str = "1",
) -> dict[str, Any]:
    """
    Check video quality on a Pearl channel using AI analysis.

    Analyzes the current frame for technical quality issues and provides
    actionable feedback for production improvement.

    Checks for:
    - Lighting issues (over/underexposed areas, uneven lighting)
    - Focus problems (blur, soft focus)
    - Framing issues (headroom, rule of thirds, cropping)
    - Visible artifacts or technical problems
    - Overall production quality rating

    Args:
        device_id: Pearl device identifier.
        channel: Channel ID to check.

    Returns:
        Quality assessment with specific issues and recommendations.

    Example:
        >>> result = await check_video_quality(channel="1")
        >>> print(result["quality_report"])
        "Video quality assessment:
        - Lighting: Good, even illumination
        - Focus: Sharp
        - Framing: Presenter has adequate headroom
        - Issues: None detected
        Overall quality: Excellent"
    """
    return await _check_video_quality(device_id=device_id, channel=channel)


@mcp.tool()
async def clear_change_detection_cache(
    device_id: str | None = None,
    channel: str | None = None,
) -> dict[str, Any]:
    """
    Clear the change detection cache.

    Resets stored frames used for change detection. Call this when:
    - Starting a new monitoring session
    - After intentional content changes
    - When resetting the baseline for comparison

    Args:
        device_id: Specific device to clear (None for all devices).
        channel: Specific channel to clear (None for all channels on device).

    Returns:
        Confirmation of cache clear.
    """
    return await _clear_change_detection_cache(device_id=device_id, channel=channel)
