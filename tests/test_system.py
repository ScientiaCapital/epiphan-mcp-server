"""Tests for system control tools.

Tests reboot_device, shutdown_device, and get_system_info
from tools/system.py.
"""

from unittest.mock import AsyncMock, patch

import pytest

from epiphan_mcp.client import PearlAPIError
from epiphan_mcp.models import OperationResult, SystemStatus

# ============================================================
# reboot_device Tests
# ============================================================


class TestRebootDevice:
    """Tests for reboot_device tool function."""

    @pytest.mark.asyncio
    async def test_reboot_without_confirm_rejected(self):
        """Test that reboot is rejected without confirm=True."""
        from epiphan_mcp.tools.system import reboot_device

        result = await reboot_device(device_id="default")

        assert result.success is False
        assert "confirm" in result.error.lower()

    @pytest.mark.asyncio
    async def test_reboot_with_confirm_false_rejected(self):
        """Test that reboot is rejected with confirm=False."""
        from epiphan_mcp.tools.system import reboot_device

        result = await reboot_device(device_id="default", confirm=False)

        assert result.success is False
        assert "confirm" in result.error.lower()

    @pytest.mark.asyncio
    async def test_reboot_with_confirm_success(self):
        """Test successful reboot with confirm=True."""
        from epiphan_mcp.tools.system import reboot_device

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.reboot = AsyncMock(
            return_value=OperationResult(
                success=True,
                message="Rebooting",
                device="192.168.1.100",
            )
        )

        with patch(
            "epiphan_mcp.tools.system.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await reboot_device(device_id="default", confirm=True)

        assert result.success is True
        assert result.device == "192.168.1.100"
        mock_client.reboot.assert_called_once()

    @pytest.mark.asyncio
    async def test_reboot_connection_error(self):
        """Test reboot with connection error."""
        from epiphan_mcp.tools.system import reboot_device

        with patch(
            "epiphan_mcp.tools.system.get_client",
            return_value=AsyncMock(
                __aenter__=AsyncMock(side_effect=PearlAPIError("Connection refused"))
            ),
        ):
            result = await reboot_device(device_id="default", confirm=True)

        assert result.success is False
        assert hasattr(result, "error")

    @pytest.mark.asyncio
    async def test_reboot_invalid_device(self):
        """Test reboot with no configured devices."""
        from epiphan_mcp.tools.system import reboot_device

        with patch(
            "epiphan_mcp.tools.system.get_client",
            side_effect=ValueError("No default device configured"),
        ):
            result = await reboot_device(device_id="default", confirm=True)

        assert result.success is False
        assert "No default device configured" in result.error

    @pytest.mark.asyncio
    async def test_reboot_audit_logged_on_success(self):
        """Successful reboot should produce an audit log entry."""
        from epiphan_mcp.tools.system import reboot_device

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.reboot = AsyncMock(
            return_value=OperationResult(success=True, message="Rebooting", device="192.168.1.100")
        )

        with (
            patch(
                "epiphan_mcp.tools.system.get_client",
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
            ),
            patch("epiphan_mcp.tools.system.log_operation") as mock_audit,
        ):
            await reboot_device(device_id="default", confirm=True)

        mock_audit.assert_called_once_with(
            "reboot", "192.168.1.100", details={"device_id": "default"}
        )

    @pytest.mark.asyncio
    async def test_reboot_audit_logged_on_failure(self):
        """Failed reboot should produce an audit log with success=False."""
        from epiphan_mcp.tools.system import reboot_device

        with (
            patch(
                "epiphan_mcp.tools.system.get_client",
                return_value=AsyncMock(
                    __aenter__=AsyncMock(side_effect=PearlAPIError("Connection refused"))
                ),
            ),
            patch("epiphan_mcp.tools.system.log_operation") as mock_audit,
        ):
            await reboot_device(device_id="default", confirm=True)

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args
        assert call_kwargs[0][0] == "reboot"
        assert call_kwargs[1]["success"] is False


# ============================================================
# shutdown_device Tests
# ============================================================


class TestShutdownDevice:
    """Tests for shutdown_device tool function."""

    @pytest.mark.asyncio
    async def test_shutdown_without_confirm_rejected(self):
        """Test that shutdown is rejected without confirm=True."""
        from epiphan_mcp.tools.system import shutdown_device

        result = await shutdown_device(device_id="default")

        assert result.success is False
        assert "confirm" in result.error.lower()

    @pytest.mark.asyncio
    async def test_shutdown_with_confirm_success(self):
        """Test successful shutdown with confirm=True."""
        from epiphan_mcp.tools.system import shutdown_device

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.shutdown = AsyncMock(
            return_value=OperationResult(
                success=True,
                message="Shutting down",
                device="192.168.1.100",
            )
        )

        with patch(
            "epiphan_mcp.tools.system.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await shutdown_device(device_id="default", confirm=True)

        assert result.success is True
        assert result.device == "192.168.1.100"
        mock_client.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_connection_error(self):
        """Test shutdown with connection error."""
        from epiphan_mcp.tools.system import shutdown_device

        with patch(
            "epiphan_mcp.tools.system.get_client",
            return_value=AsyncMock(
                __aenter__=AsyncMock(side_effect=PearlAPIError("Connection refused"))
            ),
        ):
            result = await shutdown_device(device_id="default", confirm=True)

        assert result.success is False
        assert hasattr(result, "error")


# ============================================================
# get_system_info Tests
# ============================================================


class TestGetSystemInfo:
    """Tests for get_system_info tool function."""

    @pytest.mark.asyncio
    async def test_get_system_info_success(self):
        """Test successful system info retrieval."""
        from epiphan_mcp.tools.system import get_system_info

        mock_status = SystemStatus(
            device_name="Pearl Mini",
            model="Pearl Mini",
            serial_number="SN12345",
            firmware_version="4.14.2",
            uptime_seconds=86400,
            storage_total_gb=500.0,
            storage_free_gb=250.0,
            storage_used_percent=50.0,
            cpu_usage=25.0,
            memory_usage=40.0,
            temperature=45.0,
        )
        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_system_status = AsyncMock(return_value=mock_status)

        with patch(
            "epiphan_mcp.tools.system.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await get_system_info(device_id="default")

        assert result.success is True
        assert result.device == "192.168.1.100"
        assert result.system["device_name"] == "Pearl Mini"
        assert result.system["firmware_version"] == "4.14.2"
        assert result.system["uptime_seconds"] == 86400
        assert result.system["storage_used_percent"] == 50.0
        assert result.system["cpu_usage"] == 25.0

    @pytest.mark.asyncio
    async def test_get_system_info_connection_error(self):
        """Test system info with connection error."""
        from epiphan_mcp.tools.system import get_system_info

        with patch(
            "epiphan_mcp.tools.system.get_client",
            return_value=AsyncMock(
                __aenter__=AsyncMock(side_effect=PearlAPIError("Connection refused"))
            ),
        ):
            result = await get_system_info(device_id="default")

        assert result.success is False
        assert hasattr(result, "error")

    @pytest.mark.asyncio
    async def test_get_system_info_invalid_device(self):
        """Test system info with no configured devices."""
        from epiphan_mcp.tools.system import get_system_info

        with patch(
            "epiphan_mcp.tools.system.get_client",
            side_effect=ValueError("No default device configured"),
        ):
            result = await get_system_info(device_id="default")

        assert result.success is False
        assert "No default device configured" in result.error
