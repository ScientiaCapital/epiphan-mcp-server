"""Async HTTP client for Epiphan EC20 PTZ camera control.

This module provides an async HTTP client for EC20 PTZ cameras, enabling:
- PTZ control (pan, tilt, zoom)
- Preset management (save, recall, list)
- AI tracking control (presenter mode, zone mode)
- Camera status and position retrieval
- Preview image capture

The EC20 supports multiple control protocols:
- REST API (HTTP) - used by this client
- VISCA over IP - alternative for legacy systems
- ONVIF - open standard

API Endpoints (placeholder - to be discovered from real hardware):
The actual endpoints will be documented after accessing the EC20 web interface
at http://<camera-ip>. Common patterns include:
- /api/ptz/position - Get/set PTZ position
- /api/ptz/preset - Manage presets
- /api/tracking - AI tracking control
- /api/status - Camera status

Example:
    ```python
    async with EC20Client(host="192.168.1.100") as client:
        # Get camera status
        status = await client.get_status()

        # Pan camera 30 degrees right
        await client.pan(degrees=30.0, speed=50)

        # Enable presenter tracking
        await client.enable_tracking(mode="presenter")

        # Go to preset "Podium"
        await client.goto_preset(preset_id=1)
    ```
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EC20ConnectionError(Exception):
    """Connection error with EC20 camera."""

    pass


class EC20APIError(Exception):
    """API error from EC20 camera."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class EC20Client:
    """Async HTTP client for Epiphan EC20 PTZ camera.

    Provides PTZ control, preset management, and AI tracking via REST API.

    Attributes:
        host: EC20 camera IP address or hostname
        username: Camera username (default "admin")
        password: Camera password
        use_https: Use HTTPS instead of HTTP
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        host: str,
        username: str = "admin",
        password: str = "",
        use_https: bool = False,
        timeout: float = 30.0,
    ):
        """Initialize EC20 client.

        Args:
            host: EC20 camera IP or hostname
            username: Camera username (default "admin")
            password: Camera password
            use_https: Use HTTPS instead of HTTP
            timeout: Request timeout in seconds
        """
        self.host = host
        self.username = username
        self.password = password
        self.use_https = use_https
        self.timeout = timeout

        # Build base URL
        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{host}"

        # HTTP client (created in __aenter__)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "EC20Client":
        """Async context manager entry - create HTTP client."""
        auth = None
        if self.username or self.password:
            auth = httpx.BasicAuth(self.username, self.password)

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=auth,
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # Internal HTTP Methods
    # =========================================================================

    async def _get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make GET request to EC20 API.

        Args:
            path: API path (e.g., "/api/status")
            **kwargs: Additional arguments for httpx.get()

        Returns:
            JSON response as dict

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API returned error
        """
        if not self._client:
            raise EC20ConnectionError("Not connected - use async with")

        try:
            response = await self._client.get(path, **kwargs)
            return self._handle_response(response)
        except httpx.ConnectError as e:
            raise EC20ConnectionError(f"Connection failed: {e}") from e
        except httpx.TimeoutException as e:
            raise EC20ConnectionError(f"Request timeout: {e}") from e

    async def _post(
        self,
        path: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make POST request to EC20 API.

        Args:
            path: API path (e.g., "/api/ptz/move")
            data: JSON data to send
            **kwargs: Additional arguments for httpx.post()

        Returns:
            JSON response as dict

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API returned error
        """
        if not self._client:
            raise EC20ConnectionError("Not connected - use async with")

        try:
            response = await self._client.post(path, json=data, **kwargs)
            return self._handle_response(response)
        except httpx.ConnectError as e:
            raise EC20ConnectionError(f"Connection failed: {e}") from e
        except httpx.TimeoutException as e:
            raise EC20ConnectionError(f"Request timeout: {e}") from e

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response, raising errors for non-success.

        Args:
            response: httpx.Response object

        Returns:
            JSON response as dict

        Raises:
            EC20APIError: API returned error status
        """
        # Check for HTTP errors
        if response.status_code >= 400:
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                error_msg = error_data.get("error", error_data.get("message", str(error_data)))
            except Exception:
                error_msg = response.text or f"HTTP {response.status_code}"

            raise EC20APIError(error_msg, status_code=response.status_code)

        # Parse JSON response
        try:
            return response.json()
        except Exception:
            # Return empty dict for non-JSON responses (e.g., images)
            return {}

    # =========================================================================
    # Status Methods
    # =========================================================================

    async def get_status(self) -> dict[str, Any]:
        """Get camera status information.

        Returns:
            Camera status including model, firmware, PTZ position, tracking state

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        # TODO: Replace with actual endpoint discovered from hardware
        return await self._get("/api/status")

    async def get_position(self) -> dict[str, Any]:
        """Get current PTZ position.

        Returns:
            Dict with pan, tilt, zoom values

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        # TODO: Replace with actual endpoint discovered from hardware
        return await self._get("/api/ptz/position")

    # =========================================================================
    # PTZ Control Methods
    # =========================================================================

    async def pan(self, degrees: float, speed: int = 50) -> dict[str, Any]:
        """Pan camera to absolute position.

        Args:
            degrees: Pan position in degrees (-162.5 to +162.5)
            speed: Pan speed (1-100, default 50)

        Returns:
            Result of pan operation

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        # TODO: Replace with actual endpoint discovered from hardware
        return await self._post("/api/ptz/pan", data={"degrees": degrees, "speed": speed})

    async def tilt(self, degrees: float, speed: int = 50) -> dict[str, Any]:
        """Tilt camera to absolute position.

        Args:
            degrees: Tilt position in degrees (-30 to +90 typical)
            speed: Tilt speed (1-100, default 50)

        Returns:
            Result of tilt operation

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        # TODO: Replace with actual endpoint discovered from hardware
        return await self._post("/api/ptz/tilt", data={"degrees": degrees, "speed": speed})

    async def zoom(self, level: int) -> dict[str, Any]:
        """Set zoom level.

        Args:
            level: Zoom level (1-36: 1-20 optical, 21-36 digital)

        Returns:
            Result of zoom operation

        Raises:
            ValueError: Invalid zoom level
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        if not 1 <= level <= 36:
            raise ValueError(f"Zoom level must be 1-36, got {level}")

        # TODO: Replace with actual endpoint discovered from hardware
        return await self._post("/api/ptz/zoom", data={"level": level})

    async def home(self) -> dict[str, Any]:
        """Return camera to home position.

        Returns:
            Result showing camera at home position (pan=0, tilt=0, zoom=1)

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        # TODO: Replace with actual endpoint discovered from hardware
        return await self._post("/api/ptz/home")

    # =========================================================================
    # Preset Methods
    # =========================================================================

    async def get_presets(self) -> list[dict[str, Any]]:
        """Get list of saved presets.

        Returns:
            List of preset dicts with id, name, pan, tilt, zoom

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        # TODO: Replace with actual endpoint discovered from hardware
        result = await self._get("/api/ptz/presets")
        return result.get("presets", [])

    async def goto_preset(self, preset_id: int) -> dict[str, Any]:
        """Move camera to saved preset position.

        Args:
            preset_id: ID of preset to recall

        Returns:
            Result of preset recall operation

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        # TODO: Replace with actual endpoint discovered from hardware
        return await self._post("/api/ptz/preset/goto", data={"preset_id": preset_id})

    async def save_preset(self, preset_id: int, name: str) -> dict[str, Any]:
        """Save current position as preset.

        Args:
            preset_id: ID for the preset (1-255)
            name: Name for the preset

        Returns:
            Result of preset save operation

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        # TODO: Replace with actual endpoint discovered from hardware
        return await self._post(
            "/api/ptz/preset/save",
            data={"preset_id": preset_id, "name": name},
        )

    # =========================================================================
    # AI Tracking Methods
    # =========================================================================

    async def enable_tracking(self, mode: str = "presenter") -> dict[str, Any]:
        """Enable AI tracking.

        Args:
            mode: Tracking mode - "presenter", "zone", or "body"

        Returns:
            Result with tracking status

        Raises:
            ValueError: Invalid tracking mode
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        valid_modes = {"presenter", "zone", "body"}
        if mode not in valid_modes:
            raise ValueError(f"Invalid tracking mode: {mode}. Must be one of {valid_modes}")

        # TODO: Replace with actual endpoint discovered from hardware
        return await self._post("/api/tracking/enable", data={"mode": mode})

    async def disable_tracking(self) -> dict[str, Any]:
        """Disable AI tracking.

        Returns:
            Result with tracking disabled status

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        # TODO: Replace with actual endpoint discovered from hardware
        return await self._post("/api/tracking/disable")

    # =========================================================================
    # Preview Methods
    # =========================================================================

    async def get_preview(self) -> bytes:
        """Get camera preview image.

        Returns:
            JPEG image bytes

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        if not self._client:
            raise EC20ConnectionError("Not connected - use async with")

        try:
            # TODO: Replace with actual endpoint discovered from hardware
            response = await self._client.get("/api/preview")

            if response.status_code >= 400:
                raise EC20APIError(
                    f"Failed to get preview: HTTP {response.status_code}",
                    status_code=response.status_code,
                )

            return response.content

        except httpx.ConnectError as e:
            raise EC20ConnectionError(f"Connection failed: {e}") from e
        except httpx.TimeoutException as e:
            raise EC20ConnectionError(f"Request timeout: {e}") from e
