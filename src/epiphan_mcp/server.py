"""FastMCP server for Epiphan Pearl devices.

This module creates the MCP server and registers all tools.
Tool implementations are organized in the tools/ subpackage.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from fastmcp import FastMCP

from .client import PearlClient
from .config import Settings, get_settings
from .llm.providers import LLMError, get_provider
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
    detect_recording_issues as _detect_recording_issues,
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
from .tools.fleet import (
    generate_shift_handoff as _generate_shift_handoff,
)
from .tools.fleet import (
    predict_fleet_issues as _predict_fleet_issues,
)
from .tools.fleet import (
    suggest_maintenance_window as _suggest_maintenance_window,
)
from .tools.inputs import (
    create_network_input as _create_network_input,
)
from .tools.inputs import (
    get_input_settings as _get_input_settings,
)
from .tools.inputs import (
    list_outputs as _list_outputs,
)
from .tools.inputs import (
    set_output_source as _set_output_source,
)
from .tools.inputs import (
    update_input_settings as _update_input_settings,
)

# Kaltura CMS integration tools
from .tools.kaltura import (
    create_kaltura_category as _create_kaltura_category,
)
from .tools.kaltura import (
    create_kaltura_media as _create_kaltura_media,
)
from .tools.kaltura import (
    get_kaltura_category as _get_kaltura_category,
)
from .tools.kaltura import (
    get_kaltura_media as _get_kaltura_media,
)
from .tools.kaltura import (
    get_kaltura_upload_status as _get_kaltura_upload_status,
)
from .tools.kaltura import (
    list_kaltura_categories as _list_kaltura_categories,
)
from .tools.kaltura import (
    list_kaltura_media as _list_kaltura_media,
)
from .tools.kaltura import (
    schedule_kaltura_event as _schedule_kaltura_event,
)
from .tools.kaltura import (
    upload_to_kaltura as _upload_to_kaltura,
)

# Opencast CMS integration tools
from .tools.opencast import (
    create_opencast_series as _create_opencast_series,
)
from .tools.opencast import (
    delete_opencast_event as _delete_opencast_event,
)
from .tools.opencast import (
    get_opencast_event as _get_opencast_event,
)
from .tools.opencast import (
    get_opencast_ingest_status as _get_opencast_ingest_status,
)
from .tools.opencast import (
    get_opencast_series as _get_opencast_series,
)
from .tools.opencast import (
    ingest_to_opencast as _ingest_to_opencast,
)
from .tools.opencast import (
    list_opencast_events as _list_opencast_events,
)
from .tools.opencast import (
    list_opencast_series as _list_opencast_series,
)
from .tools.opencast import (
    schedule_opencast_capture as _schedule_opencast_capture,
)

# Q-SYS AV control integration tools
from .tools.qsys import (
    list_qsys_components as _list_qsys_components,
)
from .tools.qsys import (
    qsys_get_pearl_status as _qsys_get_pearl_status,
)
from .tools.qsys import (
    qsys_start_recording as _qsys_start_recording,
)
from .tools.qsys import (
    qsys_stop_recording as _qsys_stop_recording,
)
from .tools.qsys import (
    qsys_switch_layout as _qsys_switch_layout,
)

# YouTube Live streaming integration tools
from .tools.youtube import (
    create_youtube_broadcast as _create_youtube_broadcast,
)
from .tools.youtube import (
    end_youtube_broadcast as _end_youtube_broadcast,
)
from .tools.youtube import (
    get_youtube_broadcast_status as _get_youtube_broadcast_status,
)
from .tools.youtube import (
    list_youtube_broadcasts as _list_youtube_broadcasts,
)

# EC20 PTZ camera control tools
from .tools.ec20 import (
    ec20_disable_tracking as _ec20_disable_tracking,
)
from .tools.ec20 import (
    ec20_enable_tracking as _ec20_enable_tracking,
)
from .tools.ec20 import (
    ec20_get_preview as _ec20_get_preview,
)
from .tools.ec20 import (
    ec20_get_status as _ec20_get_status,
)
from .tools.ec20 import (
    ec20_goto_preset as _ec20_goto_preset,
)
from .tools.ec20 import (
    ec20_home as _ec20_home,
)
from .tools.ec20 import (
    ec20_list_presets as _ec20_list_presets,
)
from .tools.ec20 import (
    ec20_pan_tilt as _ec20_pan_tilt,
)
from .tools.ec20 import (
    ec20_save_preset as _ec20_save_preset,
)
from .tools.ec20 import (
    ec20_zoom as _ec20_zoom,
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

# Panopto CMS integration tools
from .tools.panopto import (
    create_panopto_folder as _create_panopto_folder,
)
from .tools.panopto import (
    create_panopto_session as _create_panopto_session,
)
from .tools.panopto import (
    delete_panopto_session as _delete_panopto_session,
)
from .tools.panopto import (
    get_panopto_folder as _get_panopto_folder,
)
from .tools.panopto import (
    get_panopto_session as _get_panopto_session,
)
from .tools.panopto import (
    get_panopto_upload_status as _get_panopto_upload_status,
)
from .tools.panopto import (
    list_panopto_folders as _list_panopto_folders,
)
from .tools.panopto import (
    list_panopto_sessions as _list_panopto_sessions,
)
from .tools.panopto import (
    upload_to_panopto as _upload_to_panopto,
)
from .tools.publishers import (
    create_publisher as _create_publisher,
)
from .tools.publishers import (
    delete_publisher as _delete_publisher,
)
from .tools.publishers import (
    get_publisher_settings as _get_publisher_settings,
)
from .tools.publishers import (
    list_publisher_types as _list_publisher_types,
)
from .tools.publishers import (
    rename_publisher as _rename_publisher,
)
from .tools.publishers import (
    update_publisher_settings as _update_publisher_settings,
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
    create_scheduled_event as _create_scheduled_event,
)
from .tools.schedule import (
    get_scheduled_events as _get_scheduled_events,
)
from .tools.schedule import (
    pause_event as _pause_event,
)
from .tools.schedule import (
    resume_event as _resume_event,
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

# Security: Limit concurrent device operations to prevent fleet DoS
FLEET_SEMAPHORE = asyncio.Semaphore(10)  # Max 10 concurrent device operations


async def _execute_on_fleet(
    hosts: list[str],
    operation: Callable[[PearlClient], Awaitable[dict[str, Any]]],
    settings: Settings,
    timeout_per_device: float = 10.0,
) -> list[dict[str, Any]]:
    """
    Execute operation on all devices in parallel using asyncio.gather.

    Concurrency is limited by FLEET_SEMAPHORE to prevent overwhelming
    the network or devices with too many simultaneous connections.

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
        """Execute operation on a single device with timeout, semaphore, and error handling."""
        async with FLEET_SEMAPHORE:  # Limit concurrent operations
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


@mcp.tool()
async def create_scheduled_event(
    device_id: str = "default",
    name: str = "",
    start_time: str | None = None,
    end_time: str | None = None,
    recorders: str | None = None,
    publishers: str | None = None,
) -> dict[str, Any]:
    """
    Create an ad-hoc recording event.

    Creates an event that can be scheduled to start at a specific time,
    or starts immediately if no start_time is provided.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        name: Event name (required).
        start_time: Start time in ISO format (e.g., "2024-01-15T10:00:00").
                    If not provided, event starts immediately.
        end_time: End time in ISO format. If not provided, event runs until stopped.
        recorders: Comma-separated list of recorder IDs (e.g., "recorder-1,recorder-2").
        publishers: Comma-separated list of publisher IDs (e.g., "publisher-1").

    Returns:
        Created event info including the assigned ID.
    """
    return await _create_scheduled_event(
        device_id=device_id,
        name=name,
        start_time=start_time,
        end_time=end_time,
        recorders=recorders,
        publishers=publishers,
    )


@mcp.tool()
async def pause_event(
    device_id: str = "default",
    event_id: str = "",
) -> dict[str, Any]:
    """
    Pause an active recording event.

    Temporarily pauses the event - recording and streaming continue but
    can be resumed without creating a new event.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        event_id: Event ID to pause.

    Returns:
        Confirmation that the event was paused.
    """
    return await _pause_event(device_id=device_id, event_id=event_id)


@mcp.tool()
async def resume_event(
    device_id: str = "default",
    event_id: str = "",
) -> dict[str, Any]:
    """
    Resume a paused recording event.

    Continues a previously paused event.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        event_id: Event ID to resume.

    Returns:
        Confirmation that the event was resumed.
    """
    return await _resume_event(device_id=device_id, event_id=event_id)


# ============================================================
# Publisher Management Tools (API Expansion Phase 1)
# ============================================================


@mcp.tool()
async def create_publisher(
    device_id: str = "default",
    channel: int = 1,
    name: str = "",
    publisher_type: str = "rtmp",
    url: str | None = None,
    stream_key: str | None = None,
    bitrate: int | None = None,
) -> dict[str, Any]:
    """
    Create a new streaming destination on a Pearl channel.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based).
        name: Display name for the publisher.
        publisher_type: Stream protocol - rtmp, srt, hls, rtsp, or mpeg_ts.
        url: Destination URL (e.g., rtmp://live.twitch.tv/app).
        stream_key: Stream key for RTMP destinations.
        bitrate: Target bitrate in bps (optional).

    Returns:
        Created publisher info including the assigned ID.
    """
    return await _create_publisher(
        device_id=device_id,
        channel=channel,
        name=name,
        publisher_type=publisher_type,
        url=url,
        stream_key=stream_key,
        bitrate=bitrate,
    )


@mcp.tool()
async def delete_publisher(
    device_id: str = "default",
    channel: int = 1,
    publisher: str = "publisher-1",
) -> dict[str, Any]:
    """
    Delete a streaming destination from a Pearl channel.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based).
        publisher: Publisher ID to delete (e.g., "publisher-1").

    Returns:
        Confirmation of deletion.
    """
    return await _delete_publisher(
        device_id=device_id, channel=channel, publisher=publisher
    )


@mcp.tool()
async def get_publisher_settings(
    device_id: str = "default",
    channel: int = 1,
    publisher: str = "publisher-1",
) -> dict[str, Any]:
    """
    Get configuration settings for a streaming destination.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based).
        publisher: Publisher ID (e.g., "publisher-1").

    Returns:
        Publisher settings including URL, stream key, bitrate, etc.
    """
    return await _get_publisher_settings(
        device_id=device_id, channel=channel, publisher=publisher
    )


@mcp.tool()
async def update_publisher_settings(
    device_id: str = "default",
    channel: int = 1,
    publisher: str = "publisher-1",
    url: str | None = None,
    stream_key: str | None = None,
    bitrate: int | None = None,
    enabled: bool | None = None,
) -> dict[str, Any]:
    """
    Update settings for a streaming destination (partial update).

    Only provided settings will be changed; other settings remain unchanged.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based).
        publisher: Publisher ID (e.g., "publisher-1").
        url: New destination URL.
        stream_key: New stream key.
        bitrate: New target bitrate in bps.
        enabled: Enable or disable the publisher.

    Returns:
        Confirmation of settings update.
    """
    return await _update_publisher_settings(
        device_id=device_id,
        channel=channel,
        publisher=publisher,
        url=url,
        stream_key=stream_key,
        bitrate=bitrate,
        enabled=enabled,
    )


@mcp.tool()
async def list_publisher_types(
    device_id: str = "default",
    channel: int = 1,
) -> dict[str, Any]:
    """
    List available streaming protocols for a channel.

    Returns the types of publishers that can be created on this channel.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based).

    Returns:
        List of available publisher types (rtmp, srt, hls, etc.).
    """
    return await _list_publisher_types(device_id=device_id, channel=channel)


@mcp.tool()
async def rename_publisher(
    device_id: str = "default",
    channel: int = 1,
    publisher: str = "publisher-1",
    name: str = "",
) -> dict[str, Any]:
    """
    Rename a streaming destination.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based).
        publisher: Publisher ID (e.g., "publisher-1").
        name: New display name for the publisher.

    Returns:
        Confirmation of rename operation.
    """
    return await _rename_publisher(
        device_id=device_id, channel=channel, publisher=publisher, name=name
    )


# ============================================================
# Input/Output Management Tools (API Expansion Phase 2)
# ============================================================


@mcp.tool()
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
    return await _create_network_input(
        device_id=device_id,
        name=name,
        input_type=input_type,
        url=url,
        passphrase=passphrase,
        latency=latency,
    )


@mcp.tool()
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
    return await _get_input_settings(device_id=device_id, input_id=input_id)


@mcp.tool()
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
    return await _update_input_settings(
        device_id=device_id,
        input_id=input_id,
        url=url,
        passphrase=passphrase,
        latency=latency,
    )


@mcp.tool()
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
        List of output ports including type, name, and current source.
    """
    return await _list_outputs(device_id=device_id)


@mcp.tool()
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
    return await _set_output_source(
        device_id=device_id, output_id=output_id, source_channel=source_channel
    )


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


def _calculate_health_score(
    storage_used_percent: float,
    recorder_accessible: bool = True,
) -> dict[str, Any]:
    """
    Calculate health score for a device (0-100).

    Scoring breakdown:
    - Storage health: 50 points max
    - Recording system health: 50 points max
    """
    issues: list[str] = []

    # Storage health (50 points max)
    if storage_used_percent >= 90:
        storage_score = 10  # Critical
        issues.append(f"Storage critically low: {storage_used_percent:.0f}% used")
    elif storage_used_percent >= 75:
        storage_score = 30  # Warning
        issues.append(f"Storage running low: {storage_used_percent:.0f}% used")
    else:
        storage_score = 50  # Healthy

    # Recording system health (50 points max)
    if recorder_accessible:
        recording_score = 50
    else:
        recording_score = 25
        issues.append("Could not check recorder status")

    return {
        "score": storage_score + recording_score,
        "issues": issues,
    }


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
        """Get status for a single device including health score."""
        host = client.host
        try:
            status = await client.get_system_status()
            recorder_accessible = True
            try:
                recorder = await client.get_recorder_status("recorder-1")
                is_recording = recorder.state.value == "recording"
            except Exception:
                recorder_accessible = False
                is_recording = False

            # Calculate health score
            health = _calculate_health_score(
                storage_used_percent=status.storage_used_percent,
                recorder_accessible=recorder_accessible,
            )

            result: dict[str, Any] = {
                "host": host,
                "online": True,
                "recording": is_recording,
                "storage_percent": status.storage_used_percent,
                "health_score": health["score"],
                "health_issues": health["issues"],
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
                "health_score": 0,
                "health_issues": [f"Device offline: {e}"],
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
    health_scores = []

    for raw_result in raw_results:
        # Extract alert if present
        alert = raw_result.pop("alert", None)
        if alert:
            alerts.append(alert)

        results.append(raw_result)

        if raw_result.get("online", False):
            online_count += 1
            health_scores.append(raw_result.get("health_score", 0))
        if raw_result.get("recording", False):
            recording_count += 1

    # Calculate fleet-level health metrics
    average_health = (
        sum(health_scores) / len(health_scores) if health_scores else 0.0
    )
    unhealthy_count = len([s for s in health_scores if s < 60])

    return {
        "success": True,
        "fleet_name": settings.fleet_name,
        "total_devices": len(devices),
        "online_devices": online_count,
        "recording_devices": recording_count,
        "average_health": round(average_health, 1),
        "unhealthy_devices": unhealthy_count,
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


@mcp.tool()
async def fleet_health_report() -> dict[str, Any]:
    """
    Generate AI-summarized fleet health report with recommendations.

    Returns natural language summary with:
    - Fleet health overview
    - Devices needing attention
    - Prioritized recommendations

    Returns:
        Structured report with AI-generated summary and actionable recommendations.
    """
    settings = get_settings()

    # Get fleet status with health scores
    fleet_status = await get_fleet_status.fn()

    if not fleet_status.get("success"):
        return {
            "success": False,
            "error": "Failed to get fleet status",
        }

    total_devices = fleet_status.get("total_devices", 0)

    if total_devices == 0:
        return {
            "success": True,
            "fleet_name": settings.fleet_name,
            "generated_at": datetime.now().isoformat(),
            "summary": "No devices configured in fleet.",
            "health_score": 0,
            "attention_required": [],
            "recommendations": ["Configure devices in PEARL_DEVICES environment variable."],
        }

    # Extract devices needing attention
    attention_required: list[dict[str, str]] = []
    for device in fleet_status.get("devices", []):
        host = device.get("host", "unknown")

        if not device.get("online", False):
            attention_required.append({
                "device": host,
                "issue": "Device offline",
                "action": "Check network connectivity and power",
            })
        elif device.get("health_score", 100) < 60:
            issues = device.get("health_issues", [])
            issue_str = issues[0] if issues else "Health score below threshold"
            attention_required.append({
                "device": host,
                "issue": issue_str,
                "action": _get_action_for_issue(issue_str),
            })
        elif device.get("storage_percent", 0) > settings.storage_warning_percent:
            attention_required.append({
                "device": host,
                "issue": f"Storage at {device.get('storage_percent', 0):.0f}%",
                "action": "Archive or delete old recordings",
            })

    # Build prompt for AI summary
    online = fleet_status.get("online_devices", 0)
    recording = fleet_status.get("recording_devices", 0)
    avg_health = fleet_status.get("average_health", 0)

    prompt = f"""Generate a brief fleet health summary for an IT administrator.

Fleet Status:
- Fleet name: {settings.fleet_name}
- Total devices: {total_devices}
- Online: {online}
- Currently recording: {recording}
- Average health score: {avg_health}/100

Devices needing attention: {len(attention_required)}
{_format_attention_list(attention_required)}

Provide:
1. A 1-2 sentence summary of fleet health
2. Top 2-3 prioritized recommendations (if any issues exist)

Keep the response concise and actionable. Use plain language."""

    # Generate AI summary
    try:
        provider = get_provider()
        ai_response = await provider.complete(prompt, max_tokens=300)
        if hasattr(provider, "close"):
            await provider.close()

        # Parse AI response for summary and recommendations
        summary, recommendations = _parse_ai_response(ai_response, attention_required)
    except LLMError as e:
        logger.warning(f"LLM summarization failed: {e}")
        # Fallback to basic summary
        summary = _generate_fallback_summary(fleet_status)
        recommendations = _generate_fallback_recommendations(attention_required)

    return {
        "success": True,
        "fleet_name": settings.fleet_name,
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "health_score": round(avg_health),
        "devices_online": online,
        "devices_recording": recording,
        "attention_required": attention_required,
        "recommendations": recommendations,
    }


def _get_action_for_issue(issue: str) -> str:
    """Get recommended action for a health issue."""
    issue_lower = issue.lower()
    if "storage" in issue_lower:
        return "Archive or delete old recordings to free space"
    elif "recorder" in issue_lower:
        return "Check recorder configuration and restart if needed"
    elif "offline" in issue_lower:
        return "Check network connectivity and power"
    return "Investigate and resolve the issue"


def _format_attention_list(attention_required: list[dict[str, str]]) -> str:
    """Format attention list for prompt."""
    if not attention_required:
        return "None - all devices healthy"
    lines = []
    for item in attention_required[:5]:  # Limit to top 5
        lines.append(f"- {item['device']}: {item['issue']}")
    return "\n".join(lines)


def _parse_ai_response(
    response: str,
    attention_required: list[dict[str, str]],
) -> tuple[str, list[str]]:
    """Parse AI response to extract summary and recommendations."""
    lines = response.strip().split("\n")

    # First non-empty line(s) are usually the summary
    summary_lines = []
    recommendations = []
    in_recommendations = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for recommendation markers
        if any(
            line.lower().startswith(prefix)
            for prefix in ["recommendation", "1.", "2.", "3.", "-", "*"]
        ):
            in_recommendations = True

        if in_recommendations:
            # Clean up recommendation line
            cleaned = line.lstrip("0123456789.-*) ")
            if cleaned and len(cleaned) > 5:
                recommendations.append(cleaned)
        else:
            summary_lines.append(line)

    summary = " ".join(summary_lines[:2]) if summary_lines else "Fleet status retrieved."

    # Use AI recommendations or generate from attention list
    if not recommendations and attention_required:
        recommendations = [item["action"] for item in attention_required[:3]]

    return summary, recommendations[:3]


def _generate_fallback_summary(fleet_status: dict[str, Any]) -> str:
    """Generate basic summary without AI."""
    online = fleet_status.get("online_devices", 0)
    total = fleet_status.get("total_devices", 0)
    recording = fleet_status.get("recording_devices", 0)
    avg_health = fleet_status.get("average_health", 0)

    if online == 0:
        return "All devices are offline. Check network connectivity."
    elif avg_health >= 80:
        return f"Fleet healthy. {online}/{total} devices online, {recording} recording."
    elif avg_health >= 60:
        return f"Fleet has minor issues. {online}/{total} devices online, average health {avg_health:.0f}%."
    else:
        return f"Fleet needs attention. {online}/{total} devices online, average health {avg_health:.0f}%."


def _generate_fallback_recommendations(
    attention_required: list[dict[str, str]],
) -> list[str]:
    """Generate basic recommendations without AI."""
    if not attention_required:
        return ["Continue monitoring fleet health."]

    recommendations = []
    seen_actions = set()
    for item in attention_required:
        action = item["action"]
        if action not in seen_actions:
            recommendations.append(action)
            seen_actions.add(action)
        if len(recommendations) >= 3:
            break

    return recommendations


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


# ============================================================
# Fleet Intelligence Tools (Sprint 3 - Pearl Copilot)
# ============================================================
# These tools provide proactive monitoring, prediction, and operational intelligence.


@mcp.tool()
async def detect_recording_issues(
    device_id: str = "default",
    channel: str = "1",
) -> dict[str, Any]:
    """
    Detect video quality issues during an active recording.

    Performs proactive monitoring by analyzing the current frame for common
    production problems like black frames, frozen video, poor lighting, and focus issues.

    Use this during recordings to catch issues early before they affect the entire capture.

    Args:
        device_id: Pearl device identifier.
        channel: Channel ID to monitor.

    Returns:
        Detection results including:
        - issues_detected: True if any problems found
        - issues: List of issues with severity and recommended actions
        - quality_score: 0-100 rating
        - recommendation: Overall suggested action
    """
    return await _detect_recording_issues(device_id=device_id, channel=channel)


@mcp.tool()
async def suggest_maintenance_window(
    min_duration_hours: float = 2.0,
) -> dict[str, Any]:
    """
    Suggest optimal maintenance window based on fleet usage patterns.

    Analyzes current fleet status and activity to recommend the best time
    for maintenance with minimal disruption to operations.

    Args:
        min_duration_hours: Minimum maintenance window duration needed (default 2 hours).

    Returns:
        Maintenance suggestion including:
        - suggested_window: Recommended time window
        - confidence: How confident in the recommendation (high/medium/low)
        - reasoning: Explanation for the suggestion
        - devices_affected: Count of devices that would be impacted
    """
    return await _suggest_maintenance_window(min_duration_hours=min_duration_hours)


@mcp.tool()
async def predict_fleet_issues(
    hours_ahead: int = 24,
) -> dict[str, Any]:
    """
    Predict fleet issues for the next 24/48/72 hours.

    Analyzes current health scores, storage trends, and patterns to forecast
    potential problems before they occur.

    Args:
        hours_ahead: How many hours ahead to predict (24, 48, or 72).

    Returns:
        Predictions including:
        - predictions: List of predicted issues with timeframes
        - risk_level: Overall risk level (low/medium/high/critical)
        - devices_at_risk: Count of devices with predicted issues
        - summary: AI-generated summary of predictions
    """
    return await _predict_fleet_issues(hours_ahead=hours_ahead)


@mcp.tool()
async def generate_shift_handoff(
    shift_hours: int = 8,
) -> dict[str, Any]:
    """
    Generate end-of-shift handoff summary for AV operations teams.

    Creates a comprehensive summary of fleet activity, resolved issues,
    and items requiring attention for the next shift.

    Args:
        shift_hours: Length of shift to summarize (default 8 hours).

    Returns:
        Handoff report including:
        - summary: AI-generated shift summary
        - activity_summary: Recording/streaming statistics
        - attention_required: Items needing attention for next shift
        - fleet_status: Current fleet health snapshot
    """
    return await _generate_shift_handoff(shift_hours=shift_hours)


# =============================================================================
# Panopto CMS Integration Tools
# =============================================================================


@mcp.tool()
async def list_panopto_folders(
    parent_folder_id: str = "",
    search_query: str = "",
) -> dict[str, Any]:
    """
    List folders in Panopto video platform.

    Retrieves folders accessible to the configured service account.
    Can filter by parent folder or search by name.

    Args:
        parent_folder_id: Optional parent folder UUID to list children.
        search_query: Optional search term to filter folders.

    Returns:
        Dict with folders list and count.

    Requires PANOPTO_HOST, PANOPTO_CLIENT_ID, PANOPTO_USERNAME, PANOPTO_PASSWORD
    environment variables to be set.
    """
    return await _list_panopto_folders(
        parent_folder_id=parent_folder_id,
        search_query=search_query,
    )


@mcp.tool()
async def get_panopto_folder(folder_id: str) -> dict[str, Any]:
    """
    Get details of a specific Panopto folder.

    Args:
        folder_id: Folder UUID.

    Returns:
        Folder details including name, description, parent.
    """
    return await _get_panopto_folder(folder_id=folder_id)


@mcp.tool()
async def create_panopto_folder(
    name: str,
    parent_folder_id: str = "",
    description: str = "",
) -> dict[str, Any]:
    """
    Create a new folder in Panopto.

    Args:
        name: Folder name.
        parent_folder_id: Optional parent folder UUID (root if empty).
        description: Optional folder description.

    Returns:
        Created folder details.
    """
    return await _create_panopto_folder(
        name=name,
        parent_folder_id=parent_folder_id,
        description=description,
    )


@mcp.tool()
async def list_panopto_sessions(
    folder_id: str = "",
    search_query: str = "",
) -> dict[str, Any]:
    """
    List sessions (recordings) in Panopto.

    Args:
        folder_id: Optional folder UUID to filter sessions.
        search_query: Optional search term.

    Returns:
        Dict with sessions list and count.
    """
    return await _list_panopto_sessions(
        folder_id=folder_id,
        search_query=search_query,
    )


@mcp.tool()
async def get_panopto_session(session_id: str) -> dict[str, Any]:
    """
    Get details of a specific Panopto session.

    Args:
        session_id: Session UUID.

    Returns:
        Session details including name, duration, folder, streams.
    """
    return await _get_panopto_session(session_id=session_id)


@mcp.tool()
async def create_panopto_session(
    folder_id: str,
    name: str,
    description: str = "",
) -> dict[str, Any]:
    """
    Create a new session (recording placeholder) in Panopto.

    Creates an empty session that can receive uploaded video content.

    Args:
        folder_id: Target folder UUID.
        name: Session name.
        description: Optional session description.

    Returns:
        Created session details.
    """
    return await _create_panopto_session(
        folder_id=folder_id,
        name=name,
        description=description,
    )


@mcp.tool()
async def upload_to_panopto(
    folder_id: str,
    file_path: str,
    session_name: str = "",
    wait_for_processing: bool = False,
) -> dict[str, Any]:
    """
    Upload a video file to Panopto.

    Handles the complete upload workflow:
    1. Creates upload session
    2. Uploads file to S3
    3. Signals upload complete
    4. Optionally waits for processing

    Args:
        folder_id: Target folder UUID.
        file_path: Local path to video file.
        session_name: Optional session name (defaults to filename).
        wait_for_processing: Wait for Panopto to finish processing.

    Returns:
        Upload status and session details.
    """
    return await _upload_to_panopto(
        folder_id=folder_id,
        file_path=file_path,
        session_name=session_name,
        wait_for_processing=wait_for_processing,
    )


@mcp.tool()
async def get_panopto_upload_status(upload_id: str) -> dict[str, Any]:
    """
    Check the status of a Panopto upload.

    Args:
        upload_id: Upload session ID.

    Returns:
        Upload status including processing state.
    """
    return await _get_panopto_upload_status(upload_id=upload_id)


@mcp.tool()
async def delete_panopto_session(session_id: str) -> dict[str, Any]:
    """
    Delete a session from Panopto.

    Args:
        session_id: Session UUID to delete.

    Returns:
        Confirmation of deletion.
    """
    return await _delete_panopto_session(session_id=session_id)


# =============================================================================
# Kaltura CMS Integration Tools
# =============================================================================


@mcp.tool()
async def list_kaltura_categories(
    parent_id: int | None = None,
    page_size: int = 50,
    page_index: int = 1,
) -> dict[str, Any]:
    """
    List categories (folders) in Kaltura video platform.

    Retrieves categories accessible to the configured service account.
    Categories are used to organize video content hierarchically.

    Args:
        parent_id: Optional parent category ID to list children (None for all).
        page_size: Number of results per page (default 50, max 500).
        page_index: Page number, 1-based (default 1).

    Returns:
        Dict with categories list and count.

    Requires KALTURA_PARTNER_ID, KALTURA_APP_TOKEN_ID, KALTURA_APP_TOKEN
    environment variables to be set.
    """
    return await _list_kaltura_categories(
        parent_id=parent_id,
        page_size=page_size,
        page_index=page_index,
    )


@mcp.tool()
async def get_kaltura_category(category_id: int) -> dict[str, Any]:
    """
    Get details of a specific Kaltura category.

    Args:
        category_id: Category ID (numeric).

    Returns:
        Category details including name, description, parent, entry count.
    """
    return await _get_kaltura_category(category_id=category_id)


@mcp.tool()
async def create_kaltura_category(
    name: str,
    parent_id: int | None = None,
    description: str = "",
) -> dict[str, Any]:
    """
    Create a new category in Kaltura.

    Args:
        name: Category name.
        parent_id: Optional parent category ID (None for root level).
        description: Optional category description.

    Returns:
        Created category details.
    """
    return await _create_kaltura_category(
        name=name,
        parent_id=parent_id,
        description=description,
    )


@mcp.tool()
async def list_kaltura_media(
    category_ids: str = "",
    search_text: str = "",
    page_size: int = 50,
    page_index: int = 1,
) -> dict[str, Any]:
    """
    List media entries (videos) in Kaltura.

    Args:
        category_ids: Comma-separated category IDs to filter by (optional).
        search_text: Search term for name, description, tags (optional).
        page_size: Number of results per page (default 50, max 500).
        page_index: Page number, 1-based (default 1).

    Returns:
        Dict with media entries list and count.
    """
    return await _list_kaltura_media(
        category_ids=category_ids,
        search_text=search_text,
        page_size=page_size,
        page_index=page_index,
    )


@mcp.tool()
async def get_kaltura_media(entry_id: str) -> dict[str, Any]:
    """
    Get details of a specific Kaltura media entry.

    Args:
        entry_id: Media entry ID (alphanumeric, starts with 0_ or 1_).

    Returns:
        Media entry details including name, duration, status, thumbnails.
    """
    return await _get_kaltura_media(entry_id=entry_id)


@mcp.tool()
async def create_kaltura_media(
    name: str,
    description: str = "",
    tags: str = "",
    category_ids: str = "",
) -> dict[str, Any]:
    """
    Create a new media entry (video placeholder) in Kaltura.

    Creates an empty media entry that can receive uploaded video content.

    Args:
        name: Media entry name/title.
        description: Optional description.
        tags: Optional comma-separated tags.
        category_ids: Optional comma-separated category IDs to assign.

    Returns:
        Created media entry details.
    """
    return await _create_kaltura_media(
        name=name,
        description=description,
        tags=tags,
        category_ids=category_ids,
    )


@mcp.tool()
async def upload_to_kaltura(
    file_path: str,
    entry_name: str = "",
    description: str = "",
    category_ids: str = "",
    wait_for_ready: bool = False,
) -> dict[str, Any]:
    """
    Upload a video file to Kaltura.

    Handles the complete upload workflow:
    1. Creates media entry with metadata
    2. Creates upload token
    3. Uploads file in chunks (10MB each)
    4. Attaches content to entry
    5. Optionally waits for transcoding

    Args:
        file_path: Local path to video file.
        entry_name: Optional entry name (defaults to filename).
        description: Optional description.
        category_ids: Optional comma-separated category IDs.
        wait_for_ready: Wait for transcoding to complete (default False).

    Returns:
        Upload result with media entry details.
    """
    return await _upload_to_kaltura(
        file_path=file_path,
        entry_name=entry_name,
        description=description,
        category_ids=category_ids,
        wait_for_ready=wait_for_ready,
    )


@mcp.tool()
async def schedule_kaltura_event(
    name: str,
    start_time: str,
    end_time: str,
    entry_id: str = "",
    resource_id: str = "",
    description: str = "",
) -> dict[str, Any]:
    """
    Schedule a recording event in Kaltura for Pearl auto-record.

    Creates a scheduled event that Pearl devices synced with Kaltura
    will automatically pick up and record.

    Args:
        name: Event name/title.
        start_time: Start time in ISO format (e.g., "2024-01-15T10:00:00").
        end_time: End time in ISO format (e.g., "2024-01-15T11:00:00").
        entry_id: Optional existing media entry to associate.
        resource_id: Optional recording resource/room ID.
        description: Optional event description.

    Returns:
        Created schedule event details.
    """
    return await _schedule_kaltura_event(
        name=name,
        start_time=start_time,
        end_time=end_time,
        entry_id=entry_id,
        resource_id=resource_id,
        description=description,
    )


@mcp.tool()
async def get_kaltura_upload_status(upload_token_id: str) -> dict[str, Any]:
    """
    Check the status of a Kaltura upload.

    Args:
        upload_token_id: Upload token ID from upload workflow.

    Returns:
        Upload status including bytes uploaded, status.
    """
    return await _get_kaltura_upload_status(upload_token_id=upload_token_id)


# =============================================================================
# Opencast CMS Integration Tools
# =============================================================================


@mcp.tool()
async def list_opencast_series(
    filter_text: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    List series (courses/channels) in Opencast video platform.

    Retrieves series accessible to the configured admin account.
    Series are used to organize recordings by course or topic.

    Args:
        filter_text: Optional filter by title (partial match).
        limit: Maximum number of results (default 50).
        offset: Pagination offset for paging through results.

    Returns:
        Dict with series list and count.

    Requires OPENCAST_HOST, OPENCAST_USERNAME, OPENCAST_PASSWORD
    environment variables to be set.
    """
    return await _list_opencast_series(
        filter_text=filter_text,
        limit=limit,
        offset=offset,
    )


@mcp.tool()
async def get_opencast_series(series_id: str) -> dict[str, Any]:
    """
    Get details of a specific Opencast series.

    Args:
        series_id: Series UUID.

    Returns:
        Series details including title, description, creator.
    """
    return await _get_opencast_series(series_id=series_id)


@mcp.tool()
async def create_opencast_series(
    title: str,
    description: str = "",
    creator: str = "",
    subject: str = "",
    language: str = "en",
) -> dict[str, Any]:
    """
    Create a new series in Opencast.

    Series are containers for organizing recordings by course or topic.

    Args:
        title: Series title (required).
        description: Series description.
        creator: Creator/instructor name.
        subject: Subject or topic.
        language: Language code (default "en").

    Returns:
        Created series details including UUID.
    """
    return await _create_opencast_series(
        title=title,
        description=description,
        creator=creator,
        subject=subject,
        language=language,
    )


@mcp.tool()
async def list_opencast_events(
    series_id: str = "",
    status: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    List events (recordings) in Opencast.

    Args:
        series_id: Filter by series UUID (optional).
        status: Filter by status - e.g., "PROCESSED", "PROCESSING" (optional).
        limit: Maximum number of results (default 50).
        offset: Pagination offset.

    Returns:
        Dict with events list and count.
    """
    return await _list_opencast_events(
        series_id=series_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@mcp.tool()
async def get_opencast_event(event_id: str) -> dict[str, Any]:
    """
    Get details of a specific Opencast event (recording).

    Args:
        event_id: Event UUID.

    Returns:
        Event details including title, duration, status, publications.
    """
    return await _get_opencast_event(event_id=event_id)


@mcp.tool()
async def ingest_to_opencast(
    file_path: str,
    title: str,
    series_id: str = "",
    creator: str = "",
    description: str = "",
    spatial: str = "",
    workflow: str = "fast",
) -> dict[str, Any]:
    """
    Ingest a video recording to Opencast.

    Uploads a video file and starts the processing workflow.
    Large files may take several minutes to upload.

    Args:
        file_path: Local path to video file.
        title: Recording title.
        series_id: Target series UUID (uses default if not provided).
        creator: Presenter/creator name.
        description: Recording description.
        spatial: Location/room name.
        workflow: Processing workflow ID (default "fast").

    Returns:
        Ingest result with workflow instance ID.
    """
    return await _ingest_to_opencast(
        file_path=file_path,
        title=title,
        series_id=series_id,
        creator=creator,
        description=description,
        spatial=spatial,
        workflow=workflow,
    )


@mcp.tool()
async def get_opencast_ingest_status(workflow_id: str) -> dict[str, Any]:
    """
    Check the status of an Opencast ingest workflow.

    Args:
        workflow_id: Workflow instance ID from ingest.

    Returns:
        Workflow status including state and progress.
    """
    return await _get_opencast_ingest_status(workflow_id=workflow_id)


@mcp.tool()
async def schedule_opencast_capture(
    title: str,
    start_time: str,
    end_time: str,
    capture_agent: str,
    series_id: str = "",
    creator: str = "",
    description: str = "",
    spatial: str = "",
) -> dict[str, Any]:
    """
    Schedule a capture event in Opencast for Pearl auto-record.

    Creates a scheduled event that Pearl devices (registered as capture agents)
    will automatically pick up and record at the scheduled time.

    Args:
        title: Event title.
        start_time: Start time in ISO format (e.g., "2024-01-15T10:00:00").
        end_time: End time in ISO format (e.g., "2024-01-15T11:00:00").
        capture_agent: Capture agent ID (Pearl device identifier).
        series_id: Target series UUID.
        creator: Presenter name.
        description: Event description.
        spatial: Room/location.

    Returns:
        Created scheduled event.
    """
    return await _schedule_opencast_capture(
        title=title,
        start_time=start_time,
        end_time=end_time,
        capture_agent=capture_agent,
        series_id=series_id,
        creator=creator,
        description=description,
        spatial=spatial,
    )


@mcp.tool()
async def delete_opencast_event(event_id: str) -> dict[str, Any]:
    """
    Delete an event from Opencast.

    Permanently removes an event/recording. Use with caution.

    Args:
        event_id: Event UUID to delete.

    Returns:
        Confirmation of deletion.
    """
    return await _delete_opencast_event(event_id=event_id)


# =============================================================================
# Q-SYS AV Control Integration Tools
# =============================================================================


@mcp.tool()
async def list_qsys_components(name_filter: str = "Pearl") -> dict[str, Any]:
    """
    List Q-SYS components, optionally filtered by name.

    Discovers components in the Q-SYS design that match the filter.
    Use this to find Pearl-related components like recorders and layout controls.

    Args:
        name_filter: Filter components containing this string (default "Pearl").
                     Use empty string to list all components.

    Returns:
        Dict with components list and count.

    Requires QSYS_CORE_IP environment variable. Optional: QSYS_PORT, QSYS_PIN.
    """
    return await _list_qsys_components(name_filter=name_filter)


@mcp.tool()
async def qsys_get_pearl_status(component_name: str = "Pearl_Recorder") -> dict[str, Any]:
    """
    Get Pearl recording/streaming status through Q-SYS.

    Retrieves the current state of a Pearl device controlled by Q-SYS.

    Args:
        component_name: Name of the Pearl component in Q-SYS design.
                        Common names: "Pearl_Recorder", "Pearl_1", etc.

    Returns:
        Status dict with is_recording, is_streaming, current_layout.
    """
    return await _qsys_get_pearl_status(component_name=component_name)


@mcp.tool()
async def qsys_start_recording(component_name: str = "Pearl_Recorder") -> dict[str, Any]:
    """
    Start recording on Pearl through Q-SYS.

    Triggers recording start via the Q-SYS Pearl component. This is useful
    when Pearl is integrated into a larger Q-SYS controlled AV system.

    Args:
        component_name: Name of the Pearl component in Q-SYS design.

    Returns:
        Confirmation of recording start.
    """
    return await _qsys_start_recording(component_name=component_name)


@mcp.tool()
async def qsys_stop_recording(component_name: str = "Pearl_Recorder") -> dict[str, Any]:
    """
    Stop recording on Pearl through Q-SYS.

    Triggers recording stop via the Q-SYS Pearl component.

    Args:
        component_name: Name of the Pearl component in Q-SYS design.

    Returns:
        Confirmation of recording stop.
    """
    return await _qsys_stop_recording(component_name=component_name)


@mcp.tool()
async def qsys_switch_layout(
    layout_id: str,
    component_name: str = "Pearl_Layout",
) -> dict[str, Any]:
    """
    Switch Pearl layout through Q-SYS.

    Changes the active layout/scene on a Pearl device via Q-SYS control.
    The layout component must be configured in the Q-SYS design.

    Args:
        layout_id: Layout ID or index to switch to.
        component_name: Name of the Pearl layout component in Q-SYS.

    Returns:
        Confirmation of layout switch.
    """
    return await _qsys_switch_layout(
        layout_id=layout_id,
        component_name=component_name,
    )


# =============================================================================
# YouTube Live Streaming Integration Tools
# =============================================================================


@mcp.tool()
async def create_youtube_broadcast(
    title: str,
    scheduled_start: str,
    description: str = "",
    privacy: str = "unlisted",
    resolution: str = "1080p",
    frame_rate: str = "30fps",
) -> dict[str, Any]:
    """
    Create a YouTube Live broadcast with stream for Pearl integration.

    Creates a broadcast, stream, and binds them together. Returns RTMP
    credentials that can be used to configure a Pearl publisher.

    Args:
        title: Broadcast title (visible to viewers).
        scheduled_start: Start time in ISO 8601 format (e.g., "2024-01-15T10:00:00Z").
        description: Broadcast description.
        privacy: Privacy status - "public", "unlisted", or "private" (default "unlisted").
        resolution: Video resolution - "720p", "1080p", "1440p", "2160p" (default "1080p").
        frame_rate: Frame rate - "30fps" or "60fps" (default "30fps").

    Returns:
        Dict with broadcast details and RTMP credentials for Pearl.

    Requires YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
    environment variables to be set.
    """
    return await _create_youtube_broadcast(
        title=title,
        scheduled_start=scheduled_start,
        description=description,
        privacy=privacy,
        resolution=resolution,
        frame_rate=frame_rate,
    )


@mcp.tool()
async def get_youtube_broadcast_status(broadcast_id: str) -> dict[str, Any]:
    """
    Get the status of a YouTube Live broadcast.

    Returns the current lifecycle status of the broadcast and its
    bound stream, including health information.

    Args:
        broadcast_id: The YouTube broadcast ID.

    Returns:
        Dict with broadcast status, stream status, and timing info.
    """
    return await _get_youtube_broadcast_status(broadcast_id=broadcast_id)


@mcp.tool()
async def list_youtube_broadcasts(
    status_filter: str = "",
    limit: int = 25,
) -> dict[str, Any]:
    """
    List YouTube Live broadcasts for the authenticated account.

    Args:
        status_filter: Filter by status - "active", "all", "completed", "upcoming"
                      (empty for all statuses).
        limit: Maximum number of results (default 25, max 50).

    Returns:
        Dict with broadcasts list and count.
    """
    return await _list_youtube_broadcasts(
        status_filter=status_filter,
        limit=limit,
    )


@mcp.tool()
async def end_youtube_broadcast(broadcast_id: str) -> dict[str, Any]:
    """
    End a YouTube Live broadcast.

    Transitions the broadcast to 'complete' status. The broadcast must
    currently be in 'live' status. After ending, the recording (if enabled)
    will be processed and available as a VOD.

    Args:
        broadcast_id: The YouTube broadcast ID to end.

    Returns:
        Confirmation of broadcast completion.
    """
    return await _end_youtube_broadcast(broadcast_id=broadcast_id)


# ============================================================
# EC20 PTZ Camera Control Tools
# ============================================================


@mcp.tool()
async def ec20_get_status(camera_id: str = "default") -> dict[str, Any]:
    """
    Get EC20 PTZ camera status including position and tracking state.

    Returns camera model, firmware, current PTZ position, and AI tracking status.

    Args:
        camera_id: EC20 camera identifier. Can be:
            - "default" - first configured EC20 camera
            - IP address or hostname - used directly
            - Index like "0", "1" - nth configured camera

    Returns:
        Camera status including model, firmware, PTZ position, tracking mode.

    Requires EC20_DEVICES environment variable to be set.
    """
    return await _ec20_get_status(camera_id=camera_id)


@mcp.tool()
async def ec20_pan_tilt(
    camera_id: str = "default",
    pan: float = 0.0,
    tilt: float = 0.0,
    speed: int = 50,
) -> dict[str, Any]:
    """
    Move EC20 camera to absolute pan/tilt position.

    Pan range is -162.5 to +162.5 degrees. Tilt range is typically -30 to +90 degrees.
    Speed controls movement velocity (1-100, higher is faster).

    Args:
        camera_id: EC20 camera identifier.
        pan: Pan position in degrees (-162.5 to +162.5).
        tilt: Tilt position in degrees (-30 to +90 typical).
        speed: Movement speed (1-100, default 50).

    Returns:
        Confirmation with new pan/tilt positions.
    """
    return await _ec20_pan_tilt(camera_id=camera_id, pan=pan, tilt=tilt, speed=speed)


@mcp.tool()
async def ec20_zoom(
    camera_id: str = "default",
    level: int = 1,
) -> dict[str, Any]:
    """
    Set EC20 camera zoom level.

    EC20 supports 20x optical zoom (levels 1-20) and 16x digital zoom (levels 21-36).
    For best quality, prefer optical zoom (1-20).

    Args:
        camera_id: EC20 camera identifier.
        level: Zoom level (1-36: 1-20 optical, 21-36 digital).

    Returns:
        Confirmation with new zoom level.
    """
    return await _ec20_zoom(camera_id=camera_id, level=level)


@mcp.tool()
async def ec20_goto_preset(
    camera_id: str = "default",
    preset_id: int = 1,
) -> dict[str, Any]:
    """
    Move EC20 camera to a saved preset position.

    Presets store pan, tilt, and zoom positions for quick recall.
    Use ec20_list_presets to see available presets.

    Args:
        camera_id: EC20 camera identifier.
        preset_id: ID of preset to recall (1-255).

    Returns:
        Confirmation of preset recall.
    """
    return await _ec20_goto_preset(camera_id=camera_id, preset_id=preset_id)


@mcp.tool()
async def ec20_save_preset(
    camera_id: str = "default",
    preset_id: int = 1,
    name: str = "",
) -> dict[str, Any]:
    """
    Save current EC20 camera position as a preset.

    Stores the current pan, tilt, and zoom position for later recall.

    Args:
        camera_id: EC20 camera identifier.
        preset_id: ID for the preset (1-255).
        name: Friendly name for the preset (e.g., "Podium", "Whiteboard").

    Returns:
        Confirmation with preset ID and name.
    """
    return await _ec20_save_preset(camera_id=camera_id, preset_id=preset_id, name=name)


@mcp.tool()
async def ec20_home(camera_id: str = "default") -> dict[str, Any]:
    """
    Return EC20 camera to home position.

    Home position is typically pan=0, tilt=0, zoom=1 (centered, wide view).

    Args:
        camera_id: EC20 camera identifier.

    Returns:
        Confirmation of home position.
    """
    return await _ec20_home(camera_id=camera_id)


@mcp.tool()
async def ec20_enable_tracking(
    camera_id: str = "default",
    mode: str = "presenter",
) -> dict[str, Any]:
    """
    Enable AI tracking on EC20 camera.

    EC20 uses AI to automatically follow subjects:
    - "presenter": Tracks a single person presenting
    - "zone": Tracks activity within defined zones
    - "body": Full body tracking mode

    Args:
        camera_id: EC20 camera identifier.
        mode: Tracking mode - "presenter", "zone", or "body".

    Returns:
        Confirmation with tracking mode enabled.
    """
    return await _ec20_enable_tracking(camera_id=camera_id, mode=mode)


@mcp.tool()
async def ec20_disable_tracking(camera_id: str = "default") -> dict[str, Any]:
    """
    Disable AI tracking on EC20 camera.

    Returns camera to manual PTZ control mode.

    Args:
        camera_id: EC20 camera identifier.

    Returns:
        Confirmation of tracking disabled.
    """
    return await _ec20_disable_tracking(camera_id=camera_id)


@mcp.tool()
async def ec20_list_presets(camera_id: str = "default") -> dict[str, Any]:
    """
    List all saved presets on EC20 camera.

    Returns preset ID, name, and stored PTZ positions for each preset.

    Args:
        camera_id: EC20 camera identifier.

    Returns:
        List of presets with id, name, pan, tilt, zoom values.
    """
    return await _ec20_list_presets(camera_id=camera_id)


@mcp.tool()
async def ec20_get_preview(camera_id: str = "default") -> dict[str, Any]:
    """
    Get preview image from EC20 camera.

    Returns a base64-encoded JPEG image of the current camera view.
    Useful for verifying camera position without starting a recording.

    Args:
        camera_id: EC20 camera identifier.

    Returns:
        Dict with base64-encoded JPEG image and content type.
    """
    return await _ec20_get_preview(camera_id=camera_id)
