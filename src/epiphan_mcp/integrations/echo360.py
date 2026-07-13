"""Echo360 (EchoVideo) API client for video platform integration.

This module provides an async client for the Echo360 EchoVideo public REST
API, enabling:
- OAuth2 Client Credentials authentication with rotating refresh tokens
- Course / section / media listing
- Media upload via the Capture Intake API (signed S3 URLs)

Echo360 issues access tokens that expire after 1 hour and refresh tokens
that never expire but are SINGLE-USE — every refresh returns a new
access + refresh token pair, so the client persists the latest refresh
token and falls back to a fresh client-credentials grant if a refresh
fails (e.g. the stored refresh token was already consumed).

Regional base URLs (HTTPS only):
- US:     https://echo360.org
- EMEA:   https://echo360.org.uk
- APAC:   https://echo360.org.au
- Canada: https://echo360.ca

NOTE: Echo360 publishes its full endpoint reference only through a
per-institution Swagger UI (``<base>/api-documentation``) that requires a
login, so some collection endpoint paths below are best-effort from the
public support articles and REST convention. They are flagged UNVERIFIED
in the method docstrings and should be validated against a live Swagger
instance once credentials are available (same approach as the YuJa
integration's list/channels endpoints).

References:
- https://support.echo360.com/hc/en-us/articles/360038693311-EchoVideo-API-and-SDK-Documentation
- https://support.echo360.com/hc/en-us/articles/360035034252-EchoVideo-Generating-Client-Credentials-to-Obtain-Access-Token
- https://support.echo360.com/hc/en-us/articles/360050166052-EchoVideo-Capture-Intake-API
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from ._upload import stream_file

logger = logging.getLogger(__name__)


@dataclass
class Echo360Token:
    """OAuth2 token with expiration tracking and refresh-token rotation.

    Unlike Panopto's ``OAuthToken``, Echo360 issues a refresh token whose
    value changes on every use — callers must always keep the most
    recently issued one.
    """

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def is_expired(self) -> bool:
        """Check if token has expired (with 60s buffer)."""
        expiry = self.created_at + timedelta(seconds=self.expires_in - 60)
        return datetime.now() >= expiry


class Echo360AuthError(Exception):
    """Authentication error with Echo360 (bad credentials or consumed refresh token)."""

    pass


class Echo360APIError(Exception):
    """API error from Echo360."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class Echo360Client:
    """Async client for the Echo360 EchoVideo public REST API.

    Implements OAuth2 Client Credentials authentication (with refresh-token
    rotation) and provides methods for listing courses/sections/media and
    uploading recordings via the Capture Intake API.

    Example:
        ```python
        async with Echo360Client(
            host="echo360.org",
            client_id="your-client-id",
            client_secret="your-client-secret",
        ) as client:
            courses, truncated = await client.list_courses()
            result = await client.upload_video(
                file_path="/recordings/lecture.mp4",
            )
        ```
    """

    def __init__(
        self,
        host: str,
        client_id: str,
        client_secret: str,
        timeout: float = 30.0,
    ):
        """Initialize Echo360 client.

        Args:
            host: Regional Echo360 hostname (e.g., "echo360.org",
                "echo360.org.uk", "echo360.org.au", "echo360.ca")
            client_id: OAuth2 client ID from Institution Settings > Integration
            client_secret: OAuth2 client secret (shown once at creation)
            timeout: Request timeout in seconds
        """
        self.host = host
        self.client_id = client_id
        self.client_secret = client_secret

        # Echo360 is a hosted SaaS — HTTPS only.
        self.base_url = f"https://{host}"
        self.api_base = f"{self.base_url}/public/api/v1"
        # UNVERIFIED path: docs expose only the Swagger operation ID
        # ``oauth2access_token``; the literal URL is rendered client-side.
        self.token_url = f"{self.base_url}/oauth2/access_token"

        self._token: Echo360Token | None = None
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def __aenter__(self) -> "Echo360Client":
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
        """Ensure we have a valid OAuth token, refreshing or re-granting as needed."""
        if self._token is None:
            await self._authenticate()
            return

        if self._token.is_expired:
            if self._token.refresh_token:
                try:
                    await self._refresh()
                    return
                except Echo360AuthError:
                    # Refresh tokens are single-use; a consumed/rotated-away
                    # token fails here — fall back to a fresh grant.
                    logger.info("Echo360 refresh failed; retrying client-credentials grant")
            await self._authenticate()

    async def _token_request(self, data: dict[str, str]) -> None:
        """POST to the token endpoint and store the resulting token pair."""
        if not self._client:
            raise Echo360AuthError("Client not initialized")

        try:
            response = await self._client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise Echo360AuthError(
                    f"Authentication failed: {response.status_code} - {response.text}"
                )

            token_data = response.json()
            self._token = Echo360Token(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600),
                refresh_token=token_data.get("refresh_token"),
            )

        except httpx.RequestError as e:
            raise Echo360AuthError(f"Authentication request failed: {e}") from e

    async def _authenticate(self) -> None:
        """Perform OAuth2 Client Credentials grant.

        Raises:
            Echo360AuthError: If authentication fails
        """
        await self._token_request(
            {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        )
        logger.info("Echo360 authentication successful")

    async def _refresh(self) -> None:
        """Exchange the stored (single-use) refresh token for a new token pair.

        Raises:
            Echo360AuthError: If the refresh token was already consumed
        """
        assert self._token is not None and self._token.refresh_token is not None
        await self._token_request(
            {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "refresh_token": self._token.refresh_token,
            }
        )
        logger.info("Echo360 token refreshed")

    def _auth_headers(self) -> dict[str, str]:
        """Get authorization headers."""
        if not self._token:
            raise Echo360AuthError("Not authenticated")
        return {
            "Authorization": f"{self._token.token_type} {self._token.access_token}",
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
            endpoint: API endpoint path (relative to /public/api/v1)
            **kwargs: Additional httpx request arguments

        Returns:
            JSON response data

        Raises:
            Echo360AuthError: On 401/403
            Echo360APIError: On any other request failure (429 carries a
                rate-limit hint — Echo360 allows 120 requests/minute)
        """
        if not self._client:
            raise Echo360APIError("Client not initialized")

        await self._ensure_authenticated()

        url = urljoin(self.api_base + "/", endpoint.lstrip("/"))

        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())

        try:
            response = await self._client.request(method, url, headers=headers, **kwargs)

            if response.status_code in (401, 403):
                raise Echo360AuthError(
                    f"Authentication failed: {response.status_code} - {response.text}"
                )

            if response.status_code == 429:
                raise Echo360APIError(
                    f"Rate limit exceeded (Echo360 allows 120 requests/minute) - {response.text}",
                    status_code=429,
                )

            if response.status_code >= 400:
                raise Echo360APIError(
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
            raise Echo360APIError(f"Request failed: {e}") from e

    @staticmethod
    def _extract_page(result: dict[str, Any], *keys: str) -> tuple[list[dict[str, Any]], bool]:
        """Pull the item list and a truncation flag out of a raw response.

        Echo360 responses are paginated (default 100, max 150 per page); this
        returns the current page's items plus whether the envelope indicates
        more pages exist. Fetching further pages stays deferred until the
        page-param names are validated against a live Swagger instance.
        """
        items: list[dict[str, Any]] = []
        for key in ("results", "data", *keys):
            found = result.get(key)
            if isinstance(found, list):
                items = list(found)
                break

        truncated = False
        if result.get("next") or result.get("nextToken") or result.get("hasMore") is True:
            truncated = True
        else:
            for total_key in ("total", "totalResults", "totalCount"):
                total = result.get(total_key)
                if isinstance(total, int) and total > len(items):
                    truncated = True
                    break
        return items, truncated

    # =========================================================================
    # Courses / Sections
    # =========================================================================

    async def list_courses(self) -> tuple[list[dict[str, Any]], bool]:
        """List courses visible to the API client.

        UNVERIFIED endpoint path — inferred from the documented
        ``/sections/{sectionId}/...`` sub-resource and CRUD support for
        courses; validate against a live Swagger instance.

        Returns:
            Tuple of (course objects for the first page, truncated flag)
        """
        result = await self._request("GET", "/courses")
        return self._extract_page(result, "courses")

    async def list_sections(self, course_id: str | None = None) -> tuple[list[dict[str, Any]], bool]:
        """List sections, optionally filtered to one course.

        UNVERIFIED endpoint path and filter param — the
        ``/sections/{sectionId}`` resource itself is confirmed in the LMS
        linking docs; the collection GET and ``courseId`` filter are
        inferred REST convention.

        Args:
            course_id: Optional course ID to filter sections by

        Returns:
            Tuple of (section objects for the first page, truncated flag)
        """
        params: dict[str, Any] = {}
        if course_id:
            params["courseId"] = course_id

        result = await self._request("GET", "/sections", params=params)
        return self._extract_page(result, "sections")

    # =========================================================================
    # Media
    # =========================================================================

    async def list_medias(self, search_query: str | None = None) -> tuple[list[dict[str, Any]], bool]:
        """List media items visible to the API client.

        The ``/medias`` resource is documented as GET-only. The search
        filter param name is UNVERIFIED (inferred REST convention).

        Args:
            search_query: Optional search term to filter media by title

        Returns:
            Tuple of (media objects for the first page, truncated flag)
        """
        params: dict[str, Any] = {}
        if search_query:
            params["search"] = search_query

        result = await self._request("GET", "/medias", params=params)
        return self._extract_page(result, "medias")

    async def get_media(self, media_id: str) -> dict[str, Any]:
        """Get details of one media item.

        Args:
            media_id: Echo360 media ID

        Returns:
            Media object
        """
        return await self._request("GET", f"/medias/{media_id}")

    # =========================================================================
    # Upload (Capture Intake API — signed-URL S3 upload)
    # =========================================================================

    async def create_pending_upload(
        self,
        filename: str,
        part_size_bytes: int | None = None,
    ) -> dict[str, Any]:
        """Create a pending capture upload and get signed S3 upload URL(s).

        This is step 1 of the Capture Intake workflow. Signed URLs expire
        after 24 hours; the pending upload entity itself lives 14 days.

        Args:
            filename: Name of the file being uploaded
            part_size_bytes: Optional multipart part size (5 MiB - 5 GiB);
                required for files over 5 GiB

        Returns:
            Pending upload with ID and signed upload URL(s)
        """
        payload: dict[str, Any] = {"fileName": filename}
        if part_size_bytes is not None:
            payload["partSizeInBytes"] = part_size_bytes

        return await self._request("POST", "/pending-capture-uploads", json=payload)

    async def upload_file_to_url(
        self,
        signed_url: str,
        file_path: Path | str,
        content_type: str = "video/mp4",
    ) -> bool:
        """Upload file bytes to a signed S3 URL.

        This is step 2 of the upload workflow — a plain PUT to S3, without
        the Authorization header (the URL itself is pre-signed).

        Args:
            signed_url: Signed S3 upload URL from create_pending_upload
            file_path: Local file path
            content_type: MIME type of the file

        Returns:
            True if upload successful
        """
        if not self._client:
            raise Echo360APIError("Client not initialized")

        file_path = Path(file_path)
        if not file_path.exists():
            raise Echo360APIError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size
        logger.info(f"Uploading {file_path.name} ({file_size} bytes) to Echo360 S3")

        response = await self._client.put(
            signed_url,
            content=stream_file(file_path),
            headers={
                "Content-Type": content_type,
                "Content-Length": str(file_size),
            },
        )

        if response.status_code not in (200, 201):
            raise Echo360APIError(
                f"S3 upload failed: {response.status_code} - {response.text}",
                status_code=response.status_code,
            )

        logger.info(f"Successfully uploaded {file_path.name} to Echo360")
        return True

    async def submit_upload(self, upload_id: str) -> dict[str, Any]:
        """Submit a completed S3 upload so Echo360 begins processing.

        This is step 3 of the Capture Intake workflow.

        Args:
            upload_id: Pending upload ID from create_pending_upload

        Returns:
            Submitted upload status
        """
        return await self._request(
            "POST", "/submitted-capture-uploads", json={"uploadId": upload_id}
        )

    async def get_upload_status(self, upload_id: str) -> dict[str, Any]:
        """Get the status of a capture upload.

        Args:
            upload_id: Pending upload ID

        Returns:
            Upload status object
        """
        return await self._request("GET", f"/pending-capture-uploads/{upload_id}")

    async def upload_video(
        self,
        file_path: Path | str,
        title: str | None = None,
        wait_for_processing: bool = False,
        poll_interval: float = 5.0,
        max_wait: float = 300.0,
    ) -> dict[str, Any]:
        """Complete video upload workflow via the Capture Intake API.

        High-level method that handles the full signed-URL upload process:
        1. Create a pending capture upload (get signed S3 URL)
        2. PUT file to the signed URL
        3. Submit the upload to start processing
        4. Optionally poll until processing finishes

        Args:
            file_path: Local video file path
            title: Optional media title (defaults to filename)
            wait_for_processing: Wait for Echo360 to finish processing
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait for processing

        Returns:
            Final upload status
        """
        file_path = Path(file_path)
        filename = f"{title}{file_path.suffix}" if title else file_path.name

        # Step 1: Create pending upload with signed URL(s)
        pending = await self.create_pending_upload(filename=filename)
        # `or`-chain (not nested .get defaults) so an explicit JSON null
        # falls through instead of becoming the string "None".
        upload_id = str(pending.get("uploadId") or pending.get("id") or "")
        signed_url = pending.get("uploadUrl") or pending.get("url", "")
        if not upload_id or not signed_url:
            raise Echo360APIError(f"Pending upload missing uploadId/uploadUrl: {pending}")

        logger.info(f"Created Echo360 pending upload {upload_id}")

        # Step 2: PUT file bytes to signed URL
        await self.upload_file_to_url(signed_url, file_path)

        # Step 3: Submit for processing
        await self.submit_upload(upload_id)
        logger.info(f"Submitted Echo360 upload {upload_id} for processing")

        # Step 4: Optionally wait for processing
        if wait_for_processing:
            elapsed = 0.0
            while elapsed < max_wait:
                status = await self.get_upload_status(upload_id)
                state = str(status.get("state") or status.get("status") or "").lower()

                if state in ("complete", "completed", "done"):
                    logger.info(f"Processing complete for {upload_id}")
                    return status
                if state in ("error", "failed"):
                    raise Echo360APIError(f"Processing failed for {upload_id}: {status}")

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            logger.warning(f"Timed out waiting for processing of {upload_id}")

        return await self.get_upload_status(upload_id)
