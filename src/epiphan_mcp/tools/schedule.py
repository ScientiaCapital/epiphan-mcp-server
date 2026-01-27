"""Scheduling and single-touch control tools for Epiphan Pearl devices."""

import logging
from typing import Any

from ..client import PearlAPIError
from .device import get_client

logger = logging.getLogger(__name__)


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
    if not name:
        return {
            "success": False,
            "error": "Event name is required",
            "device": device_id,
        }

    try:
        async with get_client(device_id) as client:
            recorder_list = recorders.split(",") if recorders else None
            publisher_list = publishers.split(",") if publishers else None

            result = await client.create_event(
                name=name,
                start_time=start_time,
                end_time=end_time,
                recorders=recorder_list,
                publishers=publisher_list,
            )
            return {
                "success": True,
                "device": client.host,
                "event": result,
                "message": f"Event '{name}' created successfully",
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
    if not event_id:
        return {
            "success": False,
            "error": "Event ID is required",
            "device": device_id,
        }

    try:
        async with get_client(device_id) as client:
            result = await client.pause_event(event_id)
            return result.model_dump()
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "event_id": event_id,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


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
    if not event_id:
        return {
            "success": False,
            "error": "Event ID is required",
            "device": device_id,
        }

    try:
        async with get_client(device_id) as client:
            result = await client.resume_event(event_id)
            return result.model_dump()
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
            "event_id": event_id,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }
