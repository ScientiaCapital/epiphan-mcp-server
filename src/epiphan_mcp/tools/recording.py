"""Recording control tools for Epiphan Pearl devices."""

import logging
from typing import Any

from fastmcp import FastMCP

from ..client import PearlAPIError
from ..models import RecorderInfo
from .device import get_client
from .discovery import get_default_recorder

logger = logging.getLogger(__name__)


async def start_recording(device_id: str = "default", recorder: int | None = None) -> dict[str, Any]:
    """
    Start recording on an Epiphan Pearl device.

    This begins recording video to the device's local storage.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device,
                   or specify an IP address, hostname, or device index.
        recorder: Recorder number (1-based). Auto-detected if not specified.
                  Use higher numbers for multi-recorder configurations.

    Returns:
        Confirmation of recording start with device and recorder details.
    """
    if recorder is None:
        recorder = await get_default_recorder(device_id)
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


async def stop_recording(device_id: str = "default", recorder: int | None = None) -> dict[str, Any]:
    """
    Stop recording on an Epiphan Pearl device.

    This stops the active recording and finalizes the video file.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device,
                   or specify an IP address, hostname, or device index.
        recorder: Recorder number (1-based). Auto-detected if not specified.

    Returns:
        Confirmation of recording stop with device and recorder details.
    """
    if recorder is None:
        recorder = await get_default_recorder(device_id)
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


async def get_recording_status(device_id: str = "default", recorder: int | None = None) -> dict[str, Any]:
    """
    Get the current recording status of an Epiphan Pearl device.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        recorder: Recorder number (1-based). Auto-detected if not specified.

    Returns:
        Recording state (recording, stopped, paused, error) and details.
    """
    if recorder is None:
        recorder = await get_default_recorder(device_id)
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


async def list_recorders(device_id: str = "default") -> dict[str, Any]:
    """
    List all recorders on an Epiphan Pearl device.

    Recorders capture video from channels to the device's local storage.
    Use this to discover available recorders before starting/stopping recording.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device,
                   or specify an IP address, hostname, or device index.

    Returns:
        List of recorders with their IDs, names, types, and associated channels.
    """
    try:
        async with get_client(device_id) as client:
            recorders = await client.get_recorders()
            recorder_list = []
            for rec in recorders:
                if isinstance(rec, RecorderInfo):
                    recorder_list.append(rec.model_dump())
                elif isinstance(rec, dict):
                    recorder_list.append(rec)
                else:
                    recorder_list.append({"id": str(rec)})
            return {
                "success": True,
                "device": client.host,
                "total_recorders": len(recorder_list),
                "recorders": recorder_list,
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


async def list_archive_files(
    device_id: str = "default",
    recorder: int | None = None,
    from_index: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """
    List recorded files in a recorder's archive.

    Browse recordings stored on the Pearl device's local storage.
    Supports pagination for large archives.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        recorder: Recorder number (1-based). Auto-detected if not specified.
        from_index: Starting index for pagination (0-based).
        limit: Maximum number of files to return.

    Returns:
        List of archive files with filenames, sizes, durations, and creation timestamps.
    """
    if recorder is None:
        recorder = await get_default_recorder(device_id)
    try:
        async with get_client(device_id) as client:
            recorder_id = f"recorder-{recorder}" if isinstance(recorder, int) else str(recorder)
            files = await client.get_archive_files(
                recorder_id,
                from_index=from_index if from_index is not None else 0,
                limit=limit if limit is not None else 100,
            )
            return {
                "success": True,
                "device": client.host,
                "recorder": recorder_id,
                "total_files": len(files),
                "files": files,
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


async def get_all_recorder_status(device_id: str = "default") -> dict[str, Any]:
    """
    Get recording status for ALL recorders on a Pearl device at once.

    More efficient than calling get_recording_status for each recorder individually.
    Useful for multi-recorder Pearl setups (e.g., lecture halls with 2+ recorders).

    Args:
        device_id: Device identifier. Use "default" for the primary configured device,
                   or specify an IP address, hostname, or device index.

    Returns:
        List of all recorders with their current state, duration, file size, and filename.
    """
    try:
        async with get_client(device_id) as client:
            statuses = await client.get_all_recorder_status()
            return {
                "success": True,
                "device": client.host,
                "total_recorders": len(statuses),
                "recorders": [
                    {
                        "id": s.id,
                        "state": s.state.value,
                        "duration_seconds": s.duration_seconds,
                        "file_size_bytes": s.file_size_bytes,
                        "filename": s.filename,
                    }
                    for s in statuses
                ],
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


def register(server: FastMCP) -> None:
    """Register recording MCP tools."""
    server.tool()(get_all_recorder_status)
    server.tool()(get_recording_status)
    server.tool()(list_archive_files)
    server.tool()(list_recorders)
    server.tool()(start_recording)
    server.tool()(stop_recording)
