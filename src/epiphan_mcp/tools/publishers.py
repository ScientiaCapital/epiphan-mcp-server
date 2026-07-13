"""Publisher (streaming) management tools for Epiphan Pearl devices.

This module provides CRUD operations for managing stream destinations (publishers)
on Pearl channels. Publishers handle RTMP, SRT, HLS, RTSP, and MPEG-TS streaming.
"""

import logging
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..audit import log_operation
from ..client import PearlAPIError
from ..models import (
    PublisherCreateResult,
    PublisherOperationResult,
    PublisherSettingsResult,
    PublisherTypesResult,
)
from ..validation import ValidationError, validate_streaming_url
from .device import get_client
from .discovery import get_default_channel
from .params import ChannelNum, DeviceId

logger = logging.getLogger(__name__)

_PublisherName = Annotated[
    str,
    Field(description="Display name for the publisher."),
]
_PublisherType = Annotated[
    str,
    Field(description="Stream protocol: 'rtmp' (default), 'srt', 'hls', 'rtsp', or 'mpeg_ts'."),
]
_StreamUrl = Annotated[
    str | None,
    Field(description="Destination URL (e.g. 'rtmp://live.twitch.tv/app')."),
]
_StreamKey = Annotated[
    str | None,
    Field(description="Stream key for RTMP destinations."),
]
_Bitrate = Annotated[
    int | None,
    Field(description="Target bitrate in bps."),
]
_PublisherId = Annotated[
    str,
    Field(description="Publisher ID to act on (e.g. 'publisher-1')."),
]
_Enabled = Annotated[
    bool | None,
    Field(description="Enable or disable the publisher."),
]


async def create_publisher(
    device_id: DeviceId = "default",
    channel: ChannelNum = None,
    name: _PublisherName = "",
    publisher_type: _PublisherType = "rtmp",
    url: _StreamUrl = None,
    stream_key: _StreamKey = None,
    bitrate: _Bitrate = None,
) -> PublisherCreateResult:
    """
    Create a new streaming destination on a Pearl channel.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based). Auto-detected if not specified.
        name: Display name for the publisher.
        publisher_type: Stream protocol - rtmp, srt, hls, rtsp, or mpeg_ts.
        url: Destination URL (e.g., rtmp://live.twitch.tv/app).
        stream_key: Stream key for RTMP destinations.
        bitrate: Target bitrate in bps (optional).

    Returns:
        Created publisher info including the assigned ID.
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    if not name:
        return PublisherCreateResult(
            success=False,
            error="Publisher name is required",
            device=device_id,
        )

    if url:
        try:
            validate_streaming_url(url)
        except ValidationError as e:
            return PublisherCreateResult(
                success=False,
                error=f"Invalid URL: {e}",
                device=device_id,
            )

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
            log_operation(
                "create_publisher",
                client.host,
                details={"channel": channel_id, "name": name, "type": publisher_type},
            )
            return PublisherCreateResult(
                success=True,
                device=client.host,
                channel=channel_id,
                publisher=result,
                message=f"Publisher '{name}' created successfully",
            )
    except PearlAPIError as e:
        return PublisherCreateResult(
            success=False,
            error=str(e),
            device=device_id,
            channel=channel,
        )
    except ValueError as e:
        return PublisherCreateResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def delete_publisher(
    device_id: DeviceId = "default",
    channel: ChannelNum = None,
    publisher: _PublisherId = "publisher-1",
) -> PublisherOperationResult:
    """
    Delete a streaming destination from a Pearl channel.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based). Auto-detected if not specified.
        publisher: Publisher ID to delete (e.g., "publisher-1").

    Returns:
        Confirmation of deletion.
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.delete_publisher(channel_id, publisher)
            log_operation(
                "delete_publisher",
                client.host,
                details={"channel": channel_id, "publisher": publisher},
            )
            return PublisherOperationResult(**result.model_dump())
    except PearlAPIError as e:
        return PublisherOperationResult(
            success=False,
            error=str(e),
            device=device_id,
            channel=channel,
            publisher=publisher,
        )
    except ValueError as e:
        return PublisherOperationResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def get_publisher_settings(
    device_id: DeviceId = "default",
    channel: ChannelNum = None,
    publisher: _PublisherId = "publisher-1",
) -> PublisherSettingsResult:
    """
    Get configuration settings for a streaming destination.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based). Auto-detected if not specified.
        publisher: Publisher ID (e.g., "publisher-1").

    Returns:
        Publisher settings including URL, stream key, bitrate, etc.
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            settings = await client.get_publisher_settings(channel_id, publisher)
            return PublisherSettingsResult(
                success=True,
                device=client.host,
                channel=channel_id,
                publisher=publisher,
                settings=settings,
            )
    except PearlAPIError as e:
        return PublisherSettingsResult(
            success=False,
            error=str(e),
            device=device_id,
            channel=channel,
            publisher=publisher,
        )
    except ValueError as e:
        return PublisherSettingsResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def update_publisher_settings(
    device_id: DeviceId = "default",
    channel: ChannelNum = None,
    publisher: _PublisherId = "publisher-1",
    url: _StreamUrl = None,
    stream_key: _StreamKey = None,
    bitrate: _Bitrate = None,
    enabled: _Enabled = None,
) -> PublisherOperationResult:
    """
    Update settings for a streaming destination (partial update).

    Only provided settings will be changed; other settings remain unchanged.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based). Auto-detected if not specified.
        publisher: Publisher ID (e.g., "publisher-1").
        url: New destination URL.
        stream_key: New stream key.
        bitrate: New target bitrate in bps.
        enabled: Enable or disable the publisher.

    Returns:
        Confirmation of settings update.
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    if url is not None:
        try:
            validate_streaming_url(url)
        except ValidationError as e:
            return PublisherOperationResult(
                success=False,
                error=f"Invalid URL: {e}",
                device=device_id,
            )

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
        return PublisherOperationResult(
            success=False,
            error="No settings provided to update",
            device=device_id,
        )

    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.update_publisher_settings(channel_id, publisher, settings)
            log_operation(
                "update_publisher_settings",
                client.host,
                details={"channel": channel_id, "publisher": publisher, "fields": list(settings)},
            )
            return PublisherOperationResult(**result.model_dump())
    except PearlAPIError as e:
        return PublisherOperationResult(
            success=False,
            error=str(e),
            device=device_id,
            channel=channel,
            publisher=publisher,
        )
    except ValueError as e:
        return PublisherOperationResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def list_publisher_types(
    device_id: DeviceId = "default",
    channel: ChannelNum = None,
) -> PublisherTypesResult:
    """
    List available streaming protocols for a channel.

    Returns the types of publishers that can be created on this channel.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based). Auto-detected if not specified.

    Returns:
        List of available publisher types (rtmp, srt, hls, etc.).
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            types = await client.get_publisher_types(channel_id)
            return PublisherTypesResult(
                success=True,
                device=client.host,
                channel=channel_id,
                types=types,
            )
    except PearlAPIError as e:
        return PublisherTypesResult(
            success=False,
            error=str(e),
            device=device_id,
            channel=channel,
        )
    except ValueError as e:
        return PublisherTypesResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def rename_publisher(
    device_id: DeviceId = "default",
    channel: ChannelNum = None,
    publisher: _PublisherId = "publisher-1",
    name: _PublisherName = "",
) -> PublisherOperationResult:
    """
    Rename a streaming destination.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based). Auto-detected if not specified.
        publisher: Publisher ID (e.g., "publisher-1").
        name: New display name for the publisher.

    Returns:
        Confirmation of rename operation.
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    if not name:
        return PublisherOperationResult(
            success=False,
            error="New name is required",
            device=device_id,
        )

    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.update_publisher_name(channel_id, publisher, name)
            return PublisherOperationResult(**result.model_dump())
    except PearlAPIError as e:
        return PublisherOperationResult(
            success=False,
            error=str(e),
            device=device_id,
            channel=channel,
            publisher=publisher,
        )
    except ValueError as e:
        return PublisherOperationResult(
            success=False,
            error=str(e),
            device=device_id,
        )


def register(server: FastMCP) -> None:
    """Register publisher MCP tools."""
    server.tool()(create_publisher)
    server.tool()(delete_publisher)
    server.tool()(get_publisher_settings)
    server.tool()(list_publisher_types)
    server.tool()(rename_publisher)
    server.tool()(update_publisher_settings)
