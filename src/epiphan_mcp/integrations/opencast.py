"""Opencast API client for video platform integration.

This module provides an async client for the Opencast External API and Ingest
Service, enabling:
- Series (course/channel) management for content organization
- Event (recording) management and querying
- Media package ingestion with Dublin Core metadata
- Capture agent scheduling for Pearl auto-record integration

Opencast is an open-source video management system widely used in higher
education for lecture capture, live streaming, and video distribution.

Authentication uses HTTP Basic Auth with admin credentials.

Reference:
- https://docs.opencast.org/develop/developer/api/
- https://docs.opencast.org/develop/developer/api/events-api/
- https://docs.opencast.org/develop/developer/api/series-api/
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpencastAuthError(Exception):
    """Authentication error with Opencast."""

    pass


class OpencastAPIError(Exception):
    """API error from Opencast."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class OpencastClient:
    """Async client for Opencast External API.

    Implements HTTP Basic Auth and provides methods for managing series,
    events, ingestion, and capture scheduling.

    Example:
        ```python
        async with OpencastClient(
            host="opencast.university.edu",
            username="admin",
            password="secret"
        ) as client:
            series = await client.list_series()
            events = await client.list_events(series_id=series[0]["identifier"])
        ```
    """

    host: str
    username: str
    password: str
    use_https: bool = True
    timeout: float = 60.0
    default_series: str = ""

    _client: httpx.AsyncClient | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Set up API URLs."""
        protocol = "https" if self.use_https else "http"
        self.api_base = f"{protocol}://{self.host}/api"
        self.ingest_base = f"{protocol}://{self.host}/ingest"

    async def __aenter__(self) -> "OpencastClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            auth=(self.username, self.password),
        )
        # Verify connection
        await self._verify_connection()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _verify_connection(self) -> None:
        """Verify connection and authentication.

        Raises:
            OpencastAuthError: If authentication fails
            OpencastAPIError: If connection fails
        """
        if not self._client:
            raise OpencastAPIError("Client not initialized")

        try:
            response = await self._client.get(f"{self.api_base}/info/me")
            if response.status_code == 401:
                raise OpencastAuthError("Invalid credentials")
            if response.status_code == 403:
                raise OpencastAuthError("Insufficient permissions")
            if response.status_code != 200:
                raise OpencastAPIError(
                    f"Connection failed: {response.status_code}",
                    status_code=response.status_code,
                )
            logger.info(f"Connected to Opencast at {self.host}")
        except httpx.RequestError as e:
            raise OpencastAPIError(f"Connection failed: {e}") from e

    async def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make authenticated GET request.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            OpencastAPIError: If request fails
        """
        if not self._client:
            raise OpencastAPIError("Client not initialized")

        url = f"{self.api_base}{endpoint}"

        try:
            response = await self._client.get(url, params=params)

            if response.status_code == 401:
                raise OpencastAuthError("Session expired")
            if response.status_code == 404:
                raise OpencastAPIError("Resource not found", status_code=404)
            if response.status_code >= 400:
                raise OpencastAPIError(
                    f"API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                )

            result: dict[str, Any] | list[Any] = response.json()
            return result

        except httpx.RequestError as e:
            raise OpencastAPIError(f"Request failed: {e}") from e

    async def _post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | str:
        """Make authenticated POST request.

        Args:
            endpoint: API endpoint path
            data: Form data
            files: Multipart file data
            json_data: JSON body data

        Returns:
            Response data

        Raises:
            OpencastAPIError: If request fails
        """
        if not self._client:
            raise OpencastAPIError("Client not initialized")

        url = f"{self.api_base}{endpoint}"

        try:
            if json_data:
                response = await self._client.post(url, json=json_data)
            elif files:
                response = await self._client.post(url, data=data, files=files)
            else:
                response = await self._client.post(url, data=data)

            if response.status_code == 401:
                raise OpencastAuthError("Session expired")
            if response.status_code >= 400:
                raise OpencastAPIError(
                    f"API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                )

            # Try JSON, fall back to text
            try:
                result: dict[str, Any] | str = response.json()
                return result
            except Exception:
                return response.text

        except httpx.RequestError as e:
            raise OpencastAPIError(f"Request failed: {e}") from e

    async def _delete(self, endpoint: str) -> bool:
        """Make authenticated DELETE request.

        Args:
            endpoint: API endpoint path

        Returns:
            True if successful

        Raises:
            OpencastAPIError: If request fails
        """
        if not self._client:
            raise OpencastAPIError("Client not initialized")

        url = f"{self.api_base}{endpoint}"

        try:
            response = await self._client.delete(url)

            if response.status_code == 401:
                raise OpencastAuthError("Session expired")
            if response.status_code == 404:
                raise OpencastAPIError("Resource not found", status_code=404)
            if response.status_code >= 400:
                raise OpencastAPIError(
                    f"API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                )

            return True

        except httpx.RequestError as e:
            raise OpencastAPIError(f"Request failed: {e}") from e

    # =========================================================================
    # Series Management
    # =========================================================================

    async def list_series(
        self,
        limit: int = 100,
        offset: int = 0,
        filter_text: str = "",
        sort: str = "title:ASC",
    ) -> list[dict[str, Any]]:
        """List series (courses/channels).

        Args:
            limit: Max results (default 100)
            offset: Pagination offset
            filter_text: Filter by title/description
            sort: Sort order (default "title:ASC")

        Returns:
            List of series objects
        """
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "sort": sort,
        }
        if filter_text:
            params["filter"] = f"title:{filter_text}"

        result = await self._get("/series", params=params)
        return result if isinstance(result, list) else []

    async def get_series(self, series_id: str) -> dict[str, Any]:
        """Get series details.

        Args:
            series_id: Series UUID

        Returns:
            Series object with metadata
        """
        result = await self._get(f"/series/{series_id}")
        return result if isinstance(result, dict) else {}

    async def create_series(
        self,
        title: str,
        description: str = "",
        creator: str = "",
        subject: str = "",
        language: str = "en",
        license: str = "",
        contributor: str = "",
    ) -> dict[str, Any]:
        """Create a new series.

        Args:
            title: Series title
            description: Series description
            creator: Creator name
            subject: Subject/topic
            language: Language code
            license: License identifier
            contributor: Contributor names

        Returns:
            Created series object
        """
        metadata = [
            {
                "flavor": "dublincore/series",
                "fields": [
                    {"id": "title", "value": title},
                    {"id": "description", "value": description},
                    {"id": "creator", "value": [creator] if creator else []},
                    {"id": "subject", "value": subject},
                    {"id": "language", "value": language},
                    {"id": "license", "value": license},
                    {"id": "contributor", "value": [contributor] if contributor else []},
                ],
            }
        ]

        # Opencast expects metadata as JSON string in form data
        import json

        data = {
            "metadata": json.dumps(metadata),
            "acl": json.dumps([]),  # Default ACL
        }

        result = await self._post("/series", data=data)
        return result if isinstance(result, dict) else {"identifier": result}

    # =========================================================================
    # Event Management
    # =========================================================================

    async def list_events(
        self,
        series_id: str = "",
        status: str = "",
        limit: int = 100,
        offset: int = 0,
        sort: str = "start_date:DESC",
    ) -> list[dict[str, Any]]:
        """List events (recordings).

        Args:
            series_id: Filter by series UUID
            status: Filter by status (e.g., "EVENTS.EVENTS.STATUS.PROCESSED")
            limit: Max results
            offset: Pagination offset
            sort: Sort order

        Returns:
            List of event objects
        """
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "sort": sort,
        }

        filters = []
        if series_id:
            filters.append(f"is_part_of:{series_id}")
        if status:
            filters.append(f"status:{status}")
        if filters:
            params["filter"] = ",".join(filters)

        result = await self._get("/events", params=params)
        return result if isinstance(result, list) else []

    async def get_event(self, event_id: str) -> dict[str, Any]:
        """Get event details.

        Args:
            event_id: Event UUID

        Returns:
            Event object with full metadata
        """
        result = await self._get(f"/events/{event_id}")
        return result if isinstance(result, dict) else {}

    async def delete_event(self, event_id: str) -> bool:
        """Delete an event.

        Args:
            event_id: Event UUID

        Returns:
            True if successful
        """
        return await self._delete(f"/events/{event_id}")

    # =========================================================================
    # Ingest Operations
    # =========================================================================

    async def ingest_recording(
        self,
        file_path: Path | str,
        title: str,
        series_id: str = "",
        creator: str = "",
        description: str = "",
        spatial: str = "",
        flavor: str = "presenter/source",
        workflow: str = "fast",
    ) -> dict[str, Any]:
        """Ingest a recording file to Opencast.

        Performs the complete ingest workflow:
        1. Upload media file with Dublin Core metadata
        2. Start processing workflow

        Args:
            file_path: Path to video file
            title: Recording title
            series_id: Target series UUID
            creator: Presenter/creator name
            description: Recording description
            spatial: Location/room
            flavor: Media flavor (default "presenter/source")
            workflow: Processing workflow ID (default "fast")

        Returns:
            Ingest result with workflow instance ID
        """
        if not self._client:
            raise OpencastAPIError("Client not initialized")

        file_path = Path(file_path)
        if not file_path.exists():
            raise OpencastAPIError(f"File not found: {file_path}")

        # Use the addMediaPackage endpoint (simpler than multi-step ingest)
        # Note: Dublin Core metadata is passed as form fields, not XML
        url = f"{self.ingest_base}/addMediaPackage/{workflow}"

        try:
            with open(file_path, "rb") as f:
                files = {
                    "BODY": (file_path.name, f, "video/mp4"),
                }
                data = {
                    "flavor": flavor,
                    "title": title,
                    "creator": creator,
                    "description": description,
                    "isPartOf": series_id or self.default_series,
                    "spatial": spatial,
                }

                logger.info(f"Ingesting {file_path.name} to Opencast")
                response = await self._client.post(
                    url,
                    data=data,
                    files=files,
                    timeout=300.0,  # Extended timeout for upload
                )

                if response.status_code >= 400:
                    raise OpencastAPIError(
                        f"Ingest failed: {response.status_code} - {response.text}",
                        status_code=response.status_code,
                    )

                # Response is XML with workflow instance ID
                return {
                    "success": True,
                    "workflow_id": response.text.strip(),
                    "file": file_path.name,
                    "title": title,
                }

        except httpx.RequestError as e:
            raise OpencastAPIError(f"Ingest request failed: {e}") from e

    async def get_ingest_status(self, workflow_id: str) -> dict[str, Any]:
        """Get status of an ingest workflow.

        Args:
            workflow_id: Workflow instance ID from ingest

        Returns:
            Workflow status including state and progress
        """
        # Query workflow API
        result = await self._get(f"/workflow/{workflow_id}")
        if isinstance(result, dict):
            return {
                "workflow_id": workflow_id,
                "state": result.get("state", "UNKNOWN"),
                "operations": result.get("operations", []),
            }
        return {"workflow_id": workflow_id, "state": "UNKNOWN"}

    # =========================================================================
    # Capture Agent Scheduling
    # =========================================================================

    async def schedule_capture(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        capture_agent: str,
        series_id: str = "",
        creator: str = "",
        description: str = "",
        spatial: str = "",
        inputs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Schedule a capture event for a Pearl device.

        Creates a scheduled event that Pearl (registered as capture agent)
        will automatically pick up and record.

        Args:
            title: Event title
            start_time: Scheduled start time
            end_time: Scheduled end time
            capture_agent: Capture agent ID (Pearl device ID)
            series_id: Target series UUID
            creator: Presenter name
            description: Event description
            spatial: Room/location
            inputs: Input sources to capture (e.g., ["presenter", "presentation"])

        Returns:
            Created scheduled event
        """
        import json

        # Build scheduling metadata
        metadata = [
            {
                "flavor": "dublincore/episode",
                "fields": [
                    {"id": "title", "value": title},
                    {"id": "description", "value": description},
                    {"id": "creator", "value": [creator] if creator else []},
                    {"id": "spatial", "value": spatial},
                    {"id": "isPartOf", "value": series_id or self.default_series},
                ],
            }
        ]

        # Scheduling info
        scheduling = {
            "agent_id": capture_agent,
            "start": start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "end": end_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "inputs": inputs or ["default"],
        }

        data = {
            "metadata": json.dumps(metadata),
            "scheduling": json.dumps(scheduling),
            "acl": json.dumps([]),
        }

        result = await self._post("/events", data=data)
        return result if isinstance(result, dict) else {"identifier": str(result)}
