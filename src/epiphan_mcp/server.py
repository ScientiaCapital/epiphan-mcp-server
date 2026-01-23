"""FastMCP server for Epiphan Pearl devices.

This module creates the MCP server and registers all tools.
Tool implementations are organized in the tools/ subpackage.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastmcp import FastMCP

from .client import PearlClient
from .config import Settings, get_settings
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

# Import tool implementations from modules
from .tools.device import (
    get_device_status as _get_device_status,
)
from .tools.device import (
    list_devices as _list_devices,
)
from .tools.layout import (
    add_bookmark as _add_bookmark,
)
from .tools.layout import (
    list_layouts as _list_layouts,
)
from .tools.layout import (
    switch_layout as _switch_layout,
)
from .tools.maintenance import (
    get_device_health_score as _get_device_health_score,
)
from .tools.maintenance import (
    predict_storage_full as _predict_storage_full,
)
from .tools.recording import (
    get_recording_status as _get_recording_status,
)
from .tools.recording import (
    start_recording as _start_recording,
)
from .tools.recording import (
    stop_recording as _stop_recording,
)
from .tools.schedule import (
    get_scheduled_events as _get_scheduled_events,
)
from .tools.schedule import (
    single_touch_start as _single_touch_start,
)
from .tools.schedule import (
    single_touch_stop as _single_touch_stop,
)
from .tools.storage import (
    get_afu_status as _get_afu_status,
)
from .tools.storage import (
    get_storage_report as _get_storage_report,
)
from .tools.storage import (
    list_inputs as _list_inputs,
)
from .tools.streaming import (
    get_stream_status as _get_stream_status,
)
from .tools.streaming import (
    start_stream as _start_stream,
)
from .tools.streaming import (
    stop_stream as _stop_stream,
)

logger = logging.getLogger(__name__)

# Create MCP server instance
mcp = FastMCP(
    "epiphan-pearl",
    instructions="Control Epiphan Pearl video capture devices through natural language",
)


# ============================================================
# Parallel Fleet Execution Helper
# ============================================================


async def _execute_on_fleet(
    hosts: list[str],
    operation: Callable[[PearlClient], Awaitable[dict[str, Any]]],
    settings: Settings,
    timeout_per_device: float = 10.0,
) -> list[dict[str, Any]]:
    """
    Execute operation on all devices in parallel using asyncio.gather.

    Args:
        hosts: List of device hostnames/IPs to operate on.
        operation: Async function that takes a PearlClient and returns a result dict.
        settings: Settings instance for creating clients.
        timeout_per_device: Timeout in seconds for each device operation.

    Returns:
        List of results from each device, in the same order as hosts.
        Failed operations return dicts with host, success=False, online=False,
        error message, and alert dict.
    """

    async def _device_op(host: str) -> dict[str, Any]:
        """Execute operation on a single device with timeout and error handling."""
        try:
            async with asyncio.timeout(timeout_per_device):
                async with PearlClient.from_settings(host, settings) as client:
                    return await operation(client)
        except TimeoutError:
            return {
                "host": host,
                "success": False,
                "online": False,
                "error": "Device timeout",
                "alert": {
                    "device": host,
                    "severity": "error",
                    "message": "Device timeout",
                },
            }
        except Exception as e:
            return {
                "host": host,
                "success": False,
                "online": False,
                "error": str(e),
                "alert": {
                    "device": host,
                    "severity": "error",
                    "message": f"Device offline: {e}",
                },
            }

    tasks = [_device_op(host) for host in hosts]
    return await asyncio.gather(*tasks, return_exceptions=False)


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
    return await _get_device_status(device_id=device_id)


@mcp.tool()
async def list_devices() -> dict[str, Any]:
    """
    List all configured Epiphan Pearl devices.

    Returns the list of devices configured in the PEARL_DEVICES environment variable.

    Returns:
        List of device hostnames/IPs with their indices.
    """
    return await _list_devices()


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
    return await _list_inputs(device_id=device_id)


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
    return await _get_storage_report(device_id=device_id)


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
    return await _start_recording(device_id=device_id, recorder=recorder)


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
    return await _stop_recording(device_id=device_id, recorder=recorder)


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
    return await _get_recording_status(device_id=device_id, recorder=recorder)


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
    return await _start_stream(device_id=device_id, channel=channel)


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
    return await _stop_stream(device_id=device_id, channel=channel)


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
    return await _get_stream_status(device_id=device_id, channel=channel, publisher=publisher)


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
    return await _add_bookmark(device_id=device_id, channel=channel, text=text)


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
    return await _list_layouts(device_id=device_id, channel=channel)


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
    return await _switch_layout(device_id=device_id, channel=channel, layout_id=layout_id)


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
    return await _single_touch_start(device_id=device_id)


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
    return await _single_touch_stop(device_id=device_id)


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
    return await _get_scheduled_events(device_id=device_id, limit=limit)


# ============================================================
# AFU (Automatic File Upload) Tools
# ============================================================


@mcp.tool()
async def get_afu_status(device_id: str = "default") -> dict[str, Any]:
    """
    Get status of Automatic File Upload (AFU) destinations on an Epiphan Pearl device.

    AFU automatically uploads completed recordings to cloud storage or network
    destinations (S3, FTP, SFTP, Aspera, etc.).

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        AFU status including:
        - Destination ID and name
        - Protocol (s3, ftp, sftp, aspera, etc.)
        - Current state (idle, uploading, error)
        - Queue count (files waiting to upload)
        - Destination URL
    """
    return await _get_afu_status(device_id=device_id)


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
    return await _predict_storage_full(
        device_id=device_id, recorder=recorder, assumed_bitrate_mbps=assumed_bitrate_mbps
    )


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
    return await _get_device_health_score(device_id=device_id)


# ============================================================
# Fleet Management Tools (Phase 3)
# ============================================================
# Fleet tools use parallel execution for improved performance.


@mcp.tool()
async def get_fleet_status() -> dict[str, Any]:
    """
    Get status of all configured Epiphan Pearl devices.

    This provides a fleet-wide view of device health and activity.
    Operations are executed in parallel for improved performance.

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

    async def _get_device_status_op(client: PearlClient) -> dict[str, Any]:
        """Get status for a single device."""
        host = client.host
        try:
            status = await client.get_system_status()
            recorder = await client.get_recorder_status("recorder-1")

            result: dict[str, Any] = {
                "host": host,
                "online": True,
                "recording": recorder.state.value == "recording",
                "storage_percent": status.storage_used_percent,
            }

            # Check for storage alerts
            if status.storage_used_percent > settings.storage_warning_percent:
                result["alert"] = {
                    "device": host,
                    "severity": "warning",
                    "message": f"Storage at {status.storage_used_percent:.1f}%",
                }

            return result
        except Exception as e:
            return {
                "host": host,
                "online": False,
                "error": str(e),
                "alert": {
                    "device": host,
                    "severity": "error",
                    "message": f"Device offline: {e}",
                },
            }

    # Execute on all devices in parallel
    raw_results = await _execute_on_fleet(
        hosts=devices,
        operation=_get_device_status_op,
        settings=settings,
        timeout_per_device=settings.timeout,
    )

    # Aggregate results
    results = []
    alerts = []
    online_count = 0
    recording_count = 0

    for raw_result in raw_results:
        # Extract alert if present
        alert = raw_result.pop("alert", None)
        if alert:
            alerts.append(alert)

        results.append(raw_result)

        if raw_result.get("online", False):
            online_count += 1
        if raw_result.get("recording", False):
            recording_count += 1

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

    Operations are executed in parallel for improved performance.

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

    async def _start_recording_op(client: PearlClient) -> dict[str, Any]:
        """Start recording on a single device."""
        host = client.host
        try:
            await client.start_recording("recorder-1")
            return {"device": host, "success": True}
        except Exception as e:
            return {"device": host, "success": False, "error": str(e)}

    # Execute on all devices in parallel
    results = await _execute_on_fleet(
        hosts=hosts,
        operation=_start_recording_op,
        settings=settings,
        timeout_per_device=settings.timeout,
    )

    # Count successes
    success_count = sum(1 for r in results if r.get("success", False))

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

    Operations are executed in parallel for improved performance.

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

    async def _stop_recording_op(client: PearlClient) -> dict[str, Any]:
        """Stop recording on a single device."""
        host = client.host
        try:
            await client.stop_recording("recorder-1")
            return {"device": host, "success": True}
        except Exception as e:
            return {"device": host, "success": False, "error": str(e)}

    # Execute on all devices in parallel
    results = await _execute_on_fleet(
        hosts=hosts,
        operation=_stop_recording_op,
        settings=settings,
        timeout_per_device=settings.timeout,
    )

    # Count successes
    success_count = sum(1 for r in results if r.get("success", False))

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

    Args:
        device_id: Pearl device identifier.
        channel: Channel ID to analyze.

    Returns:
        Extracted text content organized by location/type.
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
    slide advances, or presenter movement.

    Args:
        device_id: Pearl device identifier.
        channel: Channel ID to monitor.
        sensitivity: Change detection sensitivity:
            - "low": Only detect major scene changes (cuts, transitions)
            - "medium": Detect slide changes, significant presenter movement
            - "high": Detect any visible changes (subtle movements)

    Returns:
        Change detection results including whether change occurred and description.
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

    Args:
        device_id: Pearl device identifier.
        channel: Channel ID to check.

    Returns:
        Quality assessment with specific issues and recommendations.
    """
    return await _check_video_quality(device_id=device_id, channel=channel)


@mcp.tool()
async def clear_change_detection_cache(
    device_id: str | None = None,
    channel: str | None = None,
) -> dict[str, Any]:
    """
    Clear the change detection cache.

    Resets stored frames used for change detection.

    Args:
        device_id: Specific device to clear (None for all devices).
        channel: Specific channel to clear (None for all channels on device).

    Returns:
        Confirmation of cache clear.
    """
    return await _clear_change_detection_cache(device_id=device_id, channel=channel)
