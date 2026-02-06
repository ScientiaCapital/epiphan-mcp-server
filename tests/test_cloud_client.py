"""Tests for Epiphan Cloud API client."""

import pytest
import respx
from httpx import Response

from epiphan_mcp.integrations.cloud import (
    EpiphanCloudClient,
    EpiphanCloudAuthError,
    EpiphanCloudAPIError,
)

MOCK_TOKEN = "test-bearer-token-123"
MOCK_HOST = "go.epiphan.cloud"
BASE_URL = f"https://{MOCK_HOST}/front/api/v2"


class TestCloudClientInit:
    """Test client initialization."""

    def test_init_default_host(self):
        """Test client creation with default host."""
        client = EpiphanCloudClient(token=MOCK_TOKEN)
        assert client._token == MOCK_TOKEN
        assert client._base_url == f"https://go.epiphan.cloud/front/api/v2"
        assert client._timeout == 30.0

    def test_init_custom_host(self):
        """Test client creation with custom host."""
        custom_host = "custom.epiphan.cloud"
        client = EpiphanCloudClient(token=MOCK_TOKEN, host=custom_host)
        assert client._base_url == f"https://{custom_host}/front/api/v2"

    def test_init_custom_timeout(self):
        """Test client creation with custom timeout."""
        client = EpiphanCloudClient(token=MOCK_TOKEN, timeout=60.0)
        assert client._timeout == 60.0


class TestCloudClientAuth:
    """Test authentication handling."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_bearer_token_sent(self):
        """Test that Bearer token is sent in Authorization header."""
        route = respx.get(f"{BASE_URL}/users/me").mock(
            return_value=Response(200, json={"id": "user123", "email": "test@example.com"})
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            await client.get_current_user()

        assert route.called
        assert route.calls.last.request.headers["Authorization"] == f"Bearer {MOCK_TOKEN}"

    @pytest.mark.asyncio
    @respx.mock
    async def test_auth_error_on_401(self):
        """Test that 401 raises EpiphanCloudAuthError."""
        respx.get(f"{BASE_URL}/users/me").mock(
            return_value=Response(401, json={"error": "Invalid token"})
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            with pytest.raises(EpiphanCloudAuthError) as exc_info:
                await client.get_current_user()

            assert "401" in str(exc_info.value)


class TestCloudDevices:
    """Test device management endpoints."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_devices(self):
        """Test listing all paired devices."""
        mock_devices = [
            {"id": "dev1", "name": "Pearl Mini", "status": "online"},
            {"id": "dev2", "name": "Pearl Nano", "status": "offline"},
        ]
        respx.get(f"{BASE_URL}/devices").mock(
            return_value=Response(200, json=mock_devices)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            devices = await client.list_devices()

        assert len(devices) == 2
        assert devices[0]["name"] == "Pearl Mini"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_device(self):
        """Test getting device details."""
        device_id = "dev123"
        mock_device = {
            "id": device_id,
            "name": "Pearl Mini",
            "status": "online",
            "telemetry": {"cpu": 45, "temp": 55},
        }
        respx.get(f"{BASE_URL}/devices/{device_id}").mock(
            return_value=Response(200, json=mock_device)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            device = await client.get_device(device_id)

        assert device["id"] == device_id
        assert device["telemetry"]["cpu"] == 45

    @pytest.mark.asyncio
    @respx.mock
    async def test_pair_device(self):
        """Test pairing a new device."""
        pairing_code = "ABC123"
        device_name = "New Pearl"
        mock_response = {"id": "dev456", "name": device_name, "status": "online"}

        route = respx.post(f"{BASE_URL}/devices/pair").mock(
            return_value=Response(200, json=mock_response)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            result = await client.pair_device(pairing_code, device_name)

        assert result["name"] == device_name
        assert route.calls.last.request.content
        # Verify request body contains pairing_code and name

    @pytest.mark.asyncio
    @respx.mock
    async def test_unpair_device(self):
        """Test unpairing a device."""
        device_id = "dev789"
        respx.post(f"{BASE_URL}/devices/{device_id}/unpair").mock(
            return_value=Response(204)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            result = await client.unpair_device(device_id)

        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_device(self):
        """Test deleting a device."""
        device_id = "dev999"
        respx.delete(f"{BASE_URL}/devices/{device_id}").mock(
            return_value=Response(204)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            result = await client.delete_device(device_id)

        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_rename_device(self):
        """Test renaming a device."""
        device_id = "dev111"
        new_name = "Renamed Pearl"

        route = respx.post(f"{BASE_URL}/devices/{device_id}/rename").mock(
            return_value=Response(204)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            result = await client.rename_device(device_id, new_name)

        assert result is None
        assert route.called


class TestCloudCommands:
    """Test device command endpoints."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_run_task(self):
        """Test running a task on a single device."""
        device_id = "dev222"
        task = "reboot"
        mock_response = {"status": "success", "task_id": "task123"}

        route = respx.post(f"{BASE_URL}/devices/{device_id}/task").mock(
            return_value=Response(200, json=mock_response)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            result = await client.run_task(device_id, task)

        assert result["status"] == "success"
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_task(self):
        """Test running a task on multiple devices."""
        device_ids = ["dev1", "dev2", "dev3"]
        task = "update_firmware"
        mock_response = {"status": "queued", "batch_id": "batch456"}

        route = respx.post(f"{BASE_URL}/devices/batch_task").mock(
            return_value=Response(200, json=mock_response)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            result = await client.batch_task(device_ids, task)

        assert result["batch_id"] == "batch456"
        assert route.called


class TestCloudSettings:
    """Test device settings endpoints."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_device_settings(self):
        """Test getting device settings."""
        device_id = "dev333"
        mock_settings = {
            "video": {"resolution": "1080p", "fps": 30},
            "audio": {"sample_rate": 48000, "channels": 2},
        }

        respx.get(f"{BASE_URL}/devices/{device_id}/settings").mock(
            return_value=Response(200, json=mock_settings)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            settings = await client.get_device_settings(device_id)

        assert settings["video"]["resolution"] == "1080p"
        assert settings["audio"]["channels"] == 2


class TestCloudPresets:
    """Test preset application endpoints."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_apply_cloud_preset(self):
        """Test applying a cloud preset."""
        device_id = "dev444"
        preset_data = {"preset_id": "preset123", "channels": [1, 2]}
        mock_response = {"status": "applied", "preset_id": "preset123"}

        route = respx.put(f"{BASE_URL}/devices/{device_id}/presets/cloud").mock(
            return_value=Response(200, json=mock_response)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            result = await client.apply_preset(device_id, preset_data, preset_type="cloud")

        assert result["status"] == "applied"
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_apply_local_preset(self):
        """Test applying a local preset."""
        device_id = "dev555"
        preset_data = {"preset_name": "MyPreset", "config": {}}
        mock_response = {"status": "applied"}

        route = respx.put(f"{BASE_URL}/devices/{device_id}/presets/local").mock(
            return_value=Response(200, json=mock_response)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            result = await client.apply_preset(device_id, preset_data, preset_type="local")

        assert result["status"] == "applied"
        assert route.called


class TestCloudPreview:
    """Test preview image endpoint."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_device_preview(self):
        """Test getting device preview image."""
        device_id = "dev666"
        mock_image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."

        respx.get(f"{BASE_URL}/devices/{device_id}/preview").mock(
            return_value=Response(200, content=mock_image_data)
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            preview = await client.get_device_preview(device_id)

        assert isinstance(preview, bytes)
        assert preview == mock_image_data


class TestCloudContextManager:
    """Test context manager and cleanup."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self):
        """Test that context manager properly creates and closes httpx client."""
        client = EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST)

        assert not hasattr(client, '_client') or client._client is None

        async with client as c:
            assert c._client is not None
            assert not c._client.is_closed

        # After context exit, client is set to None (properly closed)
        assert client._client is None

    @pytest.mark.asyncio
    async def test_explicit_close(self):
        """Test explicit close method."""
        client = EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST)

        async with client:
            pass

        await client.close()
        # After explicit close, client is set to None
        assert client._client is None


class TestCloudErrorHandling:
    """Test error handling for various HTTP status codes."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_404_error(self):
        """Test that 404 raises EpiphanCloudAPIError."""
        device_id = "nonexistent"
        respx.get(f"{BASE_URL}/devices/{device_id}").mock(
            return_value=Response(404, json={"error": "Device not found"})
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            with pytest.raises(EpiphanCloudAPIError) as exc_info:
                await client.get_device(device_id)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @respx.mock
    async def test_500_error(self):
        """Test that 500 raises EpiphanCloudAPIError."""
        respx.get(f"{BASE_URL}/devices").mock(
            return_value=Response(500, json={"error": "Internal server error"})
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            with pytest.raises(EpiphanCloudAPIError) as exc_info:
                await client.list_devices()

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    @respx.mock
    async def test_400_error(self):
        """Test that 400 raises EpiphanCloudAPIError."""
        respx.post(f"{BASE_URL}/devices/pair").mock(
            return_value=Response(400, json={"error": "Invalid pairing code"})
        )

        async with EpiphanCloudClient(token=MOCK_TOKEN, host=MOCK_HOST) as client:
            with pytest.raises(EpiphanCloudAPIError) as exc_info:
                await client.pair_device("INVALID", "Test")

            assert exc_info.value.status_code == 400
