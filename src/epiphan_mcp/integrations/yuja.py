"""YuJa API client for video platform integration.

This module provides an async client for the YuJa Enterprise Video Platform
REST API, enabling:
- Static token authentication (``authToken`` header on every request)
- Video/media management
- Channel listing
- Video upload via signed S3 URLs (two-step upload flow)

Unlike Panopto's OAuth2 flow, YuJa uses a static API token generated in the
Admin Panel (Platform > API). Epiphan documents the minimum token permissions
required for device integrations.

The upload workflow is:
1. ``create_upload_links()`` — POST to createlinks for a signed S3 URL
2. ``upload_file_to_url()`` — PUT the file bytes to the signed URL
3. ``complete_upload()`` — signal the platform to start processing

References:
- https://support.yuja.com/hc/en-us/articles/360049580714-YuJa-API
- https://www.epiphan.com/userguides/pearl-mini/Content/integrate/CMSadmin/YuJa-registration.htm
"""

import asyncio
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


class YuJaAuthError(Exception):
    """Authentication error with YuJa (invalid or under-privileged token)."""

    pass


class YuJaAPIError(Exception):
    """API error from YuJa."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class YuJaClient:
    """Async client for the YuJa Enterprise Video Platform REST API.

    Authenticates with a static API token passed as the ``authToken``
    header on every request. YuJa only allows HTTPS access.

    Example:
        ```python
        async with YuJaClient(
            host="university.yuja.com",
            auth_token="your-api-token",
        ) as client:
            videos = await client.list_videos()
            result = await client.upload_video(
                user_id="12345",
                file_path="/recordings/lecture.mp4",
            )
        ```
    """

    def __init__(
        self,
        host: str,
        auth_token: str,
        timeout: float = 30.0,
    ):
        """Initialize YuJa client.

        Args:
            host: YuJa service hostname (e.g., "university.yuja.com")
            auth_token: Static API token from the YuJa Admin Panel
            timeout: Request timeout in seconds
        """
        self.host = host
        self.auth_token = auth_token

        # YuJa allows HTTPS only.
        self.base_url = f"https://{host}"
        self.api_base = f"{self.base_url}/services"

        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def __aenter__(self) -> "YuJaClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _auth_headers(self) -> dict[str, str]:
        """Get authentication headers (static token)."""
        return {
            "authToken": self.auth_token,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make authenticated API request.

        Args:
            method: HTTP method
            endpoint: API endpoint path (relative to /services)
            **kwargs: Additional httpx request arguments

        Returns:
            JSON response data

        Raises:
            YuJaAuthError: On 401/403 (invalid or under-privileged token)
            YuJaAPIError: On any other request failure
        """
        if not self._client:
            raise YuJaAPIError("Client not initialized")

        url = urljoin(self.api_base + "/", endpoint.lstrip("/"))

        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())

        try:
            response = await self._client.request(method, url, headers=headers, **kwargs)

            if response.status_code in (401, 403):
                raise YuJaAuthError(
                    f"Authentication failed: {response.status_code} - {response.text}. "
                    "Check the token and its permissions (see Epiphan's minimum "
                    "API token requirements for YuJa)."
                )

            if response.status_code >= 400:
                raise YuJaAPIError(
                    f"API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                )

            if response.status_code == 204 or not response.content:
                return {"success": True}

            result: dict[str, Any] | list[Any] = response.json()
            if isinstance(result, list):
                return {"results": result}
            return result

        except httpx.RequestError as e:
            raise YuJaAPIError(f"Request failed: {e}") from e

    # =========================================================================
    # Video / Media Management
    # =========================================================================

    async def list_videos(self, search_query: str | None = None) -> list[dict[str, Any]]:
        """List videos accessible to the API token.

        Args:
            search_query: Optional search term to filter videos by title

        Returns:
            List of video objects
        """
        params: dict[str, Any] = {}
        if search_query:
            params["search"] = search_query

        result = await self._request("GET", "/media/videos", params=params)
        videos = result.get("results", result.get("videos", []))
        return list(videos)

    async def get_video_metadata(self, video_id: str) -> dict[str, Any]:
        """Get all metadata entries for a video.

        Args:
            video_id: Video ID

        Returns:
            Video metadata object
        """
        return await self._request("GET", f"/media/metadata/{video_id}")

    async def delete_video(self, video_id: str) -> dict[str, Any]:
        """Delete a video.

        Args:
            video_id: Video ID

        Returns:
            Success confirmation
        """
        return await self._request("DELETE", f"/media/videos/{video_id}")

    # =========================================================================
    # Channel Management
    # =========================================================================

    async def list_channels(self) -> list[dict[str, Any]]:
        """List media channels accessible to the API token.

        Returns:
            List of channel objects
        """
        result = await self._request("GET", "/channels")
        channels = result.get("results", result.get("channels", []))
        return list(channels)

    # =========================================================================
    # Upload Management (signed-URL S3 upload)
    # =========================================================================

    async def create_upload_links(
        self,
        user_id: str,
        filename: str,
    ) -> dict[str, Any]:
        """Create an upload session and get signed S3 upload URL(s).

        This is step 1 of the upload workflow.

        Args:
            user_id: YuJa user ID the upload is attributed to
            filename: Name of the file being uploaded

        Returns:
            Upload session with session ID and signed upload URL(s)
        """
        return await self._request(
            "POST",
            f"/media/upload/session/{user_id}/createlinks",
            json={"fileName": filename},
        )

    async def upload_file_to_url(
        self,
        signed_url: str,
        file_path: Path | str,
        content_type: str = "video/mp4",
    ) -> bool:
        """Upload file bytes to a signed S3 URL.

        This is step 2 of the upload workflow — a plain PUT to S3, without
        the authToken header (the URL itself is pre-signed).

        Args:
            signed_url: Signed S3 upload URL from create_upload_links
            file_path: Local file path
            content_type: MIME type of the file

        Returns:
            True if upload successful
        """
        if not self._client:
            raise YuJaAPIError("Client not initialized")

        file_path = Path(file_path)
        if not file_path.exists():
            raise YuJaAPIError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size
        logger.info(f"Uploading {file_path.name} ({file_size} bytes) to YuJa S3")

        # httpx.AsyncClient requires an async byte stream — a plain file
        # object is a sync iterable and raises at request time.
        async def _stream(chunk_size: int = 1024 * 1024) -> Any:
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    yield chunk

        response = await self._client.put(
            signed_url,
            content=_stream(),
            headers={
                "Content-Type": content_type,
                "Content-Length": str(file_size),
            },
        )

        if response.status_code not in (200, 201):
            raise YuJaAPIError(
                f"S3 upload failed: {response.status_code} - {response.text}",
                status_code=response.status_code,
            )

        logger.info(f"Successfully uploaded {file_path.name} to YuJa")
        return True

    async def complete_upload(self, session_id: str) -> dict[str, Any]:
        """Signal that the S3 upload is complete and processing should begin.

        This is step 3 of the upload workflow.

        Args:
            session_id: Upload session ID from create_upload_links

        Returns:
            Updated upload session status
        """
        return await self._request("POST", f"/media/upload/session/{session_id}")

    async def get_upload_status(self, session_id: str) -> dict[str, Any]:
        """Get upload session status.

        Args:
            session_id: Upload session ID

        Returns:
            Upload session status object
        """
        return await self._request("GET", f"/media/upload/session/{session_id}")

    async def upload_video(
        self,
        user_id: str,
        file_path: Path | str,
        title: str | None = None,
        wait_for_processing: bool = False,
        poll_interval: float = 5.0,
        max_wait: float = 300.0,
    ) -> dict[str, Any]:
        """Complete video upload workflow.

        High-level method that handles the full signed-URL upload process:
        1. Create upload session (get signed S3 URL)
        2. PUT file to the signed URL
        3. Signal completion to start processing
        4. Optionally poll until processing finishes

        Args:
            user_id: YuJa user ID the upload is attributed to
            file_path: Local video file path
            title: Optional video title (defaults to filename)
            wait_for_processing: Wait for YuJa to finish processing
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait for processing

        Returns:
            Final upload session status
        """
        file_path = Path(file_path)
        filename = f"{title}{file_path.suffix}" if title else file_path.name

        # Step 1: Create upload session with signed URL(s)
        session = await self.create_upload_links(user_id=user_id, filename=filename)
        # `or`-chain (not nested .get defaults) so an explicit JSON null
        # falls through instead of becoming the string "None".
        session_id = str(session.get("sessionId") or session.get("id") or "")
        signed_url = session.get("uploadUrl") or session.get("url", "")
        if not session_id or not signed_url:
            raise YuJaAPIError(f"Upload session missing sessionId/uploadUrl: {session}")

        logger.info(f"Created YuJa upload session {session_id}")

        # Step 2: PUT file bytes to signed URL
        await self.upload_file_to_url(signed_url, file_path)

        # Step 3: Signal completion
        await self.complete_upload(session_id)
        logger.info(f"Marked YuJa upload {session_id} as complete")

        # Step 4: Optionally wait for processing
        if wait_for_processing:
            elapsed = 0.0
            while elapsed < max_wait:
                status = await self.get_upload_status(session_id)
                state = str(status.get("state") or status.get("status") or "").lower()

                if state in ("complete", "completed", "done"):
                    logger.info(f"Processing complete for {session_id}")
                    return status
                if state in ("error", "failed"):
                    raise YuJaAPIError(f"Processing failed for {session_id}: {status}")

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            logger.warning(f"Timed out waiting for processing of {session_id}")

        return await self.get_upload_status(session_id)
