"""Tests for device resource discovery and caching."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from epiphan_mcp.tools.discovery import (
    _cache_timestamps,
    _device_cache,
    _parse_resource_number,
    clear_discovery_cache,
    discover_device,
    get_default_channel,
    get_default_recorder,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear discovery cache before each test."""
    _device_cache.clear()
    _cache_timestamps.clear()
    yield
    _device_cache.clear()
    _cache_timestamps.clear()


class TestParseResourceNumber:
    """Tests for _parse_resource_number helper."""

    def test_parse_recorder_id(self):
        assert _parse_resource_number("recorder-1") == 1

    def test_parse_recorder_id_multi(self):
        assert _parse_resource_number("recorder-3") == 3

    def test_parse_channel_id(self):
        assert _parse_resource_number("channel-2") == 2

    def test_parse_no_number(self):
        assert _parse_resource_number("unknown") == 1

    def test_parse_empty_string(self):
        assert _parse_resource_number("") == 1


class TestDiscoverDevice:
    """Tests for discover_device."""

    @pytest.mark.asyncio
    async def test_discover_returns_recorders_and_channels(self):
        """Discovery returns structured recorder/channel/input data."""
        mock_recorders = [
            AsyncMock(id="recorder-1", name="Main", type="local", channel_id="channel-1"),
            AsyncMock(id="recorder-2", name="Backup", type="local", channel_id="channel-2"),
        ]
        mock_channels = [
            AsyncMock(id="channel-1", name="Camera 1"),
            AsyncMock(id="channel-2", name="Camera 2"),
        ]
        mock_inputs = [
            AsyncMock(id="hdmi-a", name="HDMI A", type="hdmi", connected=True),
        ]

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_recorders.return_value = mock_recorders
        mock_client.get_channels.return_value = mock_channels
        mock_client.get_inputs.return_value = mock_inputs
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("epiphan_mcp.tools.discovery.get_client", return_value=mock_client):
            result = await discover_device("192.168.1.100")

        assert result["success"] is True
        assert len(result["recorders"]) == 2
        assert len(result["channels"]) == 2
        assert len(result["inputs"]) == 1
        assert result["recorders"][0]["id"] == "recorder-1"
        assert result["cached"] is False

    @pytest.mark.asyncio
    async def test_discover_uses_cache_on_second_call(self):
        """Second call returns cached data without hitting the API."""
        mock_recorders = [
            AsyncMock(id="recorder-1", name="Main", type="local", channel_id="channel-1"),
        ]
        mock_channels = [
            AsyncMock(id="channel-1", name="Camera 1"),
        ]
        mock_inputs = []

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_recorders.return_value = mock_recorders
        mock_client.get_channels.return_value = mock_channels
        mock_client.get_inputs.return_value = mock_inputs
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("epiphan_mcp.tools.discovery.get_client", return_value=mock_client):
            result1 = await discover_device("192.168.1.100")
            result2 = await discover_device("192.168.1.100")

        assert result1["cached"] is False
        assert result2["cached"] is True
        # API should only be called once
        assert mock_client.get_recorders.call_count == 1

    @pytest.mark.asyncio
    async def test_discover_fallback_on_error(self):
        """Discovery returns error dict when API fails."""
        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_recorders.side_effect = Exception("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("epiphan_mcp.tools.discovery.get_client", return_value=mock_client):
            result = await discover_device("192.168.1.100")

        assert result["success"] is False
        assert "Connection refused" in result["error"]

    @pytest.mark.asyncio
    async def test_discover_cache_expires(self):
        """Cache entries expire after TTL."""
        mock_recorders = [
            AsyncMock(id="recorder-1", name="Main", type="local", channel_id="channel-1"),
        ]
        mock_channels = []
        mock_inputs = []

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_recorders.return_value = mock_recorders
        mock_client.get_channels.return_value = mock_channels
        mock_client.get_inputs.return_value = mock_inputs
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("epiphan_mcp.tools.discovery.get_client", return_value=mock_client):
            # First call populates cache
            await discover_device("192.168.1.100")

            # Expire the cache
            _cache_timestamps["192.168.1.100"] = time.monotonic() - 400

            # Second call should hit API again
            result = await discover_device("192.168.1.100")

        assert result["cached"] is False
        assert mock_client.get_recorders.call_count == 2


class TestGetDefaultRecorder:
    """Tests for get_default_recorder."""

    @pytest.mark.asyncio
    async def test_returns_first_recorder(self):
        """Returns the first recorder number from discovery."""
        mock_recorders = [
            AsyncMock(id="recorder-2", name="Main", type="local", channel_id="channel-1"),
            AsyncMock(id="recorder-1", name="Backup", type="local", channel_id="channel-2"),
        ]

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_recorders.return_value = mock_recorders
        mock_client.get_channels.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("epiphan_mcp.tools.discovery.get_client", return_value=mock_client):
            result = await get_default_recorder("192.168.1.100")

        assert result == 2  # First in list is recorder-2

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        """Returns 1 when discovery fails."""
        with patch("epiphan_mcp.tools.discovery.get_client", side_effect=Exception("fail")):
            result = await get_default_recorder("bad-device")

        assert result == 1


class TestGetDefaultChannel:
    """Tests for get_default_channel."""

    @pytest.mark.asyncio
    async def test_returns_first_channel(self):
        """Returns the first channel number from discovery."""
        mock_channels = [
            AsyncMock(id="channel-3", name="Wide"),
            AsyncMock(id="channel-1", name="Close"),
        ]

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.get_recorders.return_value = []
        mock_client.get_channels.return_value = mock_channels
        mock_client.get_inputs.return_value = []
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("epiphan_mcp.tools.discovery.get_client", return_value=mock_client):
            result = await get_default_channel("192.168.1.100")

        assert result == 3  # First in list is channel-3

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        """Returns 1 when discovery fails."""
        with patch("epiphan_mcp.tools.discovery.get_client", side_effect=Exception("fail")):
            result = await get_default_channel("bad-device")

        assert result == 1


class TestClearDiscoveryCache:
    """Tests for clear_discovery_cache."""

    @pytest.mark.asyncio
    async def test_clear_all(self):
        """Clears all cached entries."""
        _device_cache["host1"] = {"recorders": []}
        _device_cache["host2"] = {"recorders": []}
        _cache_timestamps["host1"] = time.monotonic()
        _cache_timestamps["host2"] = time.monotonic()

        result = await clear_discovery_cache()

        assert result["success"] is True
        assert result["entries_removed"] == 2
        assert len(_device_cache) == 0

    @pytest.mark.asyncio
    async def test_clear_specific_device(self):
        """Clears cache for a specific device only."""
        _device_cache["192.168.1.100"] = {"recorders": []}
        _device_cache["192.168.1.101"] = {"recorders": []}
        _cache_timestamps["192.168.1.100"] = time.monotonic()
        _cache_timestamps["192.168.1.101"] = time.monotonic()

        mock_client = AsyncMock()
        mock_client.host = "192.168.1.100"
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("epiphan_mcp.tools.discovery.get_client", return_value=mock_client):
            result = await clear_discovery_cache("192.168.1.100")

        assert result["success"] is True
        assert result["entries_removed"] == 1
        assert "192.168.1.100" not in _device_cache
        assert "192.168.1.101" in _device_cache
