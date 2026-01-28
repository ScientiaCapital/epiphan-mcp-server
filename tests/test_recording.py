"""Integration tests for recording control tools.

Tests the tools/recording.py module with mocked HTTP responses.
"""

from httpx import ConnectError, Response, TimeoutException

from epiphan_mcp.config import Settings
from epiphan_mcp.tools.recording import (
    get_recording_status,
    start_recording,
    stop_recording,
)

from .conftest import patch_settings
from .fixtures.responses import (
    ALREADY_RECORDING_RESPONSE,
    CONTROL_SUCCESS_RESPONSE,
    RECORDER_STATUS_RECORDING,
    RECORDER_STATUS_STOPPED,
)

# ============================================================
# start_recording Tests
# ============================================================


class TestStartRecording:
    """Tests for start_recording tool function."""

    async def test_start_recording_success(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test successful recording start."""
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/start").mock(
            return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
        )

        with patch_settings(test_settings):
            result = await start_recording("default", recorder=1)

        assert result["success"] is True
        assert result["device"] == "192.168.1.100"
        assert "started" in result["message"].lower()

    async def test_start_recording_already_recording(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test starting recording when already recording (idempotent behavior)."""
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/start").mock(
            return_value=Response(200, json=ALREADY_RECORDING_RESPONSE)
        )

        with patch_settings(test_settings):
            result = await start_recording("default", recorder=1)

        # Should still return successfully or handle gracefully
        assert "error" in result or result.get("success") is False

    async def test_start_recording_auth_error(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test starting recording with 401 auth error."""
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/start").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        with patch_settings(test_settings):
            result = await start_recording("default", recorder=1)

        assert result["success"] is False
        assert "error" in result

    async def test_start_recording_connection_error(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test starting recording with connection error."""
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/start").mock(
            side_effect=ConnectError("Connection refused")
        )

        with patch_settings(test_settings):
            result = await start_recording("default", recorder=1)

        assert result["success"] is False
        assert "error" in result
        assert "Connection refused" in result["error"]

    async def test_start_recording_timeout(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test starting recording with timeout."""
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/start").mock(
            side_effect=TimeoutException("Request timed out")
        )

        with patch_settings(test_settings):
            result = await start_recording("default", recorder=1)

        assert result["success"] is False
        assert "error" in result

    async def test_start_recording_recorder_2(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test starting recording on recorder 2."""
        respx_mock.post(f"{mock_api_base}/recorders/recorder-2/control/start").mock(
            return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
        )

        with patch_settings(test_settings):
            result = await start_recording("default", recorder=2)

        assert result["success"] is True

    async def test_start_recording_invalid_device(
        self,
        empty_settings: Settings,
        respx_mock,
    ):
        """Test starting recording with no configured devices (uses default)."""
        # With empty_settings and "default" device_id, get_device_host raises ValueError
        with patch_settings(empty_settings):
            result = await start_recording("default", recorder=1)

        assert result["success"] is False
        assert "error" in result
        assert "No default device configured" in result["error"]


# ============================================================
# stop_recording Tests
# ============================================================


class TestStopRecording:
    """Tests for stop_recording tool function."""

    async def test_stop_recording_success(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test successful recording stop."""
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/stop").mock(
            return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
        )

        with patch_settings(test_settings):
            result = await stop_recording("default", recorder=1)

        assert result["success"] is True
        assert result["device"] == "192.168.1.100"
        assert "stopped" in result["message"].lower()

    async def test_stop_recording_not_recording(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test stopping when not recording (should succeed or handle gracefully)."""
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/stop").mock(
            return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
        )

        with patch_settings(test_settings):
            result = await stop_recording("default", recorder=1)

        # Should succeed even if not recording
        assert result["success"] is True

    async def test_stop_recording_connection_error(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test stopping recording with connection error."""
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/stop").mock(
            side_effect=ConnectError("Connection refused")
        )

        with patch_settings(test_settings):
            result = await stop_recording("default", recorder=1)

        assert result["success"] is False
        assert "error" in result

    async def test_stop_recording_auth_error(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test stopping recording with 401 auth error."""
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/stop").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        with patch_settings(test_settings):
            result = await stop_recording("default", recorder=1)

        assert result["success"] is False
        assert "error" in result


# ============================================================
# get_recording_status Tests
# ============================================================


class TestGetRecordingStatus:
    """Tests for get_recording_status tool function."""

    async def test_get_recording_status_stopped(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test getting status when not recording."""
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            return_value=Response(200, json=RECORDER_STATUS_STOPPED)
        )

        with patch_settings(test_settings):
            result = await get_recording_status("default", recorder=1)

        assert result["success"] is True
        assert result["device"] == "192.168.1.100"
        assert result["recorder"] == 1
        assert result["state"] == "stopped"
        assert result["duration_seconds"] == 0
        assert result["file_size_bytes"] == 0

    async def test_get_recording_status_recording(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test getting status while actively recording."""
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            return_value=Response(200, json=RECORDER_STATUS_RECORDING)
        )

        with patch_settings(test_settings):
            result = await get_recording_status("default", recorder=1)

        assert result["success"] is True
        assert result["state"] == "recording"
        assert result["duration_seconds"] == 3600  # 1 hour
        assert result["file_size_bytes"] == 1073741824  # 1GB
        assert "recording_2025-01-22" in result["filename"]

    async def test_get_recording_status_connection_error(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test getting status with connection error."""
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            side_effect=ConnectError("Connection refused")
        )

        with patch_settings(test_settings):
            result = await get_recording_status("default", recorder=1)

        assert result["success"] is False
        assert "error" in result

    async def test_get_recording_status_auth_error(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test getting status with 401 auth error."""
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        with patch_settings(test_settings):
            result = await get_recording_status("default", recorder=1)

        assert result["success"] is False
        assert "error" in result

    async def test_get_recording_status_recorder_2(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test getting status for recorder 2."""
        respx_mock.get(f"{mock_api_base}/recorders/recorder-2/status").mock(
            return_value=Response(200, json=RECORDER_STATUS_STOPPED)
        )

        with patch_settings(test_settings):
            result = await get_recording_status("default", recorder=2)

        assert result["success"] is True
        assert result["recorder"] == 2

    async def test_get_recording_status_invalid_device(
        self,
        empty_settings: Settings,
        respx_mock,
    ):
        """Test getting status with no configured devices (uses default)."""
        # With empty_settings and "default" device_id, get_device_host raises ValueError
        with patch_settings(empty_settings):
            result = await get_recording_status("default", recorder=1)

        assert result["success"] is False
        assert "error" in result
        assert "No default device configured" in result["error"]


# ============================================================
# Edge Cases and Integration Tests
# ============================================================


class TestRecordingEdgeCases:
    """Edge case and integration tests for recording operations."""

    async def test_full_recording_workflow(
        self,
        test_settings: Settings,
        mock_api_base: str,
        respx_mock,
    ):
        """Test a complete recording workflow: status -> start -> status -> stop."""
        # Mock all endpoints
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            return_value=Response(200, json=RECORDER_STATUS_STOPPED)
        )
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/start").mock(
            return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
        )
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/stop").mock(
            return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
        )

        with patch_settings(test_settings):
            # Check initial status
            status1 = await get_recording_status("default", recorder=1)
            assert status1["success"] is True
            assert status1["state"] == "stopped"

            # Start recording
            start_result = await start_recording("default", recorder=1)
            assert start_result["success"] is True

            # Stop recording
            stop_result = await stop_recording("default", recorder=1)
            assert stop_result["success"] is True

    async def test_recording_on_secondary_device(
        self,
        test_settings: Settings,
        mock_pearl_host_secondary: str,
        respx_mock,
    ):
        """Test recording on secondary device in fleet."""
        secondary_api_base = f"http://{mock_pearl_host_secondary}/api/v2.0"

        respx_mock.post(f"{secondary_api_base}/recorders/recorder-1/control/start").mock(
            return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
        )

        with patch_settings(test_settings):
            result = await start_recording("1", recorder=1)  # Device index 1

        assert result["success"] is True
        assert result["device"] == mock_pearl_host_secondary
