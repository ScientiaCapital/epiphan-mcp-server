"""YouTube Live Streaming API client.

Async client for YouTube Live Streaming API v3, enabling creation and
management of live broadcasts for Pearl streaming integration.

YouTube Live broadcasts require:
1. Create a broadcast (the event metadata)
2. Create a stream (the RTMP ingestion point)
3. Bind the stream to the broadcast
4. Transition broadcast through states: testing → live → complete

The stream's RTMP URL and key are used to configure Pearl publishers.
"""

import time
from dataclasses import dataclass, field
from typing import Any

import httpx


class YouTubeAuthError(Exception):
    """Authentication or authorization error."""

    pass


class YouTubeAPIError(Exception):
    """YouTube API error."""

    pass


class YouTubeQuotaError(Exception):
    """API quota exceeded."""

    pass


@dataclass
class YouTubeClient:
    """Async client for YouTube Live Streaming API.

    Uses OAuth2 with refresh tokens for authentication. Access tokens
    are automatically refreshed when expired.

    Attributes:
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        refresh_token: OAuth2 refresh token (long-lived)
        timeout: Request timeout in seconds
    """

    client_id: str
    client_secret: str
    refresh_token: str
    timeout: float = 30.0

    _client: httpx.AsyncClient | None = field(default=None, repr=False)
    _access_token: str = field(default="", repr=False)
    _token_expires_at: float = field(default=0.0, repr=False)

    API_BASE = "https://www.googleapis.com/youtube/v3"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    async def __aenter__(self) -> "YouTubeClient":
        """Enter async context."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        await self._ensure_valid_token()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token, refreshing if needed."""
        # Refresh if token expires in less than 60 seconds
        if time.time() >= self._token_expires_at - 60:
            await self._refresh_access_token()

    async def _refresh_access_token(self) -> None:
        """Refresh the OAuth2 access token."""
        if not self._client:
            raise YouTubeAuthError("Client not initialized")

        try:
            response = await self._client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code == 400:
                data = response.json()
                error = data.get("error", "unknown")
                error_desc = data.get("error_description", "")
                raise YouTubeAuthError(f"Token refresh failed: {error} - {error_desc}")

            response.raise_for_status()
            data = response.json()

            self._access_token = data["access_token"]
            # Access tokens typically expire in 3600 seconds (1 hour)
            expires_in = data.get("expires_in", 3600)
            self._token_expires_at = time.time() + expires_in

        except httpx.HTTPStatusError as e:
            raise YouTubeAuthError(f"Token refresh failed: {e}") from e
        except httpx.RequestError as e:
            raise YouTubeAPIError(f"Network error during token refresh: {e}") from e

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated API request."""
        if not self._client:
            raise YouTubeAPIError("Client not initialized")

        await self._ensure_valid_token()

        url = f"{self.API_BASE}/{endpoint}"
        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            response = await self._client.request(
                method,
                url,
                params=params,
                json=json_data,
                headers=headers,
            )

            # Handle specific error codes
            if response.status_code == 401:
                # Token might have been revoked, try refresh once
                await self._refresh_access_token()
                headers = {"Authorization": f"Bearer {self._access_token}"}
                response = await self._client.request(
                    method,
                    url,
                    params=params,
                    json=json_data,
                    headers=headers,
                )

            if response.status_code == 403:
                data = response.json()
                errors = data.get("error", {}).get("errors", [])
                for error in errors:
                    if error.get("reason") == "quotaExceeded":
                        raise YouTubeQuotaError("YouTube API quota exceeded")
                raise YouTubeAuthError(f"Access forbidden: {data}")

            if response.status_code == 404:
                raise YouTubeAPIError("Resource not found")

            response.raise_for_status()

            # Some endpoints return empty response on success
            if response.status_code == 204 or not response.content:
                return {"success": True}

            result: dict[str, Any] = response.json()
            return result

        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                message = error_data.get("error", {}).get("message", str(e))
            except Exception:
                message = str(e)
            raise YouTubeAPIError(f"API error: {message}") from e
        except httpx.RequestError as e:
            raise YouTubeAPIError(f"Network error: {e}") from e

    # =========================================================================
    # Broadcast Operations
    # =========================================================================

    async def create_broadcast(
        self,
        title: str,
        scheduled_start: str,
        description: str = "",
        privacy: str = "unlisted",
        enable_dvr: bool = True,
        enable_content_encryption: bool = False,
        enable_embed: bool = True,
        record_from_start: bool = True,
        enable_auto_start: bool = False,
        enable_auto_stop: bool = False,
    ) -> dict[str, Any]:
        """Create a new live broadcast.

        Args:
            title: Broadcast title
            scheduled_start: Start time in ISO 8601 format (e.g., "2024-01-15T10:00:00Z")
            description: Broadcast description
            privacy: Privacy status - "public", "unlisted", or "private"
            enable_dvr: Allow viewers to rewind during live
            enable_content_encryption: Enable DRM protection
            enable_embed: Allow embedding on other sites
            record_from_start: Record the broadcast
            enable_auto_start: Auto-start when stream becomes active
            enable_auto_stop: Auto-stop when stream ends

        Returns:
            Broadcast resource with id, snippet, status, contentDetails
        """
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "scheduledStartTime": scheduled_start,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
            "contentDetails": {
                "enableDvr": enable_dvr,
                "enableContentEncryption": enable_content_encryption,
                "enableEmbed": enable_embed,
                "recordFromStart": record_from_start,
                "enableAutoStart": enable_auto_start,
                "enableAutoStop": enable_auto_stop,
                "monitorStream": {
                    "enableMonitorStream": True,
                    "broadcastStreamDelayMs": 0,
                },
            },
        }

        return await self._request(
            "POST",
            "liveBroadcasts",
            params={"part": "snippet,status,contentDetails"},
            json_data=body,
        )

    async def get_broadcast(self, broadcast_id: str) -> dict[str, Any]:
        """Get broadcast details by ID.

        Args:
            broadcast_id: The broadcast ID

        Returns:
            Broadcast resource
        """
        result = await self._request(
            "GET",
            "liveBroadcasts",
            params={
                "part": "snippet,status,contentDetails",
                "id": broadcast_id,
            },
        )

        items = result.get("items", [])
        if not items:
            raise YouTubeAPIError(f"Broadcast not found: {broadcast_id}")

        first_item: dict[str, Any] = items[0]
        return first_item

    async def list_broadcasts(
        self,
        status_filter: str = "",
        max_results: int = 25,
    ) -> list[dict[str, Any]]:
        """List broadcasts for the authenticated user.

        Args:
            status_filter: Filter by status - "active", "all", "completed", "upcoming"
            max_results: Maximum number of results (1-50)

        Returns:
            List of broadcast resources
        """
        params: dict[str, Any] = {
            "part": "snippet,status,contentDetails",
            "mine": "true",
            "maxResults": min(max_results, 50),
        }

        if status_filter:
            params["broadcastStatus"] = status_filter

        result = await self._request("GET", "liveBroadcasts", params=params)
        items: list[dict[str, Any]] = result.get("items", [])
        return items

    async def transition_broadcast(
        self,
        broadcast_id: str,
        status: str,
    ) -> dict[str, Any]:
        """Transition broadcast to a new status.

        Broadcast lifecycle:
        - created → testing (when stream is active)
        - testing → live (go live to viewers)
        - live → complete (end broadcast)

        Args:
            broadcast_id: The broadcast ID
            status: Target status - "testing", "live", or "complete"

        Returns:
            Updated broadcast resource
        """
        return await self._request(
            "POST",
            "liveBroadcasts/transition",
            params={
                "broadcastStatus": status,
                "id": broadcast_id,
                "part": "snippet,status",
            },
        )

    async def delete_broadcast(self, broadcast_id: str) -> dict[str, Any]:
        """Delete a broadcast.

        Args:
            broadcast_id: The broadcast ID to delete

        Returns:
            Success confirmation
        """
        return await self._request(
            "DELETE",
            "liveBroadcasts",
            params={"id": broadcast_id},
        )

    # =========================================================================
    # Stream Operations
    # =========================================================================

    async def create_stream(
        self,
        title: str,
        resolution: str = "1080p",
        frame_rate: str = "30fps",
        ingestion_type: str = "rtmp",
    ) -> dict[str, Any]:
        """Create a live stream (ingestion point).

        The stream provides the RTMP URL and stream key for Pearl.

        Args:
            title: Stream title
            resolution: Video resolution - "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p"
            frame_rate: Frame rate - "30fps" or "60fps"
            ingestion_type: Ingestion type - "rtmp" or "dash"

        Returns:
            Stream resource with cdn.ingestionInfo containing RTMP credentials
        """
        body = {
            "snippet": {
                "title": title,
            },
            "cdn": {
                "frameRate": frame_rate,
                "resolution": resolution,
                "ingestionType": ingestion_type,
            },
        }

        return await self._request(
            "POST",
            "liveStreams",
            params={"part": "snippet,cdn,status"},
            json_data=body,
        )

    async def get_stream(self, stream_id: str) -> dict[str, Any]:
        """Get stream details by ID.

        Args:
            stream_id: The stream ID

        Returns:
            Stream resource with status and ingestion info
        """
        result = await self._request(
            "GET",
            "liveStreams",
            params={
                "part": "snippet,cdn,status",
                "id": stream_id,
            },
        )

        items = result.get("items", [])
        if not items:
            raise YouTubeAPIError(f"Stream not found: {stream_id}")

        first_item: dict[str, Any] = items[0]
        return first_item

    async def list_streams(self, max_results: int = 25) -> list[dict[str, Any]]:
        """List streams for the authenticated user.

        Args:
            max_results: Maximum number of results (1-50)

        Returns:
            List of stream resources
        """
        result = await self._request(
            "GET",
            "liveStreams",
            params={
                "part": "snippet,cdn,status",
                "mine": "true",
                "maxResults": min(max_results, 50),
            },
        )
        items: list[dict[str, Any]] = result.get("items", [])
        return items

    async def delete_stream(self, stream_id: str) -> dict[str, Any]:
        """Delete a stream.

        Args:
            stream_id: The stream ID to delete

        Returns:
            Success confirmation
        """
        return await self._request(
            "DELETE",
            "liveStreams",
            params={"id": stream_id},
        )

    # =========================================================================
    # Binding Operations
    # =========================================================================

    async def bind_stream_to_broadcast(
        self,
        broadcast_id: str,
        stream_id: str,
    ) -> dict[str, Any]:
        """Bind a stream to a broadcast.

        Must be done before the broadcast can go live.

        Args:
            broadcast_id: The broadcast ID
            stream_id: The stream ID to bind

        Returns:
            Updated broadcast resource
        """
        return await self._request(
            "POST",
            "liveBroadcasts/bind",
            params={
                "id": broadcast_id,
                "streamId": stream_id,
                "part": "snippet,status,contentDetails",
            },
        )

    # =========================================================================
    # Combined Operations
    # =========================================================================

    async def create_broadcast_with_stream(
        self,
        title: str,
        scheduled_start: str,
        description: str = "",
        privacy: str = "unlisted",
        resolution: str = "1080p",
        frame_rate: str = "30fps",
    ) -> dict[str, Any]:
        """Create a broadcast and stream, bind them together.

        Convenience method that creates both resources and returns
        the RTMP credentials needed for Pearl.

        Args:
            title: Broadcast/stream title
            scheduled_start: Start time in ISO 8601 format
            description: Broadcast description
            privacy: Privacy status
            resolution: Video resolution
            frame_rate: Frame rate

        Returns:
            Dict with broadcast, stream, and rtmp_credentials
        """
        # Create broadcast
        broadcast = await self.create_broadcast(
            title=title,
            scheduled_start=scheduled_start,
            description=description,
            privacy=privacy,
        )

        # Create stream
        stream = await self.create_stream(
            title=f"{title} - Stream",
            resolution=resolution,
            frame_rate=frame_rate,
        )

        # Bind stream to broadcast
        await self.bind_stream_to_broadcast(
            broadcast_id=broadcast["id"],
            stream_id=stream["id"],
        )

        # Extract RTMP credentials for Pearl
        ingestion_info = stream.get("cdn", {}).get("ingestionInfo", {})
        rtmp_url = ingestion_info.get("ingestionAddress", "")
        stream_key = ingestion_info.get("streamName", "")

        return {
            "broadcast": broadcast,
            "stream": stream,
            "rtmp_credentials": {
                "rtmp_url": rtmp_url,
                "stream_key": stream_key,
                "full_url": f"{rtmp_url}/{stream_key}" if rtmp_url and stream_key else "",
            },
        }

    async def get_broadcast_status(self, broadcast_id: str) -> dict[str, Any]:
        """Get comprehensive status of a broadcast and its bound stream.

        Args:
            broadcast_id: The broadcast ID

        Returns:
            Dict with broadcast status, stream status, and health info
        """
        broadcast = await self.get_broadcast(broadcast_id)

        # Get bound stream status if available
        bound_stream_id = broadcast.get("contentDetails", {}).get("boundStreamId", "")

        stream_status = None
        if bound_stream_id:
            try:
                stream = await self.get_stream(bound_stream_id)
                stream_status = stream.get("status", {})
            except YouTubeAPIError:
                stream_status = {"error": "Stream not found"}

        return {
            "broadcast_id": broadcast_id,
            "title": broadcast.get("snippet", {}).get("title", ""),
            "broadcast_status": broadcast.get("status", {}).get("lifeCycleStatus", ""),
            "privacy_status": broadcast.get("status", {}).get("privacyStatus", ""),
            "scheduled_start": broadcast.get("snippet", {}).get("scheduledStartTime", ""),
            "actual_start": broadcast.get("snippet", {}).get("actualStartTime", ""),
            "actual_end": broadcast.get("snippet", {}).get("actualEndTime", ""),
            "bound_stream_id": bound_stream_id,
            "stream_status": stream_status,
        }
