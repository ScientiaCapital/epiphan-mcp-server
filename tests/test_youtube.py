"""Tests for YouTube Live integration."""

import time
from unittest.mock import patch

import pytest
import respx
from httpx import Response

from epiphan_mcp.integrations.youtube import (
    YouTubeAPIError,
    YouTubeAuthError,
    YouTubeClient,
    YouTubeQuotaError,
)
from epiphan_mcp.tools.youtube import (
    create_youtube_broadcast,
    end_youtube_broadcast,
    get_youtube_broadcast_status,
    list_youtube_broadcasts,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def youtube_config():
    """YouTube client configuration for tests."""
    return {
        "client_id": "test-client-id.apps.googleusercontent.com",
        "client_secret": "test-client-secret",
        "refresh_token": "1//0gtest-refresh-token",
    }


@pytest.fixture
def mock_token_response():
    """Mock OAuth2 token refresh response."""
    return {
        "access_token": "ya29.test-access-token",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "https://www.googleapis.com/auth/youtube.force-ssl",
    }


@pytest.fixture
def mock_broadcast():
    """Mock broadcast resource."""
    return {
        "kind": "youtube#liveBroadcast",
        "etag": "test-etag",
        "id": "broadcast-123",
        "snippet": {
            "title": "Test Broadcast",
            "description": "Test description",
            "scheduledStartTime": "2024-01-15T10:00:00Z",
            "actualStartTime": None,
            "actualEndTime": None,
            "channelId": "UCtest123",
        },
        "status": {
            "lifeCycleStatus": "created",
            "privacyStatus": "unlisted",
            "recordingStatus": "notRecording",
        },
        "contentDetails": {
            "boundStreamId": "stream-456",
            "enableDvr": True,
            "enableContentEncryption": False,
            "enableEmbed": True,
            "recordFromStart": True,
            "enableAutoStart": False,
            "enableAutoStop": False,
        },
    }


@pytest.fixture
def mock_stream():
    """Mock stream resource."""
    return {
        "kind": "youtube#liveStream",
        "etag": "test-etag",
        "id": "stream-456",
        "snippet": {
            "title": "Test Stream",
            "channelId": "UCtest123",
        },
        "cdn": {
            "frameRate": "30fps",
            "resolution": "1080p",
            "ingestionType": "rtmp",
            "ingestionInfo": {
                "ingestionAddress": "rtmp://a.rtmp.youtube.com/live2",
                "streamName": "xxxx-xxxx-xxxx-xxxx",
                "backupIngestionAddress": "rtmp://b.rtmp.youtube.com/live2?backup=1",
            },
        },
        "status": {
            "streamStatus": "inactive",
            "healthStatus": {
                "status": "noData",
            },
        },
    }


# =============================================================================
# Client Tests - OAuth2
# =============================================================================


class TestYouTubeClientAuth:
    """Test OAuth2 authentication."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_token_refresh_on_init(self, youtube_config, mock_token_response):
        """Test that token is refreshed when client enters context."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )

        async with YouTubeClient(**youtube_config) as client:
            assert client._access_token == "ya29.test-access-token"
            assert client._token_expires_at > time.time()

    @respx.mock
    @pytest.mark.asyncio
    async def test_token_refresh_failure(self, youtube_config):
        """Test handling of token refresh failure."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(
                400,
                json={
                    "error": "invalid_grant",
                    "error_description": "Token has been revoked",
                },
            )
        )

        with pytest.raises(YouTubeAuthError, match="Token refresh failed"):
            async with YouTubeClient(**youtube_config):
                pass

    @respx.mock
    @pytest.mark.asyncio
    async def test_auto_refresh_near_expiry(self, youtube_config, mock_token_response):
        """Test that token is refreshed when near expiry."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.get("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(200, json={"items": []})
        )

        async with YouTubeClient(**youtube_config) as client:
            # Simulate token near expiry
            client._token_expires_at = time.time() + 30  # 30 seconds left
            await client.list_broadcasts()

            # Token should have been refreshed (2 calls total)
            assert len(respx.calls) >= 2


# =============================================================================
# Client Tests - Broadcasts
# =============================================================================


class TestYouTubeClientBroadcasts:
    """Test broadcast operations."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_broadcast(self, youtube_config, mock_token_response, mock_broadcast):
        """Test creating a broadcast."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.post("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(200, json=mock_broadcast)
        )

        async with YouTubeClient(**youtube_config) as client:
            result = await client.create_broadcast(
                title="Test Broadcast",
                scheduled_start="2024-01-15T10:00:00Z",
                description="Test description",
            )

            assert result["id"] == "broadcast-123"
            assert result["snippet"]["title"] == "Test Broadcast"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_broadcast(self, youtube_config, mock_token_response, mock_broadcast):
        """Test getting a broadcast by ID."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.get("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(200, json={"items": [mock_broadcast]})
        )

        async with YouTubeClient(**youtube_config) as client:
            result = await client.get_broadcast("broadcast-123")
            assert result["id"] == "broadcast-123"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_broadcast_not_found(self, youtube_config, mock_token_response):
        """Test getting a non-existent broadcast."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.get("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(200, json={"items": []})
        )

        async with YouTubeClient(**youtube_config) as client:
            with pytest.raises(YouTubeAPIError, match="Broadcast not found"):
                await client.get_broadcast("nonexistent")

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_broadcasts(self, youtube_config, mock_token_response, mock_broadcast):
        """Test listing broadcasts."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.get("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(200, json={"items": [mock_broadcast]})
        )

        async with YouTubeClient(**youtube_config) as client:
            result = await client.list_broadcasts(status_filter="upcoming")
            assert len(result) == 1
            assert result[0]["id"] == "broadcast-123"

    @respx.mock
    @pytest.mark.asyncio
    async def test_transition_broadcast(self, youtube_config, mock_token_response, mock_broadcast):
        """Test transitioning broadcast status."""
        mock_broadcast["status"]["lifeCycleStatus"] = "live"
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.post("https://www.googleapis.com/youtube/v3/liveBroadcasts/transition").mock(
            return_value=Response(200, json=mock_broadcast)
        )

        async with YouTubeClient(**youtube_config) as client:
            result = await client.transition_broadcast("broadcast-123", "live")
            assert result["status"]["lifeCycleStatus"] == "live"

    @respx.mock
    @pytest.mark.asyncio
    async def test_delete_broadcast(self, youtube_config, mock_token_response):
        """Test deleting a broadcast."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.delete("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(204)
        )

        async with YouTubeClient(**youtube_config) as client:
            result = await client.delete_broadcast("broadcast-123")
            assert result["success"] is True


# =============================================================================
# Client Tests - Streams
# =============================================================================


class TestYouTubeClientStreams:
    """Test stream operations."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_stream(self, youtube_config, mock_token_response, mock_stream):
        """Test creating a stream."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.post("https://www.googleapis.com/youtube/v3/liveStreams").mock(
            return_value=Response(200, json=mock_stream)
        )

        async with YouTubeClient(**youtube_config) as client:
            result = await client.create_stream(
                title="Test Stream",
                resolution="1080p",
                frame_rate="30fps",
            )

            assert result["id"] == "stream-456"
            assert result["cdn"]["ingestionInfo"]["streamName"] == "xxxx-xxxx-xxxx-xxxx"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_stream(self, youtube_config, mock_token_response, mock_stream):
        """Test getting a stream by ID."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.get("https://www.googleapis.com/youtube/v3/liveStreams").mock(
            return_value=Response(200, json={"items": [mock_stream]})
        )

        async with YouTubeClient(**youtube_config) as client:
            result = await client.get_stream("stream-456")
            assert result["id"] == "stream-456"


# =============================================================================
# Client Tests - Combined Operations
# =============================================================================


class TestYouTubeClientCombined:
    """Test combined operations."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_broadcast_with_stream(
        self, youtube_config, mock_token_response, mock_broadcast, mock_stream
    ):
        """Test creating broadcast with stream."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.post("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(200, json=mock_broadcast)
        )
        respx.post("https://www.googleapis.com/youtube/v3/liveStreams").mock(
            return_value=Response(200, json=mock_stream)
        )
        respx.post("https://www.googleapis.com/youtube/v3/liveBroadcasts/bind").mock(
            return_value=Response(200, json=mock_broadcast)
        )

        async with YouTubeClient(**youtube_config) as client:
            result = await client.create_broadcast_with_stream(
                title="Test",
                scheduled_start="2024-01-15T10:00:00Z",
            )

            assert result["broadcast"]["id"] == "broadcast-123"
            assert result["stream"]["id"] == "stream-456"
            assert result["rtmp_credentials"]["rtmp_url"] == "rtmp://a.rtmp.youtube.com/live2"
            assert result["rtmp_credentials"]["stream_key"] == "xxxx-xxxx-xxxx-xxxx"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_broadcast_status(
        self, youtube_config, mock_token_response, mock_broadcast, mock_stream
    ):
        """Test getting comprehensive broadcast status."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        # First call gets broadcast
        respx.get(
            "https://www.googleapis.com/youtube/v3/liveBroadcasts",
            params__contains={"id": "broadcast-123"},
        ).mock(return_value=Response(200, json={"items": [mock_broadcast]}))
        # Second call gets stream
        respx.get(
            "https://www.googleapis.com/youtube/v3/liveStreams",
            params__contains={"id": "stream-456"},
        ).mock(return_value=Response(200, json={"items": [mock_stream]}))

        async with YouTubeClient(**youtube_config) as client:
            result = await client.get_broadcast_status("broadcast-123")

            assert result["broadcast_id"] == "broadcast-123"
            assert result["title"] == "Test Broadcast"
            assert result["broadcast_status"] == "created"
            assert result["bound_stream_id"] == "stream-456"
            assert result["stream_status"] is not None


# =============================================================================
# Client Tests - Error Handling
# =============================================================================


class TestYouTubeClientErrors:
    """Test error handling."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_quota_exceeded(self, youtube_config, mock_token_response):
        """Test handling of quota exceeded error."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.get("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(
                403,
                json={
                    "error": {
                        "code": 403,
                        "message": "Quota exceeded",
                        "errors": [{"reason": "quotaExceeded"}],
                    }
                },
            )
        )

        async with YouTubeClient(**youtube_config) as client:
            with pytest.raises(YouTubeQuotaError, match="quota exceeded"):
                await client.list_broadcasts()

    @respx.mock
    @pytest.mark.asyncio
    async def test_forbidden_error(self, youtube_config, mock_token_response):
        """Test handling of forbidden error."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.get("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(
                403,
                json={
                    "error": {
                        "code": 403,
                        "message": "Access forbidden",
                        "errors": [{"reason": "forbidden"}],
                    }
                },
            )
        )

        async with YouTubeClient(**youtube_config) as client:
            with pytest.raises(YouTubeAuthError, match="Access forbidden"):
                await client.list_broadcasts()

    @respx.mock
    @pytest.mark.asyncio
    async def test_token_retry_on_401(self, youtube_config, mock_token_response, mock_broadcast):
        """Test that 401 triggers token refresh retry."""
        call_count = {"token": 0, "api": 0}

        def token_side_effect(request):
            call_count["token"] += 1
            return Response(200, json=mock_token_response)

        def api_side_effect(request):
            call_count["api"] += 1
            if call_count["api"] == 1:
                return Response(401, json={"error": {"message": "Unauthorized"}})
            return Response(200, json={"items": [mock_broadcast]})

        respx.post("https://oauth2.googleapis.com/token").mock(side_effect=token_side_effect)
        respx.get("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            side_effect=api_side_effect
        )

        async with YouTubeClient(**youtube_config) as client:
            result = await client.list_broadcasts()
            assert len(result) == 1
            assert call_count["token"] == 2  # Initial + retry
            assert call_count["api"] == 2  # Initial fail + retry success


# =============================================================================
# MCP Tool Tests
# =============================================================================


class TestMCPTools:
    """Test MCP tools."""

    @pytest.mark.asyncio
    async def test_create_youtube_broadcast_missing_config(self):
        """Test tool with missing configuration."""
        with patch.dict("os.environ", {}, clear=True):
            result = await create_youtube_broadcast(
                title="Test",
                scheduled_start="2024-01-15T10:00:00Z",
            )
            assert "error" in result
            assert "YOUTUBE_CLIENT_ID" in result["error"]

    @pytest.mark.asyncio
    async def test_create_youtube_broadcast_missing_title(self):
        """Test tool with missing title."""
        result = await create_youtube_broadcast(
            title="",
            scheduled_start="2024-01-15T10:00:00Z",
        )
        assert result == {"error": "title is required"}

    @pytest.mark.asyncio
    async def test_create_youtube_broadcast_missing_start(self):
        """Test tool with missing scheduled start."""
        result = await create_youtube_broadcast(
            title="Test",
            scheduled_start="",
        )
        assert result == {"error": "scheduled_start is required (ISO 8601 format)"}

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_youtube_broadcast_success(
        self, mock_token_response, mock_broadcast, mock_stream
    ):
        """Test successful broadcast creation."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.post("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(200, json=mock_broadcast)
        )
        respx.post("https://www.googleapis.com/youtube/v3/liveStreams").mock(
            return_value=Response(200, json=mock_stream)
        )
        respx.post("https://www.googleapis.com/youtube/v3/liveBroadcasts/bind").mock(
            return_value=Response(200, json=mock_broadcast)
        )

        with patch.dict(
            "os.environ",
            {
                "YOUTUBE_CLIENT_ID": "test-id",
                "YOUTUBE_CLIENT_SECRET": "test-secret",
                "YOUTUBE_REFRESH_TOKEN": "test-token",
            },
        ):
            result = await create_youtube_broadcast(
                title="Test Broadcast",
                scheduled_start="2024-01-15T10:00:00Z",
            )

            assert "error" not in result
            assert result["broadcast_id"] == "broadcast-123"
            assert result["stream_id"] == "stream-456"
            assert result["rtmp_url"] == "rtmp://a.rtmp.youtube.com/live2"
            assert result["stream_key"] == "xxxx-xxxx-xxxx-xxxx"

    @pytest.mark.asyncio
    async def test_get_youtube_broadcast_status_missing_id(self):
        """Test tool with missing broadcast ID."""
        result = await get_youtube_broadcast_status("")
        assert result == {"error": "broadcast_id is required"}

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_youtube_broadcast_status_success(
        self, mock_token_response, mock_broadcast, mock_stream
    ):
        """Test successful status retrieval."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.get("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(200, json={"items": [mock_broadcast]})
        )
        respx.get("https://www.googleapis.com/youtube/v3/liveStreams").mock(
            return_value=Response(200, json={"items": [mock_stream]})
        )

        with patch.dict(
            "os.environ",
            {
                "YOUTUBE_CLIENT_ID": "test-id",
                "YOUTUBE_CLIENT_SECRET": "test-secret",
                "YOUTUBE_REFRESH_TOKEN": "test-token",
            },
        ):
            result = await get_youtube_broadcast_status("broadcast-123")

            assert "error" not in result
            assert result["status"]["broadcast_id"] == "broadcast-123"
            assert result["status"]["broadcast_status"] == "created"

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_youtube_broadcasts_success(self, mock_token_response, mock_broadcast):
        """Test successful broadcast listing."""
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.get("https://www.googleapis.com/youtube/v3/liveBroadcasts").mock(
            return_value=Response(200, json={"items": [mock_broadcast]})
        )

        with patch.dict(
            "os.environ",
            {
                "YOUTUBE_CLIENT_ID": "test-id",
                "YOUTUBE_CLIENT_SECRET": "test-secret",
                "YOUTUBE_REFRESH_TOKEN": "test-token",
            },
        ):
            result = await list_youtube_broadcasts(status_filter="upcoming")

            assert "error" not in result
            assert result["count"] == 1
            assert result["broadcasts"][0]["id"] == "broadcast-123"
            assert result["filter"] == "upcoming"

    @pytest.mark.asyncio
    async def test_end_youtube_broadcast_missing_id(self):
        """Test tool with missing broadcast ID."""
        result = await end_youtube_broadcast("")
        assert result == {"error": "broadcast_id is required"}

    @respx.mock
    @pytest.mark.asyncio
    async def test_end_youtube_broadcast_success(self, mock_token_response, mock_broadcast):
        """Test successful broadcast ending."""
        mock_broadcast["status"]["lifeCycleStatus"] = "complete"
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(200, json=mock_token_response)
        )
        respx.post("https://www.googleapis.com/youtube/v3/liveBroadcasts/transition").mock(
            return_value=Response(200, json=mock_broadcast)
        )

        with patch.dict(
            "os.environ",
            {
                "YOUTUBE_CLIENT_ID": "test-id",
                "YOUTUBE_CLIENT_SECRET": "test-secret",
                "YOUTUBE_REFRESH_TOKEN": "test-token",
            },
        ):
            result = await end_youtube_broadcast("broadcast-123")

            assert "error" not in result
            assert result["success"] is True
            assert result["broadcast_id"] == "broadcast-123"
            assert result["new_status"] == "complete"


# =============================================================================
# Tool Registry Tests
# =============================================================================


class TestToolRegistry:
    """Test tool registry."""

    def test_youtube_tools_list(self):
        """Test that all tools are in the registry."""
        from epiphan_mcp.tools.youtube import YOUTUBE_TOOLS

        assert len(YOUTUBE_TOOLS) == 4
        assert create_youtube_broadcast in YOUTUBE_TOOLS
        assert get_youtube_broadcast_status in YOUTUBE_TOOLS
        assert list_youtube_broadcasts in YOUTUBE_TOOLS
        assert end_youtube_broadcast in YOUTUBE_TOOLS
