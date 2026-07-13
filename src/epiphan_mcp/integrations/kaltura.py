"""Kaltura API client for video platform integration.

This module provides an async client for the Kaltura REST API, enabling:
- KS (Kaltura Session) token authentication via appToken.startSession
- Category/folder management for content organization
- Media entry management for video content
- Chunked upload workflow for large files
- Schedule event creation for Pearl auto-record integration

Authentication uses the Application Token (appToken) method, which is the
recommended approach for server-side applications. The app token is created
in Kaltura KMC (Kaltura Management Console) and provides secure access
without exposing admin secrets directly.

Reference:
- https://developer.kaltura.com/api-docs/VPaaS-API-Getting-Started/application-tokens.html
- https://developer.kaltura.com/api-docs/service/appToken/action/startSession
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class KalturaSession:
    """Kaltura Session (KS) token with expiration tracking."""

    ks: str
    partner_id: int
    expires_in: int
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def is_expired(self) -> bool:
        """Check if session has expired (with 60s buffer)."""
        expiry = self.created_at + timedelta(seconds=self.expires_in - 60)
        return datetime.now() >= expiry


class KalturaAuthError(Exception):
    """Authentication error with Kaltura."""

    pass


class KalturaAPIError(Exception):
    """API error from Kaltura."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


class KalturaClient:
    """Async client for Kaltura REST API.

    Implements Application Token (appToken) authentication and provides methods
    for managing categories, media entries, uploads, and scheduled events.

    Example:
        ```python
        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="your_app_token_value",
            service_url="https://www.kaltura.com"
        ) as client:
            categories = await client.list_categories()
            media = await client.create_media_entry(
                name="Lecture Recording",
                category_ids=[123, 456]
            )
        ```

    Note:
        To create an app token in Kaltura KMC:
        1. Go to Settings > Integration Settings > App Tokens
        2. Create a new token with appropriate permissions
        3. Note the ID and token value for configuration
    """

    def __init__(
        self,
        partner_id: int,
        app_token_id: str,
        app_token: str,
        user_id: str = "",
        service_url: str = "https://www.kaltura.com",
        timeout: float = 30.0,
        session_duration: int = 86400,  # 24 hours
    ):
        """Initialize Kaltura client.

        Args:
            partner_id: Kaltura Partner ID (find in KMC Settings)
            app_token_id: Application token ID (starts with 0_)
            app_token: Application token value (secret)
            user_id: Optional user ID for session (for user-specific operations)
            service_url: Kaltura API base URL
            timeout: Request timeout in seconds
            session_duration: KS token duration in seconds (default 24h)
        """
        self.partner_id = partner_id
        self.app_token_id = app_token_id
        self.app_token = app_token
        self.user_id = user_id
        self.service_url = service_url.rstrip("/")
        self.api_base = f"{self.service_url}/api_v3"
        self.session_duration = session_duration

        self._session: KalturaSession | None = None
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def __aenter__(self) -> "KalturaClient":
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
        """Ensure we have a valid KS token."""
        if self._session is None or self._session.is_expired:
            await self._authenticate()

    async def _authenticate(self) -> None:
        """Perform appToken.startSession authentication.

        The appToken authentication flow:
        1. Generate a widget session (unprivileged KS)
        2. Use widget session + appToken to start a full session
        3. Hash = SHA256(widgetKS + appToken)

        Raises:
            KalturaAuthError: If authentication fails
        """
        if not self._client:
            raise KalturaAuthError("Client not initialized")

        try:
            # Step 1: Get a widget session (unprivileged)
            widget_response = await self._client.post(
                f"{self.api_base}/service/session/action/startWidgetSession",
                data={
                    "widgetId": f"_{self.partner_id}",
                    "format": "1",  # JSON format
                },
            )

            if widget_response.status_code != 200:
                raise KalturaAuthError(f"Widget session failed: {widget_response.status_code}")

            widget_data = widget_response.json()
            if "ks" not in widget_data:
                error_msg = widget_data.get("message", "Unknown error")
                raise KalturaAuthError(f"Widget session failed: {error_msg}")

            widget_ks = widget_data["ks"]

            # Step 2: Generate token hash = SHA256(widgetKS + appToken)
            token_hash = hashlib.sha256((widget_ks + self.app_token).encode()).hexdigest()

            # Step 3: Start app token session
            session_response = await self._client.post(
                f"{self.api_base}/service/appToken/action/startSession",
                data={
                    "id": self.app_token_id,
                    "tokenHash": token_hash,
                    "ks": widget_ks,
                    "userId": self.user_id,
                    "expiry": str(self.session_duration),
                    "format": "1",
                },
            )

            if session_response.status_code != 200:
                raise KalturaAuthError(f"App token session failed: {session_response.status_code}")

            session_data = session_response.json()

            # Check for API error response
            if "objectType" in session_data and session_data["objectType"] == "KalturaAPIException":
                error_msg = session_data.get("message", "Unknown error")
                error_code = session_data.get("code", "UNKNOWN")
                raise KalturaAuthError(f"Authentication failed [{error_code}]: {error_msg}")

            if "ks" not in session_data:
                error_msg = session_data.get("message", "No KS returned")
                raise KalturaAuthError(f"Session creation failed: {error_msg}")

            self._session = KalturaSession(
                ks=session_data["ks"],
                partner_id=self.partner_id,
                expires_in=self.session_duration,
            )
            logger.info("Kaltura authentication successful")

        except httpx.RequestError as e:
            raise KalturaAuthError(f"Authentication request failed: {e}") from e

    async def _request(
        self,
        service: str,
        action: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated API request.

        Args:
            service: Kaltura service name (e.g., "category", "media")
            action: Action to perform (e.g., "list", "get", "add")
            data: Request parameters

        Returns:
            JSON response data

        Raises:
            KalturaAPIError: If request fails
        """
        if not self._client:
            raise KalturaAPIError("Client not initialized")

        await self._ensure_authenticated()

        url = f"{self.api_base}/service/{service}/action/{action}"

        request_data = data.copy() if data else {}
        request_data["ks"] = self._session.ks  # type: ignore
        request_data["format"] = "1"  # JSON format

        try:
            response = await self._client.post(url, data=request_data)

            if response.status_code != 200:
                raise KalturaAPIError(f"API error: {response.status_code} - {response.text}")

            result = response.json()

            # Check for Kaltura API error response
            if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
                error_msg = result.get("message", "Unknown error")
                error_code = result.get("code", "UNKNOWN")
                raise KalturaAPIError(f"[{error_code}] {error_msg}", code=error_code)

            api_result: dict[str, Any] = result
            return api_result

        except httpx.RequestError as e:
            raise KalturaAPIError(f"Request failed: {e}") from e

    # =========================================================================
    # Category Management
    # =========================================================================

    async def list_categories(
        self,
        parent_id: int | None = None,
        page_size: int = 50,
        page_index: int = 1,
    ) -> list[dict[str, Any]]:
        """List categories (folders) in the account.

        Args:
            parent_id: Filter to children of this category (None for all)
            page_size: Results per page (max 500)
            page_index: Page number (1-based)

        Returns:
            List of category objects
        """
        filter_data: dict[str, Any] = {}
        if parent_id is not None:
            filter_data["filter:parentIdEqual"] = parent_id

        filter_data["pager:pageSize"] = page_size
        filter_data["pager:pageIndex"] = page_index

        result = await self._request("category", "list", filter_data)
        categories: list[dict[str, Any]] = result.get("objects", [])
        return categories

    async def get_category(self, category_id: int) -> dict[str, Any]:
        """Get category details.

        Args:
            category_id: Category ID

        Returns:
            Category object
        """
        return await self._request("category", "get", {"id": category_id})

    async def create_category(
        self,
        name: str,
        parent_id: int | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a new category.

        Args:
            name: Category name
            parent_id: Parent category ID (None for root)
            description: Category description

        Returns:
            Created category object
        """
        data: dict[str, Any] = {
            "category:name": name,
        }
        if parent_id is not None:
            data["category:parentId"] = parent_id
        if description:
            data["category:description"] = description

        return await self._request("category", "add", data)

    # =========================================================================
    # Media Entry Management
    # =========================================================================

    async def list_media(
        self,
        category_ids: list[int] | None = None,
        search_text: str | None = None,
        page_size: int = 50,
        page_index: int = 1,
    ) -> list[dict[str, Any]]:
        """List media entries.

        Args:
            category_ids: Filter by category IDs
            search_text: Search in name, description, tags
            page_size: Results per page (max 500)
            page_index: Page number (1-based)

        Returns:
            List of media entry objects
        """
        filter_data: dict[str, Any] = {}

        if category_ids:
            filter_data["filter:categoriesIdsMatchAnd"] = ",".join(str(cid) for cid in category_ids)
        if search_text:
            filter_data["filter:freeText"] = search_text

        filter_data["pager:pageSize"] = page_size
        filter_data["pager:pageIndex"] = page_index

        result = await self._request("media", "list", filter_data)
        entries: list[dict[str, Any]] = result.get("objects", [])
        return entries

    async def get_media(self, entry_id: str) -> dict[str, Any]:
        """Get media entry details.

        Args:
            entry_id: Media entry ID

        Returns:
            Media entry object with full details
        """
        return await self._request("media", "get", {"entryId": entry_id})

    async def create_media_entry(
        self,
        name: str,
        media_type: int = 1,  # VIDEO = 1
        description: str = "",
        tags: str = "",
        category_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Create a new media entry (placeholder for upload).

        Args:
            name: Entry name
            media_type: Media type (1=VIDEO, 2=IMAGE, 5=AUDIO)
            description: Entry description
            tags: Comma-separated tags
            category_ids: Categories to assign

        Returns:
            Created media entry object
        """
        data: dict[str, Any] = {
            "entry:name": name,
            "entry:mediaType": media_type,
        }
        if description:
            data["entry:description"] = description
        if tags:
            data["entry:tags"] = tags
        if category_ids:
            data["entry:categoriesIds"] = ",".join(str(cid) for cid in category_ids)

        return await self._request("media", "add", data)

    # =========================================================================
    # Upload Management
    # =========================================================================

    async def create_upload_token(self) -> dict[str, Any]:
        """Create an upload token for chunked uploads.

        Returns:
            Upload token object with id for subsequent chunks
        """
        return await self._request("uploadToken", "add", {})

    async def upload_chunk(
        self,
        upload_token_id: str,
        file_data: bytes,
        resume: bool = False,
        final_chunk: bool = True,
        resume_at: int = -1,
    ) -> dict[str, Any]:
        """Upload a file chunk to Kaltura.

        Args:
            upload_token_id: Upload token ID from create_upload_token
            file_data: File content bytes
            resume: Whether this is a resume upload
            final_chunk: Whether this is the last chunk
            resume_at: Byte offset to resume from (-1 for auto)

        Returns:
            Upload status
        """
        if not self._client:
            raise KalturaAPIError("Client not initialized")

        await self._ensure_authenticated()

        url = f"{self.api_base}/service/uploadToken/action/upload"

        files = {"fileData": ("upload.bin", file_data)}
        data = {
            "uploadTokenId": upload_token_id,
            "ks": self._session.ks,  # type: ignore
            "format": "1",
            "resume": "1" if resume else "0",
            "finalChunk": "1" if final_chunk else "0",
            "resumeAt": str(resume_at),
        }

        try:
            response = await self._client.post(url, data=data, files=files)

            if response.status_code != 200:
                raise KalturaAPIError(f"Upload failed: {response.status_code}")

            result = response.json()

            if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
                raise KalturaAPIError(
                    f"Upload failed: {result.get('message', 'Unknown error')}",
                    code=result.get("code"),
                )

            upload_result: dict[str, Any] = result
            return upload_result

        except httpx.RequestError as e:
            raise KalturaAPIError(f"Upload request failed: {e}") from e

    async def attach_content_to_entry(
        self,
        entry_id: str,
        upload_token_id: str,
    ) -> dict[str, Any]:
        """Attach uploaded content to a media entry.

        Args:
            entry_id: Media entry ID
            upload_token_id: Upload token with uploaded content

        Returns:
            Updated media entry
        """
        return await self._request(
            "media",
            "addContent",
            {
                "entryId": entry_id,
                "resource:objectType": "KalturaUploadedFileTokenResource",
                "resource:token": upload_token_id,
            },
        )

    async def get_upload_status(self, upload_token_id: str) -> dict[str, Any]:
        """Get upload token status.

        Args:
            upload_token_id: Upload token ID

        Returns:
            Upload token status including uploadedFileSize, status
        """
        return await self._request(
            "uploadToken",
            "get",
            {"uploadTokenId": upload_token_id},
        )

    async def upload_file(
        self,
        file_path: Path | str,
        entry_name: str | None = None,
        description: str = "",
        category_ids: list[int] | None = None,
        chunk_size: int = 10 * 1024 * 1024,  # 10MB chunks
        wait_for_ready: bool = False,
        poll_interval: float = 5.0,
        max_wait: float = 300.0,
    ) -> dict[str, Any]:
        """Complete file upload workflow.

        High-level method that handles the full upload process:
        1. Create media entry
        2. Create upload token
        3. Upload file in chunks
        4. Attach content to entry
        5. Optionally wait for transcoding

        Args:
            file_path: Local file path
            entry_name: Entry name (defaults to filename)
            description: Entry description
            category_ids: Categories to assign
            chunk_size: Size of upload chunks in bytes
            wait_for_ready: Wait for transcoding to complete
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait for transcoding

        Returns:
            Final media entry object
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise KalturaAPIError(f"File not found: {file_path}")

        if entry_name is None:
            entry_name = file_path.stem

        file_size = file_path.stat().st_size
        logger.info(f"Uploading {file_path.name} ({file_size} bytes) to Kaltura")

        # Step 1: Create media entry
        entry = await self.create_media_entry(
            name=entry_name,
            description=description,
            category_ids=category_ids,
        )
        entry_id = entry["id"]
        logger.info(f"Created media entry {entry_id}")

        # Step 2: Create upload token
        token = await self.create_upload_token()
        token_id = token["id"]
        logger.info(f"Created upload token {token_id}")

        try:
            # Step 3: Upload file in chunks
            with open(file_path, "rb") as f:
                bytes_uploaded = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break

                    is_final = len(chunk) < chunk_size or (bytes_uploaded + len(chunk) >= file_size)

                    await self.upload_chunk(
                        upload_token_id=token_id,
                        file_data=chunk,
                        resume=bytes_uploaded > 0,
                        final_chunk=is_final,
                        resume_at=bytes_uploaded,
                    )

                    bytes_uploaded += len(chunk)
                    progress = (bytes_uploaded / file_size) * 100
                    logger.info(f"Upload progress: {progress:.1f}%")

            # Step 4: Attach content to entry
            await self.attach_content_to_entry(entry_id, token_id)
            logger.info(f"Attached content to entry {entry_id}")

            # Step 5: Optionally wait for transcoding
            if wait_for_ready:
                elapsed = 0.0
                while elapsed < max_wait:
                    entry = await self.get_media(entry_id)
                    status = entry.get("status", -1)

                    # Status 2 = READY
                    if status == 2:
                        logger.info(f"Entry {entry_id} is ready")
                        return entry
                    # Status -1 = ERROR, -2 = DELETED
                    elif status in (-1, -2):
                        raise KalturaAPIError(f"Entry processing failed with status {status}")

                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

                logger.warning(f"Timed out waiting for entry {entry_id} to be ready")

            return await self.get_media(entry_id)

        except Exception:
            logger.error(f"Upload failed for entry {entry_id}")
            raise

    # =========================================================================
    # Schedule Event Management (Pearl Integration)
    # =========================================================================

    async def create_schedule_event(
        self,
        name: str,
        start_date: datetime,
        end_date: datetime,
        entry_id: str | None = None,
        resource_id: str | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a scheduled recording event.

        This integrates with Pearl's Kaltura scheduling - when Pearl syncs
        with Kaltura, it will pick up these scheduled events and auto-record.

        Args:
            name: Event name/title
            start_date: Event start time
            end_date: Event end time
            entry_id: Optional media entry to associate
            resource_id: Recording resource/room ID
            description: Event description

        Returns:
            Created schedule event object
        """
        data: dict[str, Any] = {
            "scheduleEvent:objectType": "KalturaRecordScheduleEvent",
            "scheduleEvent:summary": name,
            "scheduleEvent:startDate": int(start_date.timestamp()),
            "scheduleEvent:endDate": int(end_date.timestamp()),
        }

        if description:
            data["scheduleEvent:description"] = description
        if entry_id:
            data["scheduleEvent:templateEntryId"] = entry_id
        if resource_id:
            data["scheduleEvent:resourceId"] = resource_id

        return await self._request("scheduleEvent", "add", data)

    async def list_schedule_events(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        """List scheduled recording events.

        Args:
            start_date: Filter events starting after this time
            end_date: Filter events ending before this time
            page_size: Results per page

        Returns:
            List of schedule event objects
        """
        filter_data: dict[str, Any] = {
            "pager:pageSize": page_size,
        }

        if start_date:
            filter_data["filter:startDateGreaterThanOrEqual"] = int(start_date.timestamp())
        if end_date:
            filter_data["filter:endDateLessThanOrEqual"] = int(end_date.timestamp())

        result = await self._request("scheduleEvent", "list", filter_data)
        events: list[dict[str, Any]] = result.get("objects", [])
        return events
