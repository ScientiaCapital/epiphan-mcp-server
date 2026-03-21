"""Opencast integration MCP tools.

These tools enable AI assistants to interact with Opencast video platform
for managing lecture recordings, series, and scheduled captures in conjunction
with Pearl capture devices.

Opencast is an open-source video management system used by hundreds of
universities worldwide for lecture capture and video distribution.

Environment Variables Required:
    OPENCAST_HOST: Opencast server hostname (e.g., "opencast.university.edu")
    OPENCAST_USERNAME: Admin username
    OPENCAST_PASSWORD: Admin password
    OPENCAST_USE_HTTPS: Use HTTPS (default "true")
    OPENCAST_DEFAULT_SERIES: Optional default series UUID
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from epiphan_mcp.integrations.opencast import (
    OpencastAPIError,
    OpencastAuthError,
    OpencastClient,
)


def _get_opencast_config() -> dict[str, Any]:
    """Get Opencast configuration from environment."""
    host = os.environ.get("OPENCAST_HOST")
    username = os.environ.get("OPENCAST_USERNAME")
    password = os.environ.get("OPENCAST_PASSWORD")

    missing = []
    if not host:
        missing.append("OPENCAST_HOST")
    if not username:
        missing.append("OPENCAST_USERNAME")
    if not password:
        missing.append("OPENCAST_PASSWORD")

    if missing:
        raise ValueError(
            f"Missing Opencast configuration. Set environment variables: {', '.join(missing)}"
        )

    return {
        "host": host,
        "username": username,
        "password": password,
        "use_https": os.environ.get("OPENCAST_USE_HTTPS", "true").lower() == "true",
        "default_series": os.environ.get("OPENCAST_DEFAULT_SERIES", ""),
    }


async def list_opencast_series(
    filter_text: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List series (courses/channels) in Opencast.

    Retrieves series accessible to the configured admin account.
    Series are used to organize recordings by course or topic.

    Args:
        filter_text: Optional filter by title (partial match)
        limit: Maximum number of results (default 50)
        offset: Pagination offset for paging through results

    Returns:
        Dict with series list and count

    Example:
        "List all Opencast series"
        "Find Opencast series containing 'Physics'"
        "Show first 20 Opencast courses"
    """
    try:
        config = _get_opencast_config()
    except ValueError as e:
        return {"error": str(e), "series": []}

    try:
        async with OpencastClient(**config) as client:
            series = await client.list_series(
                filter_text=filter_text,
                limit=limit,
                offset=offset,
            )
            return {
                "series": series,
                "count": len(series),
                "filter": filter_text or None,
                "offset": offset,
            }
    except OpencastAuthError as e:
        return {"error": f"Authentication failed: {e}", "series": []}
    except OpencastAPIError as e:
        return {"error": f"API error: {e}", "series": []}


async def get_opencast_series(series_id: str) -> dict[str, Any]:
    """Get details of a specific Opencast series.

    Args:
        series_id: Series UUID

    Returns:
        Series details including title, description, creator

    Example:
        "Get details of Opencast series abc-123"
    """
    if not series_id:
        return {"error": "series_id is required"}

    try:
        config = _get_opencast_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with OpencastClient(**config) as client:
            series = await client.get_series(series_id)
            return {"series": series}
    except OpencastAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except OpencastAPIError as e:
        return {"error": f"API error: {e}"}


async def create_opencast_series(
    title: str,
    description: str = "",
    creator: str = "",
    subject: str = "",
    language: str = "en",
) -> dict[str, Any]:
    """Create a new series in Opencast.

    Series are containers for organizing recordings by course or topic.

    Args:
        title: Series title (required)
        description: Series description
        creator: Creator/instructor name
        subject: Subject or topic
        language: Language code (default "en")

    Returns:
        Created series details including UUID

    Example:
        "Create an Opencast series called 'Physics 101 Fall 2024'"
        "Create a series for Dr. Smith's lectures"
    """
    if not title:
        return {"error": "title is required"}

    try:
        config = _get_opencast_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with OpencastClient(**config) as client:
            series = await client.create_series(
                title=title,
                description=description,
                creator=creator,
                subject=subject,
                language=language,
            )
            return {
                "series": series,
                "message": f"Created series '{title}'",
            }
    except OpencastAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except OpencastAPIError as e:
        return {"error": f"API error: {e}"}


async def list_opencast_events(
    series_id: str = "",
    status: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List events (recordings) in Opencast.

    Args:
        series_id: Filter by series UUID (optional)
        status: Filter by status - e.g., "PROCESSED", "PROCESSING" (optional)
        limit: Maximum number of results (default 50)
        offset: Pagination offset

    Returns:
        Dict with events list and count

    Example:
        "List all Opencast recordings"
        "Show events in series abc-123"
        "List processed Opencast events"
    """
    try:
        config = _get_opencast_config()
    except ValueError as e:
        return {"error": str(e), "events": []}

    try:
        async with OpencastClient(**config) as client:
            events = await client.list_events(
                series_id=series_id,
                status=status,
                limit=limit,
                offset=offset,
            )
            return {
                "events": events,
                "count": len(events),
                "series_id": series_id or "all",
                "status": status or "all",
                "offset": offset,
            }
    except OpencastAuthError as e:
        return {"error": f"Authentication failed: {e}", "events": []}
    except OpencastAPIError as e:
        return {"error": f"API error: {e}", "events": []}


async def get_opencast_event(event_id: str) -> dict[str, Any]:
    """Get details of a specific Opencast event (recording).

    Args:
        event_id: Event UUID

    Returns:
        Event details including title, duration, status, publications

    Example:
        "Get details of Opencast event xyz-789"
    """
    if not event_id:
        return {"error": "event_id is required"}

    try:
        config = _get_opencast_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with OpencastClient(**config) as client:
            event = await client.get_event(event_id)
            return {"event": event}
    except OpencastAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except OpencastAPIError as e:
        return {"error": f"API error: {e}"}


async def ingest_to_opencast(
    file_path: str,
    title: str,
    series_id: str = "",
    creator: str = "",
    description: str = "",
    spatial: str = "",
    workflow: str = "fast",
) -> dict[str, Any]:
    """Ingest a video recording to Opencast.

    Uploads a video file and starts the processing workflow.
    Large files may take several minutes to upload.

    Args:
        file_path: Local path to video file
        title: Recording title
        series_id: Target series UUID (uses default if not provided)
        creator: Presenter/creator name
        description: Recording description
        spatial: Location/room name
        workflow: Processing workflow ID (default "fast")

    Returns:
        Ingest result with workflow instance ID

    Example:
        "Upload lecture.mp4 to Opencast series abc-123"
        "Ingest the recording to Opencast as 'Physics Lecture 5'"
    """
    if not file_path:
        return {"error": "file_path is required"}
    if not title:
        return {"error": "title is required"}

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        config = _get_opencast_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with OpencastClient(**config) as client:
            result = await client.ingest_recording(
                file_path=path,
                title=title,
                series_id=series_id,
                creator=creator,
                description=description,
                spatial=spatial,
                workflow=workflow,
            )
            return {
                "result": result,
                "message": f"Ingested '{title}' to Opencast",
                "file_size": path.stat().st_size,
            }
    except OpencastAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except OpencastAPIError as e:
        return {"error": f"API error: {e}"}


async def get_opencast_ingest_status(workflow_id: str) -> dict[str, Any]:
    """Check the status of an Opencast ingest workflow.

    Args:
        workflow_id: Workflow instance ID from ingest

    Returns:
        Workflow status including state and progress

    Example:
        "Check status of Opencast ingest workflow 12345"
    """
    if not workflow_id:
        return {"error": "workflow_id is required"}

    try:
        config = _get_opencast_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with OpencastClient(**config) as client:
            status = await client.get_ingest_status(workflow_id)
            return {"status": status}
    except OpencastAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except OpencastAPIError as e:
        return {"error": f"API error: {e}"}


async def schedule_opencast_capture(
    title: str,
    start_time: str,
    end_time: str,
    capture_agent: str,
    series_id: str = "",
    creator: str = "",
    description: str = "",
    spatial: str = "",
) -> dict[str, Any]:
    """Schedule a capture event in Opencast for Pearl auto-record.

    Creates a scheduled event that Pearl devices (registered as capture agents)
    will automatically pick up and record at the scheduled time.

    Args:
        title: Event title
        start_time: Start time in ISO format (e.g., "2024-01-15T10:00:00")
        end_time: End time in ISO format (e.g., "2024-01-15T11:00:00")
        capture_agent: Capture agent ID (Pearl device identifier)
        series_id: Target series UUID
        creator: Presenter name
        description: Event description
        spatial: Room/location

    Returns:
        Created scheduled event

    Example:
        "Schedule an Opencast recording for Pearl_Room101 from 10am to 11am"
        "Schedule capture for 'Physics Lecture' tomorrow at 2pm"
    """
    if not title:
        return {"error": "title is required"}
    if not start_time:
        return {"error": "start_time is required"}
    if not end_time:
        return {"error": "end_time is required"}
    if not capture_agent:
        return {"error": "capture_agent is required"}

    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except ValueError as e:
        return {
            "error": f"Invalid datetime format: {e}. Use ISO format like '2024-01-15T10:00:00'"
        }

    if end_dt <= start_dt:
        return {"error": "end_time must be after start_time"}

    try:
        config = _get_opencast_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with OpencastClient(**config) as client:
            event = await client.schedule_capture(
                title=title,
                start_time=start_dt,
                end_time=end_dt,
                capture_agent=capture_agent,
                series_id=series_id,
                creator=creator,
                description=description,
                spatial=spatial,
            )
            return {
                "event": event,
                "message": f"Scheduled capture '{title}' on {capture_agent}",
                "start_time": start_time,
                "end_time": end_time,
            }
    except OpencastAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except OpencastAPIError as e:
        return {"error": f"API error: {e}"}


async def delete_opencast_event(event_id: str) -> dict[str, Any]:
    """Delete an event from Opencast.

    Permanently removes an event/recording. Use with caution.

    Args:
        event_id: Event UUID to delete

    Returns:
        Confirmation of deletion

    Example:
        "Delete Opencast event xyz-789"
    """
    if not event_id:
        return {"error": "event_id is required"}

    try:
        config = _get_opencast_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with OpencastClient(**config) as client:
            await client.delete_event(event_id)
            return {
                "success": True,
                "message": f"Deleted event {event_id}",
                "event_id": event_id,
            }
    except OpencastAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except OpencastAPIError as e:
        return {"error": f"API error: {e}"}


# Tool registry for MCP server registration
OPENCAST_TOOLS = [
    list_opencast_series,
    get_opencast_series,
    create_opencast_series,
    list_opencast_events,
    get_opencast_event,
    ingest_to_opencast,
    get_opencast_ingest_status,
    schedule_opencast_capture,
    delete_opencast_event,
]


def register(server: FastMCP) -> None:
    """Register Opencast MCP tools."""
    server.tool()(create_opencast_series)
    server.tool()(delete_opencast_event)
    server.tool()(get_opencast_event)
    server.tool()(get_opencast_ingest_status)
    server.tool()(get_opencast_series)
    server.tool()(ingest_to_opencast)
    server.tool()(list_opencast_events)
    server.tool()(list_opencast_series)
    server.tool()(schedule_opencast_capture)
