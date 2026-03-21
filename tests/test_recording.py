"""Integration tests for recording control tools.

Tests the tools/recording.py module with mocked HTTP responses.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ConnectError, Response, TimeoutException

from epiphan_mcp.config import Settings
from epiphan_mcp.models import RecorderInfo
from epiphan_mcp.tools.recording import (
    get_all_recorder_status,
    get_recording_status,
    list_archive_files,
    list_recorders,
    start_all_recorders,
    start_recording,
    stop_all_recorders,
    stop_recording,
)

from .conftest import patch_settings
from .fixtures.responses import (
    ALREADY_RECORDING_RESPONSE,
    ARCHIVE_FILES_RESPONSE,
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


# ============================================================
# list_recorders Tests
# ============================================================


class TestListRecorders:
    """Tests for list_recorders tool function."""

    @pytest.mark.asyncio
    async def test_list_recorders_success(self):
        """Test successful listing of recorders."""
        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_recorders = AsyncMock(
            return_value=[
                RecorderInfo(
                    id="recorder-1",
                    name="Channel 1 Recorder",
                    type="mp4",
                    channel_id="channel-1",
                ),
                RecorderInfo(
                    id="recorder-2",
                    name="Channel 2 Recorder",
                    type="mp4",
                    channel_id="channel-2",
                ),
            ]
        )

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_recorders(device_id="default")

        assert result["success"] is True
        assert result["device"] == "192.168.1.100"
        assert result["total_recorders"] == 2
        assert len(result["recorders"]) == 2
        assert result["recorders"][0]["id"] == "recorder-1"

    @pytest.mark.asyncio
    async def test_list_recorders_empty(self):
        """Test listing recorders on device with none configured."""
        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_recorders = AsyncMock(return_value=[])

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_recorders(device_id="default")

        assert result["success"] is True
        assert result["total_recorders"] == 0
        assert result["recorders"] == []

    @pytest.mark.asyncio
    async def test_list_recorders_connection_error(self):
        """Test listing recorders with connection error."""
        from epiphan_mcp.client import PearlAPIError

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(
                __aenter__=AsyncMock(side_effect=PearlAPIError("Connection refused"))
            ),
        ):
            result = await list_recorders(device_id="default")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_recorders_invalid_device(self):
        """Test listing recorders with no configured devices."""
        with patch(
            "epiphan_mcp.tools.recording.get_client",
            side_effect=ValueError("No default device configured"),
        ):
            result = await list_recorders(device_id="default")

        assert result["success"] is False
        assert "No default device configured" in result["error"]


# ============================================================
# list_archive_files Tests
# ============================================================


class TestListArchiveFiles:
    """Tests for list_archive_files tool function."""

    @pytest.mark.asyncio
    async def test_list_archive_files_success(self):
        """Test successful listing of recorded files."""
        mock_files = ARCHIVE_FILES_RESPONSE["result"]
        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_archive_files = AsyncMock(return_value=mock_files)

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_archive_files(device_id="default", recorder=1)

        assert result["success"] is True
        assert result["device"] == "192.168.1.100"
        assert result["recorder"] == "recorder-1"
        assert result["total_files"] == len(mock_files)
        assert len(result["files"]) == len(mock_files)
        mock_client.get_archive_files.assert_called_once_with(
            "recorder-1", from_index=0, limit=100
        )

    @pytest.mark.asyncio
    async def test_list_archive_files_with_pagination(self):
        """Test listing archive files with custom pagination."""
        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_archive_files = AsyncMock(return_value=[])

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_archive_files(
                device_id="default", recorder=1, from_index=10, limit=25
            )

        assert result["success"] is True
        mock_client.get_archive_files.assert_called_once_with(
            "recorder-1", from_index=10, limit=25
        )

    @pytest.mark.asyncio
    async def test_list_archive_files_empty(self):
        """Test listing when no files exist."""
        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_archive_files = AsyncMock(return_value=[])

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_archive_files(device_id="default", recorder=1)

        assert result["success"] is True
        assert result["total_files"] == 0
        assert result["files"] == []

    @pytest.mark.asyncio
    async def test_list_archive_files_connection_error(self):
        """Test listing files with connection error."""
        from epiphan_mcp.client import PearlAPIError

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(
                __aenter__=AsyncMock(side_effect=PearlAPIError("Connection refused"))
            ),
        ):
            result = await list_archive_files(device_id="default", recorder=1)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_archive_files_recorder_2(self):
        """Test listing files for recorder 2."""
        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_archive_files = AsyncMock(return_value=[])

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_archive_files(device_id="default", recorder=2)

        assert result["success"] is True
        assert result["recorder"] == "recorder-2"
        mock_client.get_archive_files.assert_called_once_with(
            "recorder-2", from_index=0, limit=100
        )


class TestGetAllRecorderStatus:
    """Tests for get_all_recorder_status tool."""

    @pytest.mark.asyncio
    async def test_get_all_recorder_status_success(self):
        """Test successful retrieval of all recorder statuses."""
        mock_statuses = [
            AsyncMock(
                id="recorder-1",
                state=AsyncMock(value="recording"),
                duration_seconds=120,
                file_size_bytes=50000000,
                filename="recording_001.mp4",
            ),
            AsyncMock(
                id="recorder-2",
                state=AsyncMock(value="stopped"),
                duration_seconds=0,
                file_size_bytes=0,
                filename="",
            ),
        ]
        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_all_recorder_status = AsyncMock(return_value=mock_statuses)

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await get_all_recorder_status(device_id="default")

        assert result["success"] is True
        assert result["device"] == "192.168.1.100"
        assert result["total_recorders"] == 2
        assert result["recorders"][0]["id"] == "recorder-1"
        assert result["recorders"][0]["state"] == "recording"
        assert result["recorders"][1]["id"] == "recorder-2"
        assert result["recorders"][1]["state"] == "stopped"

    @pytest.mark.asyncio
    async def test_get_all_recorder_status_error(self):
        """Test error handling for get_all_recorder_status."""
        from epiphan_mcp.client import PearlAPIError

        mock_client = AsyncMock()
        mock_client.get_all_recorder_status = AsyncMock(
            side_effect=PearlAPIError("Connection refused")
        )

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await get_all_recorder_status(device_id="default")

        assert result["success"] is False
        assert "Connection refused" in result["error"]


class TestStartAllRecorders:
    """Tests for start_all_recorders tool."""

    @pytest.mark.asyncio
    async def test_start_all_recorders_success(self):
        """Test starting all recorders simultaneously."""
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "success": True,
            "message": "Recording started on all recorder(s)",
            "device": "192.168.1.100",
            "details": {"recorders": "all"},
        }
        mock_client = AsyncMock()
        mock_client.start_all_recorders = AsyncMock(return_value=mock_result)

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await start_all_recorders(device_id="default")

        assert result["success"] is True
        mock_client.start_all_recorders.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_all_recorders_error(self):
        """Test error handling for start_all_recorders."""
        from epiphan_mcp.client import PearlAPIError

        mock_client = AsyncMock()
        mock_client.start_all_recorders = AsyncMock(
            side_effect=PearlAPIError("Device busy")
        )

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await start_all_recorders(device_id="default")

        assert result["success"] is False
        assert "Device busy" in result["error"]


class TestStopAllRecorders:
    """Tests for stop_all_recorders tool."""

    @pytest.mark.asyncio
    async def test_stop_all_recorders_success(self):
        """Test stopping all recorders simultaneously."""
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "success": True,
            "message": "Recording stopped on all recorder(s)",
            "device": "192.168.1.100",
            "details": {"recorders": "all"},
        }
        mock_client = AsyncMock()
        mock_client.stop_all_recorders = AsyncMock(return_value=mock_result)

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await stop_all_recorders(device_id="default")

        assert result["success"] is True
        mock_client.stop_all_recorders.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_all_recorders_error(self):
        """Test error handling for stop_all_recorders."""
        from epiphan_mcp.client import PearlAPIError

        mock_client = AsyncMock()
        mock_client.stop_all_recorders = AsyncMock(
            side_effect=PearlAPIError("Not recording")
        )

        with patch(
            "epiphan_mcp.tools.recording.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await stop_all_recorders(device_id="default")

        assert result["success"] is False
        assert "Not recording" in result["error"]
