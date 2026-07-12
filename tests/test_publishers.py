"""Tests for publisher management tools."""

from unittest.mock import AsyncMock, patch

import pytest

from epiphan_mcp.models import OperationResult


class TestCreatePublisher:
    """Tests for create_publisher tool."""

    @pytest.mark.asyncio
    async def test_create_publisher_success(self):
        """Test successful publisher creation."""
        from epiphan_mcp.tools.publishers import create_publisher

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.create_publisher = AsyncMock(
            return_value={"id": "publisher-2", "name": "YouTube Stream", "type": "rtmp"}
        )

        with patch(
            "epiphan_mcp.tools.publishers.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await create_publisher(
                device_id="default",
                channel=1,
                name="YouTube Stream",
                publisher_type="rtmp",
                url="rtmp://a.rtmp.youtube.com/live2",
                stream_key="xxxx-xxxx-xxxx",
            )

        assert result["success"] is True
        assert result["device"] == "192.168.1.100"
        assert "publisher" in result

    @pytest.mark.asyncio
    async def test_create_publisher_missing_name(self):
        """Test that create_publisher fails without a name."""
        from epiphan_mcp.tools.publishers import create_publisher

        result = await create_publisher(
            device_id="default",
            channel=1,
            name="",  # Empty name
            publisher_type="rtmp",
        )

        assert result["success"] is False
        assert "name is required" in result["error"].lower()


class TestDeletePublisher:
    """Tests for delete_publisher tool."""

    @pytest.mark.asyncio
    async def test_delete_publisher_success(self):
        """Test successful publisher deletion."""
        from epiphan_mcp.tools.publishers import delete_publisher

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.delete_publisher = AsyncMock(
            return_value=OperationResult(
                success=True,
                message="Publisher deleted",
                device="192.168.1.100",
            )
        )

        with patch(
            "epiphan_mcp.tools.publishers.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await delete_publisher(
                device_id="default",
                channel=1,
                publisher="publisher-2",
            )

        assert result["success"] is True


class TestGetPublisherSettings:
    """Tests for get_publisher_settings tool."""

    @pytest.mark.asyncio
    async def test_get_publisher_settings_success(self):
        """Test successful settings retrieval."""
        from epiphan_mcp.tools.publishers import get_publisher_settings

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_publisher_settings = AsyncMock(
            return_value={
                "url": "rtmp://example.com/live",
                "stream_key": "xxx",
                "bitrate": 5000000,
                "enabled": True,
            }
        )

        with patch(
            "epiphan_mcp.tools.publishers.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await get_publisher_settings(
                device_id="default",
                channel=1,
                publisher="publisher-1",
            )

        assert result["success"] is True
        assert "settings" in result
        assert result["settings"]["enabled"] is True


class TestUpdatePublisherSettings:
    """Tests for update_publisher_settings tool."""

    @pytest.mark.asyncio
    async def test_update_publisher_settings_success(self):
        """Test successful settings update."""
        from epiphan_mcp.tools.publishers import update_publisher_settings

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.update_publisher_settings = AsyncMock(
            return_value=OperationResult(
                success=True,
                message="Settings updated",
                device="192.168.1.100",
            )
        )

        with patch(
            "epiphan_mcp.tools.publishers.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await update_publisher_settings(
                device_id="default",
                channel=1,
                publisher="publisher-1",
                bitrate=8000000,
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_publisher_settings_no_changes(self):
        """Test that update fails when no settings provided."""
        from epiphan_mcp.tools.publishers import update_publisher_settings

        result = await update_publisher_settings(
            device_id="default",
            channel=1,
            publisher="publisher-1",
            # No settings provided
        )

        assert result["success"] is False
        assert "no settings" in result["error"].lower()


class TestListPublisherTypes:
    """Tests for list_publisher_types tool."""

    @pytest.mark.asyncio
    async def test_list_publisher_types_success(self):
        """Test successful publisher types listing."""
        from epiphan_mcp.tools.publishers import list_publisher_types

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_publisher_types = AsyncMock(return_value=["rtmp", "srt", "hls", "rtsp"])

        with patch(
            "epiphan_mcp.tools.publishers.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_publisher_types(device_id="default", channel=1)

        assert result["success"] is True
        assert "rtmp" in result["types"]
        assert "srt" in result["types"]


class TestRenamePublisher:
    """Tests for rename_publisher tool."""

    @pytest.mark.asyncio
    async def test_rename_publisher_success(self):
        """Test successful publisher rename."""
        from epiphan_mcp.tools.publishers import rename_publisher

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.update_publisher_name = AsyncMock(
            return_value=OperationResult(
                success=True,
                message="Publisher renamed",
                device="192.168.1.100",
            )
        )

        with patch(
            "epiphan_mcp.tools.publishers.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await rename_publisher(
                device_id="default",
                channel=1,
                publisher="publisher-1",
                name="Main Stream",
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_rename_publisher_missing_name(self):
        """Test that rename fails without a new name."""
        from epiphan_mcp.tools.publishers import rename_publisher

        result = await rename_publisher(
            device_id="default",
            channel=1,
            publisher="publisher-1",
            name="",  # Empty name
        )

        assert result["success"] is False
        assert "name is required" in result["error"].lower()
