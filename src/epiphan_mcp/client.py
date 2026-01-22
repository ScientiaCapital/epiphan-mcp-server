"""Async HTTP client for Epiphan Pearl REST API."""

import logging
from typing import Any, Optional

import httpx

from .config import Settings, get_settings
from .models import (
    ChannelParams,
    InputSource,
    Layout,
    OperationResult,
    Recording,
    RecorderStatus,
    RecordingState,
    SystemStatus,
)

logger = logging.getLogger(__name__)


class PearlAPIError(Exception):
    """Exception raised for Pearl API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class PearlClient:
    """
    Async client for Epiphan Pearl REST API.

    Supports both the legacy HTTP API and newer REST API endpoints.
    Based on patterns from harvard-dce/epipearl.

    Usage:
        async with PearlClient("192.168.1.100", "admin", "password") as client:
            status = await client.get_system_status()
            await client.start_recording(1)
    """

    def __init__(
        self,
        host: str,
        username: str = "admin",
        password: str = "",
        use_https: bool = False,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ):
        """
        Initialize Pearl client.

        Args:
            host: Pearl device IP or hostname
            username: Admin username
            password: Admin password
            use_https: Use HTTPS instead of HTTP
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
        """
        self.host = host
        self.base_url = f"{'https' if use_https else 'http'}://{host}"
        self.auth = httpx.BasicAuth(username, password)
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client: Optional[httpx.AsyncClient] = None

    @classmethod
    def from_settings(cls, host: str, settings: Optional[Settings] = None) -> "PearlClient":
        """Create client from settings."""
        settings = settings or get_settings()
        return cls(
            host=host,
            username=settings.username,
            password=settings.password,
            use_https=settings.use_https,
            timeout=settings.timeout,
            verify_ssl=settings.verify_ssl,
        )

    async def __aenter__(self) -> "PearlClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=self.auth,
            timeout=self.timeout,
            verify=self.verify_ssl,
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

    async def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> httpx.Response:
        """Make GET request."""
        try:
            response = await self.client.get(path, params=params)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for GET {path}")
            raise PearlAPIError(str(e), e.response.status_code) from e
        except httpx.RequestError as e:
            logger.error(f"Request error for GET {path}: {e}")
            raise PearlAPIError(str(e)) from e

    async def _post(
        self, path: str, params: Optional[dict[str, Any]] = None, data: Optional[dict[str, Any]] = None
    ) -> httpx.Response:
        """Make POST request."""
        try:
            response = await self.client.post(path, params=params, data=data)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for POST {path}")
            raise PearlAPIError(str(e), e.response.status_code) from e
        except httpx.RequestError as e:
            logger.error(f"Request error for POST {path}: {e}")
            raise PearlAPIError(str(e)) from e

    # ========== System Status ==========

    async def get_system_status(self) -> SystemStatus:
        """
        Get system status including storage, uptime, etc.

        Returns:
            SystemStatus with device information.
        """
        # Try REST API first, fall back to legacy
        try:
            response = await self._get("/api/system/status")
            data = response.json()
            return SystemStatus.model_validate(data)
        except PearlAPIError:
            # Fall back to legacy endpoint
            response = await self._get("/admin/sysstat")
            # Parse legacy format (may be different structure)
            data = self._parse_legacy_response(response.text)
            return SystemStatus.model_validate(data)

    def _parse_legacy_response(self, text: str) -> dict[str, Any]:
        """Parse legacy key=value response format."""
        result: dict[str, Any] = {}
        for line in text.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
        return result

    # ========== Channel Operations ==========

    async def get_channel_params(self, channel: int) -> ChannelParams:
        """
        Get parameters for a channel.

        Args:
            channel: Channel number (1-based)

        Returns:
            ChannelParams with channel configuration.
        """
        # Request specific parameters
        params = {
            "rec_enabled": "",
            "publish_type": "",
            "framesize": "",
            "framerate": "",
            "bitrate": "",
        }
        response = await self._get(f"/admin/channel{channel}/get_params.cgi", params=params)
        data = self._parse_legacy_response(response.text)
        data["channel_id"] = channel
        return ChannelParams.model_validate(data)

    async def set_channel_params(self, channel: int, params: dict[str, Any]) -> OperationResult:
        """
        Set parameters for a channel.

        Args:
            channel: Channel number (1-based)
            params: Parameters to set

        Returns:
            OperationResult with status.
        """
        response = await self._post(f"/admin/channel{channel}/set_params.cgi", params=params)
        return OperationResult(
            success=True,
            message=f"Channel {channel} parameters updated",
            device=self.host,
            details={"response": response.text},
        )

    # ========== Recording Operations ==========

    async def get_recorder_status(self, recorder: int = 1) -> RecorderStatus:
        """
        Get status of a recorder.

        Args:
            recorder: Recorder number (1-based, corresponds to channelm{N})

        Returns:
            RecorderStatus with current state.
        """
        params = {"rec_enabled": ""}
        response = await self._get(f"/admin/channelm{recorder}/get_params.cgi", params=params)
        data = self._parse_legacy_response(response.text)

        # Determine state from rec_enabled value
        rec_enabled = data.get("rec_enabled", "")
        if rec_enabled.lower() in ("on", "1", "true"):
            state = RecordingState.RECORDING
        else:
            state = RecordingState.STOPPED

        return RecorderStatus(
            recorder_id=recorder,
            state=state,
        )

    async def start_recording(self, recorder: int = 1) -> OperationResult:
        """
        Start recording on specified recorder.

        Args:
            recorder: Recorder number (1-based)

        Returns:
            OperationResult with status.
        """
        logger.info(f"Starting recording on recorder {recorder}")
        response = await self._post(
            f"/admin/channelm{recorder}/set_params.cgi",
            params={"rec_enabled": "on"},
        )
        return OperationResult(
            success=True,
            message=f"Recording started on recorder {recorder}",
            device=self.host,
            details={"recorder": recorder, "response": response.text},
        )

    async def stop_recording(self, recorder: int = 1) -> OperationResult:
        """
        Stop recording on specified recorder.

        Args:
            recorder: Recorder number (1-based)

        Returns:
            OperationResult with status.
        """
        logger.info(f"Stopping recording on recorder {recorder}")
        response = await self._post(
            f"/admin/channelm{recorder}/set_params.cgi",
            params={"rec_enabled": ""},
        )
        return OperationResult(
            success=True,
            message=f"Recording stopped on recorder {recorder}",
            device=self.host,
            details={"recorder": recorder, "response": response.text},
        )

    # ========== Streaming Operations ==========

    async def start_stream(self, channel: int = 1) -> OperationResult:
        """
        Start streaming on specified channel.

        Args:
            channel: Channel number (1-based)

        Returns:
            OperationResult with status.
        """
        logger.info(f"Starting stream on channel {channel}")
        # publish_type values: 0=none, 1=rtmp, 2=pull, etc.
        response = await self._post(
            f"/admin/channel{channel}/set_params.cgi",
            params={"publish_type": "1"},  # RTMP push
        )
        return OperationResult(
            success=True,
            message=f"Streaming started on channel {channel}",
            device=self.host,
            details={"channel": channel, "response": response.text},
        )

    async def stop_stream(self, channel: int = 1) -> OperationResult:
        """
        Stop streaming on specified channel.

        Args:
            channel: Channel number (1-based)

        Returns:
            OperationResult with status.
        """
        logger.info(f"Stopping stream on channel {channel}")
        response = await self._post(
            f"/admin/channel{channel}/set_params.cgi",
            params={"publish_type": "0"},  # None
        )
        return OperationResult(
            success=True,
            message=f"Streaming stopped on channel {channel}",
            device=self.host,
            details={"channel": channel, "response": response.text},
        )

    # ========== Sources & Layouts ==========

    async def get_sources(self) -> list[InputSource]:
        """
        Get list of input sources.

        Returns:
            List of InputSource objects.
        """
        response = await self._get("/admin/sources")
        # TODO: Parse actual response format
        return []

    async def get_layouts(self, channel: int = 1) -> list[Layout]:
        """
        Get available layouts for a channel.

        Args:
            channel: Channel number

        Returns:
            List of Layout objects.
        """
        # TODO: Implement based on actual API
        return []

    async def switch_layout(self, channel: int, layout_id: str) -> OperationResult:
        """
        Switch to a different layout.

        Args:
            channel: Channel number
            layout_id: Layout identifier

        Returns:
            OperationResult with status.
        """
        response = await self._post(
            f"/admin/channel{channel}/set_params.cgi",
            params={"layout": layout_id},
        )
        return OperationResult(
            success=True,
            message=f"Layout switched to {layout_id}",
            device=self.host,
            details={"channel": channel, "layout": layout_id},
        )

    # ========== Media Files ==========

    async def list_recordings(self) -> list[Recording]:
        """
        List recorded files on device.

        Returns:
            List of Recording objects.
        """
        response = await self._get("/admin/mediafiles")
        # TODO: Parse actual response format
        return []
