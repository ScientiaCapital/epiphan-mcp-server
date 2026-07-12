"""Epiphan Cloud API client for remote device management.

This module provides an async client for the Epiphan Cloud REST API v2, enabling:
- Device pairing and management
- Remote command execution
- Device settings and preset management
- Device preview and telemetry access

Authentication uses Bearer tokens obtained from the Epiphan Cloud portal.

Reference: https://docs.epiphan.com/cloud-api
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EpiphanCloudAuthError(Exception):
    """Authentication error with Epiphan Cloud."""

    pass


class EpiphanCloudAPIError(Exception):
    """API error from Epiphan Cloud."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class EpiphanCloudClient:
    """Async client for Epiphan Cloud REST API v2.

    Provides methods for managing Epiphan devices remotely through the cloud,
    including pairing, configuration, command execution, and monitoring.

    Example:
        ```python
        async with EpiphanCloudClient(token="your-bearer-token") as client:
            devices = await client.list_devices()
            device = await client.get_device(device_id="dev123")
            await client.run_task(device_id="dev123", task="reboot")
        ```
    """

    def __init__(
        self,
        token: str,
        host: str = "go.epiphan.cloud",
        timeout: float = 30.0,
    ):
        """Initialize Epiphan Cloud client.

        Args:
            token: Bearer token for authentication
            host: Cloud API hostname (defaults to go.epiphan.cloud)
            timeout: Request timeout in seconds
        """
        self._token = token
        self._base_url = f"https://{host}/front/api/v2"
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "EpiphanCloudClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _auth_headers(self) -> dict[str, str]:
        """Get authorization headers with Bearer token."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make authenticated API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API endpoint path (e.g., "/devices")
            **kwargs: Additional httpx request arguments

        Returns:
            JSON response data

        Raises:
            EpiphanCloudAuthError: If authentication fails (401)
            EpiphanCloudAPIError: If request fails with 4xx/5xx status
        """
        if not self._client:
            raise EpiphanCloudAPIError("Client not initialized")

        url = f"{self._base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())

        try:
            response = await self._client.request(method, url, headers=headers, **kwargs)

            # Handle authentication errors specifically
            if response.status_code == 401:
                raise EpiphanCloudAuthError(f"Authentication failed: 401 - {response.text}")

            # Handle other client/server errors
            if response.status_code >= 400:
                raise EpiphanCloudAPIError(
                    f"API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                )

            # Return empty dict for 204 No Content
            if response.status_code == 204:
                return {}

            result: dict[str, Any] = response.json()
            return result

        except httpx.RequestError as e:
            raise EpiphanCloudAPIError(f"Request failed: {e}") from e

    async def _request_bytes(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> bytes:
        """Make authenticated API request and return raw bytes.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API endpoint path
            **kwargs: Additional httpx request arguments

        Returns:
            Raw response content as bytes

        Raises:
            EpiphanCloudAuthError: If authentication fails (401)
            EpiphanCloudAPIError: If request fails with 4xx/5xx status
        """
        if not self._client:
            raise EpiphanCloudAPIError("Client not initialized")

        url = f"{self._base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())

        try:
            response = await self._client.request(method, url, headers=headers, **kwargs)

            # Handle authentication errors specifically
            if response.status_code == 401:
                raise EpiphanCloudAuthError(f"Authentication failed: 401 - {response.text}")

            # Handle other client/server errors
            if response.status_code >= 400:
                raise EpiphanCloudAPIError(
                    f"API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                )

            return response.content

        except httpx.RequestError as e:
            raise EpiphanCloudAPIError(f"Request failed: {e}") from e

    # =========================================================================
    # User Management
    # =========================================================================

    async def get_current_user(self) -> dict[str, Any]:
        """Get current authenticated user information.

        Returns:
            User object with id, email, name, etc.
        """
        return await self._request("GET", "/users/me")

    # =========================================================================
    # Device Management
    # =========================================================================

    async def list_devices(self) -> list[dict[str, Any]]:
        """List all paired devices in the cloud account.

        Returns:
            List of device objects with id, name, status, etc.
        """
        result = await self._request("GET", "/devices")
        # Cloud API may return devices directly or wrapped in a response object
        if isinstance(result, list):
            return result
        devices: list[dict[str, Any]] = result.get("devices", result.get("data", []))
        return devices

    async def get_device(self, device_id: str) -> dict[str, Any]:
        """Get device details and telemetry.

        Args:
            device_id: Device identifier

        Returns:
            Device object with full details including telemetry data
        """
        return await self._request("GET", f"/devices/{device_id}")

    async def pair_device(self, pairing_code: str, name: str) -> dict[str, Any]:
        """Pair a new device to the cloud account.

        Args:
            pairing_code: Pairing code displayed on the device
            name: Friendly name for the device

        Returns:
            Newly paired device object
        """
        return await self._request(
            "POST",
            "/devices/pair",
            json={"pairing_code": pairing_code, "name": name},
        )

    async def unpair_device(self, device_id: str) -> None:
        """Unpair a device from the cloud account.

        Args:
            device_id: Device identifier
        """
        await self._request("POST", f"/devices/{device_id}/unpair")

    async def delete_device(self, device_id: str) -> None:
        """Delete a device from the cloud account.

        Args:
            device_id: Device identifier
        """
        await self._request("DELETE", f"/devices/{device_id}")

    async def rename_device(self, device_id: str, name: str) -> None:
        """Rename a device.

        Args:
            device_id: Device identifier
            name: New friendly name for the device
        """
        await self._request(
            "POST",
            f"/devices/{device_id}/rename",
            json={"name": name},
        )

    # =========================================================================
    # Device Commands
    # =========================================================================

    async def run_task(self, device_id: str, task: str) -> dict[str, Any]:
        """Run a command/task on a single device.

        Args:
            device_id: Device identifier
            task: Task/command to execute (e.g., "reboot", "update_firmware")

        Returns:
            Task execution status
        """
        return await self._request(
            "POST",
            f"/devices/{device_id}/task",
            json={"task": task},
        )

    async def batch_task(self, device_ids: list[str], task: str) -> dict[str, Any]:
        """Run a command/task on multiple devices.

        Args:
            device_ids: List of device identifiers
            task: Task/command to execute on all devices

        Returns:
            Batch task execution status
        """
        return await self._request(
            "POST",
            "/devices/batch_task",
            json={"device_ids": device_ids, "task": task},
        )

    # =========================================================================
    # Device Settings
    # =========================================================================

    async def get_device_settings(self, device_id: str) -> dict[str, Any]:
        """Get all device settings.

        Args:
            device_id: Device identifier

        Returns:
            Device settings object with all configuration parameters
        """
        return await self._request("GET", f"/devices/{device_id}/settings")

    # =========================================================================
    # Device Preview
    # =========================================================================

    async def get_device_preview(self, device_id: str) -> bytes:
        """Get device preview image.

        Args:
            device_id: Device identifier

        Returns:
            Preview image as raw bytes (typically JPEG or PNG)
        """
        return await self._request_bytes("GET", f"/devices/{device_id}/preview")

    # =========================================================================
    # Presets
    # =========================================================================

    async def apply_preset(
        self,
        device_id: str,
        preset_data: dict[str, Any],
        preset_type: str = "cloud",
    ) -> dict[str, Any]:
        """Apply a preset to a device.

        Args:
            device_id: Device identifier
            preset_data: Preset configuration data
            preset_type: Type of preset - "cloud" or "local"

        Returns:
            Preset application status
        """
        if preset_type not in ("cloud", "local"):
            raise EpiphanCloudAPIError(
                f"Invalid preset_type: {preset_type}. Must be 'cloud' or 'local'."
            )

        return await self._request(
            "PUT",
            f"/devices/{device_id}/presets/{preset_type}",
            json=preset_data,
        )

    # =========================================================================
    # Cleanup
    # =========================================================================

    async def close(self) -> None:
        """Explicitly close the HTTP client.

        This is automatically called when using the async context manager,
        but can be called manually if needed.
        """
        if self._client:
            await self._client.aclose()
            self._client = None
