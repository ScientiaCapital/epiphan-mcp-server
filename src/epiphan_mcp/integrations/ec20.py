"""Async HTTP client for Epiphan EC20 PTZ camera control.

The EC20's control API was captured from **live hardware** (unit serial
EP6601037, firmware "SOC v3.0.30 - ARM 6.1.84SEpiphan", model VX752A/ESP1895)
and its web-UI JavaScript bundle. It is a **CGI interface guarded by HTTP
Digest auth** — NOT the REST-over-Basic scheme earlier versions assumed:

- **Auth**: HTTP Digest (MD5). Basic auth is rejected with 401.
- **Config / status**: ``GET /cgi-bin/param.cgi?<command>`` returns a
  line-based ``key="value"`` body (NOT JSON). Read commands include
  ``get_device_conf``, ``get_system_conf``, ``get_target_status``.
- **PTZ**: ``GET /cgi-bin/ptzctrl.cgi?ptzcmd&<action>[&<arg>...]`` returns JSON
  ``{"Response": {"Result": ...}}``. This is the standard VISCA-over-HTTP
  command set: directional ``up``/``down``/``left``/``right`` (+ pan/tilt
  speed) held until ``ptzstop``; ``zoomin``/``zoomout`` (+ speed) held until
  ``zoomstop``; ``home``; and numeric presets ``poscall``/``posset`` (0-11).
- **AI tracking**: ``GET /cgi-bin/vip?set_ai_vip&<arg>``.

Deliberately NOT modelled (no such command exists on the device): absolute
pan/tilt/zoom positioning, position queries, and named / enumerable presets.
The camera is a stateless directional device.

Live read-only validation (2026-07-18, unit at 192.168.8.11) confirmed:
- ``get_status`` returns real device data; Digest ``admin``/``admin`` works.
- Preview is genuinely WebSocket-only (``/ws/mjpeg``); there is no single-frame
  HTTP endpoint, so ``get_preview`` fails explicitly rather than hit a fake URL.
- ``get_target_status`` (the exact command the camera web UI uses) returns 404
  on this firmware/model (VX752A, SOC v3.0.30) — the AI target-status read is
  simply absent here, so ``get_tracking_status`` surfaces that 404.
- ``set_ai_vip`` is the correct tracking endpoint but requires a VIP-target
  argument: called bare it returns ``{"Result":"Failed","Msg":"vip is null"}``.
  The exact target-argument grammar is still UNVERIFIED (needs a destructive
  pass) — ``enable_tracking`` sends a best-effort flag until then.

Capability facts (Epiphan EC20 Q-SYS plugin README): presets 0-11 (firmware
>= 3.3.40); AI tracking modes are "presenter" and "zone" only; API is HTTP
port 80 only (443 disabled), so ``use_https`` is unsupported on current firmware.

Example:
    ```python
    async with EC20Client(host="192.168.8.5", password="admin") as client:
        status = await client.get_status()      # real device info
        await client.move("left", pan_speed=12) # start panning left
        await client.stop()                      # stop
        await client.goto_preset(3)              # recall preset 3
        await client.enable_tracking("presenter")
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

# Directional PTZ action tokens (confirmed literals in the camera web-UI JS).
_MOVE_DIRECTIONS = {"up", "down", "left", "right"}
_ZOOM_DIRECTIONS = {"in": "zoomin", "out": "zoomout"}

# AI auto-tracking modes (Q-SYS plugin README) — "body" is NOT a real mode.
_TRACKING_MODES = {"presenter", "zone"}

# Keys from param.cgi whose values are secrets and must never be surfaced.
_SECRET_KEY_MARKERS = ("passwd", "password")


def _validate_preset_id(preset_id: int) -> None:
    """Raise ValueError if preset_id is outside the EC20's documented 0-11 range."""
    if not PRESET_ID_MIN <= preset_id <= PRESET_ID_MAX:
        raise ValueError(
            f"Invalid preset_id: {preset_id}. "
            f"EC20 supports presets {PRESET_ID_MIN}-{PRESET_ID_MAX}."
        )


def _parse_param_body(text: str) -> dict[str, str]:
    """Parse a param.cgi ``key="value"`` response body into a dict.

    The EC20 returns configuration as newline-separated ``key="value"`` pairs.
    Secret-looking keys (``*passwd*``/``*password*``) are redacted — the device
    echoes ``userpasswd`` in plaintext.
    """
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip().rstrip(",")
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"')
        if any(marker in key.lower() for marker in _SECRET_KEY_MARKERS):
            value = "***"
        result[key] = value
    return result


class EC20Client:
    """Async HTTP client for Epiphan EC20 PTZ camera (CGI + Digest auth).

    Attributes:
        host: EC20 camera IP address or hostname
        username: Camera username (default "admin")
        password: Camera password
        use_https: Use HTTPS (unsupported on current firmware — 443 disabled)
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
        self.host = host
        self.username = username
        self.password = password
        self.use_https = use_https
        self.timeout = timeout

        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{host}"

        # HTTP client (created in __aenter__)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "EC20Client":
        """Create the HTTP client. The EC20 requires HTTP **Digest** auth."""
        auth: httpx.Auth | None = None
        if self.username or self.password:
            auth = httpx.DigestAuth(self.username, self.password)

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=auth,
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # Internal transport
    # =========================================================================

    async def _get(self, path_and_query: str) -> httpx.Response:
        """GET a raw path+query (the EC20 uses bare ``&`` flags, not key=value)."""
        if not self._client:
            raise EC20ConnectionError("Not connected - use 'async with EC20Client(...)'")
        try:
            response = await self._client.get(path_and_query)
        except httpx.ConnectError as e:
            raise EC20ConnectionError(f"Connection failed: {e}") from e
        except httpx.TimeoutException as e:
            raise EC20ConnectionError(f"Request timeout: {e}") from e
        self._raise_for_status(response)
        return response

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code in (401, 403):
            raise EC20AuthError(
                f"Authentication failed: {response.status_code}. "
                "The EC20 requires HTTP Digest auth and valid credentials.",
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise EC20APIError(
                response.text or f"HTTP {response.status_code}",
                status_code=response.status_code,
            )

    async def _param(self, command: str) -> dict[str, str]:
        """GET /cgi-bin/param.cgi?<command> and parse the key=\"value\" body."""
        response = await self._get(f"/cgi-bin/param.cgi?{command}")
        return _parse_param_body(response.text)

    def _json_result(self, response: httpx.Response) -> dict[str, Any]:
        """Parse a JSON command response, raising on the device's own failure verdict.

        ptzctrl.cgi / vip return HTTP 200 with ``{"Response": {"Result":
        "Success"|"Failed", ...}}``. A ``Failed`` result (e.g. tracking with no
        VIP target -> ``Msg: "vip is null"``) is a real command failure and must
        not be reported to callers as success.
        """
        try:
            data: dict[str, Any] = response.json()
        except Exception:
            return {}
        response_obj = data.get("Response")
        if isinstance(response_obj, dict) and response_obj.get("Result") == "Failed":
            msg = response_obj.get("Msg") or response_obj.get("msg") or "command failed"
            code = response_obj.get("Code")
            detail = f"{msg}" + (f" (code {code})" if code is not None else "")
            raise EC20APIError(f"EC20 command failed: {detail}")
        return data

    async def _ptz(self, *parts: str | int) -> dict[str, Any]:
        """GET /cgi-bin/ptzctrl.cgi?ptzcmd&<parts...> and parse the JSON body."""
        query = "&".join(["ptzcmd", *(str(p) for p in parts)])
        response = await self._get(f"/cgi-bin/ptzctrl.cgi?{query}")
        return self._json_result(response)

    # =========================================================================
    # Status
    # =========================================================================

    async def get_status(self) -> dict[str, Any]:
        """Get camera identity and system configuration.

        Merges ``get_device_conf`` (model/firmware/serial/NDI) and
        ``get_system_conf`` (work mode, tally, user names). Password fields are
        redacted.
        """
        status: dict[str, Any] = {}
        status.update(await self._param("get_device_conf"))
        status.update(await self._param("get_system_conf"))
        return status

    # =========================================================================
    # PTZ directional control
    # =========================================================================

    async def move(
        self, direction: str, pan_speed: int = 12, tilt_speed: int = 12
    ) -> dict[str, Any]:
        """Start moving the camera in a direction; motion holds until ``stop()``.

        Args:
            direction: one of up / down / left / right
            pan_speed / tilt_speed: movement speeds (VISCA-style; typical pan
                1-24, tilt 1-20 — exact caps unverified on this firmware).
        """
        if direction not in _MOVE_DIRECTIONS:
            raise ValueError(
                f"Invalid direction: {direction!r}. Must be one of {sorted(_MOVE_DIRECTIONS)}."
            )
        return await self._ptz(direction, pan_speed, tilt_speed)

    async def stop(self) -> dict[str, Any]:
        """Stop pan/tilt motion."""
        return await self._ptz("ptzstop", 1, 1)

    async def zoom(self, direction: str, speed: int = 5) -> dict[str, Any]:
        """Start zooming in/out; motion holds until ``zoom_stop()``.

        Args:
            direction: "in" or "out"
            speed: zoom speed (typical 1-7 — exact cap unverified).
        """
        action = _ZOOM_DIRECTIONS.get(direction)
        if action is None:
            raise ValueError(
                f"Invalid zoom direction: {direction!r}. Must be one of "
                f"{sorted(_ZOOM_DIRECTIONS)}."
            )
        return await self._ptz(action, speed)

    async def zoom_stop(self) -> dict[str, Any]:
        """Stop zoom motion."""
        return await self._ptz("zoomstop")

    async def home(self) -> dict[str, Any]:
        """Return the camera to its home position."""
        return await self._ptz("home")

    # =========================================================================
    # Presets (numeric 0-11)
    # =========================================================================

    async def goto_preset(self, preset_id: int) -> dict[str, Any]:
        """Recall a saved preset position (0-11)."""
        _validate_preset_id(preset_id)
        return await self._ptz("poscall", preset_id)

    async def save_preset(self, preset_id: int) -> dict[str, Any]:
        """Save the current position to a preset slot (0-11).

        The EC20 stores presets by number only — there is no name field.
        """
        _validate_preset_id(preset_id)
        return await self._ptz("posset", preset_id)

    # =========================================================================
    # AI tracking
    # =========================================================================

    async def enable_tracking(self, mode: str = "presenter") -> dict[str, Any]:
        """Enable AI auto-tracking.

        Args:
            mode: "presenter" or "zone" (per Q-SYS plugin README).

        Note: ``set_ai_vip`` is the correct endpoint (verified live) but expects
        a VIP-target argument — called with just a flag it returns
        ``{"Result":"Failed","Msg":"vip is null"}``. The exact target grammar is
        UNVERIFIED (needs a destructive pass); zone-mode additionally requires a
        ``tracking.area.*`` bounding box this method does not yet set.
        """
        if mode not in _TRACKING_MODES:
            raise ValueError(
                f"Invalid tracking mode: {mode!r}. Must be one of {sorted(_TRACKING_MODES)}."
            )
        return await self._vip("set_ai_vip", 1)

    async def disable_tracking(self) -> dict[str, Any]:
        """Disable AI auto-tracking."""
        return await self._vip("set_ai_vip", 0)

    async def get_tracking_status(self) -> dict[str, Any]:
        """Get AI tracking / target status.

        Uses ``get_target_status`` — the exact command the camera web UI issues.
        Note: this returns 404 on some firmware/models (e.g. VX752A / SOC
        v3.0.30), where the target-status read is not exposed; callers get an
        EC20APIError in that case.
        """
        return await self._param("get_target_status")

    async def _vip(self, *parts: str | int) -> dict[str, Any]:
        """GET /cgi-bin/vip?<parts...> (AI tracking control)."""
        query = "&".join(str(p) for p in parts)
        response = await self._get(f"/cgi-bin/vip?{query}")
        return self._json_result(response)

    # =========================================================================
    # Preview
    # =========================================================================

    async def get_preview(self) -> bytes:
        """Not supported on current firmware.

        The EC20 exposes its live preview only as an MJPEG **WebSocket** stream
        at ``/ws/mjpeg`` — there is no single-frame HTTP endpoint. Rather than
        fabricate a URL, this fails explicitly.
        """
        raise EC20APIError(
            "EC20 preview is an MJPEG WebSocket stream (/ws/mjpeg); single-frame "
            "HTTP capture is not supported on this firmware."
        )
