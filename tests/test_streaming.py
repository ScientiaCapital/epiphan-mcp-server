"""Tests for streaming discovery and preview tools.

Tests list_channels, list_publishers, and get_channel_preview
from tools/streaming.py.
"""

import base64
from unittest.mock import AsyncMock, patch

import pytest

from epiphan_mcp.client import PearlAPIError

# ============================================================
# list_channels Tests
# ============================================================


class TestListChannels:
    """Tests for list_channels tool function."""

    @pytest.mark.asyncio
    async def test_list_channels_basic(self):
        """Test listing channels with basic info."""
        from epiphan_mcp.tools.streaming import list_channels

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_channels = AsyncMock(
            return_value=[
                {
                    "id": "channel-1",
                    "name": "Main Channel",
                    "active_layout": "layout-1",
                },
                {
                    "id": "channel-2",
                    "name": "Secondary Channel",
                    "active_layout": "layout-1",
                },
            ]
        )

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_channels(device_id="default")

        assert result["success"] is True
        assert result["device"] == "192.168.1.100"
        assert result["total_channels"] == 2
        assert len(result["channels"]) == 2
        assert result["channels"][0]["id"] == "channel-1"

    @pytest.mark.asyncio
    async def test_list_channels_with_publishers(self):
        """Test listing channels with publisher details included."""
        from epiphan_mcp.tools.streaming import list_channels

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_channels = AsyncMock(
            return_value=[
                {
                    "id": "channel-1",
                    "name": "Main Channel",
                    "publishers": [
                        {"id": "publisher-1", "name": "YouTube Stream"},
                    ],
                },
            ]
        )

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_channels(device_id="default", include_publishers=True)

        assert result["success"] is True
        mock_client.get_channels.assert_called_once_with(
            include_publishers=True, include_layouts=False
        )

    @pytest.mark.asyncio
    async def test_list_channels_with_layouts(self):
        """Test listing channels with layout details included."""
        from epiphan_mcp.tools.streaming import list_channels

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_channels = AsyncMock(
            return_value=[
                {
                    "id": "channel-1",
                    "name": "Main Channel",
                    "layouts": [
                        {"id": "layout-1", "name": "Full Screen"},
                    ],
                },
            ]
        )

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_channels(device_id="default", include_layouts=True)

        assert result["success"] is True
        mock_client.get_channels.assert_called_once_with(
            include_publishers=False, include_layouts=True
        )

    @pytest.mark.asyncio
    async def test_list_channels_empty(self):
        """Test listing when no channels exist."""
        from epiphan_mcp.tools.streaming import list_channels

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_channels = AsyncMock(return_value=[])

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_channels(device_id="default")

        assert result["success"] is True
        assert result["total_channels"] == 0

    @pytest.mark.asyncio
    async def test_list_channels_connection_error(self):
        """Test listing channels with connection error."""
        from epiphan_mcp.tools.streaming import list_channels

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(
                __aenter__=AsyncMock(side_effect=PearlAPIError("Connection refused"))
            ),
        ):
            result = await list_channels(device_id="default")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_channels_invalid_device(self):
        """Test listing channels with no configured devices."""
        from epiphan_mcp.tools.streaming import list_channels

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            side_effect=ValueError("No default device configured"),
        ):
            result = await list_channels(device_id="default")

        assert result["success"] is False
        assert "No default device configured" in result["error"]


# ============================================================
# list_publishers Tests
# ============================================================


class TestListPublishers:
    """Tests for list_publishers tool function."""

    @pytest.mark.asyncio
    async def test_list_publishers_success(self):
        """Test successful listing of publishers."""
        from epiphan_mcp.tools.streaming import list_publishers

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_publishers = AsyncMock(
            return_value=[
                {
                    "id": "publisher-1",
                    "name": "YouTube Stream",
                    "type": "rtmp",
                    "enabled": True,
                },
                {
                    "id": "publisher-2",
                    "name": "Backup SRT",
                    "type": "srt",
                    "enabled": True,
                },
            ]
        )

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_publishers(device_id="default", channel=1)

        assert result["success"] is True
        assert result["device"] == "192.168.1.100"
        assert result["channel"] == "channel-1"
        assert result["total_publishers"] == 2
        assert len(result["publishers"]) == 2
        assert result["publishers"][0]["id"] == "publisher-1"

    @pytest.mark.asyncio
    async def test_list_publishers_empty(self):
        """Test listing publishers when none configured."""
        from epiphan_mcp.tools.streaming import list_publishers

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_publishers = AsyncMock(return_value=[])

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_publishers(device_id="default", channel=1)

        assert result["success"] is True
        assert result["total_publishers"] == 0
        assert result["publishers"] == []

    @pytest.mark.asyncio
    async def test_list_publishers_connection_error(self):
        """Test listing publishers with connection error."""
        from epiphan_mcp.tools.streaming import list_publishers

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(
                __aenter__=AsyncMock(side_effect=PearlAPIError("Connection refused"))
            ),
        ):
            result = await list_publishers(device_id="default", channel=1)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_publishers_channel_2(self):
        """Test listing publishers on channel 2."""
        from epiphan_mcp.tools.streaming import list_publishers

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_publishers = AsyncMock(return_value=[])

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_publishers(device_id="default", channel=2)

        assert result["channel"] == "channel-2"
        mock_client.get_publishers.assert_called_once_with("channel-2")


# ============================================================
# get_channel_preview Tests
# ============================================================


class TestGetChannelPreview:
    """Tests for get_channel_preview tool function."""

    @pytest.mark.asyncio
    async def test_get_channel_preview_success(self):
        """Test successful channel preview retrieval."""
        from epiphan_mcp.tools.streaming import get_channel_preview

        fake_jpg = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # Fake JPEG header
        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_channel_preview = AsyncMock(return_value=fake_jpg)

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await get_channel_preview(device_id="default", channel=1)

        assert result["success"] is True
        assert result["device"] == "192.168.1.100"
        assert result["channel"] == "channel-1"
        assert result["format"] == "jpg"
        # Verify base64 encoding
        assert "preview_base64" in result
        decoded = base64.b64decode(result["preview_base64"])
        assert decoded == fake_jpg

    @pytest.mark.asyncio
    async def test_get_channel_preview_png_format(self):
        """Test preview retrieval in PNG format."""
        from epiphan_mcp.tools.streaming import get_channel_preview

        fake_png = b"\x89PNG" + b"\x00" * 100
        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_channel_preview = AsyncMock(return_value=fake_png)

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await get_channel_preview(device_id="default", channel=1, format="png")

        assert result["success"] is True
        assert result["format"] == "png"

    @pytest.mark.asyncio
    async def test_get_channel_preview_custom_resolution(self):
        """Test preview with custom resolution."""
        from epiphan_mcp.tools.streaming import get_channel_preview

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_channel_preview = AsyncMock(return_value=b"\xff\xd8\xff")

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await get_channel_preview(
                device_id="default", channel=1, resolution="1920x1080"
            )

        assert result["success"] is True
        assert result["resolution"] == "1920x1080"
        mock_client.get_channel_preview.assert_called_once_with(
            "channel-1", resolution="1920x1080", format="jpg"
        )

    @pytest.mark.asyncio
    async def test_get_channel_preview_connection_error(self):
        """Test preview with connection error."""
        from epiphan_mcp.tools.streaming import get_channel_preview

        with patch(
            "epiphan_mcp.tools.streaming.get_client",
            return_value=AsyncMock(
                __aenter__=AsyncMock(side_effect=PearlAPIError("Connection refused"))
            ),
        ):
            result = await get_channel_preview(device_id="default", channel=1)

        assert result["success"] is False
        assert "error" in result
