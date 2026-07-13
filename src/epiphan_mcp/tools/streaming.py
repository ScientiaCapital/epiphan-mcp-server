"""Streaming control tools for Epiphan Pearl devices."""

import base64
import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..client import PearlAPIError
from ..models import (
    ChannelListResult,
    ChannelPreviewResult,
    PublisherListResult,
    StreamControlResult,
    StreamStatusResult,
)
from .device import get_client
from .discovery import get_default_channel
from .params import ChannelNum, DeviceId, ImageFormat, PreviewResolution

logger = logging.getLogger(__name__)

_PublisherId = Annotated[
    str,
    Field(description="Publisher ID to query (e.g. 'publisher-1')."),
]
_IncludePublishers = Annotated[
    bool,
    Field(description="Include publisher (stream) details for each channel."),
]
_IncludeLayouts = Annotated[
    bool,
    Field(description="Include layout details for each channel."),
]


async def start_stream(
    device_id: DeviceId = "default", channel: ChannelNum = None
) -> StreamControlResult:
    """
    Start streaming on an Epiphan Pearl device.

    This begins streaming video to the configured destination (RTMP, SRT, etc.).
    The stream destination must be configured on the device beforehand.
    Starts all publishers/streams on the specified channel.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based) to start streaming. Auto-detected if not specified.

    Returns:
        Confirmation of stream start with device and channel details.
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.start_all_publishers(channel_id)
            return StreamControlResult(**result.model_dump())
    except PearlAPIError as e:
        return StreamControlResult(
            success=False,
            error=str(e),
            device=device_id,
            channel=channel,
        )
    except ValueError as e:
        return StreamControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def stop_stream(
    device_id: DeviceId = "default", channel: ChannelNum = None
) -> StreamControlResult:
    """
    Stop streaming on an Epiphan Pearl device.

    This stops all active streams on the specified channel.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based) to stop streaming. Auto-detected if not specified.

    Returns:
        Confirmation of stream stop with device and channel details.
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            result = await client.stop_all_publishers(channel_id)
            return StreamControlResult(**result.model_dump())
    except PearlAPIError as e:
        return StreamControlResult(
            success=False,
            error=str(e),
            device=device_id,
            channel=channel,
        )
    except ValueError as e:
        return StreamControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def get_stream_status(
    device_id: DeviceId = "default",
    channel: ChannelNum = None,
    publisher: _PublisherId = "publisher-1",
) -> StreamStatusResult:
    """
    Get the status of a specific stream/publisher on an Epiphan Pearl device.

    Use this to check if a stream is active, its duration, bitrate, and bytes sent.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based) containing the publisher. Auto-detected if not specified.
        publisher: Publisher ID (e.g., "publisher-1").

    Returns:
        Stream status including:
        - state: Current state (streaming, stopped, etc.)
        - duration_seconds: How long the stream has been active
        - bitrate_bps: Current bitrate in bits per second
        - bytes_sent: Total bytes sent since stream started
        - destination: Stream destination URL
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            status = await client.get_publisher_status(channel_id, publisher)
            return StreamStatusResult(
                success=True,
                device=client.host,
                channel=channel_id,
                publisher=publisher,
                state=status.state.value,
                duration_seconds=status.duration_seconds,
                bitrate_bps=status.bitrate_actual or 0,
                bytes_sent=status.bytes_sent or 0,
                destination=status.destination or "",
            )
    except PearlAPIError as e:
        return StreamStatusResult(
            success=False,
            error=str(e),
            device=device_id,
            channel=channel,
            publisher=publisher,
        )
    except ValueError as e:
        return StreamStatusResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def list_channels(
    device_id: DeviceId = "default",
    include_publishers: _IncludePublishers = False,
    include_layouts: _IncludeLayouts = False,
) -> ChannelListResult:
    """
    List all channels on an Epiphan Pearl device.

    Channels represent video processing pipelines that combine inputs, layouts,
    and outputs. Each channel can have recorders and publishers attached.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        include_publishers: Include publisher (stream) details for each channel.
        include_layouts: Include layout details for each channel.

    Returns:
        List of channels with their IDs, names, and optionally publishers/layouts.
    """
    try:
        async with get_client(device_id) as client:
            channels = await client.get_channels(
                include_publishers=include_publishers,
                include_layouts=include_layouts,
            )
            channel_dicts = [c.model_dump() if isinstance(c, BaseModel) else c for c in channels]
            return ChannelListResult(
                success=True,
                device=client.host,
                total_channels=len(channel_dicts),
                channels=channel_dicts,
            )
    except PearlAPIError as e:
        return ChannelListResult(
            success=False,
            error=str(e),
            device=device_id,
        )
    except ValueError as e:
        return ChannelListResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def list_publishers(
    device_id: DeviceId = "default",
    channel: ChannelNum = None,
) -> PublisherListResult:
    """
    List all publishers (stream destinations) on a channel.

    Publishers define where a channel's video is streamed to (RTMP, SRT, etc.).
    Use this to discover available streams before starting/stopping them.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based). Auto-detected if not specified.

    Returns:
        List of publishers with their IDs, names, types, and enabled status.
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            publishers = await client.get_publishers(channel_id)
            return PublisherListResult(
                success=True,
                device=client.host,
                channel=channel_id,
                total_publishers=len(publishers),
                publishers=publishers,
            )
    except PearlAPIError as e:
        return PublisherListResult(
            success=False,
            error=str(e),
            device=device_id,
            channel=channel,
        )
    except ValueError as e:
        return PublisherListResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def get_channel_preview(
    device_id: DeviceId = "default",
    channel: ChannelNum = None,
    resolution: PreviewResolution = None,
    format: ImageFormat = "jpg",
) -> ChannelPreviewResult:
    """
    Get a live preview image from a channel.

    Captures a snapshot of the channel's current output as a JPEG or PNG image.
    The image is returned as a base64-encoded string for easy embedding.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        channel: Channel number (1-based). Auto-detected if not specified.
        resolution: Optional resolution (e.g., "1920x1080", "640x360").
                    If not specified, uses the channel's native resolution.
        format: Image format - "jpg" (default) or "png".

    Returns:
        Preview image as base64-encoded string with format and resolution metadata.
    """
    if channel is None:
        channel = await get_default_channel(device_id)
    try:
        async with get_client(device_id) as client:
            channel_id = f"channel-{channel}" if isinstance(channel, int) else str(channel)
            image_bytes = await client.get_channel_preview(
                channel_id,
                resolution=resolution or "640x360",
                format=format,
            )
            preview_b64 = base64.b64encode(image_bytes).decode("ascii")
            return ChannelPreviewResult(
                success=True,
                device=client.host,
                channel=channel_id,
                format=format,
                preview_base64=preview_b64,
                size_bytes=len(image_bytes),
                resolution=resolution,
            )
    except PearlAPIError as e:
        return ChannelPreviewResult(
            success=False,
            error=str(e),
            device=device_id,
            channel=channel,
        )
    except ValueError as e:
        return ChannelPreviewResult(
            success=False,
            error=str(e),
            device=device_id,
        )


def register(server: FastMCP) -> None:
    """Register streaming MCP tools."""
    server.tool()(get_channel_preview)
    server.tool()(get_stream_status)
    server.tool()(list_channels)
    server.tool()(list_publishers)
    server.tool()(start_stream)
    server.tool()(stop_stream)
