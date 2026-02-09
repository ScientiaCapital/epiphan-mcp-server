"""Publisher (streaming) management tools for Epiphan Pearl devices.

This module provides CRUD operations for managing stream destinations (publishers)
on Pearl channels. Publishers handle RTMP, SRT, HLS, RTSP, and MPEG-TS streaming.
"""

import logging
from typing import Any

from ..audit import log_operation
from ..client import PearlAPIError
from ..validation import ValidationError, validate_streaming_url
from .device import get_client

logger = logging.getLogger(__name__)


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
    if not name:
        return {
            "success": False,
            "error": "Publisher name is required",
            "device": device_id,
        }

    if url:
        try:
            validate_streaming_url(url)
        except ValidationError as e:
            return {
                "success": False,
                "error": f"Invalid URL: {e}",
                "device": device_id,
            }

    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)

            # Build settings dict
            settings: dict[str, Any] = {}
            if url:
                settings["url"] = url
            if stream_key:
                settings["stream_key"] = stream_key
            if bitrate:
                settings["bitrate"] = bitrate

            result = await client.create_publisher(
                channel_id=channel_id,
                name=name,
                publisher_type=publisher_type,
                settings=settings if settings else None,
            )
            return {
                "success": True,
                "device": client.host,
                "channel": channel_id,
                "publisher": result,
                "message": f"Publisher '{name}' created successfully",
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
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.delete_publisher(channel_id, publisher)
            log_operation(
                "delete_publisher",
                client.host,
                details={"channel": channel_id, "publisher": publisher},
            )
            return result.model_dump()
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
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            settings = await client.get_publisher_settings(channel_id, publisher)
            return {
                "success": True,
                "device": client.host,
                "channel": channel_id,
                "publisher": publisher,
                "settings": settings,
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
    if url is not None:
        try:
            validate_streaming_url(url)
        except ValidationError as e:
            return {
                "success": False,
                "error": f"Invalid URL: {e}",
                "device": device_id,
            }

    # Build settings dict with only provided values
    settings: dict[str, Any] = {}
    if url is not None:
        settings["url"] = url
    if stream_key is not None:
        settings["stream_key"] = stream_key
    if bitrate is not None:
        settings["bitrate"] = bitrate
    if enabled is not None:
        settings["enabled"] = enabled

    if not settings:
        return {
            "success": False,
            "error": "No settings provided to update",
            "device": device_id,
        }

    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.update_publisher_settings(channel_id, publisher, settings)
            return result.model_dump()
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
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            types = await client.get_publisher_types(channel_id)
            return {
                "success": True,
                "device": client.host,
                "channel": channel_id,
                "types": types,
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
    if not name:
        return {
            "success": False,
            "error": "New name is required",
            "device": device_id,
        }

    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.update_publisher_name(channel_id, publisher, name)
            return result.model_dump()
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
