"""Async HTTP client for Epiphan Pearl REST API v2.0.

Modern REST API implementation based on:
https://epiphan-video.github.io/pearl_api_swagger_ui/api/v2.0/openapi.yml

Requires firmware 4.14.2+ with password authentication.
"""

import logging
from typing import Any

import httpx

from .config import Settings, get_settings
from .models import (
    ChannelInfo,
    InputSource,
    OperationResult,
    PublisherStatus,
    RecorderInfo,
    RecorderStatus,
    StorageInfo,
    SystemStatus,
)
from .retry import with_retry

logger = logging.getLogger(__name__)

# API v2.0 base path
API_V2_BASE = "/api/v2.0"


class PearlAPIError(Exception):
    """Exception raised for Pearl API errors."""

    def __init__(self, message: str, status_code: int | None = None, api_status: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.api_status = api_status  # 'ok', 'error', or 'busy'


class PearlClient:
    """
    Async client for Epiphan Pearl REST API v2.0.

    Based on OpenAPI spec: https://epiphan-video.github.io/pearl_api_swagger_ui/

    API Response Format:
        All responses include a top-level 'status' field:
        - 'ok': Success, result in 'result' field
        - 'error': Error, details in 'message' field
        - 'busy': Resource busy, retry later

    Usage:
        async with PearlClient("192.168.1.100", "admin", "password") as client:
            recorders = await client.get_recorders()
            await client.start_recording("recorder-1")
    """

    def __init__(
        self,
        host: str,
        username: str = "admin",
        password: str = "",
        use_https: bool = False,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 30.0,
    ):
        """
        Initialize Pearl client.

        Args:
            host: Pearl device IP or hostname
            username: Admin username (required for API v2.0)
            password: Admin password (required since firmware 4.14.2)
            use_https: Use HTTPS instead of HTTP
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
            max_retries: Maximum retry attempts for transient failures
            retry_base_delay: Base delay between retries (seconds)
            retry_max_delay: Maximum retry delay cap (seconds)
        """
        self.host = host
        self.base_url = f"{'https' if use_https else 'http'}://{host}"
        self.api_base = f"{self.base_url}{API_V2_BASE}"
        self.auth = httpx.BasicAuth(username, password)
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client: httpx.AsyncClient | None = None

        # Retry configuration
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay

    @classmethod
    def from_settings(cls, host: str, settings: Settings | None = None) -> "PearlClient":
        """Create client from settings."""
        settings = settings or get_settings()
        return cls(
            host=host,
            username=settings.username,
            password=settings.password,
            use_https=settings.use_https,
            timeout=settings.timeout,
            verify_ssl=settings.verify_ssl,
            max_retries=settings.max_retries,
            retry_base_delay=settings.retry_base_delay,
            retry_max_delay=settings.retry_max_delay,
        )

    async def __aenter__(self) -> "PearlClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.api_base,
            auth=self.auth,
            timeout=self.timeout,
            verify=self.verify_ssl,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client, raising if not in context manager."""
        if self._client is None:
            raise RuntimeError("PearlClient must be used as async context manager")
        return self._client

    def _handle_response(self, response: httpx.Response, path: str) -> dict[str, Any]:
        """
        Handle API response and extract result.

        API responses have format:
            {"status": "ok", "result": {...}}
            {"status": "error", "message": "..."}
            {"status": "busy"}
        """
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {path}")
            raise PearlAPIError(str(e), e.response.status_code) from e

        # Handle non-JSON responses (images, binary)
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return {"status": "ok", "result": response.content}

        data: dict[str, Any] = response.json()
        status = data.get("status", "ok")

        if status == "error":
            message = data.get("message", "Unknown error")
            logger.error(f"API error for {path}: {message}")
            raise PearlAPIError(message, response.status_code, api_status="error")

        if status == "busy":
            logger.warning(f"Resource busy for {path}")
            raise PearlAPIError(
                "Resource busy, try again later", response.status_code, api_status="busy"
            )

        return data

    async def _get_raw(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make raw GET request without retry (internal use)."""
        response = await self.client.get(path, params=params)
        return self._handle_response(response, path)

    async def _post_raw(
        self, path: str, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make raw POST request without retry (internal use)."""
        response = await self.client.post(path, params=params, json=json)
        return self._handle_response(response, path)

    async def _put_raw(
        self, path: str, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make raw PUT request without retry (internal use)."""
        response = await self.client.put(path, params=params, json=json)
        return self._handle_response(response, path)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make GET request to API v2.0 endpoint with automatic retry."""
        try:
            return await with_retry(
                lambda: self._get_raw(path, params),
                max_retries=self.max_retries,
                base_delay=self.retry_base_delay,
                max_delay=self.retry_max_delay,
            )
        except httpx.RequestError as e:
            logger.error(f"Request error for GET {path}: {e}")
            raise PearlAPIError(str(e)) from e

    async def _post(
        self, path: str, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make POST request to API v2.0 endpoint with automatic retry."""
        try:
            return await with_retry(
                lambda: self._post_raw(path, params, json),
                max_retries=self.max_retries,
                base_delay=self.retry_base_delay,
                max_delay=self.retry_max_delay,
            )
        except httpx.RequestError as e:
            logger.error(f"Request error for POST {path}: {e}")
            raise PearlAPIError(str(e)) from e

    async def _put(
        self, path: str, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make PUT request to API v2.0 endpoint with automatic retry."""
        try:
            return await with_retry(
                lambda: self._put_raw(path, params, json),
                max_retries=self.max_retries,
                base_delay=self.retry_base_delay,
                max_delay=self.retry_max_delay,
            )
        except httpx.RequestError as e:
            logger.error(f"Request error for PUT {path}: {e}")
            raise PearlAPIError(str(e)) from e

    # ========== Recorders ==========

    async def get_recorders(self, ids: list[str] | None = None) -> list[RecorderInfo]:
        """
        Get list of available recorders with their properties.

        GET /recorders

        Args:
            ids: Optional list of recorder IDs to filter

        Returns:
            List of RecorderInfo objects.
        """
        params = {"ids": ",".join(ids)} if ids else None
        data = await self._get("/recorders", params=params)
        result = data.get("result", [])
        return [RecorderInfo.model_validate(r) for r in result]

    async def get_all_recorder_status(self, ids: list[str] | None = None) -> list[RecorderStatus]:
        """
        Get status for all recorders.

        GET /recorders/status

        Args:
            ids: Optional list of recorder IDs to filter

        Returns:
            List of RecorderStatus objects.
        """
        params = {"ids": ",".join(ids)} if ids else None
        data = await self._get("/recorders/status", params=params)
        result = data.get("result", [])
        return [RecorderStatus.model_validate(r) for r in result]

    async def get_recorder_status(self, recorder_id: str) -> RecorderStatus:
        """
        Get status of a specific recorder.

        GET /recorders/{rid}/status

        Args:
            recorder_id: Recorder ID (e.g., "recorder-1")

        Returns:
            RecorderStatus with current state, duration, file info.
        """
        data = await self._get(f"/recorders/{recorder_id}/status")
        result = data.get("result", {})
        return RecorderStatus.model_validate(result)

    async def start_all_recorders(self, ids: list[str] | None = None) -> OperationResult:
        """
        Start all recorders (or filtered by IDs).

        POST /recorders/control/start

        Args:
            ids: Optional list of recorder IDs to start

        Returns:
            OperationResult with status.
        """
        params = {"ids": ",".join(ids)} if ids else None
        logger.info(f"Starting recorders: {ids or 'all'}")
        await self._post("/recorders/control/start", params=params)
        return OperationResult(
            success=True,
            message=f"Recording started on {len(ids) if ids else 'all'} recorder(s)",
            device=self.host,
            details={"recorders": ids or "all"},
        )

    async def stop_all_recorders(self, ids: list[str] | None = None) -> OperationResult:
        """
        Stop all recorders (or filtered by IDs).

        POST /recorders/control/stop

        Args:
            ids: Optional list of recorder IDs to stop

        Returns:
            OperationResult with status.
        """
        params = {"ids": ",".join(ids)} if ids else None
        logger.info(f"Stopping recorders: {ids or 'all'}")
        await self._post("/recorders/control/stop", params=params)
        return OperationResult(
            success=True,
            message=f"Recording stopped on {len(ids) if ids else 'all'} recorder(s)",
            device=self.host,
            details={"recorders": ids or "all"},
        )

    async def start_recording(self, recorder_id: str) -> OperationResult:
        """
        Start recording on specified recorder.

        POST /recorders/{rid}/control/start

        Args:
            recorder_id: Recorder ID (e.g., "recorder-1")

        Returns:
            OperationResult with status.
        """
        logger.info(f"Starting recording on {recorder_id}")
        await self._post(f"/recorders/{recorder_id}/control/start")
        return OperationResult(
            success=True,
            message=f"Recording started on {recorder_id}",
            device=self.host,
            details={"recorder": recorder_id},
        )

    async def stop_recording(self, recorder_id: str) -> OperationResult:
        """
        Stop recording on specified recorder.

        POST /recorders/{rid}/control/stop

        Args:
            recorder_id: Recorder ID (e.g., "recorder-1")

        Returns:
            OperationResult with status.
        """
        logger.info(f"Stopping recording on {recorder_id}")
        await self._post(f"/recorders/{recorder_id}/control/stop")
        return OperationResult(
            success=True,
            message=f"Recording stopped on {recorder_id}",
            device=self.host,
            details={"recorder": recorder_id},
        )

    async def get_archive_files(
        self, recorder_id: str, from_index: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get list of recorded files for a recorder.

        GET /recorders/{rid}/archive/files

        Args:
            recorder_id: Recorder ID
            from_index: Starting index for pagination
            limit: Maximum number of files to return

        Returns:
            List of archive file objects.
        """
        data = await self._get(
            f"/recorders/{recorder_id}/archive/files",
            params={"from_index": from_index, "limit": limit},
        )
        result: list[dict[str, Any]] = data.get("result", [])
        return result

    # ========== Channels ==========

    async def get_channels(
        self,
        ids: list[str] | None = None,
        include_publishers: bool = False,
        include_encoders: bool = False,
        include_layouts: bool = False,
    ) -> list[ChannelInfo]:
        """
        Get list of available channels.

        GET /channels

        Args:
            ids: Optional list of channel IDs to filter
            include_publishers: Include publisher details
            include_encoders: Include encoder details
            include_layouts: Include layout details

        Returns:
            List of ChannelInfo objects.
        """
        params: dict[str, Any] = {}
        if ids:
            params["ids"] = ",".join(ids)
        if include_publishers:
            params["include_publishers"] = "true"
        if include_encoders:
            params["include_encoders"] = "true"
        if include_layouts:
            params["include_layouts"] = "true"

        data = await self._get("/channels", params=params or None)
        result = data.get("result", [])
        return [ChannelInfo.model_validate(c) for c in result]

    async def get_channel_preview(
        self,
        channel_id: str,
        resolution: str = "640x360",
        format: str = "jpg",
        keep_aspect_ratio: bool = True,
    ) -> bytes:
        """
        Get channel preview image.

        GET /channels/{cid}/preview

        Args:
            channel_id: Channel ID
            resolution: Image resolution (e.g., "640x360")
            format: Image format ("jpg" or "png")
            keep_aspect_ratio: Maintain aspect ratio

        Returns:
            Binary image data.
        """
        # Need to use base client for binary response
        response = await self.client.get(
            f"/channels/{channel_id}/preview",
            params={
                "resolution": resolution,
                "format": format,
                "keep_aspect_ratio": str(keep_aspect_ratio).lower(),
            },
        )
        response.raise_for_status()
        return response.content

    async def switch_layout(self, channel_id: str, layout_id: str) -> OperationResult:
        """
        Activate a layout in the channel.

        PUT /channels/{cid}/layouts/active

        Args:
            channel_id: Channel ID
            layout_id: Layout ID to activate

        Returns:
            OperationResult with status.
        """
        logger.info(f"Switching channel {channel_id} to layout {layout_id}")
        await self._put(
            f"/channels/{channel_id}/layouts/active",
            params={"layout_id": layout_id},
        )
        return OperationResult(
            success=True,
            message=f"Layout switched to {layout_id}",
            device=self.host,
            details={"channel": channel_id, "layout": layout_id},
        )

    async def add_bookmark(self, channel_id: str, text: str = "") -> OperationResult:
        """
        Add bookmark to active recording.

        POST /channels/{cid}/bookmarks

        Args:
            channel_id: Channel ID
            text: Bookmark text (optional)

        Returns:
            OperationResult with status.
        """
        await self._post(f"/channels/{channel_id}/bookmarks", params={"text": text})
        return OperationResult(
            success=True,
            message=f"Bookmark added to channel {channel_id}",
            device=self.host,
            details={"channel": channel_id, "text": text},
        )

    async def get_layouts(self, channel_id: str) -> list[dict[str, Any]]:
        """
        Get available layouts for a channel.

        GET /channels/{cid}/layouts

        Args:
            channel_id: Channel ID

        Returns:
            List of layout objects with id, name, and is_active flag.
        """
        data = await self._get(f"/channels/{channel_id}/layouts")
        result: list[dict[str, Any]] = data.get("result", [])
        return result

    # ========== Publishers (Streams) ==========

    async def get_publishers(self, channel_id: str) -> list[dict[str, Any]]:
        """
        Get publishers (streams) for a channel.

        GET /channels/{cid}/publishers

        Args:
            channel_id: Channel ID

        Returns:
            List of publisher objects with settings.
        """
        data = await self._get(f"/channels/{channel_id}/publishers")
        result: list[dict[str, Any]] = data.get("result", [])
        return result

    async def get_publisher_status(self, channel_id: str, publisher_id: str) -> PublisherStatus:
        """
        Get status of a specific publisher.

        GET /channels/{cid}/publishers/{pid}/status

        Args:
            channel_id: Channel ID
            publisher_id: Publisher ID

        Returns:
            PublisherStatus with state, duration, statistics.
        """
        data = await self._get(f"/channels/{channel_id}/publishers/{publisher_id}/status")
        result = data.get("result", {})
        return PublisherStatus.model_validate(result)

    async def start_all_publishers(self, channel_id: str) -> OperationResult:
        """
        Start all publishers (streams) for a channel.

        POST /channels/{cid}/publishers/control/start

        Args:
            channel_id: Channel ID

        Returns:
            OperationResult with status.
        """
        logger.info(f"Starting all publishers on channel {channel_id}")
        await self._post(f"/channels/{channel_id}/publishers/control/start")
        return OperationResult(
            success=True,
            message=f"Streaming started on channel {channel_id}",
            device=self.host,
            details={"channel": channel_id},
        )

    async def stop_all_publishers(self, channel_id: str) -> OperationResult:
        """
        Stop all publishers (streams) for a channel.

        POST /channels/{cid}/publishers/control/stop

        Args:
            channel_id: Channel ID

        Returns:
            OperationResult with status.
        """
        logger.info(f"Stopping all publishers on channel {channel_id}")
        await self._post(f"/channels/{channel_id}/publishers/control/stop")
        return OperationResult(
            success=True,
            message=f"Streaming stopped on channel {channel_id}",
            device=self.host,
            details={"channel": channel_id},
        )

    async def start_stream(self, channel_id: str, publisher_id: str) -> OperationResult:
        """
        Start a specific publisher (stream).

        POST /channels/{cid}/publishers/{pid}/control/start

        Args:
            channel_id: Channel ID
            publisher_id: Publisher ID

        Returns:
            OperationResult with status.
        """
        logger.info(f"Starting stream {publisher_id} on channel {channel_id}")
        await self._post(f"/channels/{channel_id}/publishers/{publisher_id}/control/start")
        return OperationResult(
            success=True,
            message=f"Stream {publisher_id} started",
            device=self.host,
            details={"channel": channel_id, "publisher": publisher_id},
        )

    async def stop_stream(self, channel_id: str, publisher_id: str) -> OperationResult:
        """
        Stop a specific publisher (stream).

        POST /channels/{cid}/publishers/{pid}/control/stop

        Args:
            channel_id: Channel ID
            publisher_id: Publisher ID

        Returns:
            OperationResult with status.
        """
        logger.info(f"Stopping stream {publisher_id} on channel {channel_id}")
        await self._post(f"/channels/{channel_id}/publishers/{publisher_id}/control/stop")
        return OperationResult(
            success=True,
            message=f"Stream {publisher_id} stopped",
            device=self.host,
            details={"channel": channel_id, "publisher": publisher_id},
        )

    # ========== Inputs ==========

    async def get_inputs(
        self, types: list[str] | None = None, ids: list[str] | None = None
    ) -> list[InputSource]:
        """
        Get list of available inputs.

        GET /inputs

        Args:
            types: Filter by input types
            ids: Filter by input IDs

        Returns:
            List of InputSource objects.
        """
        params: dict[str, Any] = {}
        if types:
            params["types"] = ",".join(types)
        if ids:
            params["ids"] = ",".join(ids)

        data = await self._get("/inputs", params=params or None)
        result = data.get("result", [])
        return [InputSource.model_validate(i) for i in result]

    async def get_input_preview(
        self,
        input_id: str,
        resolution: str = "640x360",
        format: str = "jpg",
    ) -> bytes:
        """
        Get input preview image.

        GET /inputs/{sid}/preview

        Args:
            input_id: Input source ID
            resolution: Image resolution
            format: Image format ("jpg" or "png")

        Returns:
            Binary image data.
        """
        response = await self.client.get(
            f"/inputs/{input_id}/preview",
            params={"resolution": resolution, "format": format},
        )
        response.raise_for_status()
        return response.content

    # ========== Storage ==========

    async def get_storages(self, ids: list[str] | None = None) -> list[StorageInfo]:
        """
        Get storage information.

        GET /storages

        Args:
            ids: Optional list of storage IDs to filter

        Returns:
            List of StorageInfo objects.
        """
        params = {"ids": ",".join(ids)} if ids else None
        data = await self._get("/storages", params=params)
        result = data.get("result", [])
        return [StorageInfo.model_validate(s) for s in result]

    # ========== System ==========

    async def get_system_status(self) -> SystemStatus:
        """
        Get system status.

        GET /system/status (mapped from System status endpoints)

        Returns:
            SystemStatus with device information.
        """
        # The v2.0 API uses different endpoints for system info
        # Combine data from multiple sources
        try:
            # Get device identity
            identity_data = await self._get("/device")
            # Get storage info
            storage_data = await self._get("/storages")

            result = identity_data.get("result", {})
            storages = storage_data.get("result", [])

            # Calculate total storage
            total_bytes = sum(s.get("total_bytes", 0) for s in storages)
            free_bytes = sum(s.get("free_bytes", 0) for s in storages)

            return SystemStatus(
                device_name=result.get("name", self.host),
                model=result.get("model", "Unknown"),
                serial_number=result.get("serial", ""),
                firmware_version=result.get("firmware", ""),
                storage_total_gb=total_bytes / (1024**3) if total_bytes else 0,
                storage_free_gb=free_bytes / (1024**3) if free_bytes else 0,
                storage_used_percent=((total_bytes - free_bytes) / total_bytes * 100)
                if total_bytes
                else 0,
            )
        except PearlAPIError as e:
            logger.warning(f"Error getting system status: {e}")
            return SystemStatus(device_name=self.host, model="Unknown")

    async def reboot(self) -> OperationResult:
        """
        Reboot the Pearl device.

        POST /system/control/reboot

        Returns:
            OperationResult with status.
        """
        logger.warning(f"Rebooting device {self.host}")
        await self._post("/system/control/reboot")
        return OperationResult(
            success=True,
            message=f"Device {self.host} is rebooting",
            device=self.host,
        )

    async def shutdown(self) -> OperationResult:
        """
        Shutdown the Pearl device.

        POST /system/control/shutdown

        Returns:
            OperationResult with status.
        """
        logger.warning(f"Shutting down device {self.host}")
        await self._post("/system/control/shutdown")
        return OperationResult(
            success=True,
            message=f"Device {self.host} is shutting down",
            device=self.host,
        )

    # ========== Events (Scheduled Recording) ==========

    async def get_events(
        self,
        from_time: str | None = None,
        to_time: str | None = None,
        limit: int = 100,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get scheduled events (Kaltura/Panopto/Opencast).

        GET /schedule/events

        Args:
            from_time: Start time filter (ISO format)
            to_time: End time filter (ISO format)
            limit: Maximum events to return
            status: Filter by status

        Returns:
            List of event objects.
        """
        params: dict[str, Any] = {"limit": limit}
        if from_time:
            params["from"] = from_time
        if to_time:
            params["to"] = to_time
        if status:
            params["status"] = status

        data = await self._get("/schedule/events", params=params)
        result: list[dict[str, Any]] = data.get("result", [])
        return result

    async def start_event(self, event_id: str) -> OperationResult:
        """
        Force start an upcoming event.

        POST /schedule/events/{eventId}/control/start

        Args:
            event_id: Event ID

        Returns:
            OperationResult with status.
        """
        await self._post(f"/schedule/events/{event_id}/control/start")
        return OperationResult(
            success=True,
            message=f"Event {event_id} started",
            device=self.host,
            details={"event": event_id},
        )

    async def stop_event(self, event_id: str) -> OperationResult:
        """
        Force stop an ongoing event.

        POST /schedule/events/{eventId}/control/stop

        Args:
            event_id: Event ID

        Returns:
            OperationResult with status.
        """
        await self._post(f"/schedule/events/{event_id}/control/stop")
        return OperationResult(
            success=True,
            message=f"Event {event_id} stopped",
            device=self.host,
            details={"event": event_id},
        )

    # ========== AFU (Automatic File Upload) ==========

    async def get_afu_status(self) -> list[dict[str, Any]]:
        """
        Get status of all Automatic File Upload destinations.

        GET /afu/status

        Returns:
            List of AFU status objects.
        """
        data = await self._get("/afu/status")
        result: list[dict[str, Any]] = data.get("result", [])
        return result

    # ========== Single Touch Control ==========

    async def single_touch_start(self) -> OperationResult:
        """
        Start all recorders and publishers with single touch.

        POST /singletouch/control/start

        Returns:
            OperationResult with status.
        """
        logger.info("Single touch start - starting all recorders and streams")
        await self._post("/singletouch/control/start")
        return OperationResult(
            success=True,
            message="All recorders and streams started",
            device=self.host,
        )

    async def single_touch_stop(self) -> OperationResult:
        """
        Stop all recorders and publishers with single touch.

        POST /singletouch/control/stop

        Returns:
            OperationResult with status.
        """
        logger.info("Single touch stop - stopping all recorders and streams")
        await self._post("/singletouch/control/stop")
        return OperationResult(
            success=True,
            message="All recorders and streams stopped",
            device=self.host,
        )
