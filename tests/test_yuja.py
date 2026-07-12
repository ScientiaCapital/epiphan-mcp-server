"""Tests for YuJa CMS integration.

Tests cover:
- YuJaClient static-token authentication (authToken header)
- Video/media management operations
- Channel listing
- Signed-URL two-step upload workflow
- MCP tool wrappers
"""

import json
import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from httpx import Response

from epiphan_mcp.integrations.yuja import (
    YuJaAPIError,
    YuJaAuthError,
    YuJaClient,
)

# ============================================================================
# YuJaClient Tests
# ============================================================================

HOST = "university.yuja.com"
API = f"https://{HOST}/services"


def _client() -> YuJaClient:
    return YuJaClient(host=HOST, auth_token="test-token")


class TestYuJaClientInit:
    """Tests for YuJaClient initialization."""

    def test_client_init_https_only(self):
        """YuJa is HTTPS-only; base URLs reflect that."""
        client = _client()
        assert client.base_url == f"https://{HOST}"
        assert client.api_base == API

    def test_auth_headers_use_authtoken(self):
        """The static token rides in the authToken header."""
        client = _client()
        headers = client._auth_headers()
        assert headers["authToken"] == "test-token"

    @pytest.mark.asyncio
    async def test_request_without_context_raises(self):
        """Requests outside the context manager fail cleanly."""
        client = _client()
        with pytest.raises(YuJaAPIError, match="not initialized"):
            await client._request("GET", "/media/videos")


class TestYuJaClientAuth:
    """Tests for authentication error handling."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_401_raises_auth_error(self):
        """A 401 response raises YuJaAuthError."""
        respx.get(f"{API}/media/videos").mock(
            return_value=Response(401, text="invalid token")
        )
        async with _client() as client:
            with pytest.raises(YuJaAuthError, match="Authentication failed"):
                await client.list_videos()

    @pytest.mark.asyncio
    @respx.mock
    async def test_403_raises_auth_error_with_permission_hint(self):
        """A 403 mentions the Epiphan minimum-permission requirements."""
        respx.get(f"{API}/media/videos").mock(
            return_value=Response(403, text="insufficient permissions")
        )
        async with _client() as client:
            with pytest.raises(YuJaAuthError, match="permissions"):
                await client.list_videos()

    @pytest.mark.asyncio
    @respx.mock
    async def test_500_raises_api_error_with_status(self):
        """Non-auth HTTP errors raise YuJaAPIError with status_code."""
        respx.get(f"{API}/media/videos").mock(return_value=Response(500, text="boom"))
        async with _client() as client:
            with pytest.raises(YuJaAPIError) as exc_info:
                await client.list_videos()
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    @respx.mock
    async def test_network_error_raises_api_error(self):
        """Transport failures surface as YuJaAPIError."""
        respx.get(f"{API}/media/videos").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        async with _client() as client:
            with pytest.raises(YuJaAPIError, match="Request failed"):
                await client.list_videos()

    @pytest.mark.asyncio
    @respx.mock
    async def test_authtoken_header_sent(self):
        """Every API call carries the authToken header."""
        route = respx.get(f"{API}/media/videos").mock(return_value=Response(200, json=[]))
        async with _client() as client:
            await client.list_videos()
        assert route.calls.last.request.headers["authToken"] == "test-token"


class TestYuJaClientVideos:
    """Tests for video/media management."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_videos_from_list_response(self):
        """A bare JSON list response is returned as the video list."""
        respx.get(f"{API}/media/videos").mock(
            return_value=Response(200, json=[{"id": "1", "title": "Lecture 1"}])
        )
        async with _client() as client:
            videos = await client.list_videos()
        assert len(videos) == 1
        assert videos[0]["title"] == "Lecture 1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_videos_with_search(self):
        """The search term is passed as a query parameter."""
        route = respx.get(f"{API}/media/videos").mock(return_value=Response(200, json=[]))
        async with _client() as client:
            await client.list_videos(search_query="physics")
        assert route.calls.last.request.url.params["search"] == "physics"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_video_metadata(self):
        """Metadata is fetched from /media/metadata/{id}."""
        respx.get(f"{API}/media/metadata/187195").mock(
            return_value=Response(200, json={"id": "187195", "title": "Lecture"})
        )
        async with _client() as client:
            video = await client.get_video_metadata("187195")
        assert video["id"] == "187195"

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_video(self):
        """Delete returns success on 204."""
        respx.delete(f"{API}/media/videos/187195").mock(return_value=Response(204))
        async with _client() as client:
            result = await client.delete_video("187195")
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_channels(self):
        """Channels come back from /channels."""
        respx.get(f"{API}/channels").mock(
            return_value=Response(200, json=[{"id": "c1", "name": "Physics"}])
        )
        async with _client() as client:
            channels = await client.list_channels()
        assert channels[0]["name"] == "Physics"


class TestYuJaClientUpload:
    """Tests for the signed-URL two-step upload workflow."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_upload_links(self):
        """Step 1 posts the filename and returns the upload session."""
        route = respx.post(f"{API}/media/upload/session/619/createlinks").mock(
            return_value=Response(
                200, json={"sessionId": 1234, "uploadUrl": "https://s3.example.com/signed"}
            )
        )
        async with _client() as client:
            session = await client.create_upload_links(user_id="619", filename="lecture.mp4")
        assert session["sessionId"] == 1234
        assert json.loads(route.calls.last.request.content) == {"fileName": "lecture.mp4"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file_to_url(self, tmp_path):
        """Step 2 PUTs the file bytes to the signed URL."""
        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.put("https://s3.example.com/signed").mock(return_value=Response(200))
        async with _client() as client:
            ok = await client.upload_file_to_url("https://s3.example.com/signed", video)
        assert ok is True

    @pytest.mark.asyncio
    async def test_upload_file_missing_raises(self):
        """A nonexistent file fails before any network call."""
        async with _client() as client:
            with pytest.raises(YuJaAPIError, match="File not found"):
                await client.upload_file_to_url(
                    "https://s3.example.com/signed", "/nonexistent/file.mp4"
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file_s3_failure_raises(self, tmp_path):
        """An S3 error status raises YuJaAPIError."""
        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.put("https://s3.example.com/signed").mock(
            return_value=Response(403, text="signature expired")
        )
        async with _client() as client:
            with pytest.raises(YuJaAPIError, match="S3 upload failed"):
                await client.upload_file_to_url("https://s3.example.com/signed", video)

    @pytest.mark.asyncio
    @respx.mock
    async def test_complete_upload(self):
        """Step 3 signals processing should begin."""
        respx.post(f"{API}/media/upload/session/1234").mock(
            return_value=Response(200, json={"sessionId": 1234, "state": "processing"})
        )
        async with _client() as client:
            result = await client.complete_upload("1234")
        assert result["state"] == "processing"

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_video_full_flow(self, tmp_path):
        """The high-level upload runs createlinks -> S3 PUT -> complete -> status."""
        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.post(f"{API}/media/upload/session/619/createlinks").mock(
            return_value=Response(
                200, json={"sessionId": 1234, "uploadUrl": "https://s3.example.com/signed"}
            )
        )
        s3_route = respx.put("https://s3.example.com/signed").mock(return_value=Response(200))
        complete_route = respx.post(f"{API}/media/upload/session/1234").mock(
            return_value=Response(200, json={"sessionId": 1234, "state": "processing"})
        )
        respx.get(f"{API}/media/upload/session/1234").mock(
            return_value=Response(200, json={"sessionId": 1234, "state": "processing"})
        )

        async with _client() as client:
            status = await client.upload_video(user_id="619", file_path=video)

        assert s3_route.called
        assert complete_route.called
        assert status["state"] == "processing"

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_video_missing_session_fields_raises(self, tmp_path):
        """A malformed createlinks response fails loudly, not silently."""
        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.post(f"{API}/media/upload/session/619/createlinks").mock(
            return_value=Response(200, json={"unexpected": "shape"})
        )
        async with _client() as client:
            with pytest.raises(YuJaAPIError, match="missing sessionId/uploadUrl"):
                await client.upload_video(user_id="619", file_path=video)


# ============================================================================
# MCP Tool Tests
# ============================================================================

YUJA_ENV = {
    "YUJA_HOST": HOST,
    "YUJA_AUTH_TOKEN": "test-token",
    "YUJA_USER_ID": "619",
}


class TestYuJaConfigValidation:
    """Tests for YuJa tool configuration validation."""

    @pytest.mark.asyncio
    async def test_missing_config_returns_error(self):
        """Missing env vars produce a typed error, not an exception."""
        from epiphan_mcp.tools.yuja import list_yuja_videos

        with patch.dict(os.environ, {}, clear=True):
            result = await list_yuja_videos()
        assert result.error is not None
        assert "YUJA_HOST" in result.error
        assert "YUJA_AUTH_TOKEN" in result.error

    @pytest.mark.asyncio
    async def test_missing_config_all_tools(self):
        """Every tool degrades gracefully without configuration."""
        from epiphan_mcp.tools.yuja import (
            delete_yuja_video,
            get_yuja_upload_status,
            get_yuja_video,
            list_yuja_channels,
        )

        with patch.dict(os.environ, {}, clear=True):
            assert (await get_yuja_video(video_id="1")).error is not None
            assert (await list_yuja_channels()).error is not None
            assert (await get_yuja_upload_status(session_id="1")).error is not None
            assert (await delete_yuja_video(video_id="1")).error is not None


class TestListYuJaVideos:
    """Tests for list_yuja_videos tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_videos_success(self):
        from epiphan_mcp.tools.yuja import list_yuja_videos

        respx.get(f"{API}/media/videos").mock(
            return_value=Response(200, json=[{"id": "1", "title": "Lecture 1"}])
        )
        with patch.dict(os.environ, YUJA_ENV):
            result = await list_yuja_videos()

        assert result.error is None
        assert result.count == 1
        assert result.videos[0]["title"] == "Lecture 1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_videos_auth_error(self):
        from epiphan_mcp.tools.yuja import list_yuja_videos

        respx.get(f"{API}/media/videos").mock(return_value=Response(401, text="bad token"))
        with patch.dict(os.environ, YUJA_ENV):
            result = await list_yuja_videos()

        assert result.error is not None
        assert "Authentication failed" in result.error
        assert result.videos == []


class TestGetYuJaVideo:
    """Tests for get_yuja_video tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_video_success(self):
        from epiphan_mcp.tools.yuja import get_yuja_video

        respx.get(f"{API}/media/metadata/187195").mock(
            return_value=Response(200, json={"id": "187195", "title": "Lecture"})
        )
        with patch.dict(os.environ, YUJA_ENV):
            result = await get_yuja_video(video_id="187195")

        assert result.error is None
        assert result.video is not None
        assert result.video["id"] == "187195"

    @pytest.mark.asyncio
    async def test_get_video_requires_id(self):
        from epiphan_mcp.tools.yuja import get_yuja_video

        result = await get_yuja_video(video_id="")
        assert result.error is not None
        assert "video_id" in result.error


class TestListYuJaChannels:
    """Tests for list_yuja_channels tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_channels_success(self):
        from epiphan_mcp.tools.yuja import list_yuja_channels

        respx.get(f"{API}/channels").mock(
            return_value=Response(200, json=[{"id": "c1", "name": "Physics"}])
        )
        with patch.dict(os.environ, YUJA_ENV):
            result = await list_yuja_channels()

        assert result.error is None
        assert result.count == 1
        assert result.channels[0]["name"] == "Physics"


class TestUploadVideoToYuJa:
    """Tests for upload_video_to_yuja tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_success(self, tmp_path):
        from epiphan_mcp.tools.yuja import upload_video_to_yuja

        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.post(f"{API}/media/upload/session/619/createlinks").mock(
            return_value=Response(
                200, json={"sessionId": 1234, "uploadUrl": "https://s3.example.com/signed"}
            )
        )
        respx.put("https://s3.example.com/signed").mock(return_value=Response(200))
        respx.post(f"{API}/media/upload/session/1234").mock(
            return_value=Response(200, json={"sessionId": 1234, "state": "processing"})
        )
        respx.get(f"{API}/media/upload/session/1234").mock(
            return_value=Response(200, json={"sessionId": 1234, "state": "processing"})
        )

        with patch.dict(os.environ, YUJA_ENV):
            result = await upload_video_to_yuja(file_path=str(video))

        assert result.error is None
        assert result.upload is not None
        assert result.file_size == len(b"fake video content")
        assert "lecture.mp4" in (result.message or "")

    @pytest.mark.asyncio
    async def test_upload_missing_file(self):
        from epiphan_mcp.tools.yuja import upload_video_to_yuja

        with patch.dict(os.environ, YUJA_ENV):
            result = await upload_video_to_yuja(file_path="/nonexistent/file.mp4")
        assert result.error is not None
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_upload_requires_user_id(self, tmp_path):
        from epiphan_mcp.tools.yuja import upload_video_to_yuja

        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        env = {k: v for k, v in YUJA_ENV.items() if k != "YUJA_USER_ID"}
        with patch.dict(os.environ, env, clear=True):
            result = await upload_video_to_yuja(file_path=str(video))
        assert result.error is not None
        assert "user_id" in result.error

    @pytest.mark.asyncio
    async def test_upload_logs_audit_entry(self, tmp_path):
        """Destructive/outbound operations hit the audit log."""
        from epiphan_mcp.tools import yuja as yuja_tools

        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        with (
            patch.dict(os.environ, YUJA_ENV),
            patch.object(yuja_tools, "log_operation") as mock_log,
            patch.object(yuja_tools.YuJaClient, "upload_video", new=AsyncMock(return_value={})),
        ):
            result = await yuja_tools.upload_video_to_yuja(file_path=str(video))

        assert result.error is None
        mock_log.assert_called_once()


class TestGetYuJaUploadStatus:
    """Tests for get_yuja_upload_status tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_status_success(self):
        from epiphan_mcp.tools.yuja import get_yuja_upload_status

        respx.get(f"{API}/media/upload/session/1234").mock(
            return_value=Response(200, json={"sessionId": 1234, "state": "complete"})
        )
        with patch.dict(os.environ, YUJA_ENV):
            result = await get_yuja_upload_status(session_id="1234")

        assert result.error is None
        assert result.session_id == "1234"
        assert result.status == "complete"

    @pytest.mark.asyncio
    async def test_status_requires_session_id(self):
        from epiphan_mcp.tools.yuja import get_yuja_upload_status

        result = await get_yuja_upload_status(session_id="")
        assert result.error is not None


class TestDeleteYuJaVideo:
    """Tests for delete_yuja_video tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_success(self):
        from epiphan_mcp.tools.yuja import delete_yuja_video

        respx.delete(f"{API}/media/videos/187195").mock(return_value=Response(204))
        with patch.dict(os.environ, YUJA_ENV):
            result = await delete_yuja_video(video_id="187195")

        assert result.success is True
        assert result.video_id == "187195"

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_api_error(self):
        from epiphan_mcp.tools.yuja import delete_yuja_video

        respx.delete(f"{API}/media/videos/187195").mock(
            return_value=Response(404, text="not found")
        )
        with patch.dict(os.environ, YUJA_ENV):
            result = await delete_yuja_video(video_id="187195")

        assert result.success is None
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_delete_requires_id(self):
        from epiphan_mcp.tools.yuja import delete_yuja_video

        result = await delete_yuja_video(video_id="")
        assert result.error is not None
