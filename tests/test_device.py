"""Integration tests for device status tools.

Tests the tools/device.py module with mocked HTTP responses.
"""

from httpx import ConnectError, Response, TimeoutException

from epiphan_mcp.config import Settings
from epiphan_mcp.tools.device import get_device_status, list_devices

from .conftest import patch_settings
from .fixtures.responses import (
    DEVICE_RESPONSE,
    RECORDER_STATUS_RECORDING,
    RECORDER_STATUS_STOPPED,
    STORAGE_RESPONSE,
)

# ============================================================
# get_device_status Tests
# ============================================================


class TestGetDeviceStatus:
    """Tests for get_device_status tool function."""

    async def test_get_device_status_success(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test successful device status retrieval."""
        # Mock device info endpoint
        respx_mock.get(f"{mock_api_base}/device").mock(
            return_value=Response(200, json=DEVICE_RESPONSE)
        )
        # Mock storage endpoint
        respx_mock.get(f"{mock_api_base}/storages").mock(
            return_value=Response(200, json=STORAGE_RESPONSE)
        )
        # Mock recorder status
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            return_value=Response(200, json=RECORDER_STATUS_STOPPED)
        )

        with patch_settings(test_settings):
            result = await get_device_status("default")

        assert result.success is True
        assert result.device == "192.168.1.100"
        assert hasattr(result, "status")
        assert result.status["model"] == "Pearl-2"
        assert result.status["firmware"] == "4.14.2"
        assert result.status["recording"] == "stopped"
        assert result.status["storage"]["free_gb"] > 0

    async def test_get_device_status_while_recording(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test device status when actively recording."""
        respx_mock.get(f"{mock_api_base}/device").mock(
            return_value=Response(200, json=DEVICE_RESPONSE)
        )
        respx_mock.get(f"{mock_api_base}/storages").mock(
            return_value=Response(200, json=STORAGE_RESPONSE)
        )
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            return_value=Response(200, json=RECORDER_STATUS_RECORDING)
        )

        with patch_settings(test_settings):
            result = await get_device_status("default")

        assert result.success is True
        assert result.status["recording"] == "recording"

    async def test_get_device_status_auth_error(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test device status with 401 authentication error."""
        # get_system_status handles errors gracefully, so we need to fail recorder status
        respx_mock.get(f"{mock_api_base}/device").mock(
            return_value=Response(200, json=DEVICE_RESPONSE)
        )
        respx_mock.get(f"{mock_api_base}/storages").mock(
            return_value=Response(200, json=STORAGE_RESPONSE)
        )
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        with patch_settings(test_settings):
            result = await get_device_status("default")

        assert result.success is False
        assert hasattr(result, "error")
        # The error should mention auth/401
        assert "401" in result.error or "Unauthorized" in result.error

    async def test_get_device_status_connection_error(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test device status with connection error (device offline)."""
        # get_system_status handles errors gracefully, so we need to fail recorder status
        respx_mock.get(f"{mock_api_base}/device").mock(
            return_value=Response(200, json=DEVICE_RESPONSE)
        )
        respx_mock.get(f"{mock_api_base}/storages").mock(
            return_value=Response(200, json=STORAGE_RESPONSE)
        )
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            side_effect=ConnectError("Connection refused")
        )

        with patch_settings(test_settings):
            result = await get_device_status("default")

        assert result.success is False
        assert hasattr(result, "error")
        assert "Connection refused" in result.error

    async def test_get_device_status_timeout(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test device status with timeout."""
        # get_system_status handles errors gracefully, so we need to fail recorder status
        respx_mock.get(f"{mock_api_base}/device").mock(
            return_value=Response(200, json=DEVICE_RESPONSE)
        )
        respx_mock.get(f"{mock_api_base}/storages").mock(
            return_value=Response(200, json=STORAGE_RESPONSE)
        )
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            side_effect=TimeoutException("Request timed out")
        )

        with patch_settings(test_settings):
            result = await get_device_status("default")

        assert result.success is False
        assert hasattr(result, "error")

    async def test_get_device_status_invalid_device(
        self,
        empty_settings: Settings,
        respx_mock,
    ):
        """Test device status with no configured devices (uses default)."""
        # With empty_settings and "default" device_id, get_device_host raises ValueError
        with patch_settings(empty_settings):
            result = await get_device_status("default")

        assert result.success is False
        assert hasattr(result, "error")
        assert "No default device configured" in result.error

    async def test_get_device_status_by_index(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test getting device status using numeric index."""
        respx_mock.get(f"{mock_api_base}/device").mock(
            return_value=Response(200, json=DEVICE_RESPONSE)
        )
        respx_mock.get(f"{mock_api_base}/storages").mock(
            return_value=Response(200, json=STORAGE_RESPONSE)
        )
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            return_value=Response(200, json=RECORDER_STATUS_STOPPED)
        )

        with patch_settings(test_settings):
            result = await get_device_status("0")  # First device by index

        assert result.success is True
        assert result.device == "192.168.1.100"


# ============================================================
# list_devices Tests
# ============================================================


class TestListDevices:
    """Tests for list_devices tool function."""

    async def test_list_devices_multiple(self, test_settings: Settings):
        """Test listing multiple configured devices."""
        with patch_settings(test_settings):
            result = await list_devices()

        assert result.success is True
        assert result.device_count == 2
        assert result.fleet_name == "test-fleet"
        assert len(result.devices) == 2
        assert result.devices[0]["host"] == "192.168.1.100"
        assert result.devices[1]["host"] == "192.168.1.101"

    async def test_list_devices_single(self, single_device_settings: Settings):
        """Test listing single configured device."""
        with patch_settings(single_device_settings):
            result = await list_devices()

        assert result.success is True
        assert result.device_count == 1
        assert result.fleet_name == "single-device"

    async def test_list_devices_empty(self, empty_settings: Settings):
        """Test listing when no devices configured."""
        with patch_settings(empty_settings):
            result = await list_devices()

        assert result.success is True
        assert result.device_count == 0
        assert result.devices == []
