"""Panopto integration MCP tools.

These tools enable AI assistants to interact with Panopto video platform
for managing recordings, folders, and video uploads in conjunction with
Pearl capture devices.

Environment Variables Required:
    PANOPTO_HOST: Panopto server hostname
    PANOPTO_CLIENT_ID: OAuth2 client ID
    PANOPTO_USERNAME: Service account username
    PANOPTO_PASSWORD: Service account password
    PANOPTO_CLIENT_SECRET: OAuth2 client secret (optional)
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from epiphan_mcp.integrations.panopto import (
    PanoptoAPIError,
    PanoptoAuthError,
    PanoptoClient,
)


@dataclass(frozen=True)
class _PanoptoConfig:
    """Validated Panopto configuration."""

    host: str
    client_id: str
    username: str
    password: str
    client_secret: str | None


def _get_panopto_config() -> _PanoptoConfig:
    """Get Panopto configuration from environment."""
    host = os.environ.get("PANOPTO_HOST")
    client_id = os.environ.get("PANOPTO_CLIENT_ID")
    username = os.environ.get("PANOPTO_USERNAME")
    password = os.environ.get("PANOPTO_PASSWORD")

    missing = []
    if not host:
        missing.append("PANOPTO_HOST")
    if not client_id:
        missing.append("PANOPTO_CLIENT_ID")
    if not username:
        missing.append("PANOPTO_USERNAME")
    if not password:
        missing.append("PANOPTO_PASSWORD")

    if missing:
        raise ValueError(
            f"Missing Panopto configuration. Set environment variables: {', '.join(missing)}"
        )

    # After validation, all required fields are guaranteed non-None
    assert host is not None
    assert client_id is not None
    assert username is not None
    assert password is not None

    return _PanoptoConfig(
        host=host,
        client_id=client_id,
        username=username,
        password=password,
        client_secret=os.environ.get("PANOPTO_CLIENT_SECRET"),
    )


async def list_panopto_folders(
    parent_folder_id: str = "",
    search_query: str = "",
) -> dict[str, Any]:
    """List folders in Panopto.

    Retrieves folders accessible to the configured service account.
    Can filter by parent folder or search by name.

    Args:
        parent_folder_id: Optional parent folder UUID to list children
        search_query: Optional search term to filter folders

    Returns:
        Dict with folders list and count

    Example:
        "List all Panopto folders"
        "Show folders in the Lectures folder"
        "Search Panopto for 'Physics 101'"
    """
    try:
        config = _get_panopto_config()
    except ValueError as e:
        return {"error": str(e), "folders": []}

    try:
        async with PanoptoClient(
            host=config.host,
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            client_secret=config.client_secret,
        ) as client:
            folders = await client.list_folders(
                parent_folder_id=parent_folder_id or None,
                search_query=search_query or None,
            )
            return {
                "folders": folders,
                "count": len(folders),
                "parent_folder_id": parent_folder_id or "root",
            }
    except PanoptoAuthError as e:
        return {"error": f"Authentication failed: {e}", "folders": []}
    except PanoptoAPIError as e:
        return {"error": f"API error: {e}", "folders": []}


async def get_panopto_folder(folder_id: str) -> dict[str, Any]:
    """Get details of a specific Panopto folder.

    Args:
        folder_id: Folder UUID

    Returns:
        Folder details including name, description, parent

    Example:
        "Get details of folder abc-123"
    """
    if not folder_id:
        return {"error": "folder_id is required"}

    try:
        config = _get_panopto_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with PanoptoClient(
            host=config.host,
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            client_secret=config.client_secret,
        ) as client:
            folder = await client.get_folder(folder_id)
            return {"folder": folder}
    except PanoptoAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except PanoptoAPIError as e:
        return {"error": f"API error: {e}"}


async def create_panopto_folder(
    name: str,
    parent_folder_id: str = "",
    description: str = "",
) -> dict[str, Any]:
    """Create a new folder in Panopto.

    Args:
        name: Folder name
        parent_folder_id: Optional parent folder UUID (root if empty)
        description: Optional folder description

    Returns:
        Created folder details

    Example:
        "Create a Panopto folder called 'Fall 2024 Lectures'"
        "Create a subfolder 'Week 1' in folder abc-123"
    """
    if not name:
        return {"error": "name is required"}

    try:
        config = _get_panopto_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with PanoptoClient(
            host=config.host,
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            client_secret=config.client_secret,
        ) as client:
            folder = await client.create_folder(
                name=name,
                parent_folder_id=parent_folder_id or None,
                description=description,
            )
            return {"folder": folder, "message": f"Created folder '{name}'"}
    except PanoptoAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except PanoptoAPIError as e:
        return {"error": f"API error: {e}"}


async def list_panopto_sessions(
    folder_id: str = "",
    search_query: str = "",
) -> dict[str, Any]:
    """List sessions (recordings) in Panopto.

    Args:
        folder_id: Optional folder UUID to filter sessions
        search_query: Optional search term

    Returns:
        Dict with sessions list and count

    Example:
        "List all Panopto recordings"
        "Show sessions in folder abc-123"
        "Search Panopto sessions for 'Chemistry'"
    """
    try:
        config = _get_panopto_config()
    except ValueError as e:
        return {"error": str(e), "sessions": []}

    try:
        async with PanoptoClient(
            host=config.host,
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            client_secret=config.client_secret,
        ) as client:
            sessions = await client.list_sessions(
                folder_id=folder_id or None,
                search_query=search_query or None,
            )
            return {
                "sessions": sessions,
                "count": len(sessions),
                "folder_id": folder_id or "all",
            }
    except PanoptoAuthError as e:
        return {"error": f"Authentication failed: {e}", "sessions": []}
    except PanoptoAPIError as e:
        return {"error": f"API error: {e}", "sessions": []}


async def get_panopto_session(session_id: str) -> dict[str, Any]:
    """Get details of a specific Panopto session.

    Args:
        session_id: Session UUID

    Returns:
        Session details including name, duration, folder, streams

    Example:
        "Get details of Panopto session abc-123"
    """
    if not session_id:
        return {"error": "session_id is required"}

    try:
        config = _get_panopto_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with PanoptoClient(
            host=config.host,
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            client_secret=config.client_secret,
        ) as client:
            session = await client.get_session(session_id)
            return {"session": session}
    except PanoptoAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except PanoptoAPIError as e:
        return {"error": f"API error: {e}"}


async def create_panopto_session(
    folder_id: str,
    name: str,
    description: str = "",
) -> dict[str, Any]:
    """Create a new session (recording placeholder) in Panopto.

    Creates an empty session that can receive uploaded video content.

    Args:
        folder_id: Target folder UUID
        name: Session name
        description: Optional session description

    Returns:
        Created session details

    Example:
        "Create a Panopto session called 'Lecture 5' in folder abc-123"
    """
    if not folder_id:
        return {"error": "folder_id is required"}
    if not name:
        return {"error": "name is required"}

    try:
        config = _get_panopto_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with PanoptoClient(
            host=config.host,
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            client_secret=config.client_secret,
        ) as client:
            session = await client.create_session(
                folder_id=folder_id,
                name=name,
                description=description,
            )
            return {"session": session, "message": f"Created session '{name}'"}
    except PanoptoAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except PanoptoAPIError as e:
        return {"error": f"API error: {e}"}


async def upload_to_panopto(
    folder_id: str,
    file_path: str,
    session_name: str = "",
    wait_for_processing: bool = False,
) -> dict[str, Any]:
    """Upload a video file to Panopto.

    Handles the complete upload workflow:
    1. Creates upload session
    2. Uploads file to S3
    3. Signals upload complete
    4. Optionally waits for processing

    Args:
        folder_id: Target folder UUID
        file_path: Local path to video file
        session_name: Optional session name (defaults to filename)
        wait_for_processing: Wait for Panopto to finish processing

    Returns:
        Upload status and session details

    Example:
        "Upload /recordings/lecture.mp4 to Panopto folder abc-123"
        "Upload the latest recording to Panopto and wait for processing"
    """
    if not folder_id:
        return {"error": "folder_id is required"}
    if not file_path:
        return {"error": "file_path is required"}

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        config = _get_panopto_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with PanoptoClient(
            host=config.host,
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            client_secret=config.client_secret,
        ) as client:
            result = await client.upload_video(
                folder_id=folder_id,
                file_path=path,
                session_name=session_name or None,
                wait_for_processing=wait_for_processing,
            )
            return {
                "upload": result,
                "message": f"Uploaded {path.name} to Panopto",
                "file_size": path.stat().st_size,
            }
    except PanoptoAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except PanoptoAPIError as e:
        return {"error": f"API error: {e}"}


async def get_panopto_upload_status(upload_id: str) -> dict[str, Any]:
    """Check the status of a Panopto upload.

    Args:
        upload_id: Upload session ID

    Returns:
        Upload status including processing state

    Example:
        "Check status of Panopto upload abc-123"
    """
    if not upload_id:
        return {"error": "upload_id is required"}

    try:
        config = _get_panopto_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with PanoptoClient(
            host=config.host,
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            client_secret=config.client_secret,
        ) as client:
            status = await client.get_upload_status(upload_id)

            # Map state codes to readable names
            state_names = {
                0: "Created",
                1: "Uploading",
                2: "UploadComplete",
                3: "Processing",
                4: "Complete",
                5: "Error",
            }
            state_code = status.get("State", -1)
            state_name = state_names.get(state_code, f"Unknown ({state_code})")

            return {
                "upload_id": upload_id,
                "state": state_name,
                "state_code": state_code,
                "details": status,
            }
    except PanoptoAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except PanoptoAPIError as e:
        return {"error": f"API error: {e}"}


async def delete_panopto_session(session_id: str) -> dict[str, Any]:
    """Delete a session from Panopto.

    Args:
        session_id: Session UUID to delete

    Returns:
        Confirmation of deletion

    Example:
        "Delete Panopto session abc-123"
    """
    if not session_id:
        return {"error": "session_id is required"}

    try:
        config = _get_panopto_config()
    except ValueError as e:
        return {"error": str(e)}

    try:
        async with PanoptoClient(
            host=config.host,
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            client_secret=config.client_secret,
        ) as client:
            await client.delete_session(session_id)
            return {"message": f"Deleted session {session_id}", "success": True}
    except PanoptoAuthError as e:
        return {"error": f"Authentication failed: {e}"}
    except PanoptoAPIError as e:
        return {"error": f"API error: {e}"}


# Tool registry for MCP server registration
PANOPTO_TOOLS = [
    list_panopto_folders,
    get_panopto_folder,
    create_panopto_folder,
    list_panopto_sessions,
    get_panopto_session,
    create_panopto_session,
    upload_to_panopto,
    get_panopto_upload_status,
    delete_panopto_session,
]


def register(server: FastMCP) -> None:
    """Register Panopto MCP tools."""
    server.tool()(create_panopto_folder)
    server.tool()(create_panopto_session)
    server.tool()(delete_panopto_session)
    server.tool()(get_panopto_folder)
    server.tool()(get_panopto_session)
    server.tool()(get_panopto_upload_status)
    server.tool()(list_panopto_folders)
    server.tool()(list_panopto_sessions)
    server.tool()(upload_to_panopto)
