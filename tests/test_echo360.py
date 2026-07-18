"""Tests for Echo360 (EchoVideo) CMS integration.

Tests cover:
- Echo360Client OAuth2 client-credentials authentication
- Refresh-token rotation (single-use refresh tokens)
- Course / section / media listing
- Capture Intake signed-URL upload workflow
- Rate-limit (429) handling
- MCP tool wrappers
"""

import json
import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from httpx import Response

from epiphan_mcp.integrations.echo360 import (
    Echo360APIError,
    Echo360AuthError,
    Echo360Client,
)

# ============================================================================
# Echo360Client Tests
# ============================================================================

HOST = "echo360.org"
API = f"https://{HOST}/public/api/v1"
TOKEN_URL = f"https://{HOST}/oauth2/access_token"


def _client() -> Echo360Client:
    return Echo360Client(host=HOST, client_id="test-id", client_secret="test-secret")


def _mock_token(
    access_token: str = "tok-1",
    refresh_token: str | None = "refresh-1",
    expires_in: int = 3600,
) -> respx.Route:
    payload: dict = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
    }
    if refresh_token is not None:
        payload["refresh_token"] = refresh_token
    return respx.post(TOKEN_URL).mock(return_value=Response(200, json=payload))


class TestEcho360ClientInit:
    """Tests for Echo360Client initialization."""

    def test_client_init_https_only(self):
        """Echo360 is hosted SaaS; base URLs are HTTPS."""
        client = _client()
        assert client.base_url == f"https://{HOST}"
        assert client.api_base == API
        assert client.token_url == TOKEN_URL

    def test_auth_headers_require_token(self):
        """Auth headers before authentication fail cleanly."""
        client = _client()
        with pytest.raises(Echo360AuthError, match="Not authenticated"):
            client._auth_headers()

    @pytest.mark.asyncio
    async def test_request_without_context_raises(self):
        """Requests outside the context manager fail cleanly."""
        client = _client()
        with pytest.raises(Echo360APIError, match="not initialized"):
            await client._request("GET", "/medias")


class TestEcho360ClientAuth:
    """Tests for OAuth2 client-credentials auth and refresh rotation."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_client_credentials_grant_posted(self):
        """Entering the context posts a client_credentials grant."""
        route = _mock_token()
        async with _client():
            pass
        body = route.calls.last.request.content.decode()
        assert "grant_type=client_credentials" in body
        assert "client_id=test-id" in body
        assert "client_secret=test-secret" in body

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_failure_raises_auth_error(self):
        """A non-200 token response raises Echo360AuthError."""
        respx.post(TOKEN_URL).mock(return_value=Response(400, text="invalid_client"))
        with pytest.raises(Echo360AuthError, match="Authentication failed"):
            async with _client():
                pass

    @pytest.mark.asyncio
    @respx.mock
    async def test_bearer_header_sent(self):
        """Every API call carries the Bearer token."""
        _mock_token(access_token="tok-abc")
        route = respx.get(f"{API}/medias").mock(return_value=Response(200, json=[]))
        async with _client() as client:
            await client.list_medias()
        assert route.calls.last.request.headers["Authorization"] == "Bearer tok-abc"

    @pytest.mark.asyncio
    @respx.mock
    async def test_expired_token_uses_refresh_grant(self):
        """An expired token triggers a refresh grant with the stored token."""
        token_route = respx.post(TOKEN_URL)
        token_route.side_effect = [
            Response(
                200,
                json={
                    "access_token": "tok-1",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "refresh_token": "refresh-1",
                },
            ),
            Response(
                200,
                json={
                    "access_token": "tok-2",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "refresh_token": "refresh-2",
                },
            ),
        ]
        respx.get(f"{API}/medias").mock(return_value=Response(200, json=[]))

        async with _client() as client:
            assert client._token is not None
            client._token.expires_in = 0  # force expiry
            await client.list_medias()

        body = token_route.calls.last.request.content.decode()
        assert "grant_type=refresh_token" in body
        assert "refresh_token=refresh-1" in body
        # Rotation: the newly issued refresh token replaces the consumed one
        assert client._token is not None
        assert client._token.refresh_token == "refresh-2"
        assert client._token.access_token == "tok-2"

    @pytest.mark.asyncio
    @respx.mock
    async def test_failed_refresh_falls_back_to_client_credentials(self):
        """A consumed refresh token falls back to a fresh grant."""
        token_route = respx.post(TOKEN_URL)
        token_route.side_effect = [
            Response(
                200,
                json={
                    "access_token": "tok-1",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "refresh_token": "refresh-1",
                },
            ),
            Response(400, text="refresh token already used"),
            Response(
                200,
                json={
                    "access_token": "tok-3",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "refresh_token": "refresh-3",
                },
            ),
        ]
        respx.get(f"{API}/medias").mock(return_value=Response(200, json=[]))

        async with _client() as client:
            assert client._token is not None
            client._token.expires_in = 0  # force expiry
            await client.list_medias()
            assert client._token.access_token == "tok-3"

        final_grant = token_route.calls.last.request.content.decode()
        assert "grant_type=client_credentials" in final_grant

    @pytest.mark.asyncio
    @respx.mock
    async def test_401_raises_auth_error(self):
        """A 401 API response raises Echo360AuthError."""
        _mock_token()
        respx.get(f"{API}/medias").mock(return_value=Response(401, text="unauthorized"))
        async with _client() as client:
            with pytest.raises(Echo360AuthError, match="Authentication failed"):
                await client.list_medias()

    @pytest.mark.asyncio
    @respx.mock
    async def test_429_raises_api_error_with_rate_limit_hint(self):
        """A 429 mentions the 120 requests/minute limit."""
        _mock_token()
        respx.get(f"{API}/medias").mock(return_value=Response(429, text="slow down"))
        async with _client() as client:
            with pytest.raises(Echo360APIError, match="120 requests/minute") as exc_info:
                await client.list_medias()
            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    @respx.mock
    async def test_500_raises_api_error_with_status(self):
        """Non-auth HTTP errors raise Echo360APIError with status_code."""
        _mock_token()
        respx.get(f"{API}/medias").mock(return_value=Response(500, text="boom"))
        async with _client() as client:
            with pytest.raises(Echo360APIError) as exc_info:
                await client.list_medias()
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    @respx.mock
    async def test_network_error_raises_api_error(self):
        """Transport failures surface as Echo360APIError."""
        _mock_token()
        respx.get(f"{API}/medias").mock(side_effect=httpx.ConnectError("connection refused"))
        async with _client() as client:
            with pytest.raises(Echo360APIError, match="Request failed"):
                await client.list_medias()


class TestEcho360ClientContent:
    """Tests for course / section / media listing."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_courses_from_list_response(self):
        """A bare JSON list response is returned as the course list."""
        _mock_token()
        respx.get(f"{API}/courses").mock(
            return_value=Response(200, json=[{"id": "c1", "name": "Physics 101"}])
        )
        async with _client() as client:
            courses, truncated = await client.list_courses()
        assert len(courses) == 1
        assert courses[0]["name"] == "Physics 101"
        assert truncated is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_courses_from_data_envelope(self):
        """A paginated ``data`` envelope is unwrapped."""
        _mock_token()
        respx.get(f"{API}/courses").mock(
            return_value=Response(200, json={"data": [{"id": "c1"}], "total": 1})
        )
        async with _client() as client:
            courses, truncated = await client.list_courses()
        assert courses == [{"id": "c1"}]
        assert truncated is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_sections_with_course_filter(self):
        """The course filter is passed as a query parameter."""
        _mock_token()
        route = respx.get(f"{API}/sections").mock(return_value=Response(200, json=[]))
        async with _client() as client:
            await client.list_sections(course_id="c1")
        assert route.calls.last.request.url.params["courseId"] == "c1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_medias_with_search(self):
        """The search term is passed as a query parameter."""
        _mock_token()
        route = respx.get(f"{API}/medias").mock(return_value=Response(200, json=[]))
        async with _client() as client:
            await client.list_medias(search_query="physics")
        assert route.calls.last.request.url.params["search"] == "physics"

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_courses_reports_truncation_from_total(self):
        """An envelope total larger than the page marks the result truncated."""
        _mock_token()
        respx.get(f"{API}/courses").mock(
            return_value=Response(200, json={"data": [{"id": "c1"}, {"id": "c2"}], "total": 250})
        )
        async with _client() as client:
            courses, truncated = await client.list_courses()
        assert len(courses) == 2
        assert truncated is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_courses_reports_truncation_from_next_link(self):
        """A non-null next link marks the result truncated."""
        _mock_token()
        respx.get(f"{API}/courses").mock(
            return_value=Response(200, json={"data": [{"id": "c1"}], "next": "/courses?page=2"})
        )
        async with _client() as client:
            _courses, truncated = await client.list_courses()
        assert truncated is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_courses_complete_page_not_truncated(self):
        """A complete page (total == items, no next link) is not truncated."""
        _mock_token()
        respx.get(f"{API}/courses").mock(
            return_value=Response(200, json={"data": [{"id": "c1"}], "total": 1})
        )
        async with _client() as client:
            _courses, truncated = await client.list_courses()
        assert truncated is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_media(self):
        """Media detail is fetched from /medias/{id}."""
        _mock_token()
        respx.get(f"{API}/medias/m1").mock(
            return_value=Response(200, json={"id": "m1", "title": "Lecture"})
        )
        async with _client() as client:
            media = await client.get_media("m1")
        assert media["id"] == "m1"


class TestEcho360ClientUpload:
    """Tests for the Capture Intake signed-URL upload workflow."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_pending_upload(self):
        """Step 1 posts the filename and returns the pending upload."""
        _mock_token()
        route = respx.post(f"{API}/pending-capture-uploads").mock(
            return_value=Response(
                200, json={"uploadId": "u1", "uploadUrl": "https://s3.example.com/signed"}
            )
        )
        async with _client() as client:
            pending = await client.create_pending_upload(filename="lecture.mp4")
        assert pending["uploadId"] == "u1"
        assert json.loads(route.calls.last.request.content) == {"fileName": "lecture.mp4"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_pending_upload_with_part_size(self):
        """Multipart part size is included when specified."""
        _mock_token()
        route = respx.post(f"{API}/pending-capture-uploads").mock(
            return_value=Response(200, json={"uploadId": "u1", "uploadUrl": "https://s3/x"})
        )
        async with _client() as client:
            await client.create_pending_upload(filename="big.mp4", part_size_bytes=5 * 1024 * 1024)
        body = json.loads(route.calls.last.request.content)
        assert body["partSizeInBytes"] == 5 * 1024 * 1024

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file_to_url(self, tmp_path):
        """Step 2 PUTs the file bytes to the signed URL."""
        _mock_token()
        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.put("https://s3.example.com/signed").mock(return_value=Response(200))
        async with _client() as client:
            ok = await client.upload_file_to_url("https://s3.example.com/signed", video)
        assert ok is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file_missing_raises(self):
        """A nonexistent file fails before any network call."""
        _mock_token()
        async with _client() as client:
            with pytest.raises(Echo360APIError, match="File not found"):
                await client.upload_file_to_url(
                    "https://s3.example.com/signed", "/nonexistent/file.mp4"
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file_s3_failure_raises(self, tmp_path):
        """An S3 error status raises Echo360APIError."""
        _mock_token()
        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.put("https://s3.example.com/signed").mock(
            return_value=Response(403, text="signature expired")
        )
        async with _client() as client:
            with pytest.raises(Echo360APIError, match="S3 upload failed"):
                await client.upload_file_to_url("https://s3.example.com/signed", video)

    @pytest.mark.asyncio
    @respx.mock
    async def test_submit_upload(self):
        """Step 3 submits the upload for processing."""
        _mock_token()
        route = respx.post(f"{API}/submitted-capture-uploads").mock(
            return_value=Response(200, json={"uploadId": "u1", "state": "processing"})
        )
        async with _client() as client:
            result = await client.submit_upload("u1")
        assert result["state"] == "processing"
        assert json.loads(route.calls.last.request.content) == {"uploadId": "u1"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_video_full_flow(self, tmp_path):
        """The high-level upload runs pending -> S3 PUT -> submit -> status."""
        _mock_token()
        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.post(f"{API}/pending-capture-uploads").mock(
            return_value=Response(
                200, json={"uploadId": "u1", "uploadUrl": "https://s3.example.com/signed"}
            )
        )
        s3_route = respx.put("https://s3.example.com/signed").mock(return_value=Response(200))
        submit_route = respx.post(f"{API}/submitted-capture-uploads").mock(
            return_value=Response(200, json={"uploadId": "u1", "state": "processing"})
        )
        respx.get(f"{API}/pending-capture-uploads/u1").mock(
            return_value=Response(200, json={"uploadId": "u1", "state": "processing"})
        )

        async with _client() as client:
            status = await client.upload_video(file_path=video)

        assert s3_route.called
        assert submit_route.called
        assert status["state"] == "processing"

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_video_missing_pending_fields_raises(self, tmp_path):
        """A malformed pending-upload response fails loudly, not silently."""
        _mock_token()
        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.post(f"{API}/pending-capture-uploads").mock(
            return_value=Response(200, json={"unexpected": "shape"})
        )
        async with _client() as client:
            with pytest.raises(Echo360APIError, match="missing uploadId/uploadUrl"):
                await client.upload_video(file_path=video)

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_video_null_upload_id_falls_back_to_id(self, tmp_path):
        """An explicit JSON null uploadId falls through to the id key.

        Regression: `.get("uploadId", .get("id"))` returned None for an
        explicit null, which str() turned into the truthy string "None".
        """
        _mock_token()
        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.post(f"{API}/pending-capture-uploads").mock(
            return_value=Response(
                200,
                json={"uploadId": None, "id": "u9", "uploadUrl": "https://s3.example.com/signed"},
            )
        )
        respx.put("https://s3.example.com/signed").mock(return_value=Response(200))
        submit_route = respx.post(f"{API}/submitted-capture-uploads").mock(
            return_value=Response(200, json={"uploadId": "u9", "state": "processing"})
        )
        respx.get(f"{API}/pending-capture-uploads/u9").mock(
            return_value=Response(200, json={"uploadId": "u9", "state": "processing"})
        )

        async with _client() as client:
            await client.upload_video(file_path=video)

        assert submit_route.called
        assert json.loads(submit_route.calls.last.request.content) == {"uploadId": "u9"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_video_null_ids_raise(self, tmp_path):
        """uploadId and id both null raise the clear missing-fields error."""
        _mock_token()
        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.post(f"{API}/pending-capture-uploads").mock(
            return_value=Response(
                200,
                json={"uploadId": None, "id": None, "uploadUrl": "https://s3.example.com/signed"},
            )
        )
        async with _client() as client:
            with pytest.raises(Echo360APIError, match="missing uploadId/uploadUrl"):
                await client.upload_video(file_path=video)


# ============================================================================
# MCP Tool Tests
# ============================================================================

ECHO360_ENV = {
    "ECHO360_HOST": HOST,
    "ECHO360_CLIENT_ID": "test-id",
    "ECHO360_CLIENT_SECRET": "test-secret",
}


class TestEcho360ConfigValidation:
    """Tests for Echo360 tool configuration validation."""

    @pytest.mark.asyncio
    async def test_missing_config_returns_error(self):
        """Missing env vars produce a typed error, not an exception."""
        from epiphan_mcp.tools.echo360 import list_echo360_medias

        with patch.dict(os.environ, {}, clear=True):
            result = await list_echo360_medias()
        assert result.error is not None
        assert "ECHO360_HOST" in result.error
        assert "ECHO360_CLIENT_ID" in result.error
        assert "ECHO360_CLIENT_SECRET" in result.error

    @pytest.mark.asyncio
    async def test_missing_config_all_tools(self):
        """Every tool degrades gracefully without configuration."""
        from epiphan_mcp.tools.echo360 import (
            get_echo360_media,
            get_echo360_upload_status,
            list_echo360_courses,
            list_echo360_sections,
        )

        with patch.dict(os.environ, {}, clear=True):
            assert (await list_echo360_courses()).error is not None
            assert (await list_echo360_sections()).error is not None
            assert (await get_echo360_media(media_id="m1")).error is not None
            assert (await get_echo360_upload_status(upload_id="u1")).error is not None


class TestListEcho360Courses:
    """Tests for list_echo360_courses tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_courses_success(self):
        from epiphan_mcp.tools.echo360 import list_echo360_courses

        _mock_token()
        respx.get(f"{API}/courses").mock(
            return_value=Response(200, json=[{"id": "c1", "name": "Physics 101"}])
        )
        with patch.dict(os.environ, ECHO360_ENV):
            result = await list_echo360_courses()

        assert result.error is None
        assert result.count == 1
        assert result.courses[0]["name"] == "Physics 101"

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_courses_surfaces_truncation(self):
        """The tool exposes a truncated flag so callers know the list is partial."""
        from epiphan_mcp.tools.echo360 import list_echo360_courses

        _mock_token()
        respx.get(f"{API}/courses").mock(
            return_value=Response(200, json={"data": [{"id": "c1"}, {"id": "c2"}], "total": 250})
        )
        with patch.dict(os.environ, ECHO360_ENV):
            result = await list_echo360_courses()

        assert result.error is None
        assert result.count == 2
        assert result.truncated is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_courses_auth_error(self):
        from epiphan_mcp.tools.echo360 import list_echo360_courses

        respx.post(TOKEN_URL).mock(return_value=Response(400, text="invalid_client"))
        with patch.dict(os.environ, ECHO360_ENV):
            result = await list_echo360_courses()

        assert result.error is not None
        assert "Authentication failed" in result.error
        assert result.courses == []


class TestListEcho360Sections:
    """Tests for list_echo360_sections tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_sections_success(self):
        from epiphan_mcp.tools.echo360 import list_echo360_sections

        _mock_token()
        respx.get(f"{API}/sections").mock(
            return_value=Response(200, json=[{"id": "s1", "name": "Fall 2026"}])
        )
        with patch.dict(os.environ, ECHO360_ENV):
            result = await list_echo360_sections(course_id="c1")

        assert result.error is None
        assert result.count == 1
        assert result.course_id == "c1"


class TestListEcho360Medias:
    """Tests for list_echo360_medias tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_medias_success(self):
        from epiphan_mcp.tools.echo360 import list_echo360_medias

        _mock_token()
        respx.get(f"{API}/medias").mock(
            return_value=Response(200, json=[{"id": "m1", "title": "Lecture 1"}])
        )
        with patch.dict(os.environ, ECHO360_ENV):
            result = await list_echo360_medias(search_query="lecture")

        assert result.error is None
        assert result.count == 1
        assert result.search_query == "lecture"
        assert result.medias[0]["title"] == "Lecture 1"


class TestGetEcho360Media:
    """Tests for get_echo360_media tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_media_success(self):
        from epiphan_mcp.tools.echo360 import get_echo360_media

        _mock_token()
        respx.get(f"{API}/medias/m1").mock(
            return_value=Response(200, json={"id": "m1", "title": "Lecture"})
        )
        with patch.dict(os.environ, ECHO360_ENV):
            result = await get_echo360_media(media_id="m1")

        assert result.error is None
        assert result.media is not None
        assert result.media["id"] == "m1"

    @pytest.mark.asyncio
    async def test_get_media_requires_id(self):
        from epiphan_mcp.tools.echo360 import get_echo360_media

        result = await get_echo360_media(media_id="")
        assert result.error is not None
        assert "media_id" in result.error


class TestUploadVideoToEcho360:
    """Tests for upload_video_to_echo360 tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_success(self, tmp_path):
        from epiphan_mcp.tools.echo360 import upload_video_to_echo360

        _mock_token()
        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        respx.post(f"{API}/pending-capture-uploads").mock(
            return_value=Response(
                200, json={"uploadId": "u1", "uploadUrl": "https://s3.example.com/signed"}
            )
        )
        respx.put("https://s3.example.com/signed").mock(return_value=Response(200))
        respx.post(f"{API}/submitted-capture-uploads").mock(
            return_value=Response(200, json={"uploadId": "u1", "state": "processing"})
        )
        respx.get(f"{API}/pending-capture-uploads/u1").mock(
            return_value=Response(200, json={"uploadId": "u1", "state": "processing"})
        )

        with patch.dict(os.environ, ECHO360_ENV):
            result = await upload_video_to_echo360(file_path=str(video))

        assert result.error is None
        assert result.upload is not None
        assert result.file_size == len(b"fake video content")
        assert "lecture.mp4" in (result.message or "")

    @pytest.mark.asyncio
    async def test_upload_missing_file(self):
        from epiphan_mcp.tools.echo360 import upload_video_to_echo360

        with patch.dict(os.environ, ECHO360_ENV):
            result = await upload_video_to_echo360(file_path="/nonexistent/file.mp4")
        assert result.error is not None
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_upload_logs_audit_entry(self, tmp_path):
        """Outbound uploads hit the audit log."""
        from epiphan_mcp.tools import echo360 as echo360_tools

        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        with (
            patch.dict(os.environ, ECHO360_ENV),
            patch.object(echo360_tools, "log_operation") as mock_log,
            patch.object(
                echo360_tools.Echo360Client,
                "_ensure_authenticated",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                echo360_tools.Echo360Client, "upload_video", new=AsyncMock(return_value={})
            ),
        ):
            result = await echo360_tools.upload_video_to_echo360(file_path=str(video))

        assert result.error is None
        mock_log.assert_called_once()


class TestGetEcho360UploadStatus:
    """Tests for get_echo360_upload_status tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_status_success(self):
        from epiphan_mcp.tools.echo360 import get_echo360_upload_status

        _mock_token()
        respx.get(f"{API}/pending-capture-uploads/u1").mock(
            return_value=Response(200, json={"uploadId": "u1", "state": "complete"})
        )
        with patch.dict(os.environ, ECHO360_ENV):
            result = await get_echo360_upload_status(upload_id="u1")

        assert result.error is None
        assert result.upload_id == "u1"
        assert result.status == "complete"

    @pytest.mark.asyncio
    async def test_status_requires_upload_id(self):
        from epiphan_mcp.tools.echo360 import get_echo360_upload_status

        result = await get_echo360_upload_status(upload_id="")
        assert result.error is not None
