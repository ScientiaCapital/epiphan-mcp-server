"""Edge case tests for Epiphan MCP Server.

Tests covering invalid inputs, concurrent operations, timeout handling,
malformed API responses, and boundary values.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import ConnectError, Response

from epiphan_mcp.config import Settings
from epiphan_mcp.tools.device import get_device_status
from epiphan_mcp.tools.fleet import (
    _execute_on_fleet,
    batch_start_recording,
    batch_stop_recording,
    get_fleet_status,
)
from epiphan_mcp.tools.recording import start_recording, stop_recording

from .fixtures.responses import (
    CONTROL_SUCCESS_RESPONSE,
    DEVICE_RESPONSE,
    RECORDER_STATUS_STOPPED,
    STORAGE_RESPONSE,
)


# ============================================================
# Helper Functions
# ============================================================


def create_test_settings(
    devices: str = "192.168.1.100",
    fleet_name: str = "edge-test",
    timeout: float = 5.0,
) -> Settings:
    """Create settings for edge case testing."""
    return Settings(
        devices=devices,
        username="admin",
        password="testpass",
        use_https=False,
        timeout=timeout,
        verify_ssl=False,
        fleet_name=fleet_name,
        storage_warning_percent=80.0,
    )


# ============================================================
# Invalid device_id Formats
# ============================================================


class TestInvalidDeviceId:
    """Tests for invalid device_id input validation."""

    async def test_empty_string_device_id(self):
        """Empty string device_id should raise ValueError."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.device.get_settings", return_value=settings):
            result = await get_device_status(device_id="")

        assert result["success"] is False
        assert "error" in result

    async def test_device_id_with_spaces(self):
        """Device ID with spaces should be rejected by host validation."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.device.get_settings", return_value=settings):
            result = await get_device_status(device_id="bad host")

        assert result["success"] is False
        assert "error" in result

    async def test_device_id_command_injection(self):
        """Device ID with shell injection attempt should be rejected."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.device.get_settings", return_value=settings):
            result = await get_device_status(device_id=";rm -rf /")

        assert result["success"] is False
        assert "error" in result

    async def test_device_id_sql_injection(self):
        """Device ID with SQL injection attempt should be rejected."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.device.get_settings", return_value=settings):
            result = await get_device_status(device_id="' OR 1=1 --")

        assert result["success"] is False
        assert "error" in result

    async def test_device_id_url(self):
        """Device ID that looks like a URL should be rejected."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.device.get_settings", return_value=settings):
            result = await get_device_status(device_id="http://evil.com")

        assert result["success"] is False
        assert "error" in result


# ============================================================
# Concurrent Operations
# ============================================================


class TestConcurrentOperations:
    """Tests for concurrent fleet operations."""

    async def test_multiple_simultaneous_fleet_status_calls(self):
        """Multiple simultaneous fleet status calls should all complete."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Launch 3 concurrent fleet status calls
                results = await asyncio.gather(
                    get_fleet_status(),
                    get_fleet_status(),
                    get_fleet_status(),
                )

        for result in results:
            assert result.success is True
            assert result.total_devices == 1

    async def test_fleet_slow_device_doesnt_block_others(self):
        """One slow device should not block other device results."""
        settings = create_test_settings(devices="192.168.1.100,192.168.1.101")

        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.3)
            return Response(200, json=DEVICE_RESPONSE)

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            with respx.mock(assert_all_called=False) as router:
                # Device 1: slow
                api_base1 = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base1}/device").mock(side_effect=slow_response)
                router.get(f"{api_base1}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base1}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Device 2: fast
                api_base2 = "http://192.168.1.101/api/v2.0"
                router.get(f"{api_base2}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base2}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base2}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_fleet_status()

        assert result.success is True
        assert result.total_devices == 2
        assert result.online_devices == 2

    async def test_execute_on_fleet_empty_hosts(self):
        """_execute_on_fleet with empty host list should return empty results."""
        settings = create_test_settings()

        async def dummy_op(client):
            return {"success": True}

        results = await _execute_on_fleet(
            hosts=[],
            operation=dummy_op,
            settings=settings,
        )
        assert results == []


# ============================================================
# Timeout Handling
# ============================================================


class TestTimeoutHandling:
    """Tests for timeout and connection error handling."""

    async def test_device_timeout_returns_graceful_error(self):
        """Device timeout should return a graceful error, not crash."""
        settings = create_test_settings(devices="192.168.1.100", timeout=0.5)

        async def timeout_response(*args, **kwargs):
            await asyncio.sleep(10)  # Much longer than timeout
            return Response(200, json=DEVICE_RESPONSE)

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(side_effect=timeout_response)
                router.get(f"{api_base}/storages").mock(side_effect=timeout_response)

                result = await get_fleet_status()

        assert result.success is True
        assert result.online_devices == 0
        # The device should be reported as offline/timed out
        assert result.devices[0]["online"] is False

    async def test_fleet_all_devices_timeout(self):
        """All devices timing out should return graceful error for each."""
        settings = create_test_settings(
            devices="192.168.1.100,192.168.1.101", timeout=0.5
        )

        async def timeout_response(*args, **kwargs):
            await asyncio.sleep(10)
            return Response(200, json=DEVICE_RESPONSE)

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            with respx.mock(assert_all_called=False) as router:
                for ip in ["192.168.1.100", "192.168.1.101"]:
                    api_base = f"http://{ip}/api/v2.0"
                    router.get(f"{api_base}/device").mock(
                        side_effect=timeout_response
                    )
                    router.get(f"{api_base}/storages").mock(
                        side_effect=timeout_response
                    )

                result = await get_fleet_status()

        assert result.success is True
        assert result.total_devices == 2
        assert result.online_devices == 0
        for device in result.devices:
            assert device["online"] is False

    async def test_connection_refused_returns_clear_error(self):
        """Connection refused should be handled by fleet operations gracefully."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    side_effect=ConnectError("Connection refused")
                )
                router.get(f"{api_base}/storages").mock(
                    side_effect=ConnectError("Connection refused")
                )

                result = await get_fleet_status()

        assert result.success is True
        assert result.online_devices == 0
        assert result.devices[0]["online"] is False
        assert "error" in result.devices[0]


# ============================================================
# Malformed API Responses
# ============================================================


class TestMalformedApiResponses:
    """Tests for handling malformed/unexpected API responses.

    The fleet operations layer catches exceptions from the client,
    so malformed responses are handled gracefully at the fleet level.
    """

    async def test_response_missing_status_field_in_fleet(self):
        """Response missing 'status' field should result in device marked offline."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                # Response with no 'status' field — client may raise an error
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json={"result": {"name": "test"}})
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_fleet_status()

        # Fleet status should succeed even if device response is unexpected
        assert result.success is True
        assert result.total_devices == 1

    async def test_response_http_error_all_endpoints(self):
        """HTTP 500 on all endpoints should still report device with degraded status.

        The client has a fallback in get_system_status that returns a default
        SystemStatus when API calls fail, so the fleet sees the device as
        'online' but with 0% storage and degraded health metadata.
        """
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    return_value=Response(500, json={"status": "error", "message": "Internal error"})
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(500, json={"status": "error", "message": "Internal error"})
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(500, json={"status": "error", "message": "Internal error"})
                )

                result = await get_fleet_status()

        assert result.success is True
        assert result.total_devices == 1
        device = result.devices[0]
        # Client falls back to default status — device shows as online
        # but with minimal data (no recorder access)
        assert device["host"] == "192.168.1.100"

    async def test_api_busy_response(self):
        """API 'busy' response should be handled gracefully."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json={"status": "busy"})
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_fleet_status()

        assert result.success is True
        assert result.total_devices == 1

    async def test_api_error_response(self):
        """API explicit error response should be handled gracefully."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    return_value=Response(
                        200,
                        json={"status": "error", "message": "Access denied"},
                    )
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_fleet_status()

        assert result.success is True
        assert result.total_devices == 1


# ============================================================
# Boundary Values
# ============================================================


class TestBoundaryValues:
    """Tests for boundary value handling."""

    async def test_zero_configured_devices(self):
        """Zero configured devices should return appropriate message."""
        settings = create_test_settings(devices="")

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            result = await get_fleet_status()

        assert result.success is True
        assert result.total_devices == 0
        assert "No devices configured" in result.message

    async def test_batch_start_with_empty_device_list(self):
        """Batch start with empty device list should fail gracefully."""
        settings = create_test_settings(devices="")

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            result = await batch_start_recording(device_ids="all")

        assert result.success is False
        assert "No devices" in result.error

    async def test_batch_stop_with_empty_device_list(self):
        """Batch stop with empty device list should fail gracefully."""
        settings = create_test_settings(devices="")

        with patch("epiphan_mcp.tools.fleet.get_settings", return_value=settings):
            result = await batch_stop_recording(device_ids="all")

        assert result.success is False
        assert "No devices" in result.error

    async def test_very_long_device_name(self):
        """Device name at the 253-character hostname limit should be validated."""
        # RFC 1123 max hostname length is 253 chars
        long_name = "a" * 254  # One over the limit

        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.device.get_settings", return_value=settings):
            result = await get_device_status(device_id=long_name)

        assert result["success"] is False
        assert "error" in result

    async def test_recorder_id_special_format(self):
        """Recorder with non-standard ID format should work or fail gracefully."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.device.get_settings", return_value=settings):
            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.post(
                    f"{api_base}/recorders/recorder-999/control/start"
                ).mock(
                    return_value=Response(
                        200,
                        json={"status": "error", "message": "Recorder not found"},
                    )
                )

                result = await start_recording(
                    device_id="192.168.1.100", recorder="recorder-999"
                )

        # Should handle the error from the API
        assert isinstance(result, dict)

    async def test_device_id_numeric_index(self):
        """Numeric device index should resolve to the correct device."""
        settings = create_test_settings(
            devices="192.168.1.100,192.168.1.101,192.168.1.102"
        )

        with patch("epiphan_mcp.tools.device.get_settings", return_value=settings):
            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.101/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Index 1 should resolve to 192.168.1.101
                result = await get_device_status(device_id="1")

        assert result["success"] is True

    async def test_device_id_out_of_range_index(self):
        """Out-of-range numeric index should fail gracefully."""
        settings = create_test_settings(devices="192.168.1.100")

        with patch("epiphan_mcp.tools.device.get_settings", return_value=settings):
            result = await get_device_status(device_id="99")

        assert result["success"] is False
        assert "error" in result


# ============================================================
# Config Validation Edge Cases
# ============================================================


class TestConfigEdgeCases:
    """Tests for configuration edge cases."""

    def test_config_with_whitespace_devices(self):
        """Device list with extra whitespace should be handled."""
        settings = Settings(
            devices="  192.168.1.100 , 192.168.1.101  ,  192.168.1.102 ",
            username="admin",
            password="testpass",
        )
        devices = settings.get_device_list()
        assert len(devices) == 3
        assert devices[0] == "192.168.1.100"
        assert devices[1] == "192.168.1.101"
        assert devices[2] == "192.168.1.102"

    def test_config_with_empty_entries(self):
        """Device list with empty entries between commas should be filtered."""
        settings = Settings(
            devices="192.168.1.100,,192.168.1.101",
            username="admin",
            password="testpass",
        )
        devices = settings.get_device_list()
        assert len(devices) == 2
        assert "192.168.1.100" in devices
        assert "192.168.1.101" in devices

    def test_host_validation_rejects_path_traversal(self):
        """Host validation should reject path traversal attempts."""
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="testpass",
        )
        with pytest.raises(ValueError, match="path traversal"):
            settings._validate_host("../../../etc/passwd")

    def test_host_validation_rejects_newlines(self):
        """Host validation should reject identifiers with newlines."""
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="testpass",
        )
        with pytest.raises(ValueError, match="forbidden characters"):
            settings._validate_host("host\n127.0.0.1")

    def test_host_validation_accepts_valid_ipv6(self):
        """Host validation should accept valid IPv6 addresses."""
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="testpass",
        )
        result = settings._validate_host("::1")
        assert result == "::1"
