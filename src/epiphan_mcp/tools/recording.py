"""Recording control tools for Epiphan Pearl devices."""

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..client import PearlAPIError
from ..models import (
    ArchiveFilesResult,
    RecorderInfo,
    RecorderListResult,
    RecordingControlResult,
    RecordingStatusResult,
)
from .device import get_client
from .discovery import get_default_recorder
from .params import DeviceId, RecorderNum

logger = logging.getLogger(__name__)

_FromIndex = Annotated[
    int | None,
    Field(description="Starting index for pagination (0-based). Defaults to 0."),
]
_Limit = Annotated[
    int | None,
    Field(description="Maximum number of files to return. Defaults to 100."),
]


async def start_recording(
    device_id: DeviceId = "default", recorder: RecorderNum = None
) -> RecordingControlResult:
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
            return RecordingControlResult(**result.model_dump())
    except PearlAPIError as e:
        return RecordingControlResult(
            success=False,
            error=str(e),
            device=device_id,
            recorder=recorder,
        )
    except ValueError as e:
        return RecordingControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def stop_recording(
    device_id: DeviceId = "default", recorder: RecorderNum = None
) -> RecordingControlResult:
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
            return RecordingControlResult(**result.model_dump())
    except PearlAPIError as e:
        return RecordingControlResult(
            success=False,
            error=str(e),
            device=device_id,
            recorder=recorder,
        )
    except ValueError as e:
        return RecordingControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def get_recording_status(
    device_id: DeviceId = "default", recorder: RecorderNum = None
) -> RecordingStatusResult:
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
            return RecordingStatusResult(
                success=True,
                device=client.host,
                recorder=recorder,
                state=status.state.value,
                duration_seconds=status.duration_seconds,
                file_size_bytes=status.file_size_bytes,
                filename=status.filename,
            )
    except PearlAPIError as e:
        return RecordingStatusResult(
            success=False,
            error=str(e),
            device=device_id,
            recorder=recorder,
        )
    except ValueError as e:
        return RecordingStatusResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def list_recorders(device_id: DeviceId = "default") -> RecorderListResult:
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
            return RecorderListResult(
                success=True,
                device=client.host,
                total_recorders=len(recorder_list),
                recorders=recorder_list,
            )
    except PearlAPIError as e:
        return RecorderListResult(
            success=False,
            error=str(e),
            device=device_id,
        )
    except ValueError as e:
        return RecorderListResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def list_archive_files(
    device_id: DeviceId = "default",
    recorder: RecorderNum = None,
    from_index: _FromIndex = None,
    limit: _Limit = None,
) -> ArchiveFilesResult:
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
            return ArchiveFilesResult(
                success=True,
                device=client.host,
                recorder=recorder_id,
                total_files=len(files),
                files=files,
            )
    except PearlAPIError as e:
        return ArchiveFilesResult(
            success=False,
            error=str(e),
            device=device_id,
            recorder=recorder,
        )
    except ValueError as e:
        return ArchiveFilesResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def get_all_recorder_status(device_id: DeviceId = "default") -> RecorderListResult:
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
            return RecorderListResult(
                success=True,
                device=client.host,
                total_recorders=len(statuses),
                recorders=[
                    {
                        "id": s.id,
                        "state": s.state.value,
                        "duration_seconds": s.duration_seconds,
                        "file_size_bytes": s.file_size_bytes,
                        "filename": s.filename,
                    }
                    for s in statuses
                ],
            )
    except PearlAPIError as e:
        return RecorderListResult(
            success=False,
            error=str(e),
            device=device_id,
        )
    except ValueError as e:
        return RecorderListResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def start_all_recorders(device_id: DeviceId = "default") -> RecordingControlResult:
    """
    Start ALL recorders on a Pearl device simultaneously.

    More efficient than starting each recorder individually. Useful for lecture halls
    and multi-recorder setups where all recorders should start at the same time.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device,
                   or specify an IP address, hostname, or device index.

    Returns:
        Confirmation that all recorders have been started.
    """
    try:
        async with get_client(device_id) as client:
            result = await client.start_all_recorders()
            return RecordingControlResult(**result.model_dump())
    except PearlAPIError as e:
        return RecordingControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )
    except ValueError as e:
        return RecordingControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def stop_all_recorders(device_id: DeviceId = "default") -> RecordingControlResult:
    """
    Stop ALL recorders on a Pearl device simultaneously.

    More efficient than stopping each recorder individually. Ensures all recorders
    stop at the same time, producing consistent end timestamps across recordings.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device,
                   or specify an IP address, hostname, or device index.

    Returns:
        Confirmation that all recorders have been stopped.
    """
    try:
        async with get_client(device_id) as client:
            result = await client.stop_all_recorders()
            return RecordingControlResult(**result.model_dump())
    except PearlAPIError as e:
        return RecordingControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )
    except ValueError as e:
        return RecordingControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )


def register(server: FastMCP) -> None:
    """Register recording MCP tools."""
    server.tool()(get_all_recorder_status)
    server.tool()(get_recording_status)
    server.tool()(list_archive_files)
    server.tool()(list_recorders)
    server.tool()(start_all_recorders)
    server.tool()(start_recording)
    server.tool()(stop_all_recorders)
    server.tool()(stop_recording)
