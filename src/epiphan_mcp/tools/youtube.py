"""YouTube Live integration MCP tools.

These tools enable AI assistants to create and manage YouTube Live broadcasts
for Pearl streaming integration. Pearl devices can stream to YouTube Live
using the RTMP credentials provided by these tools.

Environment Variables Required:
    YOUTUBE_CLIENT_ID: OAuth2 client ID
    YOUTUBE_CLIENT_SECRET: OAuth2 client secret
    YOUTUBE_REFRESH_TOKEN: OAuth2 refresh token (long-lived)
"""

import os
from typing import Any

from fastmcp import FastMCP

from epiphan_mcp.integrations.youtube import (
    YouTubeAPIError,
    YouTubeAuthError,
    YouTubeClient,
    YouTubeQuotaError,
)


def _get_youtube_config() -> dict[str, Any]:
    """Get YouTube configuration from environment."""
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    missing = []
    if not client_id:
        missing.append("YOUTUBE_CLIENT_ID")
    if not client_secret:
        missing.append("YOUTUBE_CLIENT_SECRET")
    if not refresh_token:
        missing.append("YOUTUBE_REFRESH_TOKEN")

    if missing:
        raise ValueError(
            f"Missing YouTube configuration. Set environment variables: {', '.join(missing)}"
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }


async def create_youtube_broadcast(
    title: str,
    scheduled_start: str,
    description: str = "",
    privacy: str = "unlisted",
    resolution: str = "1080p",
    frame_rate: str = "30fps",
) -> dict[str, Any]:
    """Create a YouTube Live broadcast with stream for Pearl integration.

    Creates a broadcast, stream, and binds them together. Returns RTMP
    credentials that can be used to configure a Pearl publisher.

    Args:
        title: Broadcast title (visible to viewers)
        scheduled_start: Start time in ISO 8601 format (e.g., "2024-01-15T10:00:00Z")
        description: Broadcast description
        privacy: Privacy status - "public", "unlisted", or "private" (default "unlisted")
        resolution: Video resolution - "720p", "1080p", "1440p", "2160p" (default "1080p")
        frame_rate: Frame rate - "30fps" or "60fps" (default "30fps")

    Returns:
        Dict with broadcast details and RTMP credentials for Pearl:
        - broadcast_id: YouTube broadcast ID
        - stream_id: YouTube stream ID
        - rtmp_url: RTMP server URL
        - stream_key: Stream key for authentication
        - full_rtmp_url: Complete URL (rtmp_url/stream_key)

    Example:
        "Create a YouTube Live broadcast for 'Physics Lecture' starting at 10am"
        "Set up YouTube streaming for Pearl with 1080p60"
    """
    if not title:
        return {"error": "title is required"}
    if not scheduled_start:
        return {"error": "scheduled_start is required (ISO 8601 format)"}

    try:
        config = _get_youtube_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with YouTubeClient(**config) as client:
            result = await client.create_broadcast_with_stream(
                title=title,
                scheduled_start=scheduled_start,
                description=description,
                privacy=privacy,
                resolution=resolution,
                frame_rate=frame_rate,
            )

            rtmp_creds = result["rtmp_credentials"]
            broadcast = result["broadcast"]
            stream = result["stream"]

            return {
                "broadcast_id": broadcast["id"],
                "stream_id": stream["id"],
                "title": title,
                "scheduled_start": scheduled_start,
                "privacy": privacy,
                "rtmp_url": rtmp_creds["rtmp_url"],
                "stream_key": rtmp_creds["stream_key"],
                "full_rtmp_url": rtmp_creds["full_url"],
                "message": f"Created YouTube broadcast '{title}'. Use RTMP credentials to configure Pearl publisher.",
                "pearl_config_hint": {
                    "publisher_type": "rtmp",
                    "url": rtmp_creds["full_url"],
                    "note": "Create Pearl publisher with these RTMP settings",
                },
            }
    except YouTubeAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except YouTubeQuotaError as e:
        return {"error": f"Quota exceeded: {e}"}
    except YouTubeAPIError as e:
        return {"error": f"API error: {e}"}


async def get_youtube_broadcast_status(broadcast_id: str) -> dict[str, Any]:
    """Get the status of a YouTube Live broadcast.

    Returns the current lifecycle status of the broadcast and its
    bound stream, including health information.

    Args:
        broadcast_id: The YouTube broadcast ID

    Returns:
        Dict with broadcast status, stream status, and timing info

    Example:
        "Check status of YouTube broadcast abc123"
        "Is the YouTube stream healthy?"
    """
    if not broadcast_id:
        return {"error": "broadcast_id is required"}

    try:
        config = _get_youtube_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with YouTubeClient(**config) as client:
            status = await client.get_broadcast_status(broadcast_id)
            return {"status": status}
    except YouTubeAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except YouTubeQuotaError as e:
        return {"error": f"Quota exceeded: {e}"}
    except YouTubeAPIError as e:
        return {"error": f"API error: {e}"}


async def list_youtube_broadcasts(
    status_filter: str = "",
    limit: int = 25,
) -> dict[str, Any]:
    """List YouTube Live broadcasts for the authenticated account.

    Args:
        status_filter: Filter by status - "active", "all", "completed", "upcoming"
                      (empty for all statuses)
        limit: Maximum number of results (default 25, max 50)

    Returns:
        Dict with broadcasts list and count

    Example:
        "List my YouTube broadcasts"
        "Show upcoming YouTube Live events"
        "List active YouTube streams"
    """
    try:
        config = _get_youtube_config()
    except ValueError as e:
        return {"error": str(e), "broadcasts": []}

    try:
        async with YouTubeClient(**config) as client:
            broadcasts = await client.list_broadcasts(
                status_filter=status_filter,
                max_results=limit,
            )

            # Simplify the response
            simplified = []
            for b in broadcasts:
                snippet = b.get("snippet", {})
                status = b.get("status", {})
                simplified.append({
                    "id": b.get("id"),
                    "title": snippet.get("title"),
                    "scheduled_start": snippet.get("scheduledStartTime"),
                    "actual_start": snippet.get("actualStartTime"),
                    "status": status.get("lifeCycleStatus"),
                    "privacy": status.get("privacyStatus"),
                })

            return {
                "broadcasts": simplified,
                "count": len(simplified),
                "filter": status_filter or "all",
            }
    except YouTubeAuthError as e:
        return {"error": f"Authentication failed: {e}", "broadcasts": []}
    except YouTubeQuotaError as e:
        return {"error": f"Quota exceeded: {e}", "broadcasts": []}
    except YouTubeAPIError as e:
        return {"error": f"API error: {e}", "broadcasts": []}


async def end_youtube_broadcast(broadcast_id: str) -> dict[str, Any]:
    """End a YouTube Live broadcast.

    Transitions the broadcast to 'complete' status. The broadcast must
    currently be in 'live' status. After ending, the recording (if enabled)
    will be processed and available as a VOD.

    Args:
        broadcast_id: The YouTube broadcast ID to end

    Returns:
        Confirmation of broadcast completion

    Example:
        "End YouTube broadcast abc123"
        "Stop the YouTube Live stream"
    """
    if not broadcast_id:
        return {"error": "broadcast_id is required"}

    try:
        config = _get_youtube_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with YouTubeClient(**config) as client:
            result = await client.transition_broadcast(
                broadcast_id=broadcast_id,
                status="complete",
            )

            return {
                "success": True,
                "broadcast_id": broadcast_id,
                "new_status": result.get("status", {}).get("lifeCycleStatus", "complete"),
                "message": f"Broadcast {broadcast_id} ended successfully",
            }
    except YouTubeAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except YouTubeQuotaError as e:
        return {"error": f"Quota exceeded: {e}"}
    except YouTubeAPIError as e:
        return {"error": f"API error: {e}"}


# Tool registry for MCP server registration
YOUTUBE_TOOLS = [
    create_youtube_broadcast,
    get_youtube_broadcast_status,
    list_youtube_broadcasts,
    end_youtube_broadcast,
]


def register(server: FastMCP) -> None:
    """Register YouTube MCP tools."""
    server.tool()(create_youtube_broadcast)
    server.tool()(end_youtube_broadcast)
    server.tool()(get_youtube_broadcast_status)
    server.tool()(list_youtube_broadcasts)
