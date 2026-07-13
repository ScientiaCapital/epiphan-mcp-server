"""YuJa integration MCP tools.

These tools enable AI assistants to interact with the YuJa Enterprise Video
Platform for managing videos, channels, and uploads in conjunction with
Pearl capture devices.

Environment Variables Required:
    YUJA_HOST: YuJa service hostname (e.g., "university.yuja.com")
    YUJA_AUTH_TOKEN: Static API token from the YuJa Admin Panel
    YUJA_USER_ID: Default YuJa user ID for upload attribution (optional;
        can also be passed per upload call)
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from epiphan_mcp.audit import log_operation
from epiphan_mcp.config import require_env, validate_integration_host
from epiphan_mcp.integrations.yuja import (
    YuJaAPIError,
    YuJaAuthError,
    YuJaClient,
)
from epiphan_mcp.models import (
    YuJaChannelListResult,
    YuJaDeleteResult,
    YuJaUploadResult,
    YuJaUploadStatusResult,
    YuJaVideoListResult,
    YuJaVideoResult,
)

_VideoSearch = Annotated[
    str, Field(description="Search term to filter videos by title (optional).")
]
_VideoId = Annotated[str, Field(description="YuJa video ID.")]
_FilePath = Annotated[str, Field(description="Local path to the video file to upload.")]
_VideoTitle = Annotated[str, Field(description="Video title (defaults to the filename if empty).")]
_UploadUserId = Annotated[
    str,
    Field(
        description="YuJa user ID the upload is attributed to "
        "(defaults to the YUJA_USER_ID environment variable if empty)."
    ),
]
_WaitForProcessing = Annotated[
    bool,
    Field(description="Whether to wait for YuJa to finish processing before returning."),
]
_SessionId = Annotated[str, Field(description="Upload session ID.")]


@dataclass(frozen=True)
class _YuJaConfig:
    """Validated YuJa configuration."""

    host: str
    auth_token: str
    user_id: str | None


def _get_yuja_config() -> _YuJaConfig:
    """Get YuJa configuration from environment."""
    env = require_env("YuJa", "YUJA_HOST", "YUJA_AUTH_TOKEN")
    return _YuJaConfig(
        host=validate_integration_host(env["YUJA_HOST"], "YuJa"),
        auth_token=env["YUJA_AUTH_TOKEN"],
        user_id=os.environ.get("YUJA_USER_ID"),
    )


async def list_yuja_videos(search_query: _VideoSearch = "") -> YuJaVideoListResult:
    """List videos on the YuJa video platform.

    Retrieves videos accessible to the configured API token,
    optionally filtered by a title search.

    Args:
        search_query: Optional search term to filter videos

    Returns:
        Videos list and count.

    Example:
        "List all YuJa videos"
        "Search YuJa for 'Physics 101'"
    """
    try:
        config = _get_yuja_config()
    except ValueError as e:
        return YuJaVideoListResult(error=str(e), videos=[])

    try:
        async with YuJaClient(host=config.host, auth_token=config.auth_token) as client:
            videos, truncated = await client.list_videos(search_query=search_query or None)
            return YuJaVideoListResult(
                videos=videos,
                count=len(videos),
                search_query=search_query or None,
                truncated=truncated,
            )
    except YuJaAuthError as e:
        return YuJaVideoListResult(error=f"Authentication failed: {e}", videos=[])
    except YuJaAPIError as e:
        return YuJaVideoListResult(error=f"API error: {e}", videos=[])


async def get_yuja_video(video_id: _VideoId) -> YuJaVideoResult:
    """Get details and metadata of a specific YuJa video.

    Args:
        video_id: YuJa video ID

    Returns:
        Video detail including metadata entries.

    Example:
        "Get details of YuJa video 187195"
    """
    if not video_id:
        return YuJaVideoResult(error="video_id is required")

    try:
        config = _get_yuja_config()
    except ValueError as e:
        return YuJaVideoResult(error=str(e))

    try:
        async with YuJaClient(host=config.host, auth_token=config.auth_token) as client:
            video = await client.get_video_metadata(video_id)
            return YuJaVideoResult(video=video)
    except YuJaAuthError as e:
        return YuJaVideoResult(error=f"Authentication failed: {e}")
    except YuJaAPIError as e:
        return YuJaVideoResult(error=f"API error: {e}")


async def list_yuja_channels() -> YuJaChannelListResult:
    """List media channels on the YuJa video platform.

    Channels are YuJa's shared media collections (similar to folders).

    Returns:
        Channels list and count.

    Example:
        "List YuJa channels"
        "What channels can I publish to on YuJa?"
    """
    try:
        config = _get_yuja_config()
    except ValueError as e:
        return YuJaChannelListResult(error=str(e), channels=[])

    try:
        async with YuJaClient(host=config.host, auth_token=config.auth_token) as client:
            channels, truncated = await client.list_channels()
            return YuJaChannelListResult(
                channels=channels, count=len(channels), truncated=truncated
            )
    except YuJaAuthError as e:
        return YuJaChannelListResult(error=f"Authentication failed: {e}", channels=[])
    except YuJaAPIError as e:
        return YuJaChannelListResult(error=f"API error: {e}", channels=[])


async def upload_video_to_yuja(
    file_path: _FilePath,
    title: _VideoTitle = "",
    user_id: _UploadUserId = "",
    wait_for_processing: _WaitForProcessing = False,
) -> YuJaUploadResult:
    """Upload a video file to the YuJa video platform.

    Runs the full signed-URL upload workflow: creates an upload session,
    PUTs the file to the signed S3 URL, and signals completion so YuJa
    starts processing. Use this to publish Pearl recordings to YuJa.

    Args:
        file_path: Local path to the video file
        title: Optional video title (defaults to filename)
        user_id: YuJa user ID to attribute the upload to
            (defaults to YUJA_USER_ID)
        wait_for_processing: Wait for YuJa to finish processing

    Returns:
        Final upload session status.

    Example:
        "Upload /recordings/lecture.mp4 to YuJa"
        "Publish the latest Pearl recording to YuJa as 'Physics 101 - Week 3'"
    """
    if not file_path:
        return YuJaUploadResult(error="file_path is required")

    path = Path(file_path)
    if not path.exists():
        return YuJaUploadResult(error=f"File not found: {file_path}")

    try:
        config = _get_yuja_config()
    except ValueError as e:
        return YuJaUploadResult(error=str(e))

    resolved_user_id = user_id or config.user_id
    if not resolved_user_id:
        return YuJaUploadResult(
            error="user_id is required (pass it or set the YUJA_USER_ID environment variable)"
        )

    file_size = path.stat().st_size

    try:
        async with YuJaClient(host=config.host, auth_token=config.auth_token) as client:
            upload = await client.upload_video(
                user_id=resolved_user_id,
                file_path=path,
                title=title or None,
                wait_for_processing=wait_for_processing,
            )
            log_operation(
                "upload_video_to_yuja",
                config.host,
                details={"file": path.name, "size_bytes": file_size},
            )
            return YuJaUploadResult(
                upload=upload,
                message=f"Uploaded '{path.name}' to YuJa",
                file_size=file_size,
            )
    except YuJaAuthError as e:
        return YuJaUploadResult(error=f"Authentication failed: {e}")
    except YuJaAPIError as e:
        return YuJaUploadResult(error=f"API error: {e}")


async def get_yuja_upload_status(session_id: _SessionId) -> YuJaUploadStatusResult:
    """Get the status of a YuJa upload session.

    Args:
        session_id: Upload session ID (from upload_video_to_yuja)

    Returns:
        Upload/processing state and full raw status.

    Example:
        "Check YuJa upload session 1234"
    """
    if not session_id:
        return YuJaUploadStatusResult(error="session_id is required")

    try:
        config = _get_yuja_config()
    except ValueError as e:
        return YuJaUploadStatusResult(error=str(e))

    try:
        async with YuJaClient(host=config.host, auth_token=config.auth_token) as client:
            status = await client.get_upload_status(session_id)
            return YuJaUploadStatusResult(
                session_id=session_id,
                status=str(status.get("state", status.get("status", ""))) or None,
                details=status,
            )
    except YuJaAuthError as e:
        return YuJaUploadStatusResult(error=f"Authentication failed: {e}")
    except YuJaAPIError as e:
        return YuJaUploadStatusResult(error=f"API error: {e}")


async def delete_yuja_video(video_id: _VideoId) -> YuJaDeleteResult:
    """Delete a video from the YuJa video platform.

    This permanently removes the video. Use with caution.

    Args:
        video_id: YuJa video ID to delete

    Returns:
        Confirmation of deletion.

    Example:
        "Delete YuJa video 187195"
    """
    if not video_id:
        return YuJaDeleteResult(error="video_id is required")

    try:
        config = _get_yuja_config()
    except ValueError as e:
        return YuJaDeleteResult(error=str(e))

    try:
        async with YuJaClient(host=config.host, auth_token=config.auth_token) as client:
            await client.delete_video(video_id)
            log_operation("delete_yuja_video", config.host, details={"video_id": video_id})
            return YuJaDeleteResult(
                success=True,
                message=f"Deleted YuJa video {video_id}",
                video_id=video_id,
            )
    except YuJaAuthError as e:
        return YuJaDeleteResult(error=f"Authentication failed: {e}", video_id=video_id)
    except YuJaAPIError as e:
        return YuJaDeleteResult(error=f"API error: {e}", video_id=video_id)


def register(server: FastMCP) -> None:
    """Register YuJa MCP tools."""
    server.tool()(delete_yuja_video)
    server.tool()(get_yuja_upload_status)
    server.tool()(get_yuja_video)
    server.tool()(list_yuja_channels)
    server.tool()(list_yuja_videos)
    server.tool()(upload_video_to_yuja)
