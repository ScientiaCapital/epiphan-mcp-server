"""Tests for Panopto CMS integration.

Tests cover:
- PanoptoClient OAuth2 authentication
- Folder management operations
- Session management operations
- Upload workflow
- MCP tool wrappers
"""

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import httpx
import pytest
import respx

from epiphan_mcp.integrations.panopto import (
    OAuthToken,
    PanoptoAPIError,
    PanoptoAuthError,
    PanoptoClient,
)

# ============================================================================
# OAuthToken Tests
# ============================================================================


class TestOAuthToken:
    """Tests for OAuthToken dataclass."""

    def test_token_not_expired_when_new(self):
        """Test that a new token is not expired."""
        token = OAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
        )
        assert not token.is_expired

    def test_token_expired_after_expiry(self):
        """Test that token is expired after expiry time."""
        token = OAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
            created_at=datetime.now() - timedelta(seconds=3700),
        )
        assert token.is_expired

    def test_token_expired_with_buffer(self):
        """Test that token is expired 60 seconds before actual expiry."""
        token = OAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
            created_at=datetime.now() - timedelta(seconds=3550),
        )
        assert token.is_expired


# ============================================================================
# PanoptoClient Tests
# ============================================================================


class TestPanoptoClientInit:
    """Tests for PanoptoClient initialization."""

    def test_client_init_with_https(self):
        """Test client initialization with HTTPS."""
        client = PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user@example.edu",
            password="secret",
            use_https=True,
        )
        assert client.base_url == "https://panopto.example.edu"
        assert client.api_base == "https://panopto.example.edu/api/v1"

    def test_client_init_with_http(self):
        """Test client initialization with HTTP."""
        client = PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user@example.edu",
            password="secret",
            use_https=False,
        )
        assert client.base_url == "http://panopto.example.edu"

    def test_client_init_with_client_secret(self):
        """Test client initialization with optional client secret."""
        client = PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user@example.edu",
            password="secret",
            client_secret="client-secret-value",
        )
        assert client.client_secret == "client-secret-value"


class TestPanoptoClientAuth:
    """Tests for PanoptoClient authentication."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_success(self):
        """Test successful OAuth2 authentication."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "test_access_token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user@example.edu",
            password="secret",
        ) as client:
            assert client._token is not None
            assert client._token.access_token == "test_access_token"
            assert client._token.token_type == "Bearer"

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_failure(self):
        """Test authentication failure raises PanoptoAuthError."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(401, text="Invalid credentials")
        )

        with pytest.raises(PanoptoAuthError, match="Authentication failed"):
            async with PanoptoClient(
                host="panopto.example.edu",
                client_id="test-client",
                username="user@example.edu",
                password="wrong-password",
            ):
                pass

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_with_client_secret(self):
        """Test authentication includes client_secret when provided."""
        route = respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "test_token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user@example.edu",
            password="secret",
            client_secret="my-secret",
        ):
            pass

        assert route.called
        # Verify client_secret was sent in the request
        request = route.calls[0].request
        assert b"client_secret=my-secret" in request.content


class TestPanoptoClientFolders:
    """Tests for PanoptoClient folder operations."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_folders(self):
        """Test listing folders."""
        # Auth endpoint
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        # Folders endpoint
        respx.get("https://panopto.example.edu/api/v1/folders").mock(
            return_value=httpx.Response(
                200,
                json={
                    "Results": [
                        {"Id": "folder-1", "Name": "Lectures"},
                        {"Id": "folder-2", "Name": "Labs"},
                    ]
                },
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            folders, truncated = await client.list_folders()
            assert len(folders) == 2
            assert folders[0]["Name"] == "Lectures"
            assert truncated is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_folders_with_search(self):
        """Test listing folders with search query."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        route = respx.get("https://panopto.example.edu/api/v1/folders").mock(
            return_value=httpx.Response(200, json={"Results": []})
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            await client.list_folders(search_query="Physics")

        assert "searchQuery=Physics" in str(route.calls[0].request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_folders_reports_truncation_from_total(self):
        """An envelope total larger than the page marks the result truncated."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/folders").mock(
            return_value=httpx.Response(
                200,
                json={
                    "Results": [{"Id": "f1"}, {"Id": "f2"}],
                    "TotalNumberOfResults": 50,
                },
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            folders, truncated = await client.list_folders()
        assert len(folders) == 2
        assert truncated is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_folders_complete_page_not_truncated(self):
        """A complete page (total == items) is not truncated."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/folders").mock(
            return_value=httpx.Response(
                200,
                json={"Results": [{"Id": "f1"}], "TotalNumberOfResults": 1},
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            _folders, truncated = await client.list_folders()
        assert truncated is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_folder(self):
        """Test getting a specific folder."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/folders/folder-123").mock(
            return_value=httpx.Response(
                200,
                json={"Id": "folder-123", "Name": "Test Folder"},
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            folder = await client.get_folder("folder-123")
            assert folder["Id"] == "folder-123"
            assert folder["Name"] == "Test Folder"

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_folder(self):
        """Test creating a folder."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.post("https://panopto.example.edu/api/v1/folders").mock(
            return_value=httpx.Response(
                200,
                json={"Id": "new-folder", "Name": "New Folder"},
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            folder = await client.create_folder(name="New Folder")
            assert folder["Name"] == "New Folder"


class TestPanoptoClientSessions:
    """Tests for PanoptoClient session operations."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_sessions(self):
        """Test listing sessions."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/sessions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "Results": [
                        {"Id": "session-1", "Name": "Lecture 1"},
                        {"Id": "session-2", "Name": "Lecture 2"},
                    ]
                },
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            sessions, truncated = await client.list_sessions()
            assert len(sessions) == 2
            assert truncated is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_sessions_reports_truncation_from_total(self):
        """An envelope total larger than the page marks the result truncated."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/sessions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "Results": [{"Id": "s1"}, {"Id": "s2"}],
                    "TotalNumberOfResults": 200,
                },
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            sessions, truncated = await client.list_sessions()
        assert len(sessions) == 2
        assert truncated is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_session(self):
        """Test getting a specific session."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/sessions/session-123").mock(
            return_value=httpx.Response(
                200,
                json={"Id": "session-123", "Name": "Test Session", "Duration": 3600},
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            session = await client.get_session("session-123")
            assert session["Id"] == "session-123"
            assert session["Duration"] == 3600

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_session(self):
        """Test creating a session."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.post("https://panopto.example.edu/api/v1/sessions").mock(
            return_value=httpx.Response(
                200,
                json={"Id": "new-session", "Name": "My Recording"},
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            session = await client.create_session(
                folder_id="folder-123",
                name="My Recording",
            )
            assert session["Name"] == "My Recording"

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_session(self):
        """Test deleting a session."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.delete("https://panopto.example.edu/api/v1/sessions/session-123").mock(
            return_value=httpx.Response(204)
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            result = await client.delete_session("session-123")
            assert result["success"] is True


class TestPanoptoClientUpload:
    """Tests for PanoptoClient upload operations."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_upload_session(self):
        """Test creating an upload session."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.post(
            "https://panopto.example.edu/Panopto/Services/PublicAPI/REST/sessionUpload"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "ID": "upload-123",
                    "UploadTarget": "https://s3.amazonaws.com/bucket/key",
                    "State": 0,
                },
            )
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            upload = await client.create_upload_session("folder-123")
            assert upload["ID"] == "upload-123"
            assert "s3.amazonaws.com" in upload["UploadTarget"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_upload_status(self):
        """Test getting upload status."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get(
            "https://panopto.example.edu/Panopto/Services/PublicAPI/REST/sessionUpload/upload-123"
        ).mock(return_value=httpx.Response(200, json={"ID": "upload-123", "State": 3}))

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            status = await client.get_upload_status("upload-123")
            assert status["State"] == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_complete_upload(self):
        """Test marking upload as complete."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.put(
            "https://panopto.example.edu/Panopto/Services/PublicAPI/REST/sessionUpload/upload-123"
        ).mock(return_value=httpx.Response(200, json={"ID": "upload-123", "State": 2}))

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            result = await client.complete_upload("upload-123")
            assert result["State"] == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file_to_s3_streams_through_async_client(self, tmp_path):
        """The S3 PUT must go through the real async transport.

        Regression test: passing a sync file object as ``content`` to
        httpx.AsyncClient raises RuntimeError at request time; the client
        must stream the file as an async byte iterator instead.
        """
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.put("https://s3.amazonaws.com/bucket/key").mock(
            return_value=httpx.Response(200)
        )

        video = tmp_path / "lecture.mp4"
        video.write_bytes(b"fake video content")

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            ok = await client.upload_file_to_s3("https://s3.amazonaws.com/bucket/key", video)
        assert ok is True


class TestPanoptoClientErrors:
    """Tests for PanoptoClient error handling."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_error_on_404(self):
        """Test that 404 response raises PanoptoAPIError."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/folders/nonexistent").mock(
            return_value=httpx.Response(404, text="Not found")
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            with pytest.raises(PanoptoAPIError) as exc_info:
                await client.get_folder("nonexistent")
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_error_on_500(self):
        """Test that 500 response raises PanoptoAPIError."""
        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/sessions").mock(
            return_value=httpx.Response(500, text="Internal server error")
        )

        async with PanoptoClient(
            host="panopto.example.edu",
            client_id="test-client",
            username="user",
            password="pass",
        ) as client:
            with pytest.raises(PanoptoAPIError) as exc_info:
                await client.list_sessions()
            assert exc_info.value.status_code == 500


# ============================================================================
# MCP Tool Tests
# ============================================================================


class TestPanoptoTools:
    """Tests for Panopto MCP tool functions."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        """Set up mock environment variables for Panopto."""
        with patch.dict(
            os.environ,
            {
                "PANOPTO_HOST": "panopto.example.edu",
                "PANOPTO_CLIENT_ID": "test-client",
                "PANOPTO_USERNAME": "user@example.edu",
                "PANOPTO_PASSWORD": "test-password",
            },
        ):
            yield

    @pytest.mark.asyncio
    async def test_list_panopto_folders_missing_config(self):
        """Test that missing config returns error."""
        from epiphan_mcp.tools.panopto import list_panopto_folders

        with patch.dict(os.environ, {}, clear=True):
            result = await list_panopto_folders()
            assert result.error is not None
            assert "Missing Panopto configuration" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_panopto_folders_success(self):
        """Test successful folder listing via MCP tool."""
        from epiphan_mcp.tools.panopto import list_panopto_folders

        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/folders").mock(
            return_value=httpx.Response(200, json={"Results": [{"Id": "f1", "Name": "Folder 1"}]})
        )

        result = await list_panopto_folders()
        assert result.count == 1
        assert result.folders[0]["Name"] == "Folder 1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_panopto_folders_surfaces_truncation(self):
        """The tool exposes a truncated flag so callers know the list is partial."""
        from epiphan_mcp.tools.panopto import list_panopto_folders

        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/folders").mock(
            return_value=httpx.Response(
                200,
                json={
                    "Results": [{"Id": "f1", "Name": "Folder 1"}],
                    "TotalNumberOfResults": 40,
                },
            )
        )

        result = await list_panopto_folders()
        assert result.error is None
        assert result.count == 1
        assert result.truncated is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_panopto_folder_success(self):
        """Test successful folder retrieval via MCP tool."""
        from epiphan_mcp.tools.panopto import get_panopto_folder

        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/folders/folder-123").mock(
            return_value=httpx.Response(200, json={"Id": "folder-123", "Name": "Test"})
        )

        result = await get_panopto_folder("folder-123")
        assert result.folder["Id"] == "folder-123"

    @pytest.mark.asyncio
    async def test_get_panopto_folder_missing_id(self):
        """Test that missing folder_id returns error."""
        from epiphan_mcp.tools.panopto import get_panopto_folder

        result = await get_panopto_folder("")
        assert result.error is not None
        assert "folder_id is required" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_panopto_folder_success(self):
        """Test successful folder creation via MCP tool."""
        from epiphan_mcp.tools.panopto import create_panopto_folder

        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.post("https://panopto.example.edu/api/v1/folders").mock(
            return_value=httpx.Response(200, json={"Id": "new", "Name": "New Folder"})
        )

        result = await create_panopto_folder("New Folder")
        assert result.folder is not None
        assert result.message == "Created folder 'New Folder'"

    @pytest.mark.asyncio
    async def test_create_panopto_folder_missing_name(self):
        """Test that missing name returns error."""
        from epiphan_mcp.tools.panopto import create_panopto_folder

        result = await create_panopto_folder("")
        assert result.error is not None
        assert "name is required" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_panopto_sessions_success(self):
        """Test successful session listing via MCP tool."""
        from epiphan_mcp.tools.panopto import list_panopto_sessions

        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/sessions").mock(
            return_value=httpx.Response(
                200,
                json={"Results": [{"Id": "s1", "Name": "Session 1"}]},
            )
        )

        result = await list_panopto_sessions()
        assert result.count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_panopto_session_success(self):
        """Test successful session retrieval via MCP tool."""
        from epiphan_mcp.tools.panopto import get_panopto_session

        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get("https://panopto.example.edu/api/v1/sessions/session-123").mock(
            return_value=httpx.Response(200, json={"Id": "session-123", "Name": "Test"})
        )

        result = await get_panopto_session("session-123")
        assert result.session["Id"] == "session-123"

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_panopto_session_success(self):
        """Test successful session creation via MCP tool."""
        from epiphan_mcp.tools.panopto import create_panopto_session

        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.post("https://panopto.example.edu/api/v1/sessions").mock(
            return_value=httpx.Response(200, json={"Id": "new", "Name": "Recording"})
        )

        result = await create_panopto_session("folder-123", "Recording")
        assert result.message == "Created session 'Recording'"

    @pytest.mark.asyncio
    async def test_create_panopto_session_missing_params(self):
        """Test that missing parameters return errors."""
        from epiphan_mcp.tools.panopto import create_panopto_session

        result = await create_panopto_session("", "Name")
        assert "folder_id is required" in result.error

        result = await create_panopto_session("folder-123", "")
        assert "name is required" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_panopto_session_success(self):
        """Test successful session deletion via MCP tool."""
        from epiphan_mcp.tools.panopto import delete_panopto_session

        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.delete("https://panopto.example.edu/api/v1/sessions/session-123").mock(
            return_value=httpx.Response(204)
        )

        result = await delete_panopto_session("session-123")
        assert result.success is True
        assert "Deleted session" in result.message

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_panopto_upload_status_success(self):
        """Test successful upload status check via MCP tool."""
        from epiphan_mcp.tools.panopto import get_panopto_upload_status

        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.get(
            "https://panopto.example.edu/Panopto/Services/PublicAPI/REST/sessionUpload/upload-123"
        ).mock(return_value=httpx.Response(200, json={"ID": "upload-123", "State": 4}))

        result = await get_panopto_upload_status("upload-123")
        assert result.state == "Complete"
        assert result.state_code == 4

    @pytest.mark.asyncio
    async def test_upload_to_panopto_missing_file(self):
        """Test that missing file returns error."""
        from epiphan_mcp.tools.panopto import upload_to_panopto

        result = await upload_to_panopto("folder-123", "/nonexistent/file.mp4")
        assert result.error is not None
        assert "File not found" in result.error

    @pytest.mark.asyncio
    async def test_upload_to_panopto_missing_params(self):
        """Test that missing parameters return errors."""
        from epiphan_mcp.tools.panopto import upload_to_panopto

        result = await upload_to_panopto("", "/some/file.mp4")
        assert "folder_id is required" in result.error

        result = await upload_to_panopto("folder-123", "")
        assert "file_path is required" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_to_panopto_success(self, tmp_path):
        """Test successful upload via MCP tool."""
        from epiphan_mcp.tools.panopto import upload_to_panopto

        # Create a temp file
        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"fake video content")

        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
            )
        )
        respx.post(
            "https://panopto.example.edu/Panopto/Services/PublicAPI/REST/sessionUpload"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "ID": "upload-123",
                    "UploadTarget": "https://s3.amazonaws.com/test",
                    "State": 0,
                },
            )
        )
        respx.put(
            "https://panopto.example.edu/Panopto/Services/PublicAPI/REST/sessionUpload/upload-123"
        ).mock(return_value=httpx.Response(200, json={"ID": "upload-123", "State": 2}))
        respx.get(
            "https://panopto.example.edu/Panopto/Services/PublicAPI/REST/sessionUpload/upload-123"
        ).mock(return_value=httpx.Response(200, json={"ID": "upload-123", "State": 2}))

        # Patch S3 upload since respx doesn't handle file streams well
        with patch(
            "epiphan_mcp.integrations.panopto.PanoptoClient.upload_file_to_s3",
            return_value=True,
        ):
            result = await upload_to_panopto("folder-123", str(test_file))
            assert result.upload is not None
            assert "test_video.mp4" in result.message


class TestPanoptoToolsAuthErrors:
    """Tests for Panopto MCP tools auth error handling."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        """Set up mock environment variables."""
        with patch.dict(
            os.environ,
            {
                "PANOPTO_HOST": "panopto.example.edu",
                "PANOPTO_CLIENT_ID": "test-client",
                "PANOPTO_USERNAME": "user@example.edu",
                "PANOPTO_PASSWORD": "wrong-password",
            },
        ):
            yield

    @pytest.mark.asyncio
    @respx.mock
    async def test_auth_error_returns_error_dict(self):
        """Test that auth errors return error dict instead of raising."""
        from epiphan_mcp.tools.panopto import list_panopto_folders

        respx.post("https://panopto.example.edu/Panopto/oauth2/connect/token").mock(
            return_value=httpx.Response(401, text="Invalid credentials")
        )

        result = await list_panopto_folders()
        assert result.error is not None
        assert "Authentication failed" in result.error
