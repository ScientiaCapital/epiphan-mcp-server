"""Panopto API client for video platform integration.

This module provides an async client for the Panopto REST API, enabling:
- OAuth2 authentication (Password Grant for server applications)
- Session/recording management
- Folder organization
- Video upload via S3

Authentication uses OAuth2 Password Grant flow as recommended for
server-side applications without user interaction.

Reference: https://support.panopto.com/s/article/oauth2-for-services
"""

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


@dataclass
class OAuthToken:
    """OAuth2 token with expiration tracking."""

    access_token: str
    token_type: str
    expires_in: int
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def is_expired(self) -> bool:
        """Check if token has expired (with 60s buffer)."""
        expiry = self.created_at + timedelta(seconds=self.expires_in - 60)
        return datetime.now() >= expiry


class PanoptoAuthError(Exception):
    """Authentication error with Panopto."""

    pass


class PanoptoAPIError(Exception):
    """API error from Panopto."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class PanoptoClient:
    """Async client for Panopto REST API.

    Implements OAuth2 Password Grant authentication and provides methods
    for managing sessions, folders, and video uploads.

    Example:
        ```python
        async with PanoptoClient(
            host="panopto.university.edu",
            client_id="your-client-id",
            username="service@university.edu",
            password="secure-password"
        ) as client:
            folders = await client.list_folders()
            session = await client.create_session(
                folder_id="folder-uuid",
                name="Lecture Recording"
            )
        ```
    """

    def __init__(
        self,
        host: str,
        client_id: str,
        username: str,
        password: str,
        client_secret: str | None = None,
        use_https: bool = True,
        timeout: float = 30.0,
    ):
        """Initialize Panopto client.

        Args:
            host: Panopto server hostname (e.g., "panopto.university.edu")
            client_id: OAuth2 client ID from Panopto admin
            username: Service account username
            password: Service account password
            client_secret: OAuth2 client secret (optional for public clients)
            use_https: Use HTTPS (strongly recommended)
            timeout: Request timeout in seconds
        """
        self.host = host
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password

        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{host}"
        self.api_base = f"{self.base_url}/api/v1"
        self.upload_base = f"{self.base_url}/Panopto/Services/PublicAPI/REST"
        self.token_url = f"{self.base_url}/Panopto/oauth2/connect/token"

        self._token: OAuthToken | None = None
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def __aenter__(self) -> "PanoptoClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self._timeout)
        await self._ensure_authenticated()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid OAuth token."""
        if self._token is None or self._token.is_expired:
            await self._authenticate()

    async def _authenticate(self) -> None:
        """Perform OAuth2 Password Grant authentication.

        Raises:
            PanoptoAuthError: If authentication fails
        """
        if not self._client:
            raise PanoptoAuthError("Client not initialized")

        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": self.username,
            "password": self.password,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        try:
            response = await self._client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error_detail = response.text
                raise PanoptoAuthError(
                    f"Authentication failed: {response.status_code} - {error_detail}"
                )

            token_data = response.json()
            self._token = OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600),
            )
            logger.info("Panopto authentication successful")

        except httpx.RequestError as e:
            raise PanoptoAuthError(f"Authentication request failed: {e}") from e

    def _auth_headers(self) -> dict[str, str]:
        """Get authorization headers."""
        if not self._token:
            raise PanoptoAuthError("Not authenticated")
        return {
            "Authorization": f"{self._token.token_type} {self._token.access_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        base: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make authenticated API request.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            base: Base URL (defaults to api_base)
            **kwargs: Additional httpx request arguments

        Returns:
            JSON response data

        Raises:
            PanoptoAPIError: If request fails
        """
        if not self._client:
            raise PanoptoAPIError("Client not initialized")

        await self._ensure_authenticated()

        base_url = base or self.api_base
        url = urljoin(base_url + "/", endpoint.lstrip("/"))

        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())

        try:
            response = await self._client.request(method, url, headers=headers, **kwargs)

            if response.status_code >= 400:
                raise PanoptoAPIError(
                    f"API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                )

            if response.status_code == 204:
                return {"success": True}

            result: dict[str, Any] = response.json()
            return result

        except httpx.RequestError as e:
            raise PanoptoAPIError(f"Request failed: {e}") from e

    # =========================================================================
    # Folder Management
    # =========================================================================

    async def list_folders(
        self,
        parent_folder_id: str | None = None,
        search_query: str | None = None,
    ) -> list[dict[str, Any]]:
        """List folders accessible to the authenticated user.

        Args:
            parent_folder_id: Filter to children of this folder
            search_query: Search folders by name

        Returns:
            List of folder objects
        """
        params: dict[str, Any] = {}
        if parent_folder_id:
            params["parentFolderId"] = parent_folder_id
        if search_query:
            params["searchQuery"] = search_query

        result = await self._request("GET", "/folders", params=params)
        folders: list[dict[str, Any]] = result.get("Results", [])
        return folders

    async def get_folder(self, folder_id: str) -> dict[str, Any]:
        """Get folder details.

        Args:
            folder_id: Folder UUID

        Returns:
            Folder object
        """
        return await self._request("GET", f"/folders/{folder_id}")

    async def create_folder(
        self,
        name: str,
        parent_folder_id: str | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a new folder.

        Args:
            name: Folder name
            parent_folder_id: Parent folder UUID (None for root)
            description: Folder description

        Returns:
            Created folder object
        """
        data: dict[str, Any] = {"Name": name}
        if parent_folder_id:
            data["ParentFolder"] = parent_folder_id
        if description:
            data["Description"] = description

        return await self._request("POST", "/folders", json=data)

    async def get_folder_sessions(
        self,
        folder_id: str,
        sort_field: str = "CreatedDate",
        sort_order: str = "Desc",
    ) -> list[dict[str, Any]]:
        """Get sessions in a folder.

        Args:
            folder_id: Folder UUID
            sort_field: Field to sort by
            sort_order: Sort direction (Asc/Desc)

        Returns:
            List of session objects
        """
        params = {"sortField": sort_field, "sortOrder": sort_order}
        result = await self._request("GET", f"/folders/{folder_id}/sessions", params=params)
        sessions: list[dict[str, Any]] = result.get("Results", [])
        return sessions

    # =========================================================================
    # Session Management
    # =========================================================================

    async def list_sessions(
        self,
        folder_id: str | None = None,
        search_query: str | None = None,
    ) -> list[dict[str, Any]]:
        """List sessions accessible to the authenticated user.

        Args:
            folder_id: Filter to sessions in this folder
            search_query: Search sessions by name

        Returns:
            List of session objects
        """
        params: dict[str, Any] = {}
        if folder_id:
            params["folderId"] = folder_id
        if search_query:
            params["searchQuery"] = search_query

        result = await self._request("GET", "/sessions", params=params)
        sessions: list[dict[str, Any]] = result.get("Results", [])
        return sessions

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Get session details.

        Args:
            session_id: Session UUID

        Returns:
            Session object with full details
        """
        return await self._request("GET", f"/sessions/{session_id}")

    async def create_session(
        self,
        folder_id: str,
        name: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a new session (recording placeholder).

        Args:
            folder_id: Target folder UUID
            name: Session name
            description: Session description

        Returns:
            Created session object
        """
        data = {
            "FolderId": folder_id,
            "Name": name,
            "Description": description,
        }
        return await self._request("POST", "/sessions", json=data)

    async def update_session(
        self,
        session_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update session metadata.

        Args:
            session_id: Session UUID
            name: New name (optional)
            description: New description (optional)

        Returns:
            Updated session object
        """
        data: dict[str, Any] = {}
        if name is not None:
            data["Name"] = name
        if description is not None:
            data["Description"] = description

        return await self._request("PUT", f"/sessions/{session_id}", json=data)

    async def delete_session(self, session_id: str) -> dict[str, Any]:
        """Delete a session.

        Args:
            session_id: Session UUID

        Returns:
            Success confirmation
        """
        return await self._request("DELETE", f"/sessions/{session_id}")

    # =========================================================================
    # Upload Management (S3-based)
    # =========================================================================

    async def create_upload_session(self, folder_id: str) -> dict[str, Any]:
        """Create an upload session to get S3 upload target.

        This initiates the upload workflow:
        1. Call this to get UploadTarget (S3 URL)
        2. Upload file to S3 using the provided URL
        3. Call complete_upload() when done

        Args:
            folder_id: Target folder UUID

        Returns:
            Upload session with SessionId, UploadTarget, State
        """
        return await self._request(
            "POST",
            "/sessionUpload",
            base=self.upload_base,
            json={"FolderId": folder_id},
        )

    async def get_upload_status(self, upload_id: str) -> dict[str, Any]:
        """Get upload session status.

        Args:
            upload_id: Upload session ID

        Returns:
            Upload status with State field
        """
        return await self._request(
            "GET",
            f"/sessionUpload/{upload_id}",
            base=self.upload_base,
        )

    async def complete_upload(self, upload_id: str) -> dict[str, Any]:
        """Mark upload as complete to trigger processing.

        Args:
            upload_id: Upload session ID

        Returns:
            Updated upload status
        """
        return await self._request(
            "PUT",
            f"/sessionUpload/{upload_id}",
            base=self.upload_base,
            json={"State": 1},  # 1 = UploadComplete
        )

    async def cancel_upload(self, upload_id: str) -> dict[str, Any]:
        """Cancel an upload session.

        Args:
            upload_id: Upload session ID

        Returns:
            Success confirmation
        """
        return await self._request(
            "DELETE",
            f"/sessionUpload/{upload_id}",
            base=self.upload_base,
        )

    async def upload_file_to_s3(
        self,
        upload_target: str,
        file_path: Path | str,
        content_type: str = "video/mp4",
    ) -> bool:
        """Upload file to S3 target URL.

        This is step 2 of the upload workflow - uploads directly to S3.

        Args:
            upload_target: S3 upload URL from create_upload_session
            file_path: Local file path
            content_type: MIME type of the file

        Returns:
            True if upload successful
        """
        if not self._client:
            raise PanoptoAPIError("Client not initialized")

        file_path = Path(file_path)
        if not file_path.exists():
            raise PanoptoAPIError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size
        logger.info(f"Uploading {file_path.name} ({file_size} bytes) to Panopto S3")

        # httpx.AsyncClient requires an async byte stream — a plain file
        # object is a sync iterable and raises at request time.
        async def _stream(chunk_size: int = 1024 * 1024) -> Any:
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    yield chunk

        response = await self._client.put(
            upload_target,
            content=_stream(),
            headers={
                "Content-Type": content_type,
                "Content-Length": str(file_size),
            },
        )

        if response.status_code not in (200, 201):
            raise PanoptoAPIError(
                f"S3 upload failed: {response.status_code} - {response.text}",
                status_code=response.status_code,
            )

        logger.info(f"Successfully uploaded {file_path.name} to Panopto")
        return True

    async def upload_video(
        self,
        folder_id: str,
        file_path: Path | str,
        session_name: str | None = None,
        wait_for_processing: bool = False,
        poll_interval: float = 5.0,
        max_wait: float = 300.0,
    ) -> dict[str, Any]:
        """Complete video upload workflow.

        High-level method that handles the full upload process:
        1. Create upload session
        2. Upload file to S3
        3. Mark upload complete
        4. Optionally wait for processing

        Args:
            folder_id: Target folder UUID
            file_path: Local video file path
            session_name: Optional session name (defaults to filename)
            wait_for_processing: Wait for Panopto to finish processing
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait for processing

        Returns:
            Final upload status
        """
        file_path = Path(file_path)
        if session_name is None:
            session_name = file_path.stem

        # Step 1: Create upload session
        upload = await self.create_upload_session(folder_id)
        upload_id = upload["ID"]
        upload_target = upload["UploadTarget"]

        logger.info(f"Created upload session {upload_id}")

        try:
            # Step 2: Upload to S3
            await self.upload_file_to_s3(upload_target, file_path)

            # Step 3: Mark complete
            await self.complete_upload(upload_id)
            logger.info(f"Marked upload {upload_id} as complete")

            # Step 4: Optionally wait for processing
            if wait_for_processing:
                elapsed = 0.0
                while elapsed < max_wait:
                    status = await self.get_upload_status(upload_id)
                    state = status.get("State", 0)

                    # State 4 = Complete, State 5 = Error
                    if state == 4:
                        logger.info(f"Processing complete for {upload_id}")
                        return status
                    elif state == 5:
                        raise PanoptoAPIError(f"Processing failed for {upload_id}: {status}")

                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

                logger.warning(f"Timed out waiting for processing of {upload_id}")

            return await self.get_upload_status(upload_id)

        except Exception:
            # Try to cancel on error (suppress failures during cleanup)
            with contextlib.suppress(Exception):
                await self.cancel_upload(upload_id)
            raise

    # =========================================================================
    # User Management
    # =========================================================================

    async def search_users(self, search_query: str) -> list[dict[str, Any]]:
        """Search for users.

        Args:
            search_query: Search term

        Returns:
            List of matching users
        """
        result = await self._request("GET", "/users/search", params={"searchQuery": search_query})
        users: list[dict[str, Any]] = result.get("Results", [])
        return users

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Get user details.

        Args:
            user_id: User UUID

        Returns:
            User object
        """
        return await self._request("GET", f"/users/{user_id}")
