"""Kaltura integration MCP tools.

These tools enable AI assistants to interact with Kaltura video platform
for managing recordings, categories, and video uploads in conjunction with
Pearl capture devices.

Kaltura is the largest video platform in the education market, used by
thousands of universities and enterprises worldwide for lecture capture,
video management, and content delivery.

Environment Variables Required:
    KALTURA_PARTNER_ID: Kaltura Partner ID (numeric)
    KALTURA_APP_TOKEN_ID: Application token ID (starts with 0_)
    KALTURA_APP_TOKEN: Application token secret
    KALTURA_SERVICE_URL: Kaltura API URL (optional, defaults to kaltura.com)
    KALTURA_USER_ID: Service account user ID (optional)
"""

import os
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

from epiphan_mcp.integrations.kaltura import (
    KalturaAPIError,
    KalturaAuthError,
    KalturaClient,
)


def _get_kaltura_config() -> dict[str, str | int]:
    """Get Kaltura configuration from environment."""
    partner_id_str = os.environ.get("KALTURA_PARTNER_ID")
    app_token_id = os.environ.get("KALTURA_APP_TOKEN_ID")
    app_token = os.environ.get("KALTURA_APP_TOKEN")

    missing = []
    if not partner_id_str:
        missing.append("KALTURA_PARTNER_ID")
    if not app_token_id:
        missing.append("KALTURA_APP_TOKEN_ID")
    if not app_token:
        missing.append("KALTURA_APP_TOKEN")

    if missing:
        raise ValueError(
            f"Missing Kaltura configuration. Set environment variables: {', '.join(missing)}"
        )

    try:
        partner_id = int(partner_id_str)  # type: ignore
    except ValueError as err:
        raise ValueError("KALTURA_PARTNER_ID must be a valid integer") from err

    return {
        "partner_id": partner_id,
        "app_token_id": app_token_id,  # type: ignore
        "app_token": app_token,  # type: ignore
        "user_id": os.environ.get("KALTURA_USER_ID", ""),
        "service_url": os.environ.get("KALTURA_SERVICE_URL", "https://www.kaltura.com"),
    }


async def list_kaltura_categories(
    parent_id: int | None = None,
    page_size: int = 50,
    page_index: int = 1,
) -> dict:
    """List categories (folders) in Kaltura.

    Retrieves categories accessible to the configured service account.
    Categories are used to organize video content hierarchically.

    Args:
        parent_id: Optional parent category ID to list children (None for all)
        page_size: Number of results per page (default 50, max 500)
        page_index: Page number, 1-based (default 1)

    Returns:
        Dict with categories list and count

    Example:
        "List all Kaltura categories"
        "Show subcategories of category 12345"
        "Get first 100 Kaltura folders"
    """
    try:
        config = _get_kaltura_config()
    except ValueError as e:
        return {"error": str(e), "categories": []}

    try:
        async with KalturaClient(**config) as client:  # type: ignore
            categories = await client.list_categories(
                parent_id=parent_id,
                page_size=page_size,
                page_index=page_index,
            )
            return {
                "categories": categories,
                "count": len(categories),
                "parent_id": parent_id if parent_id else "root",
                "page": page_index,
            }
    except KalturaAuthError as e:
        return {"error": f"Authentication failed: {e}", "categories": []}
    except KalturaAPIError as e:
        return {"error": f"API error: {e}", "categories": []}


async def get_kaltura_category(category_id: int) -> dict:
    """Get details of a specific Kaltura category.

    Args:
        category_id: Category ID (numeric)

    Returns:
        Category details including name, description, parent, entry count

    Example:
        "Get details of Kaltura category 12345"
    """
    if not category_id:
        return {"error": "category_id is required"}

    try:
        config = _get_kaltura_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with KalturaClient(**config) as client:  # type: ignore
            category = await client.get_category(category_id)
            return {"category": category}
    except KalturaAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except KalturaAPIError as e:
        return {"error": f"API error: {e}"}


async def create_kaltura_category(
    name: str,
    parent_id: int | None = None,
    description: str = "",
) -> dict:
    """Create a new category in Kaltura.

    Args:
        name: Category name
        parent_id: Optional parent category ID (None for root level)
        description: Optional category description

    Returns:
        Created category details

    Example:
        "Create a Kaltura category called 'Fall 2024 Lectures'"
        "Create a subcategory 'Week 1' under category 12345"
    """
    if not name:
        return {"error": "name is required"}

    try:
        config = _get_kaltura_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with KalturaClient(**config) as client:  # type: ignore
            category = await client.create_category(
                name=name,
                parent_id=parent_id,
                description=description,
            )
            return {"category": category, "message": f"Created category '{name}'"}
    except KalturaAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except KalturaAPIError as e:
        return {"error": f"API error: {e}"}


async def list_kaltura_media(
    category_ids: str = "",
    search_text: str = "",
    page_size: int = 50,
    page_index: int = 1,
) -> dict:
    """List media entries (videos) in Kaltura.

    Args:
        category_ids: Comma-separated category IDs to filter by (optional)
        search_text: Search term for name, description, tags (optional)
        page_size: Number of results per page (default 50, max 500)
        page_index: Page number, 1-based (default 1)

    Returns:
        Dict with media entries list and count

    Example:
        "List all Kaltura videos"
        "Show videos in category 12345"
        "Search Kaltura for 'Chemistry lecture'"
    """
    try:
        config = _get_kaltura_config()
    except ValueError as e:
        return {"error": str(e), "media": []}

    # Parse category IDs
    cat_ids: list[int] | None = None
    if category_ids:
        try:
            cat_ids = [int(cid.strip()) for cid in category_ids.split(",")]
        except ValueError:
            return {"error": "category_ids must be comma-separated integers", "media": []}

    try:
        async with KalturaClient(**config) as client:  # type: ignore
            media = await client.list_media(
                category_ids=cat_ids,
                search_text=search_text or None,
                page_size=page_size,
                page_index=page_index,
            )
            return {
                "media": media,
                "count": len(media),
                "category_ids": category_ids or "all",
                "search_text": search_text or None,
                "page": page_index,
            }
    except KalturaAuthError as e:
        return {"error": f"Authentication failed: {e}", "media": []}
    except KalturaAPIError as e:
        return {"error": f"API error: {e}", "media": []}


async def get_kaltura_media(entry_id: str) -> dict:
    """Get details of a specific Kaltura media entry.

    Args:
        entry_id: Media entry ID (alphanumeric, starts with 0_ or 1_)

    Returns:
        Media entry details including name, duration, status, thumbnails

    Example:
        "Get details of Kaltura video 0_abc123"
    """
    if not entry_id:
        return {"error": "entry_id is required"}

    try:
        config = _get_kaltura_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with KalturaClient(**config) as client:  # type: ignore
            media = await client.get_media(entry_id)

            # Map status codes to readable names
            status_names = {
                -2: "Deleted",
                -1: "Error",
                0: "Pending",
                1: "Importing",
                2: "Ready",
                3: "Deleted",
                4: "Pending",
                5: "Moderate",
                6: "Blocked",
                7: "No Content",
            }
            status_code = media.get("status", -1)
            media["status_name"] = status_names.get(status_code, f"Unknown ({status_code})")

            return {"media": media}
    except KalturaAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except KalturaAPIError as e:
        return {"error": f"API error: {e}"}


async def create_kaltura_media(
    name: str,
    description: str = "",
    tags: str = "",
    category_ids: str = "",
) -> dict:
    """Create a new media entry (video placeholder) in Kaltura.

    Creates an empty media entry that can receive uploaded video content.
    Use this before uploading to prepare the metadata.

    Args:
        name: Media entry name/title
        description: Optional description
        tags: Optional comma-separated tags
        category_ids: Optional comma-separated category IDs to assign

    Returns:
        Created media entry details

    Example:
        "Create a Kaltura video entry called 'Lecture 5'"
        "Create a video placeholder in category 12345"
    """
    if not name:
        return {"error": "name is required"}

    try:
        config = _get_kaltura_config()
    except ValueError as e:
        return {"error": str(e)}

    # Parse category IDs
    cat_ids: list[int] | None = None
    if category_ids:
        try:
            cat_ids = [int(cid.strip()) for cid in category_ids.split(",")]
        except ValueError:
            return {"error": "category_ids must be comma-separated integers"}

    try:
        async with KalturaClient(**config) as client:  # type: ignore
            media = await client.create_media_entry(
                name=name,
                description=description,
                tags=tags,
                category_ids=cat_ids,
            )
            return {"media": media, "message": f"Created media entry '{name}'"}
    except KalturaAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except KalturaAPIError as e:
        return {"error": f"API error: {e}"}


async def upload_to_kaltura(
    file_path: str,
    entry_name: str = "",
    description: str = "",
    category_ids: str = "",
    wait_for_ready: bool = False,
) -> dict:
    """Upload a video file to Kaltura.

    Handles the complete upload workflow:
    1. Creates media entry with metadata
    2. Creates upload token
    3. Uploads file in chunks (10MB each)
    4. Attaches content to entry
    5. Optionally waits for transcoding

    Args:
        file_path: Local path to video file
        entry_name: Optional entry name (defaults to filename)
        description: Optional description
        category_ids: Optional comma-separated category IDs
        wait_for_ready: Wait for transcoding to complete (default False)

    Returns:
        Upload result with media entry details

    Example:
        "Upload /recordings/lecture.mp4 to Kaltura"
        "Upload the video to Kaltura category 12345 and wait for processing"
    """
    if not file_path:
        return {"error": "file_path is required"}

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        config = _get_kaltura_config()
    except ValueError as e:
        return {"error": str(e)}

    # Parse category IDs
    cat_ids: list[int] | None = None
    if category_ids:
        try:
            cat_ids = [int(cid.strip()) for cid in category_ids.split(",")]
        except ValueError:
            return {"error": "category_ids must be comma-separated integers"}

    try:
        async with KalturaClient(**config) as client:  # type: ignore
            result = await client.upload_file(
                file_path=path,
                entry_name=entry_name or None,
                description=description,
                category_ids=cat_ids,
                wait_for_ready=wait_for_ready,
            )
            return {
                "media": result,
                "message": f"Uploaded {path.name} to Kaltura",
                "file_size": path.stat().st_size,
                "entry_id": result.get("id"),
            }
    except KalturaAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except KalturaAPIError as e:
        return {"error": f"API error: {e}"}


async def schedule_kaltura_event(
    name: str,
    start_time: str,
    end_time: str,
    entry_id: str = "",
    resource_id: str = "",
    description: str = "",
) -> dict:
    """Schedule a recording event in Kaltura for Pearl auto-record.

    Creates a scheduled event that Pearl devices synced with Kaltura
    will automatically pick up and record.

    Args:
        name: Event name/title
        start_time: Start time in ISO format (e.g., "2024-01-15T10:00:00")
        end_time: End time in ISO format (e.g., "2024-01-15T11:00:00")
        entry_id: Optional existing media entry to associate
        resource_id: Optional recording resource/room ID
        description: Optional event description

    Returns:
        Created schedule event details

    Example:
        "Schedule a Kaltura recording called 'Physics 101' from 10am to 11am"
        "Create a scheduled event for tomorrow at 2pm"
    """
    if not name:
        return {"error": "name is required"}
    if not start_time:
        return {"error": "start_time is required"}
    if not end_time:
        return {"error": "end_time is required"}

    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except ValueError as e:
        return {"error": f"Invalid datetime format: {e}. Use ISO format like '2024-01-15T10:00:00'"}

    if end_dt <= start_dt:
        return {"error": "end_time must be after start_time"}

    try:
        config = _get_kaltura_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with KalturaClient(**config) as client:  # type: ignore
            event = await client.create_schedule_event(
                name=name,
                start_date=start_dt,
                end_date=end_dt,
                entry_id=entry_id or None,
                resource_id=resource_id or None,
                description=description,
            )
            return {
                "event": event,
                "message": f"Scheduled event '{name}'",
                "start_time": start_time,
                "end_time": end_time,
            }
    except KalturaAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except KalturaAPIError as e:
        return {"error": f"API error: {e}"}


async def get_kaltura_upload_status(upload_token_id: str) -> dict:
    """Check the status of a Kaltura upload.

    Args:
        upload_token_id: Upload token ID from upload workflow

    Returns:
        Upload status including bytes uploaded, status

    Example:
        "Check status of Kaltura upload 0_abc123"
    """
    if not upload_token_id:
        return {"error": "upload_token_id is required"}

    try:
        config = _get_kaltura_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with KalturaClient(**config) as client:  # type: ignore
            status = await client.get_upload_status(upload_token_id)

            # Map status codes to readable names
            status_names = {
                0: "Pending",
                1: "PartialUpload",
                2: "FullUpload",
                3: "Closed",
                4: "TimedOut",
                5: "Deleted",
            }
            status_code = status.get("status", -1)
            status_name = status_names.get(status_code, f"Unknown ({status_code})")

            return {
                "upload_token_id": upload_token_id,
                "status": status_name,
                "status_code": status_code,
                "uploaded_bytes": status.get("uploadedFileSize", 0),
                "details": status,
            }
    except KalturaAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except KalturaAPIError as e:
        return {"error": f"API error: {e}"}


# Tool registry for MCP server registration
KALTURA_TOOLS = [
    list_kaltura_categories,
    get_kaltura_category,
    create_kaltura_category,
    list_kaltura_media,
    get_kaltura_media,
    create_kaltura_media,
    upload_to_kaltura,
    schedule_kaltura_event,
    get_kaltura_upload_status,
]


def register(server: FastMCP) -> None:
    """Register Kaltura MCP tools."""
    server.tool()(create_kaltura_category)
    server.tool()(create_kaltura_media)
    server.tool()(get_kaltura_category)
    server.tool()(get_kaltura_media)
    server.tool()(get_kaltura_upload_status)
    server.tool()(list_kaltura_categories)
    server.tool()(list_kaltura_media)
    server.tool()(schedule_kaltura_event)
    server.tool()(upload_to_kaltura)
