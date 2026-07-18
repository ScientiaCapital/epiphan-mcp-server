"""Echo360 (EchoVideo) integration MCP tools.

These tools enable AI assistants to interact with the Echo360 EchoVideo
platform for managing courses, sections, and media, and for publishing
Pearl recordings via the Capture Intake API.

Environment Variables Required:
    ECHO360_HOST: Regional Echo360 hostname (e.g., "echo360.org",
        "echo360.org.uk", "echo360.org.au", "echo360.ca")
    ECHO360_CLIENT_ID: OAuth2 client ID from Institution Settings > Integration
    ECHO360_CLIENT_SECRET: OAuth2 client secret (shown once at creation)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from epiphan_mcp.audit import log_operation
from epiphan_mcp.config import require_env, validate_integration_host
from epiphan_mcp.integrations.echo360 import (
    Echo360APIError,
    Echo360AuthError,
    Echo360Client,
)
from epiphan_mcp.models import (
    Echo360CourseListResult,
    Echo360MediaListResult,
    Echo360MediaResult,
    Echo360SectionListResult,
    Echo360UploadResult,
    Echo360UploadStatusResult,
)

_CourseId = Annotated[str, Field(description="Echo360 course ID to filter sections by (optional).")]
_MediaSearch = Annotated[str, Field(description="Search term to filter media by title (optional).")]
_MediaId = Annotated[str, Field(description="Echo360 media ID.")]
_FilePath = Annotated[str, Field(description="Local path to the video file to upload.")]
_MediaTitle = Annotated[str, Field(description="Media title (defaults to the filename if empty).")]
_WaitForProcessing = Annotated[
    bool,
    Field(description="Whether to wait for Echo360 to finish processing before returning."),
]
_UploadId = Annotated[str, Field(description="Capture upload ID.")]


@dataclass(frozen=True)
class _Echo360Config:
    """Validated Echo360 configuration."""

    host: str
    client_id: str
    client_secret: str


def _get_echo360_config() -> _Echo360Config:
    """Get Echo360 configuration from environment."""
    env = require_env("Echo360", "ECHO360_HOST", "ECHO360_CLIENT_ID", "ECHO360_CLIENT_SECRET")
    return _Echo360Config(
        host=validate_integration_host(env["ECHO360_HOST"], "Echo360"),
        client_id=env["ECHO360_CLIENT_ID"],
        client_secret=env["ECHO360_CLIENT_SECRET"],
    )


async def list_echo360_courses() -> Echo360CourseListResult:
    """List courses on the Echo360 EchoVideo platform.

    Retrieves courses visible to the configured API client
    (first page; Echo360 pages default to 100 items).

    Returns:
        Courses list, count, and a truncated flag when more pages exist.

    Example:
        "List Echo360 courses"
    """
    try:
        config = _get_echo360_config()
    except ValueError as e:
        return Echo360CourseListResult(error=str(e), courses=[])

    try:
        async with Echo360Client(
            host=config.host,
            client_id=config.client_id,
            client_secret=config.client_secret,
        ) as client:
            courses, truncated = await client.list_courses()
            return Echo360CourseListResult(courses=courses, count=len(courses), truncated=truncated)
    except Echo360AuthError as e:
        return Echo360CourseListResult(error=f"Authentication failed: {e}", courses=[])
    except Echo360APIError as e:
        return Echo360CourseListResult(error=f"API error: {e}", courses=[])


async def list_echo360_sections(course_id: _CourseId = "") -> Echo360SectionListResult:
    """List sections on the Echo360 EchoVideo platform.

    Sections are the course instances recordings publish into,
    optionally filtered to one course.

    Args:
        course_id: Optional course ID to filter sections

    Returns:
        Sections list, count, and a truncated flag when more pages exist.

    Example:
        "List Echo360 sections"
        "List Echo360 sections for course abc-123"
    """
    try:
        config = _get_echo360_config()
    except ValueError as e:
        return Echo360SectionListResult(error=str(e), sections=[])

    try:
        async with Echo360Client(
            host=config.host,
            client_id=config.client_id,
            client_secret=config.client_secret,
        ) as client:
            sections, truncated = await client.list_sections(course_id=course_id or None)
            return Echo360SectionListResult(
                sections=sections,
                count=len(sections),
                course_id=course_id or None,
                truncated=truncated,
            )
    except Echo360AuthError as e:
        return Echo360SectionListResult(error=f"Authentication failed: {e}", sections=[])
    except Echo360APIError as e:
        return Echo360SectionListResult(error=f"API error: {e}", sections=[])


async def list_echo360_medias(search_query: _MediaSearch = "") -> Echo360MediaListResult:
    """List media on the Echo360 EchoVideo platform.

    Retrieves media items visible to the configured API client,
    optionally filtered by a title search.

    Args:
        search_query: Optional search term to filter media

    Returns:
        Media list, count, and a truncated flag when more pages exist.

    Example:
        "List all Echo360 media"
        "Search Echo360 for 'Physics 101'"
    """
    try:
        config = _get_echo360_config()
    except ValueError as e:
        return Echo360MediaListResult(error=str(e), medias=[])

    try:
        async with Echo360Client(
            host=config.host,
            client_id=config.client_id,
            client_secret=config.client_secret,
        ) as client:
            medias, truncated = await client.list_medias(search_query=search_query or None)
            return Echo360MediaListResult(
                medias=medias,
                count=len(medias),
                search_query=search_query or None,
                truncated=truncated,
            )
    except Echo360AuthError as e:
        return Echo360MediaListResult(error=f"Authentication failed: {e}", medias=[])
    except Echo360APIError as e:
        return Echo360MediaListResult(error=f"API error: {e}", medias=[])


async def get_echo360_media(media_id: _MediaId) -> Echo360MediaResult:
    """Get details of a specific Echo360 media item.

    Args:
        media_id: Echo360 media ID

    Returns:
        Media item detail.

    Example:
        "Get details of Echo360 media abc-123"
    """
    if not media_id:
        return Echo360MediaResult(error="media_id is required")

    try:
        config = _get_echo360_config()
    except ValueError as e:
        return Echo360MediaResult(error=str(e))

    try:
        async with Echo360Client(
            host=config.host,
            client_id=config.client_id,
            client_secret=config.client_secret,
        ) as client:
            media = await client.get_media(media_id)
            return Echo360MediaResult(media=media)
    except Echo360AuthError as e:
        return Echo360MediaResult(error=f"Authentication failed: {e}")
    except Echo360APIError as e:
        return Echo360MediaResult(error=f"API error: {e}")


async def upload_video_to_echo360(
    file_path: _FilePath,
    title: _MediaTitle = "",
    wait_for_processing: _WaitForProcessing = False,
) -> Echo360UploadResult:
    """Upload a video file to the Echo360 EchoVideo platform.

    Runs the full Capture Intake workflow: creates a pending upload,
    PUTs the file to the signed S3 URL, and submits it so Echo360
    starts processing. Use this to publish Pearl recordings to Echo360.

    Args:
        file_path: Local path to the video file
        title: Optional media title (defaults to filename)
        wait_for_processing: Wait for Echo360 to finish processing

    Returns:
        Final upload status.

    Example:
        "Upload /recordings/lecture.mp4 to Echo360"
        "Publish the latest Pearl recording to Echo360 as 'Physics 101 - Week 3'"
    """
    if not file_path:
        return Echo360UploadResult(error="file_path is required")

    path = Path(file_path)
    if not path.exists():
        return Echo360UploadResult(error=f"File not found: {file_path}")

    try:
        config = _get_echo360_config()
    except ValueError as e:
        return Echo360UploadResult(error=str(e))

    file_size = path.stat().st_size

    try:
        async with Echo360Client(
            host=config.host,
            client_id=config.client_id,
            client_secret=config.client_secret,
        ) as client:
            upload = await client.upload_video(
                file_path=path,
                title=title or None,
                wait_for_processing=wait_for_processing,
            )
            log_operation(
                "upload_video_to_echo360",
                config.host,
                details={"file": path.name, "size_bytes": file_size},
            )
            return Echo360UploadResult(
                upload=upload,
                message=f"Uploaded '{path.name}' to Echo360",
                file_size=file_size,
            )
    except Echo360AuthError as e:
        return Echo360UploadResult(error=f"Authentication failed: {e}")
    except Echo360APIError as e:
        return Echo360UploadResult(error=f"API error: {e}")


async def get_echo360_upload_status(upload_id: _UploadId) -> Echo360UploadStatusResult:
    """Get the status of an Echo360 capture upload.

    Args:
        upload_id: Capture upload ID (from upload_video_to_echo360)

    Returns:
        Upload/processing state and full raw status.

    Example:
        "Check Echo360 upload abc-123"
    """
    if not upload_id:
        return Echo360UploadStatusResult(error="upload_id is required")

    try:
        config = _get_echo360_config()
    except ValueError as e:
        return Echo360UploadStatusResult(error=str(e))

    try:
        async with Echo360Client(
            host=config.host,
            client_id=config.client_id,
            client_secret=config.client_secret,
        ) as client:
            status = await client.get_upload_status(upload_id)
            return Echo360UploadStatusResult(
                upload_id=upload_id,
                status=str(status.get("state", status.get("status", ""))) or None,
                details=status,
            )
    except Echo360AuthError as e:
        return Echo360UploadStatusResult(error=f"Authentication failed: {e}")
    except Echo360APIError as e:
        return Echo360UploadStatusResult(error=f"API error: {e}")


def register(server: FastMCP) -> None:
    """Register Echo360 MCP tools."""
    server.tool()(get_echo360_media)
    server.tool()(get_echo360_upload_status)
    server.tool()(list_echo360_courses)
    server.tool()(list_echo360_medias)
    server.tool()(list_echo360_sections)
    server.tool()(upload_video_to_echo360)
