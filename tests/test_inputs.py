"""Tests for input/output management tools."""

import pytest
from unittest.mock import AsyncMock, patch

from epiphan_mcp.models import OperationResult


class TestCreateNetworkInput:
    """Tests for create_network_input tool."""

    @pytest.mark.asyncio
    async def test_create_srt_input_success(self):
        """Test successful SRT input creation."""
        from epiphan_mcp.tools.inputs import create_network_input

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.create_input = AsyncMock(
            return_value={"id": "srt-1", "name": "SRT Feed", "type": "srt"}
        )

        with patch(
            "epiphan_mcp.tools.inputs.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await create_network_input(
                device_id="default",
                name="SRT Feed",
                input_type="srt",
                url="srt://camera.local:9000",
                passphrase="secret123",
                latency=200,
            )

        assert result["success"] is True
        assert result["device"] == "192.168.1.100"
        assert "input" in result

    @pytest.mark.asyncio
    async def test_create_rtsp_input_success(self):
        """Test successful RTSP input creation."""
        from epiphan_mcp.tools.inputs import create_network_input

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.create_input = AsyncMock(
            return_value={"id": "rtsp-1", "name": "IP Camera", "type": "rtsp"}
        )

        with patch(
            "epiphan_mcp.tools.inputs.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await create_network_input(
                device_id="default",
                name="IP Camera",
                input_type="rtsp",
                url="rtsp://admin:pass@camera.local/stream1",
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_input_missing_name(self):
        """Test that create_network_input fails without a name."""
        from epiphan_mcp.tools.inputs import create_network_input

        result = await create_network_input(
            device_id="default",
            name="",  # Empty name
            input_type="srt",
        )

        assert result["success"] is False
        assert "name is required" in result["error"].lower()


class TestGetInputSettings:
    """Tests for get_input_settings tool."""

    @pytest.mark.asyncio
    async def test_get_input_settings_success(self):
        """Test successful settings retrieval."""
        from epiphan_mcp.tools.inputs import get_input_settings

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_input_settings = AsyncMock(
            return_value={
                "srt_url": "srt://camera.local:9000",
                "latency": 200,
                "passphrase": "***",
            }
        )

        with patch(
            "epiphan_mcp.tools.inputs.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await get_input_settings(
                device_id="default",
                input_id="srt-1",
            )

        assert result["success"] is True
        assert "settings" in result
        assert result["settings"]["latency"] == 200

    @pytest.mark.asyncio
    async def test_get_input_settings_missing_id(self):
        """Test that get_input_settings fails without input_id."""
        from epiphan_mcp.tools.inputs import get_input_settings

        result = await get_input_settings(
            device_id="default",
            input_id="",  # Empty ID
        )

        assert result["success"] is False
        assert "input id is required" in result["error"].lower()


class TestUpdateInputSettings:
    """Tests for update_input_settings tool."""

    @pytest.mark.asyncio
    async def test_update_input_settings_success(self):
        """Test successful settings update."""
        from epiphan_mcp.tools.inputs import update_input_settings

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.update_input_settings = AsyncMock(
            return_value=OperationResult(
                success=True,
                message="Settings updated",
                device="192.168.1.100",
            )
        )

        with patch(
            "epiphan_mcp.tools.inputs.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await update_input_settings(
                device_id="default",
                input_id="srt-1",
                latency=300,
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_input_settings_missing_id(self):
        """Test that update fails without input_id."""
        from epiphan_mcp.tools.inputs import update_input_settings

        result = await update_input_settings(
            device_id="default",
            input_id="",  # Empty ID
            latency=300,
        )

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_update_input_settings_no_changes(self):
        """Test that update fails when no settings provided."""
        from epiphan_mcp.tools.inputs import update_input_settings

        result = await update_input_settings(
            device_id="default",
            input_id="srt-1",
            # No settings provided
        )

        assert result["success"] is False
        assert "no settings" in result["error"].lower()


class TestListOutputs:
    """Tests for list_outputs tool."""

    @pytest.mark.asyncio
    async def test_list_outputs_success(self):
        """Test successful outputs listing."""
        from epiphan_mcp.tools.inputs import list_outputs

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {"id": "hdmi-1", "name": "HDMI 1", "type": "hdmi", "source": "channel-1"},
                {"id": "sdi-1", "name": "SDI 1", "type": "sdi", "source": None},
            ]
        )

        with patch(
            "epiphan_mcp.tools.inputs.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await list_outputs(device_id="default")

        assert result["success"] is True
        assert result["total_outputs"] == 2
        assert len(result["outputs"]) == 2


class TestSetOutputSource:
    """Tests for set_output_source tool."""

    @pytest.mark.asyncio
    async def test_set_output_source_success(self):
        """Test successful output source configuration."""
        from epiphan_mcp.tools.inputs import set_output_source

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.set_output_source = AsyncMock(
            return_value=OperationResult(
                success=True,
                message="Output source set",
                device="192.168.1.100",
            )
        )

        with patch(
            "epiphan_mcp.tools.inputs.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await set_output_source(
                device_id="default",
                output_id="hdmi-1",
                source_channel=2,
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_set_output_source_disable(self):
        """Test disabling an output."""
        from epiphan_mcp.tools.inputs import set_output_source

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.set_output_source = AsyncMock(
            return_value=OperationResult(
                success=True,
                message="Output disabled",
                device="192.168.1.100",
            )
        )

        with patch(
            "epiphan_mcp.tools.inputs.get_client",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client)),
        ):
            result = await set_output_source(
                device_id="default",
                output_id="hdmi-1",
                source_channel=None,  # Disable
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_set_output_source_missing_id(self):
        """Test that set_output_source fails without output_id."""
        from epiphan_mcp.tools.inputs import set_output_source

        result = await set_output_source(
            device_id="default",
            output_id="",  # Empty ID
            source_channel=1,
        )

        assert result["success"] is False
        assert "output id is required" in result["error"].lower()
