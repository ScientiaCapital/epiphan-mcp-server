"""Streaming control tools for Epiphan Pearl devices."""

import logging
from typing import Any

from ..client import PearlAPIError
from .device import get_client

logger = logging.getLogger(__name__)


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
