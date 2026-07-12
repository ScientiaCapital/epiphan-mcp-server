"""Unit tests for MCP server tools.

Tests the FastMCP server tool implementations using mocked HTTP responses.

Note: FastMCP 2.x decorates tool functions as FunctionTool objects.
To test the underlying function, we access it via .fn attribute.
"""

from unittest.mock import patch

import pytest
import respx
from httpx import Response

from epiphan_mcp.config import Settings

from .fixtures.responses import (
    AFU_STATUS_RESPONSE,
    CONTROL_SUCCESS_RESPONSE,
    DEVICE_RESPONSE,
    ERROR_RESPONSE,
    EVENTS_RESPONSE,
    INPUTS_RESPONSE,
    LAYOUTS_RESPONSE,
    PUBLISHER_STATUS_STOPPED,
    PUBLISHER_STATUS_STREAMING,
    RECORDER_STATUS_RECORDING,
    RECORDER_STATUS_STOPPED,
    STORAGE_LOW_SPACE_RESPONSE,
    STORAGE_RESPONSE,
)

# ============================================================
# Helper to patch settings
# ============================================================


def create_test_settings(devices: str = "192.168.1.100", fleet_name: str = "test") -> Settings:
    """Create settings for testing."""
    return Settings(
        devices=devices,
        username="admin",
        password="testpass",
        use_https=False,
        timeout=5.0,
        verify_ssl=False,
        fleet_name=fleet_name,
    )


# ============================================================
# Device Status Tool Tests
# ============================================================


class TestGetDeviceStatus:
    """Tests for get_device_status tool."""

    async def test_get_device_status_success(self, mock_pearl_host: str):
        """Test successful device status retrieval."""
        from epiphan_mcp.server import get_device_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                # Note: server passes int (1), client expects str
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Access underlying function via .fn
                result = await get_device_status.fn(device_id="default")

        assert result.success is True
        assert result.device == mock_pearl_host
        assert result.status["recording"] == "stopped"
        assert result.status["model"] == "Pearl-2"

    async def test_get_device_status_recording(self, mock_pearl_host: str):
        """Test device status while recording."""
        from epiphan_mcp.server import get_device_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_RECORDING)
                )

                result = await get_device_status.fn(device_id="default")

        assert result.success is True
        assert result.status["recording"] == "recording"

    async def test_get_device_status_no_devices_configured(self):
        """Test device status with no configured devices."""
        from epiphan_mcp.server import get_device_status

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await get_device_status.fn(device_id="default")

        assert result.success is False
        assert hasattr(result, "error")

    async def test_get_device_status_api_error(self, mock_pearl_host: str):
        """Test device status with API error."""
        from epiphan_mcp.server import get_device_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_device_status.fn(device_id="default")

        # get_system_status handles errors gracefully
        assert result.success is True


class TestListDevices:
    """Tests for list_devices tool."""

    async def test_list_devices_single(self, mock_pearl_host: str):
        """Test listing single device."""
        from epiphan_mcp.server import list_devices

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            result = await list_devices.fn()

        assert result.success is True
        assert result.device_count == 1
        assert result.devices[0]["host"] == mock_pearl_host
        assert result.devices[0]["index"] == 0

    async def test_list_devices_multiple(self):
        """Test listing multiple devices."""
        from epiphan_mcp.server import list_devices

        devices = "192.168.1.100,192.168.1.101,192.168.1.102"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(
                devices=devices, fleet_name="multi-fleet"
            )

            result = await list_devices.fn()

        assert result.success is True
        assert result.device_count == 3
        assert result.fleet_name == "multi-fleet"
        assert len(result.devices) == 3

    async def test_list_devices_empty(self):
        """Test listing with no devices configured."""
        from epiphan_mcp.server import list_devices

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await list_devices.fn()

        assert result.success is True
        assert result.device_count == 0


# ============================================================
# Recording Tool Tests
# ============================================================


class TestStartRecording:
    """Tests for start_recording tool."""

    async def test_start_recording_success(self, mock_pearl_host: str):
        """Test successful recording start."""
        from epiphan_mcp.server import start_recording

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                # Server passes int 1, which gets converted to path
                router.post(f"{api_base}/recorders/recorder-1/control/start").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await start_recording.fn(device_id="default", recorder=1)

        assert result.success is True
        assert "started" in result.message.lower()

    async def test_start_recording_api_error(self, mock_pearl_host: str):
        """Test recording start with API error."""
        from epiphan_mcp.server import start_recording

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/recorders/recorder-1/control/start").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await start_recording.fn(device_id="default", recorder=1)

        assert result.success is False
        assert hasattr(result, "error")


class TestStopRecording:
    """Tests for stop_recording tool."""

    async def test_stop_recording_success(self, mock_pearl_host: str):
        """Test successful recording stop."""
        from epiphan_mcp.server import stop_recording

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/recorders/recorder-1/control/stop").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await stop_recording.fn(device_id="default", recorder=1)

        assert result.success is True
        assert "stopped" in result.message.lower()


class TestGetRecordingStatus:
    """Tests for get_recording_status tool."""

    async def test_get_recording_status_stopped(self, mock_pearl_host: str):
        """Test getting stopped recording status."""
        from epiphan_mcp.server import get_recording_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_recording_status.fn(device_id="default", recorder=1)

        assert result.success is True
        assert result.state == "stopped"
        assert result.duration_seconds == 0

    async def test_get_recording_status_recording(self, mock_pearl_host: str):
        """Test getting recording status while recording."""
        from epiphan_mcp.server import get_recording_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_RECORDING)
                )

                result = await get_recording_status.fn(device_id="default", recorder=1)

        assert result.success is True
        assert result.state == "recording"
        assert result.duration_seconds == 3600


# ============================================================
# Streaming Tool Tests
# ============================================================


class TestStartStream:
    """Tests for start_stream tool."""

    async def test_start_stream_success(self, mock_pearl_host: str):
        """Test successful stream start."""
        from epiphan_mcp.server import start_stream

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                # Note: server calls start_stream(channel) which calls
                # client.start_all_publishers(channel_id)
                router.post(f"{api_base}/channels/channel-1/publishers/control/start").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await start_stream.fn(device_id="default", channel=1)

        assert result["success"] is True


class TestStopStream:
    """Tests for stop_stream tool."""

    async def test_stop_stream_success(self, mock_pearl_host: str):
        """Test successful stream stop."""
        from epiphan_mcp.server import stop_stream

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/channels/channel-1/publishers/control/stop").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await stop_stream.fn(device_id="default", channel=1)

        assert result["success"] is True


class TestGetStreamStatus:
    """Tests for get_stream_status tool."""

    async def test_get_stream_status_streaming(self, mock_pearl_host: str):
        """Test getting status of active stream."""
        from epiphan_mcp.server import get_stream_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/channels/channel-1/publishers/publisher-1/status").mock(
                    return_value=Response(200, json=PUBLISHER_STATUS_STREAMING)
                )

                result = await get_stream_status.fn(
                    device_id="default", channel=1, publisher="publisher-1"
                )

        assert result["success"] is True
        assert result["state"] == "streaming"
        assert result["duration_seconds"] == 1800
        assert result["bitrate_bps"] == 6000000
        assert result["bytes_sent"] == 1350000000

    async def test_get_stream_status_stopped(self, mock_pearl_host: str):
        """Test getting status of stopped stream."""
        from epiphan_mcp.server import get_stream_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/channels/channel-1/publishers/publisher-1/status").mock(
                    return_value=Response(200, json=PUBLISHER_STATUS_STOPPED)
                )

                result = await get_stream_status.fn(
                    device_id="default", channel=1, publisher="publisher-1"
                )

        assert result["success"] is True
        assert result["state"] == "stopped"
        assert result["duration_seconds"] == 0

    async def test_get_stream_status_api_error(self, mock_pearl_host: str):
        """Test stream status with API error."""
        from epiphan_mcp.server import get_stream_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/channels/channel-1/publishers/publisher-1/status").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await get_stream_status.fn(
                    device_id="default", channel=1, publisher="publisher-1"
                )

        assert result["success"] is False
        assert "error" in result

    async def test_get_stream_status_invalid_device(self):
        """Test stream status with invalid device ID."""
        from epiphan_mcp.server import get_stream_status

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await get_stream_status.fn(
                device_id="nonexistent", channel=1, publisher="publisher-1"
            )

        assert result["success"] is False
        assert "error" in result


# ============================================================
# Bookmark Tool Tests
# ============================================================


class TestAddBookmark:
    """Tests for add_bookmark tool."""

    async def test_add_bookmark_success(self, mock_pearl_host: str):
        """Test successful bookmark addition."""
        from epiphan_mcp.server import add_bookmark

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/channels/channel-1/bookmarks").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await add_bookmark.fn(
                    device_id="default", channel=1, text="Important moment"
                )

        assert result.success is True
        assert result.channel == "channel-1"
        assert result.text == "Important moment"

    async def test_add_bookmark_no_text(self, mock_pearl_host: str):
        """Test bookmark without text."""
        from epiphan_mcp.server import add_bookmark

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/channels/channel-1/bookmarks").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await add_bookmark.fn(device_id="default", channel=1)

        assert result.success is True

    async def test_add_bookmark_api_error(self, mock_pearl_host: str):
        """Test bookmark with API error."""
        from epiphan_mcp.server import add_bookmark

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/channels/channel-1/bookmarks").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await add_bookmark.fn(device_id="default", channel=1)

        assert result.success is False
        assert result.error is not None

    async def test_add_bookmark_invalid_device(self):
        """Test bookmark with invalid device."""
        from epiphan_mcp.server import add_bookmark

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await add_bookmark.fn(device_id="nonexistent", channel=1)

        assert result.success is False
        assert result.error is not None


# ============================================================
# Layout Tool Tests
# ============================================================


class TestListLayouts:
    """Tests for list_layouts tool."""

    async def test_list_layouts_success(self, mock_pearl_host: str):
        """Test successful layout listing."""
        from epiphan_mcp.server import list_layouts

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/channels/channel-1/layouts").mock(
                    return_value=Response(200, json=LAYOUTS_RESPONSE)
                )

                result = await list_layouts.fn(device_id="default", channel=1)

        assert result.success is True
        assert result.total_layouts == 3
        assert len(result.layouts) == 3
        assert result.layouts[0]["name"] == "Full Screen"
        assert result.active_layout == "layout-1"

    async def test_list_layouts_api_error(self, mock_pearl_host: str):
        """Test layout listing with API error."""
        from epiphan_mcp.server import list_layouts

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/channels/channel-1/layouts").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await list_layouts.fn(device_id="default", channel=1)

        assert result.success is False
        assert result.error is not None

    async def test_list_layouts_invalid_device(self):
        """Test layout listing with invalid device."""
        from epiphan_mcp.server import list_layouts

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await list_layouts.fn(device_id="nonexistent", channel=1)

        assert result.success is False
        assert result.error is not None


class TestSwitchLayout:
    """Tests for switch_layout tool."""

    async def test_switch_layout_success(self, mock_pearl_host: str):
        """Test successful layout switch."""
        from epiphan_mcp.server import switch_layout

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.put(f"{api_base}/channels/channel-1/layouts/active").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await switch_layout.fn(
                    device_id="default", channel=1, layout_id="layout-2"
                )

        assert result.success is True

    async def test_switch_layout_missing_layout_id(self, mock_pearl_host: str):
        """Test layout switch with missing layout_id."""
        from epiphan_mcp.server import switch_layout

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            result = await switch_layout.fn(device_id="default", channel=1, layout_id="")

        assert result.success is False
        assert "layout_id is required" in result.error


# ============================================================
# Fleet Management Tool Tests
# ============================================================


class TestGetFleetStatus:
    """Tests for get_fleet_status tool."""

    async def test_get_fleet_status_single_device(self, mock_pearl_host: str):
        """Test fleet status with single device."""
        from epiphan_mcp.server import get_fleet_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_fleet_status.fn()

        assert result.success is True
        assert result.total_devices == 1
        assert result.online_devices == 1
        assert result.recording_devices == 0
        assert len(result.devices) == 1
        assert result.devices[0]["online"] is True

    async def test_get_fleet_status_with_recording(self, mock_pearl_host: str):
        """Test fleet status when device is recording."""
        from epiphan_mcp.server import get_fleet_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_RECORDING)
                )

                result = await get_fleet_status.fn()

        assert result.recording_devices == 1
        assert result.devices[0]["recording"] is True

    async def test_get_fleet_status_low_storage_alert(self, mock_pearl_host: str):
        """Test fleet status generates alert for low storage."""
        from epiphan_mcp.server import get_fleet_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_LOW_SPACE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_fleet_status.fn()

        assert result.alerts_count >= 1
        assert any("storage" in alert["message"].lower() for alert in result.alerts)

    async def test_get_fleet_status_no_devices(self):
        """Test fleet status with no devices configured."""
        from epiphan_mcp.server import get_fleet_status

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await get_fleet_status.fn()

        assert result.success is True
        assert result.total_devices == 0
        assert "No devices configured" in result.message

    async def test_get_fleet_status_device_offline(self, mock_pearl_host: str):
        """Test fleet status with offline device."""
        from httpx import ConnectError

        from epiphan_mcp.server import get_fleet_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    side_effect=ConnectError("Connection refused")
                )
                router.get(f"{api_base}/storages").mock(
                    side_effect=ConnectError("Connection refused")
                )

                result = await get_fleet_status.fn()

        assert result.success is True
        assert result.online_devices == 0
        assert result.devices[0]["online"] is False
        assert result.alerts_count >= 1


# ============================================================
# Single Touch Tool Tests
# ============================================================


class TestSingleTouchStart:
    """Tests for single_touch_start tool."""

    async def test_single_touch_start_success(self, mock_pearl_host: str):
        """Test successful single touch start."""
        from epiphan_mcp.server import single_touch_start

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/singletouch/control/start").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await single_touch_start.fn(device_id="default")

        assert result["success"] is True
        assert "started" in result["message"].lower()

    async def test_single_touch_start_api_error(self, mock_pearl_host: str):
        """Test single touch start with API error."""
        from epiphan_mcp.server import single_touch_start

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/singletouch/control/start").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await single_touch_start.fn(device_id="default")

        assert result["success"] is False
        assert "error" in result

    async def test_single_touch_start_invalid_device(self):
        """Test single touch start with invalid device."""
        from epiphan_mcp.server import single_touch_start

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await single_touch_start.fn(device_id="nonexistent")

        assert result["success"] is False
        assert "error" in result


class TestSingleTouchStop:
    """Tests for single_touch_stop tool."""

    async def test_single_touch_stop_success(self, mock_pearl_host: str):
        """Test successful single touch stop."""
        from epiphan_mcp.server import single_touch_stop

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/singletouch/control/stop").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await single_touch_stop.fn(device_id="default")

        assert result["success"] is True
        assert "stopped" in result["message"].lower()

    async def test_single_touch_stop_api_error(self, mock_pearl_host: str):
        """Test single touch stop with API error."""
        from epiphan_mcp.server import single_touch_stop

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/singletouch/control/stop").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await single_touch_stop.fn(device_id="default")

        assert result["success"] is False
        assert "error" in result

    async def test_single_touch_stop_invalid_device(self):
        """Test single touch stop with invalid device."""
        from epiphan_mcp.server import single_touch_stop

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await single_touch_stop.fn(device_id="nonexistent")

        assert result["success"] is False
        assert "error" in result


# ============================================================
# Scheduled Events Tool Tests
# ============================================================


class TestGetScheduledEvents:
    """Tests for get_scheduled_events tool."""

    async def test_get_scheduled_events_success(self, mock_pearl_host: str):
        """Test successful retrieval of scheduled events."""
        from epiphan_mcp.server import get_scheduled_events

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/schedule/events").mock(
                    return_value=Response(200, json=EVENTS_RESPONSE)
                )

                result = await get_scheduled_events.fn(device_id="default")

        assert result["success"] is True
        assert result["total_events"] == 2
        assert len(result["events"]) == 2
        assert result["events"][0]["name"] == "Morning Lecture"

    async def test_get_scheduled_events_empty(self, mock_pearl_host: str):
        """Test when no events are scheduled."""
        from epiphan_mcp.server import get_scheduled_events

        api_base = f"http://{mock_pearl_host}/api/v2.0"
        empty_response = {"status": "ok", "result": []}

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/schedule/events").mock(
                    return_value=Response(200, json=empty_response)
                )

                result = await get_scheduled_events.fn(device_id="default")

        assert result["success"] is True
        assert result["total_events"] == 0

    async def test_get_scheduled_events_api_error(self, mock_pearl_host: str):
        """Test scheduled events with API error."""
        from epiphan_mcp.server import get_scheduled_events

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/schedule/events").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await get_scheduled_events.fn(device_id="default")

        assert result["success"] is False
        assert "error" in result

    async def test_get_scheduled_events_invalid_device(self):
        """Test scheduled events with invalid device."""
        from epiphan_mcp.server import get_scheduled_events

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await get_scheduled_events.fn(device_id="nonexistent")

        assert result["success"] is False
        assert "error" in result


class TestBatchStartRecording:
    """Tests for batch_start_recording tool."""

    async def test_batch_start_all_devices(self, mock_pearl_host: str):
        """Test batch start on all devices."""
        from epiphan_mcp.server import batch_start_recording

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/recorders/recorder-1/control/start").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await batch_start_recording.fn(device_ids="all")

        assert result.success is True
        assert result.total_devices == 1
        assert result.successful == 1
        assert result.failed == 0

    async def test_batch_start_specific_devices(self):
        """Test batch start on specific devices."""
        from epiphan_mcp.server import batch_start_recording

        devices = "192.168.1.100,192.168.1.101"
        api_base1 = "http://192.168.1.100/api/v2.0"
        api_base2 = "http://192.168.1.101/api/v2.0"

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base1}/recorders/recorder-1/control/start").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )
                router.post(f"{api_base2}/recorders/recorder-1/control/start").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await batch_start_recording.fn(device_ids=devices)

        assert result.success is True
        assert result.total_devices == 2
        assert result.successful == 2

    async def test_batch_start_partial_failure(self):
        """Test batch start with some failures."""
        from httpx import ConnectError

        from epiphan_mcp.server import batch_start_recording

        devices = "192.168.1.100,192.168.1.101"
        api_base1 = "http://192.168.1.100/api/v2.0"
        api_base2 = "http://192.168.1.101/api/v2.0"

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base1}/recorders/recorder-1/control/start").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )
                router.post(f"{api_base2}/recorders/recorder-1/control/start").mock(
                    side_effect=ConnectError("Connection refused")
                )

                result = await batch_start_recording.fn(device_ids="all")

        assert result.success is False  # Not all succeeded
        assert result.successful == 1
        assert result.failed == 1

    async def test_batch_start_no_devices(self):
        """Test batch start with no devices."""
        from epiphan_mcp.server import batch_start_recording

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await batch_start_recording.fn(device_ids="all")

        assert result.success is False
        assert "No devices" in result.error


class TestBatchStopRecording:
    """Tests for batch_stop_recording tool."""

    async def test_batch_stop_all_devices(self, mock_pearl_host: str):
        """Test batch stop on all devices."""
        from epiphan_mcp.server import batch_stop_recording

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/recorders/recorder-1/control/stop").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await batch_stop_recording.fn(device_ids="all")

        assert result.success is True
        assert result.total_devices == 1
        assert result.successful == 1


# ============================================================
# Configuration Tests
# ============================================================


class TestConfigSettings:
    """Tests for configuration handling."""

    def test_settings_get_device_list(self):
        """Test parsing device list."""
        settings = create_test_settings(devices="192.168.1.100,192.168.1.101")
        devices = settings.get_device_list()

        assert len(devices) == 2
        assert "192.168.1.100" in devices
        assert "192.168.1.101" in devices

    def test_settings_get_device_list_empty(self):
        """Test parsing empty device list."""
        settings = create_test_settings(devices="")
        devices = settings.get_device_list()

        assert len(devices) == 0

    def test_settings_get_device_host_default(self):
        """Test getting default device."""
        settings = create_test_settings(devices="192.168.1.100,192.168.1.101")
        host = settings.get_device_host("default")

        assert host == "192.168.1.100"

    def test_settings_get_device_host_by_index(self):
        """Test getting device by index."""
        settings = create_test_settings(devices="192.168.1.100,192.168.1.101")

        assert settings.get_device_host("0") == "192.168.1.100"
        assert settings.get_device_host("1") == "192.168.1.101"

    def test_settings_get_device_host_direct(self):
        """Test using direct hostname."""
        settings = create_test_settings(devices="192.168.1.100")
        host = settings.get_device_host("10.0.0.50")

        assert host == "10.0.0.50"  # Direct IP passed through

    def test_settings_get_device_host_no_default(self):
        """Test getting default with no devices raises."""
        settings = create_test_settings(devices="")

        with pytest.raises(ValueError, match="No default device"):
            settings.get_device_host("default")

    def test_settings_get_device_host_index_out_of_range(self):
        """Test invalid index raises."""
        settings = create_test_settings(devices="192.168.1.100")

        with pytest.raises(ValueError, match="out of range"):
            settings.get_device_host("5")


# ============================================================
# Server Error Branch Tests (for 100% coverage)
# ============================================================


class TestServerErrorBranches:
    """Tests for server tool error handling branches."""

    async def test_get_device_status_pearl_api_error(self, mock_pearl_host: str):
        """Test get_device_status handles PearlAPIError from recorder status."""
        from epiphan_mcp.server import get_device_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                # Recorder returns error
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json={"status": "error", "message": "Recorder busy"})
                )

                result = await get_device_status.fn(device_id="default")

        # The error is caught and returned
        assert result.success is False
        assert "Recorder busy" in result.error

    async def test_stop_recording_api_error(self, mock_pearl_host: str):
        """Test stop_recording handles PearlAPIError."""
        from epiphan_mcp.server import stop_recording

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/recorders/recorder-1/control/stop").mock(
                    return_value=Response(200, json={"status": "error", "message": "Not recording"})
                )

                result = await stop_recording.fn(device_id="default", recorder=1)

        assert result.success is False
        assert "Not recording" in result.error

    async def test_stop_recording_value_error(self):
        """Test stop_recording handles ValueError (no devices configured)."""
        from epiphan_mcp.server import stop_recording

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")
            result = await stop_recording.fn(device_id="default", recorder=1)

        assert result.success is False
        assert "No default device" in result.error

    async def test_get_recording_status_api_error(self, mock_pearl_host: str):
        """Test get_recording_status handles PearlAPIError."""
        from epiphan_mcp.server import get_recording_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(
                        200, json={"status": "error", "message": "Recorder not found"}
                    )
                )

                result = await get_recording_status.fn(device_id="default", recorder=1)

        assert result.success is False
        assert "Recorder not found" in result.error

    async def test_get_recording_status_value_error(self):
        """Test get_recording_status handles ValueError."""
        from epiphan_mcp.server import get_recording_status

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")
            result = await get_recording_status.fn(device_id="default", recorder=1)

        assert result.success is False
        assert "No default device" in result.error

    async def test_start_stream_api_error(self, mock_pearl_host: str):
        """Test start_stream handles PearlAPIError."""
        from epiphan_mcp.server import start_stream

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/channels/channel-1/publishers/control/start").mock(
                    return_value=Response(
                        200, json={"status": "error", "message": "No publishers configured"}
                    )
                )

                result = await start_stream.fn(device_id="default", channel=1)

        assert result["success"] is False
        assert "No publishers configured" in result["error"]

    async def test_start_stream_value_error(self):
        """Test start_stream handles ValueError."""
        from epiphan_mcp.server import start_stream

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")
            result = await start_stream.fn(device_id="default", channel=1)

        assert result["success"] is False
        assert "No default device" in result["error"]

    async def test_stop_stream_api_error(self, mock_pearl_host: str):
        """Test stop_stream handles PearlAPIError."""
        from epiphan_mcp.server import stop_stream

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base}/channels/channel-1/publishers/control/stop").mock(
                    return_value=Response(200, json={"status": "error", "message": "Not streaming"})
                )

                result = await stop_stream.fn(device_id="default", channel=1)

        assert result["success"] is False
        assert "Not streaming" in result["error"]

    async def test_stop_stream_value_error(self):
        """Test stop_stream handles ValueError."""
        from epiphan_mcp.server import stop_stream

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")
            result = await stop_stream.fn(device_id="default", channel=1)

        assert result["success"] is False
        assert "No default device" in result["error"]

    async def test_switch_layout_api_error(self, mock_pearl_host: str):
        """Test switch_layout handles PearlAPIError."""
        from epiphan_mcp.server import switch_layout

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.put(f"{api_base}/channels/channel-1/layouts/active").mock(
                    return_value=Response(
                        200, json={"status": "error", "message": "Layout not found"}
                    )
                )

                result = await switch_layout.fn(
                    device_id="default", channel=1, layout_id="bad-layout"
                )

        assert result.success is False
        assert "Layout not found" in result.error

    async def test_switch_layout_value_error(self):
        """Test switch_layout handles ValueError."""
        from epiphan_mcp.server import switch_layout

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")
            result = await switch_layout.fn(device_id="default", channel=1, layout_id="layout-1")

        assert result.success is False
        assert "No default device" in result.error

    async def test_batch_stop_recording_partial_failure(self):
        """Test batch_stop_recording with partial failure."""
        from httpx import ConnectError

        from epiphan_mcp.server import batch_stop_recording

        devices = "192.168.1.100,192.168.1.101"
        api_base1 = "http://192.168.1.100/api/v2.0"
        api_base2 = "http://192.168.1.101/api/v2.0"

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                # First device succeeds
                router.post(f"{api_base1}/recorders/recorder-1/control/stop").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )
                # Second device fails
                router.post(f"{api_base2}/recorders/recorder-1/control/stop").mock(
                    side_effect=ConnectError("Connection refused")
                )

                result = await batch_stop_recording.fn(device_ids="all")

        assert result.success is False
        assert result.successful == 1
        assert result.failed == 1

    async def test_batch_stop_recording_no_devices(self):
        """Test batch_stop_recording with no devices."""
        from epiphan_mcp.server import batch_stop_recording

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")
            result = await batch_stop_recording.fn(device_ids="all")

        assert result.success is False
        assert "No devices specified" in result.error

    async def test_start_recording_value_error(self):
        """Test start_recording handles ValueError."""
        from epiphan_mcp.server import start_recording

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")
            result = await start_recording.fn(device_id="default", recorder=1)

        assert result.success is False
        assert "No default device" in result.error

    async def test_batch_stop_recording_specific_devices(self):
        """Test batch_stop_recording with specific device IDs (not 'all')."""
        from epiphan_mcp.server import batch_stop_recording

        specific_devices = "192.168.1.100,192.168.1.101"
        api_base1 = "http://192.168.1.100/api/v2.0"
        api_base2 = "http://192.168.1.101/api/v2.0"

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="192.168.1.200")

            with respx.mock(assert_all_called=False) as router:
                router.post(f"{api_base1}/recorders/recorder-1/control/stop").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )
                router.post(f"{api_base2}/recorders/recorder-1/control/stop").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                # Pass specific device IDs, not "all"
                result = await batch_stop_recording.fn(device_ids=specific_devices)

        assert result.success is True
        assert result.total_devices == 2
        assert result.successful == 2


# ============================================================
# Predictive Maintenance Tool Tests
# ============================================================


class TestPredictStorageFull:
    """Tests for predict_storage_full tool."""

    async def test_predict_storage_recording(self, mock_pearl_host: str):
        """Test storage prediction while recording."""
        from epiphan_mcp.server import predict_storage_full

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_RECORDING)
                )

                result = await predict_storage_full.fn(device_id="default")

        assert result.success is True
        assert result.hours_until_full is not None
        assert result.hours_until_full > 0
        assert result.is_recording is True
        assert result.storage_free_gb is not None

    async def test_predict_storage_not_recording(self, mock_pearl_host: str):
        """Test storage prediction when not recording."""
        from epiphan_mcp.server import predict_storage_full

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await predict_storage_full.fn(device_id="default")

        assert result.success is True
        assert result.is_recording is False
        # Should still provide estimate based on assumed bitrate

    async def test_predict_storage_low_space(self, mock_pearl_host: str):
        """Test storage prediction with low space warning."""
        from epiphan_mcp.server import predict_storage_full

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_LOW_SPACE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_RECORDING)
                )

                result = await predict_storage_full.fn(device_id="default")

        assert result.success is True
        assert result.warning is True  # Low space warning

    async def test_predict_storage_api_error(self, mock_pearl_host: str):
        """Test storage prediction with API error."""
        from epiphan_mcp.server import predict_storage_full

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                # Recorder returns error
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await predict_storage_full.fn(device_id="default")

        assert result.success is False
        assert result.error is not None

    async def test_predict_storage_invalid_device(self):
        """Test storage prediction with invalid device."""
        from epiphan_mcp.server import predict_storage_full

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await predict_storage_full.fn(device_id="nonexistent")

        assert result.success is False
        assert result.error is not None


# ============================================================
# Device Health Score Tool Tests
# ============================================================


class TestGetDeviceHealthScore:
    """Tests for get_device_health_score AI tool."""

    async def test_health_score_healthy_device(self, mock_pearl_host: str):
        """Test health score for a fully healthy device."""
        from epiphan_mcp.server import get_device_health_score

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_device_health_score.fn(device_id="default")

        assert result.success is True
        assert result.score is not None
        assert 0 <= result.score <= 100
        assert result.score >= 80  # Healthy device should score high
        assert "storage" in result.categories

    async def test_health_score_low_storage(self, mock_pearl_host: str):
        """Test health score with low storage warning."""
        from epiphan_mcp.server import get_device_health_score

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_LOW_SPACE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_device_health_score.fn(device_id="default")

        assert result.success is True
        assert result.score is not None
        assert result.score < 80  # Should be penalized for low storage
        assert result.categories["storage"]["healthy"] is False
        assert result.issues is not None

    async def test_health_score_recording_active(self, mock_pearl_host: str):
        """Test health score while recording (should still be healthy)."""
        from epiphan_mcp.server import get_device_health_score

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_RECORDING)
                )

                result = await get_device_health_score.fn(device_id="default")

        assert result.success is True
        assert result.score is not None
        assert result.score >= 80  # Recording is normal operation
        assert result.is_recording is True

    async def test_health_score_api_error(self, mock_pearl_host: str):
        """Test health score with API error (recorder returns error)."""
        from epiphan_mcp.server import get_device_health_score

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                # Device and storage work
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                # Recorder returns error
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await get_device_health_score.fn(device_id="default")

        # Should succeed with degraded recording score (not a total failure)
        assert result.success is True
        assert result.categories["recording"]["healthy"] is False
        assert "Could not check recorder status" in result.issues

    async def test_health_score_invalid_device(self):
        """Test health score with invalid device (no devices configured)."""
        from epiphan_mcp.server import get_device_health_score

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            # No devices configured, using "default" should raise ValueError
            mock_settings.return_value = create_test_settings(devices="")

            result = await get_device_health_score.fn(device_id="default")

        assert result.success is False
        assert result.error is not None


# ============================================================
# Input Source Tool Tests
# ============================================================


class TestListInputs:
    """Tests for list_inputs tool."""

    async def test_list_inputs_success(self, mock_pearl_host: str):
        """Test successful input listing."""
        from epiphan_mcp.server import list_inputs

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/inputs").mock(
                    return_value=Response(200, json=INPUTS_RESPONSE)
                )

                result = await list_inputs.fn(device_id="default")

        assert result.success is True
        assert result.total_inputs == 3
        assert len(result.inputs) == 3
        # Verify first input (model uses 'id' and 'type' as field names)
        assert result.inputs[0]["id"] == "hdmi-1"
        assert result.inputs[0]["type"] == "hdmi"

    async def test_list_inputs_empty(self, mock_pearl_host: str):
        """Test input listing with no inputs."""
        from epiphan_mcp.server import list_inputs

        api_base = f"http://{mock_pearl_host}/api/v2.0"
        empty_response = {"status": "ok", "result": []}

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/inputs").mock(
                    return_value=Response(200, json=empty_response)
                )

                result = await list_inputs.fn(device_id="default")

        assert result.success is True
        assert result.total_inputs == 0

    async def test_list_inputs_api_error(self, mock_pearl_host: str):
        """Test input listing with API error."""
        from epiphan_mcp.server import list_inputs

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/inputs").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await list_inputs.fn(device_id="default")

        assert result.success is False
        assert hasattr(result, "error")

    async def test_list_inputs_invalid_device(self):
        """Test input listing with invalid device."""
        from epiphan_mcp.server import list_inputs

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await list_inputs.fn(device_id="nonexistent")

        assert result.success is False
        assert hasattr(result, "error")


# ============================================================
# Storage Report Tool Tests
# ============================================================


class TestGetStorageReport:
    """Tests for get_storage_report tool."""

    async def test_get_storage_report_success(self, mock_pearl_host: str):
        """Test successful storage report."""
        from epiphan_mcp.server import get_storage_report

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )

                result = await get_storage_report.fn(device_id="default")

        assert result.success is True
        assert result.total_storages == 1
        assert len(result.storages) == 1
        assert hasattr(result, "summary")
        assert result.summary["total_gb"] > 0
        assert result.summary["free_gb"] > 0
        assert result.summary["used_percent"] == 20.0

    async def test_get_storage_report_low_space(self, mock_pearl_host: str):
        """Test storage report with low space."""
        from epiphan_mcp.server import get_storage_report

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_LOW_SPACE_RESPONSE)
                )

                result = await get_storage_report.fn(device_id="default")

        assert result.success is True
        assert result.summary["used_percent"] == 90.0

    async def test_get_storage_report_api_error(self, mock_pearl_host: str):
        """Test storage report with API error."""
        from epiphan_mcp.server import get_storage_report

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await get_storage_report.fn(device_id="default")

        assert result.success is False
        assert hasattr(result, "error")

    async def test_get_storage_report_invalid_device(self):
        """Test storage report with invalid device."""
        from epiphan_mcp.server import get_storage_report

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await get_storage_report.fn(device_id="nonexistent")

        assert result.success is False
        assert hasattr(result, "error")


# ============================================================
# AFU Status Tool Tests
# ============================================================


class TestGetAfuStatus:
    """Tests for get_afu_status tool."""

    async def test_get_afu_status_success(self, mock_pearl_host: str):
        """Test successful AFU status retrieval."""
        from epiphan_mcp.server import get_afu_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/afu/status").mock(
                    return_value=Response(200, json=AFU_STATUS_RESPONSE)
                )

                result = await get_afu_status.fn(device_id="default")

        assert result.success is True
        assert result.total_destinations == 1
        assert len(result.destinations) == 1
        assert result.destinations[0]["id"] == "afu-1"
        assert result.destinations[0]["protocol"] == "s3"
        assert hasattr(result, "summary")
        assert result.summary["total_queued_files"] == 0

    async def test_get_afu_status_with_uploads(self, mock_pearl_host: str):
        """Test AFU status with active uploads."""
        from epiphan_mcp.server import get_afu_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"
        uploading_response = {
            "status": "ok",
            "result": [
                {
                    "id": "afu-1",
                    "name": "S3 Upload",
                    "protocol": "s3",
                    "state": "uploading",
                    "queue_count": 3,
                    "destination": "s3://my-bucket/recordings/",
                },
                {
                    "id": "afu-2",
                    "name": "FTP Backup",
                    "protocol": "ftp",
                    "state": "idle",
                    "queue_count": 0,
                    "destination": "ftp://backup.example.com/",
                },
            ],
        }

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/afu/status").mock(
                    return_value=Response(200, json=uploading_response)
                )

                result = await get_afu_status.fn(device_id="default")

        assert result.success is True
        assert result.total_destinations == 2
        assert result.summary["total_queued_files"] == 3
        assert result.summary["uploading_count"] == 1

    async def test_get_afu_status_with_errors(self, mock_pearl_host: str):
        """Test AFU status with error state."""
        from epiphan_mcp.server import get_afu_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"
        error_response = {
            "status": "ok",
            "result": [
                {
                    "id": "afu-1",
                    "name": "S3 Upload",
                    "protocol": "s3",
                    "state": "error",
                    "queue_count": 5,
                    "destination": "s3://my-bucket/recordings/",
                },
            ],
        }

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/afu/status").mock(
                    return_value=Response(200, json=error_response)
                )

                result = await get_afu_status.fn(device_id="default")

        assert result.success is True
        assert result.summary["error_count"] == 1

    async def test_get_afu_status_empty(self, mock_pearl_host: str):
        """Test AFU status with no destinations configured."""
        from epiphan_mcp.server import get_afu_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"
        empty_response = {"status": "ok", "result": []}

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/afu/status").mock(
                    return_value=Response(200, json=empty_response)
                )

                result = await get_afu_status.fn(device_id="default")

        assert result.success is True
        assert result.total_destinations == 0

    async def test_get_afu_status_api_error(self, mock_pearl_host: str):
        """Test AFU status with API error."""
        from epiphan_mcp.server import get_afu_status

        api_base = f"http://{mock_pearl_host}/api/v2.0"

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(mock_pearl_host)

            with respx.mock(assert_all_called=False) as router:
                router.get(f"{api_base}/afu/status").mock(
                    return_value=Response(200, json=ERROR_RESPONSE)
                )

                result = await get_afu_status.fn(device_id="default")

        assert result.success is False
        assert hasattr(result, "error")

    async def test_get_afu_status_invalid_device(self):
        """Test AFU status with invalid device."""
        from epiphan_mcp.server import get_afu_status

        with patch("epiphan_mcp.tools.device.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await get_afu_status.fn(device_id="nonexistent")

        assert result.success is False
        assert hasattr(result, "error")
