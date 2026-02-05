"""Tests for EC20 PTZ camera integration.

Tests cover:
- EC20Client HTTP connection handling
- PTZ control (pan, tilt, zoom)
- Preset management
- AI tracking control
- Status retrieval
- MCP tool wrappers

Note: EC20 REST API endpoints are placeholders until discovered from real hardware.
The actual endpoints will be filled in after accessing the EC20 web interface.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from epiphan_mcp.integrations.ec20 import (
    EC20Client,
    EC20ConnectionError,
    EC20APIError,
)
from epiphan_mcp.config import Settings


# ============================================================================
# Mock Response Helpers
# ============================================================================


def make_response(
    data: dict,
    status_code: int = 200,
) -> httpx.Response:
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=data,
    )


# ============================================================================
# EC20Client Initialization Tests
# ============================================================================


class TestEC20ClientInit:
    """Tests for EC20Client initialization."""

    def test_client_init_defaults(self):
        """Test client initialization with defaults."""
        client = EC20Client(host="192.168.1.100")
        assert client.host == "192.168.1.100"
        assert client.username == "admin"
        assert client.password == ""
        assert client.timeout == 30.0
        assert client.use_https is False
        assert "http://192.168.1.100" in client.base_url

    def test_client_init_custom(self):
        """Test client initialization with custom values."""
        client = EC20Client(
            host="10.0.0.50",
            username="operator",
            password="secret123",
            use_https=True,
            timeout=60.0,
        )
        assert client.host == "10.0.0.50"
        assert client.username == "operator"
        assert client.password == "secret123"
        assert client.use_https is True
        assert client.timeout == 60.0
        assert "https://10.0.0.50" in client.base_url


# ============================================================================
# EC20Client Connection Tests
# ============================================================================


class TestEC20ClientConnection:
    """Tests for EC20Client connection handling."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_client(self):
        """Test that async context manager creates HTTP client."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                assert client._client is not None

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        """Test that async context manager closes HTTP client."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100"):
                pass

            mock_client.aclose.assert_called_once()


# ============================================================================
# EC20Client Status Tests
# ============================================================================


class TestEC20ClientStatus:
    """Tests for EC20Client status methods."""

    @pytest.mark.asyncio
    async def test_get_status_returns_camera_info(self):
        """Test get_status returns camera status information."""
        mock_response = {
            "model": "EC20",
            "firmware": "1.0.0",
            "serial": "EC20-12345",
            "ptz": {
                "pan": 0.0,
                "tilt": 0.0,
                "zoom": 1,
            },
            "tracking": {
                "enabled": False,
                "mode": "off",
            },
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                status = await client.get_status()

            assert status["model"] == "EC20"
            assert "ptz" in status
            assert "tracking" in status

    @pytest.mark.asyncio
    async def test_get_position_returns_ptz_values(self):
        """Test get_position returns current PTZ position."""
        mock_response = {
            "pan": 45.0,
            "tilt": -10.0,
            "zoom": 5,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                position = await client.get_position()

            assert position["pan"] == 45.0
            assert position["tilt"] == -10.0
            assert position["zoom"] == 5


# ============================================================================
# EC20Client PTZ Control Tests
# ============================================================================


class TestEC20ClientPTZ:
    """Tests for EC20Client PTZ control methods."""

    @pytest.mark.asyncio
    async def test_pan_sends_correct_request(self):
        """Test pan method sends correct API request."""
        mock_response = {"success": True, "pan": 30.0}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                result = await client.pan(degrees=30.0, speed=50)

            # Verify the request was made with correct parameters
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "pan" in call_args[0][0].lower() or "ptz" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_tilt_sends_correct_request(self):
        """Test tilt method sends correct API request."""
        mock_response = {"success": True, "tilt": -15.0}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                result = await client.tilt(degrees=-15.0, speed=30)

            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_zoom_sends_correct_request(self):
        """Test zoom method sends correct API request."""
        mock_response = {"success": True, "zoom": 10}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                result = await client.zoom(level=10)

            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_zoom_validates_range(self):
        """Test zoom method validates level is within valid range."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                # Level must be 1-36 (20 optical + 16 digital)
                with pytest.raises(ValueError, match="1.*36"):
                    await client.zoom(level=0)

                with pytest.raises(ValueError, match="1.*36"):
                    await client.zoom(level=37)

    @pytest.mark.asyncio
    async def test_home_returns_camera_to_default(self):
        """Test home method returns camera to default position."""
        mock_response = {"success": True, "pan": 0.0, "tilt": 0.0, "zoom": 1}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                result = await client.home()

            mock_client.post.assert_called_once()
            assert result["pan"] == 0.0
            assert result["tilt"] == 0.0


# ============================================================================
# EC20Client Preset Tests
# ============================================================================


class TestEC20ClientPresets:
    """Tests for EC20Client preset methods."""

    @pytest.mark.asyncio
    async def test_get_presets_returns_list(self):
        """Test get_presets returns list of saved presets."""
        mock_response = {
            "presets": [
                {"id": 1, "name": "Podium", "pan": 0, "tilt": 0, "zoom": 5},
                {"id": 2, "name": "Whiteboard", "pan": -45, "tilt": 10, "zoom": 3},
                {"id": 3, "name": "Wide", "pan": 0, "tilt": 0, "zoom": 1},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                presets = await client.get_presets()

            assert len(presets) == 3
            assert presets[0]["name"] == "Podium"

    @pytest.mark.asyncio
    async def test_goto_preset_moves_to_saved_position(self):
        """Test goto_preset moves camera to saved preset position."""
        mock_response = {"success": True, "preset_id": 1}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                result = await client.goto_preset(preset_id=1)

            mock_client.post.assert_called_once()
            assert result["preset_id"] == 1

    @pytest.mark.asyncio
    async def test_save_preset_stores_current_position(self):
        """Test save_preset saves current position as preset."""
        mock_response = {"success": True, "preset_id": 5, "name": "New Preset"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                result = await client.save_preset(preset_id=5, name="New Preset")

            mock_client.post.assert_called_once()
            assert result["name"] == "New Preset"


# ============================================================================
# EC20Client AI Tracking Tests
# ============================================================================


class TestEC20ClientTracking:
    """Tests for EC20Client AI tracking methods."""

    @pytest.mark.asyncio
    async def test_enable_tracking_with_presenter_mode(self):
        """Test enable_tracking with presenter mode."""
        mock_response = {"success": True, "tracking": {"enabled": True, "mode": "presenter"}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                result = await client.enable_tracking(mode="presenter")

            mock_client.post.assert_called_once()
            assert result["tracking"]["enabled"] is True
            assert result["tracking"]["mode"] == "presenter"

    @pytest.mark.asyncio
    async def test_enable_tracking_with_zone_mode(self):
        """Test enable_tracking with zone mode."""
        mock_response = {"success": True, "tracking": {"enabled": True, "mode": "zone"}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                result = await client.enable_tracking(mode="zone")

            assert result["tracking"]["mode"] == "zone"

    @pytest.mark.asyncio
    async def test_disable_tracking(self):
        """Test disable_tracking stops AI tracking."""
        mock_response = {"success": True, "tracking": {"enabled": False, "mode": "off"}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=make_response(mock_response))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                result = await client.disable_tracking()

            mock_client.post.assert_called_once()
            assert result["tracking"]["enabled"] is False


# ============================================================================
# EC20Client Error Handling Tests
# ============================================================================


class TestEC20ClientErrors:
    """Tests for EC20Client error handling."""

    @pytest.mark.asyncio
    async def test_connection_error_raises_exception(self):
        """Test that connection errors raise EC20ConnectionError."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                with pytest.raises(EC20ConnectionError, match="Connection"):
                    await client.get_status()

    @pytest.mark.asyncio
    async def test_timeout_error_raises_exception(self):
        """Test that timeout errors raise EC20ConnectionError."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                with pytest.raises(EC20ConnectionError, match="[Tt]imeout"):
                    await client.get_status()

    @pytest.mark.asyncio
    async def test_api_error_raises_exception(self):
        """Test that API errors raise EC20APIError."""
        error_response = httpx.Response(
            status_code=400,
            json={"error": "Invalid parameter"},
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=error_response)
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                with pytest.raises(EC20APIError, match="Invalid parameter"):
                    await client.pan(degrees=500)  # Invalid degree


# ============================================================================
# EC20Client Preview Tests
# ============================================================================


class TestEC20ClientPreview:
    """Tests for EC20Client preview methods."""

    @pytest.mark.asyncio
    async def test_get_preview_returns_image_bytes(self):
        """Test get_preview returns camera preview image as bytes."""
        # Minimal PNG bytes (1x1 transparent pixel)
        mock_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        mock_response = httpx.Response(
            status_code=200,
            content=mock_image,
            headers={"content-type": "image/jpeg"},
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            async with EC20Client(host="192.168.1.100") as client:
                preview = await client.get_preview()

            assert isinstance(preview, bytes)
            assert len(preview) > 0


# ============================================================================
# EC20 Config Tests
# ============================================================================


class TestEC20Config:
    """Tests for EC20 configuration in Settings."""

    def test_ec20_settings_defaults(self):
        """Test EC20 settings have correct defaults."""
        settings = Settings()
        assert settings.ec20_devices == ""
        assert settings.ec20_username == "admin"
        assert settings.ec20_password == ""
        assert settings.ec20_use_https is False
        assert settings.ec20_timeout == 30.0

    def test_get_ec20_device_list_empty(self):
        """Test get_ec20_device_list returns empty list when not configured."""
        settings = Settings()
        assert settings.get_ec20_device_list() == []

    def test_get_ec20_device_list_single(self):
        """Test get_ec20_device_list with single device."""
        settings = Settings(ec20_devices="192.168.1.100")
        assert settings.get_ec20_device_list() == ["192.168.1.100"]

    def test_get_ec20_device_list_multiple(self):
        """Test get_ec20_device_list with multiple devices."""
        settings = Settings(ec20_devices="192.168.1.100, 192.168.1.101, cam3.local")
        devices = settings.get_ec20_device_list()
        assert len(devices) == 3
        assert "192.168.1.100" in devices
        assert "192.168.1.101" in devices
        assert "cam3.local" in devices

    def test_get_ec20_host_default(self):
        """Test get_ec20_host returns first device for 'default'."""
        settings = Settings(ec20_devices="192.168.1.100,192.168.1.101")
        assert settings.get_ec20_host("default") == "192.168.1.100"

    def test_get_ec20_host_by_index(self):
        """Test get_ec20_host returns device by index."""
        settings = Settings(ec20_devices="192.168.1.100,192.168.1.101")
        assert settings.get_ec20_host("0") == "192.168.1.100"
        assert settings.get_ec20_host("1") == "192.168.1.101"

    def test_get_ec20_host_direct_ip(self):
        """Test get_ec20_host returns direct IP."""
        settings = Settings()
        assert settings.get_ec20_host("10.0.0.50") == "10.0.0.50"

    def test_get_ec20_host_no_default_raises(self):
        """Test get_ec20_host raises when no default configured."""
        settings = Settings()
        with pytest.raises(ValueError, match="No default EC20"):
            settings.get_ec20_host("default")


# ============================================================================
# EC20 MCP Tools Tests
# ============================================================================


class TestEC20MCPTools:
    """Tests for EC20 MCP tool functions."""

    @pytest.mark.asyncio
    async def test_ec20_get_status_tool(self):
        """Test ec20_get_status MCP tool."""
        from epiphan_mcp.tools.ec20 import ec20_get_status

        mock_status = {
            "model": "EC20",
            "firmware": "1.0.0",
            "ptz": {"pan": 0, "tilt": 0, "zoom": 1},
        }

        with patch("epiphan_mcp.tools.ec20.EC20Client") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get_status = AsyncMock(return_value=mock_status)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ec20_get_status(camera_id="192.168.1.100")

            assert result["success"] is True
            assert result["camera"]["model"] == "EC20"

    @pytest.mark.asyncio
    async def test_ec20_pan_tilt_tool(self):
        """Test ec20_pan_tilt MCP tool."""
        from epiphan_mcp.tools.ec20 import ec20_pan_tilt

        mock_result = {"success": True, "pan": 30.0, "tilt": -10.0}

        with patch("epiphan_mcp.tools.ec20.EC20Client") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.pan = AsyncMock(return_value={"success": True, "pan": 30.0})
            mock_instance.tilt = AsyncMock(return_value={"success": True, "tilt": -10.0})
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ec20_pan_tilt(camera_id="192.168.1.100", pan=30.0, tilt=-10.0)

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_ec20_zoom_tool(self):
        """Test ec20_zoom MCP tool."""
        from epiphan_mcp.tools.ec20 import ec20_zoom

        with patch("epiphan_mcp.tools.ec20.EC20Client") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.zoom = AsyncMock(return_value={"success": True, "zoom": 10})
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ec20_zoom(camera_id="192.168.1.100", level=10)

            assert result["success"] is True
            mock_instance.zoom.assert_called_with(level=10)

    @pytest.mark.asyncio
    async def test_ec20_goto_preset_tool(self):
        """Test ec20_goto_preset MCP tool."""
        from epiphan_mcp.tools.ec20 import ec20_goto_preset

        with patch("epiphan_mcp.tools.ec20.EC20Client") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.goto_preset = AsyncMock(return_value={"success": True, "preset_id": 1})
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ec20_goto_preset(camera_id="192.168.1.100", preset_id=1)

            assert result["success"] is True
            mock_instance.goto_preset.assert_called_with(preset_id=1)

    @pytest.mark.asyncio
    async def test_ec20_home_tool(self):
        """Test ec20_home MCP tool."""
        from epiphan_mcp.tools.ec20 import ec20_home

        with patch("epiphan_mcp.tools.ec20.EC20Client") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.home = AsyncMock(return_value={"success": True, "pan": 0, "tilt": 0, "zoom": 1})
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ec20_home(camera_id="192.168.1.100")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_ec20_enable_tracking_tool(self):
        """Test ec20_enable_tracking MCP tool."""
        from epiphan_mcp.tools.ec20 import ec20_enable_tracking

        with patch("epiphan_mcp.tools.ec20.EC20Client") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.enable_tracking = AsyncMock(
                return_value={"success": True, "tracking": {"enabled": True, "mode": "presenter"}}
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ec20_enable_tracking(camera_id="192.168.1.100", mode="presenter")

            assert result["success"] is True
            mock_instance.enable_tracking.assert_called_with(mode="presenter")

    @pytest.mark.asyncio
    async def test_ec20_disable_tracking_tool(self):
        """Test ec20_disable_tracking MCP tool."""
        from epiphan_mcp.tools.ec20 import ec20_disable_tracking

        with patch("epiphan_mcp.tools.ec20.EC20Client") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.disable_tracking = AsyncMock(
                return_value={"success": True, "tracking": {"enabled": False}}
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ec20_disable_tracking(camera_id="192.168.1.100")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_ec20_list_presets_tool(self):
        """Test ec20_list_presets MCP tool."""
        from epiphan_mcp.tools.ec20 import ec20_list_presets

        mock_presets = [
            {"id": 1, "name": "Podium"},
            {"id": 2, "name": "Whiteboard"},
        ]

        with patch("epiphan_mcp.tools.ec20.EC20Client") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get_presets = AsyncMock(return_value=mock_presets)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ec20_list_presets(camera_id="192.168.1.100")

            assert result["success"] is True
            assert len(result["presets"]) == 2

    @pytest.mark.asyncio
    async def test_ec20_save_preset_tool(self):
        """Test ec20_save_preset MCP tool."""
        from epiphan_mcp.tools.ec20 import ec20_save_preset

        with patch("epiphan_mcp.tools.ec20.EC20Client") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.save_preset = AsyncMock(
                return_value={"success": True, "preset_id": 5, "name": "New View"}
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ec20_save_preset(camera_id="192.168.1.100", preset_id=5, name="New View")

            assert result["success"] is True
            mock_instance.save_preset.assert_called_with(preset_id=5, name="New View")
