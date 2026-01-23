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
