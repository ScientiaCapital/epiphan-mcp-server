"""Async HTTP client for Epiphan EC20 PTZ camera control.

This module provides an async HTTP client for EC20 PTZ cameras, enabling:
- PTZ control (pan, tilt, zoom)
- Preset management (save, recall, list)
- AI tracking control (presenter mode, zone mode)
- Camera status and position retrieval
- Preview image capture

The EC20 exposes a REST API (used by this client) as a first-class control
method, alongside VISCA over IP, ONVIF, and NDI (per Epiphan tech specs). On
current firmware the API is served over **HTTP port 80 only — HTTPS/443 is
disabled** (Epiphan EC20 Q-SYS plugin README, v1.0), so `use_https=True` is
likely unsupported.

TODO: The endpoint PATHS below are best-effort placeholders — Epiphan does not
publish a REST endpoint reference; paths must be captured from the camera web UI
(http://<camera-ip>) browser dev-tools, then confirmed with scripts/validate_ec20.py.

However, several CAPABILITY facts ARE documented (Q-SYS plugin README) and are
already reflected in this client's validation/behaviour:
- Presets are numbered 0-11 (NOT 1-255). Requires firmware >= 3.3.40.
- AI auto-tracking modes are "presenter" and "zone" only (plus an Auto-Zoom
  toggle). There is no "body" mode.
- Preview is a live MJPEG stream; get_preview() returns a single best-effort frame.
- PTZ is documented as directional + speed and zoom as in/out + speed; the
  absolute pan/tilt/zoom modelled here is UNVERIFIED and must be confirmed
  against hardware.
Sources: EC20 tech specs; Epiphan EC20 Q-SYS plugin README (Carrier Labs, 2026-05).

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


class EC20AuthError(EC20APIError):
    """Authentication error with EC20 camera (bad credentials).

    Subclasses EC20APIError so existing ``except EC20APIError`` handlers
    in the tool layer keep catching auth failures while callers that care
    can distinguish them.
    """


# EC20 supports presets 0-11 (per Q-SYS plugin README; requires firmware >= 3.3.40).
PRESET_ID_MIN = 0
PRESET_ID_MAX = 11


def _validate_preset_id(preset_id: int) -> None:
    """Raise ValueError if preset_id is outside the EC20's documented 0-11 range."""
    if not PRESET_ID_MIN <= preset_id <= PRESET_ID_MAX:
        raise ValueError(
            f"Invalid preset_id: {preset_id}. "
            f"EC20 supports presets {PRESET_ID_MIN}-{PRESET_ID_MAX}."
        )


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
            EC20AuthError: On 401/403 (bad credentials)
            EC20APIError: API returned any other error status
        """
        if response.status_code in (401, 403):
            raise EC20AuthError(
                f"Authentication failed: {response.status_code} - {response.text}",
                status_code=response.status_code,
            )

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
            result: dict[str, Any] = response.json()
            return result
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
        return await self._get("/api/status")

    async def get_position(self) -> dict[str, Any]:
        """Get current PTZ position.

        Returns:
            Dict with pan, tilt, zoom values

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
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

        return await self._post("/api/ptz/zoom", data={"level": level})

    async def home(self) -> dict[str, Any]:
        """Return camera to home position.

        Returns:
            Result showing camera at home position (pan=0, tilt=0, zoom=1)

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
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
        result = await self._get("/api/ptz/presets")
        presets: list[dict[str, Any]] = result.get("presets", [])
        return presets

    async def goto_preset(self, preset_id: int) -> dict[str, Any]:
        """Move camera to saved preset position.

        Args:
            preset_id: ID of preset to recall (0-11, per EC20 spec)

        Returns:
            Result of preset recall operation

        Raises:
            ValueError: preset_id out of range
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        _validate_preset_id(preset_id)
        return await self._post("/api/ptz/preset/goto", data={"preset_id": preset_id})

    async def save_preset(self, preset_id: int, name: str) -> dict[str, Any]:
        """Save current position as preset.

        Args:
            preset_id: ID for the preset (0-11, per EC20 spec)
            name: Name for the preset

        Returns:
            Result of preset save operation

        Raises:
            ValueError: preset_id out of range
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        _validate_preset_id(preset_id)
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
            mode: Tracking mode - "presenter" or "zone" (per EC20 spec)

        Returns:
            Result with tracking status

        Raises:
            ValueError: Invalid tracking mode
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        valid_modes = {"presenter", "zone"}
        if mode not in valid_modes:
            raise ValueError(f"Invalid tracking mode: {mode}. Must be one of {valid_modes}")

        return await self._post("/api/tracking/enable", data={"mode": mode})

    async def disable_tracking(self) -> dict[str, Any]:
        """Disable AI tracking.

        Returns:
            Result with tracking disabled status

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        return await self._post("/api/tracking/disable")

    # =========================================================================
    # Preview Methods
    # =========================================================================

    async def get_preview(self) -> bytes:
        """Get a single camera preview frame.

        Note: the EC20 exposes a live MJPEG *stream*; this returns a single
        best-effort frame from it. The exact endpoint is unverified (see the
        module TODO) — confirm with scripts/validate_ec20.py against hardware.

        Returns:
            JPEG image bytes (one frame)

        Raises:
            EC20ConnectionError: Connection failed
            EC20APIError: API error
        """
        if not self._client:
            raise EC20ConnectionError("Not connected - use async with")

        try:
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
