"""Tests for Kaltura CMS integration.

Tests cover:
- KalturaSession token handling
- KalturaClient appToken authentication
- Category management operations
- Media entry management operations
- Upload workflow
- Schedule event management
- MCP tool wrappers
"""

import hashlib
import os
from datetime import datetime, timedelta
from unittest.mock import patch

import httpx
import pytest
import respx

from epiphan_mcp.integrations.kaltura import (
    KalturaAPIError,
    KalturaAuthError,
    KalturaClient,
    KalturaSession,
)

# ============================================================================
# KalturaSession Tests
# ============================================================================


class TestKalturaSession:
    """Tests for KalturaSession dataclass."""

    def test_session_not_expired_when_new(self):
        """Test that a new session is not expired."""
        session = KalturaSession(
            ks="test_ks_token",
            partner_id=12345,
            expires_in=86400,
        )
        assert not session.is_expired

    def test_session_expired_after_expiry(self):
        """Test that session is expired after expiry time."""
        session = KalturaSession(
            ks="test_ks_token",
            partner_id=12345,
            expires_in=86400,
            created_at=datetime.now() - timedelta(seconds=90000),
        )
        assert session.is_expired

    def test_session_expired_with_buffer(self):
        """Test that session is expired 60 seconds before actual expiry."""
        session = KalturaSession(
            ks="test_ks_token",
            partner_id=12345,
            expires_in=86400,
            created_at=datetime.now() - timedelta(seconds=86350),
        )
        assert session.is_expired


# ============================================================================
# KalturaClient Tests
# ============================================================================


class TestKalturaClientInit:
    """Tests for KalturaClient initialization."""

    def test_client_init_default_url(self):
        """Test client initialization with default Kaltura URL."""
        client = KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret_token",
        )
        assert client.service_url == "https://www.kaltura.com"
        assert client.api_base == "https://www.kaltura.com/api_v3"
        assert client.partner_id == 12345

    def test_client_init_custom_url(self):
        """Test client initialization with custom service URL."""
        client = KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret_token",
            service_url="https://custom.kaltura.com",
        )
        assert client.service_url == "https://custom.kaltura.com"

    def test_client_init_with_user_id(self):
        """Test client initialization with user ID."""
        client = KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret_token",
            user_id="service@example.edu",
        )
        assert client.user_id == "service@example.edu"


class TestKalturaClientAuth:
    """Tests for KalturaClient authentication."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_success(self):
        """Test successful appToken authentication flow."""
        # Step 1: Widget session
        respx.post("https://www.kaltura.com/api_v3/service/session/action/startWidgetSession").mock(
            return_value=httpx.Response(
                200,
                json={"ks": "widget_ks_123", "partnerId": 12345},
            )
        )
        # Step 2: App token session
        respx.post("https://www.kaltura.com/api_v3/service/appToken/action/startSession").mock(
            return_value=httpx.Response(
                200,
                json={"ks": "full_session_ks_456", "partnerId": 12345},
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret_token",
        ) as client:
            assert client._session is not None
            assert client._session.ks == "full_session_ks_456"
            assert client._session.partner_id == 12345

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_widget_failure(self):
        """Test authentication failure at widget session step."""
        respx.post("https://www.kaltura.com/api_v3/service/session/action/startWidgetSession").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )

        with pytest.raises(KalturaAuthError, match="Widget session failed"):
            async with KalturaClient(
                partner_id=12345,
                app_token_id="0_abc123",
                app_token="wrong_token",
            ):
                pass

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_api_error_response(self):
        """Test authentication failure with API error response."""
        respx.post("https://www.kaltura.com/api_v3/service/session/action/startWidgetSession").mock(
            return_value=httpx.Response(
                200,
                json={"ks": "widget_ks"},
            )
        )
        respx.post("https://www.kaltura.com/api_v3/service/appToken/action/startSession").mock(
            return_value=httpx.Response(
                200,
                json={
                    "objectType": "KalturaAPIException",
                    "message": "Invalid app token",
                    "code": "INVALID_APP_TOKEN",
                },
            )
        )

        with pytest.raises(KalturaAuthError, match="Authentication failed"):
            async with KalturaClient(
                partner_id=12345,
                app_token_id="0_abc123",
                app_token="invalid_token",
            ):
                pass

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_token_hash(self):
        """Test that token hash is computed correctly."""
        widget_ks = "widget_ks_123"
        app_token = "secret_token"
        expected_hash = hashlib.sha256((widget_ks + app_token).encode()).hexdigest()

        respx.post("https://www.kaltura.com/api_v3/service/session/action/startWidgetSession").mock(
            return_value=httpx.Response(200, json={"ks": widget_ks})
        )

        app_token_route = respx.post(
            "https://www.kaltura.com/api_v3/service/appToken/action/startSession"
        ).mock(return_value=httpx.Response(200, json={"ks": "full_ks"}))

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token=app_token,
        ):
            pass

        # Verify the hash was sent
        request = app_token_route.calls[0].request
        assert f"tokenHash={expected_hash}" in str(request.content)


class TestKalturaClientCategories:
    """Tests for KalturaClient category operations."""

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mocks for all category tests."""
        respx.post("https://www.kaltura.com/api_v3/service/session/action/startWidgetSession").mock(
            return_value=httpx.Response(200, json={"ks": "widget_ks"})
        )
        respx.post("https://www.kaltura.com/api_v3/service/appToken/action/startSession").mock(
            return_value=httpx.Response(200, json={"ks": "full_ks"})
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_categories(self, auth_mock):
        """Test listing categories."""
        respx.post("https://www.kaltura.com/api_v3/service/category/action/list").mock(
            return_value=httpx.Response(
                200,
                json={
                    "objects": [
                        {"id": 1, "name": "Lectures"},
                        {"id": 2, "name": "Labs"},
                    ],
                    "totalCount": 2,
                },
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            categories = await client.list_categories()
            assert len(categories) == 2
            assert categories[0]["name"] == "Lectures"

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_categories_with_parent(self, auth_mock):
        """Test listing categories with parent filter."""
        route = respx.post("https://www.kaltura.com/api_v3/service/category/action/list").mock(
            return_value=httpx.Response(200, json={"objects": []})
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            await client.list_categories(parent_id=123)

        request = route.calls[0].request
        assert b"filter%3AparentIdEqual=123" in request.content

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_category(self, auth_mock):
        """Test getting a specific category."""
        respx.post("https://www.kaltura.com/api_v3/service/category/action/get").mock(
            return_value=httpx.Response(
                200,
                json={"id": 123, "name": "Test Category", "entriesCount": 50},
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            category = await client.get_category(123)
            assert category["id"] == 123
            assert category["entriesCount"] == 50

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_category(self, auth_mock):
        """Test creating a category."""
        respx.post("https://www.kaltura.com/api_v3/service/category/action/add").mock(
            return_value=httpx.Response(
                200,
                json={"id": 456, "name": "New Category"},
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            category = await client.create_category(name="New Category")
            assert category["name"] == "New Category"


class TestKalturaClientMedia:
    """Tests for KalturaClient media operations."""

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mocks for all media tests."""
        respx.post("https://www.kaltura.com/api_v3/service/session/action/startWidgetSession").mock(
            return_value=httpx.Response(200, json={"ks": "widget_ks"})
        )
        respx.post("https://www.kaltura.com/api_v3/service/appToken/action/startSession").mock(
            return_value=httpx.Response(200, json={"ks": "full_ks"})
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_media(self, auth_mock):
        """Test listing media entries."""
        respx.post("https://www.kaltura.com/api_v3/service/media/action/list").mock(
            return_value=httpx.Response(
                200,
                json={
                    "objects": [
                        {"id": "0_abc123", "name": "Lecture 1"},
                        {"id": "0_def456", "name": "Lecture 2"},
                    ],
                    "totalCount": 2,
                },
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            media = await client.list_media()
            assert len(media) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_media_with_search(self, auth_mock):
        """Test listing media with search text."""
        route = respx.post("https://www.kaltura.com/api_v3/service/media/action/list").mock(
            return_value=httpx.Response(200, json={"objects": []})
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            await client.list_media(search_text="Physics")

        request = route.calls[0].request
        assert b"filter%3AfreeText=Physics" in request.content

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_media(self, auth_mock):
        """Test getting a specific media entry."""
        respx.post("https://www.kaltura.com/api_v3/service/media/action/get").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "0_abc123",
                    "name": "Test Video",
                    "duration": 3600,
                    "status": 2,
                },
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            media = await client.get_media("0_abc123")
            assert media["id"] == "0_abc123"
            assert media["duration"] == 3600

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_media_entry(self, auth_mock):
        """Test creating a media entry."""
        respx.post("https://www.kaltura.com/api_v3/service/media/action/add").mock(
            return_value=httpx.Response(
                200,
                json={"id": "0_new123", "name": "My Recording"},
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            media = await client.create_media_entry(name="My Recording")
            assert media["name"] == "My Recording"


class TestKalturaClientUpload:
    """Tests for KalturaClient upload operations."""

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mocks for all upload tests."""
        respx.post("https://www.kaltura.com/api_v3/service/session/action/startWidgetSession").mock(
            return_value=httpx.Response(200, json={"ks": "widget_ks"})
        )
        respx.post("https://www.kaltura.com/api_v3/service/appToken/action/startSession").mock(
            return_value=httpx.Response(200, json={"ks": "full_ks"})
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_upload_token(self, auth_mock):
        """Test creating an upload token."""
        respx.post("https://www.kaltura.com/api_v3/service/uploadToken/action/add").mock(
            return_value=httpx.Response(
                200,
                json={"id": "0_upload123", "status": 0},
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            token = await client.create_upload_token()
            assert token["id"] == "0_upload123"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_upload_status(self, auth_mock):
        """Test getting upload token status."""
        respx.post("https://www.kaltura.com/api_v3/service/uploadToken/action/get").mock(
            return_value=httpx.Response(
                200,
                json={"id": "0_upload123", "status": 2, "uploadedFileSize": 1024000},
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            status = await client.get_upload_status("0_upload123")
            assert status["status"] == 2
            assert status["uploadedFileSize"] == 1024000


class TestKalturaClientSchedule:
    """Tests for KalturaClient schedule event operations."""

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mocks for all schedule tests."""
        respx.post("https://www.kaltura.com/api_v3/service/session/action/startWidgetSession").mock(
            return_value=httpx.Response(200, json={"ks": "widget_ks"})
        )
        respx.post("https://www.kaltura.com/api_v3/service/appToken/action/startSession").mock(
            return_value=httpx.Response(200, json={"ks": "full_ks"})
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_schedule_event(self, auth_mock):
        """Test creating a schedule event."""
        respx.post("https://www.kaltura.com/api_v3/service/scheduleEvent/action/add").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 789,
                    "summary": "Physics 101",
                    "startDate": 1705311600,
                    "endDate": 1705315200,
                },
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            event = await client.create_schedule_event(
                name="Physics 101",
                start_date=datetime(2024, 1, 15, 10, 0),
                end_date=datetime(2024, 1, 15, 11, 0),
            )
            assert event["summary"] == "Physics 101"

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_schedule_events(self, auth_mock):
        """Test listing schedule events."""
        respx.post("https://www.kaltura.com/api_v3/service/scheduleEvent/action/list").mock(
            return_value=httpx.Response(
                200,
                json={
                    "objects": [
                        {"id": 1, "summary": "Event 1"},
                        {"id": 2, "summary": "Event 2"},
                    ],
                    "totalCount": 2,
                },
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            events = await client.list_schedule_events()
            assert len(events) == 2


class TestKalturaClientErrors:
    """Tests for KalturaClient error handling."""

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mocks."""
        respx.post("https://www.kaltura.com/api_v3/service/session/action/startWidgetSession").mock(
            return_value=httpx.Response(200, json={"ks": "widget_ks"})
        )
        respx.post("https://www.kaltura.com/api_v3/service/appToken/action/startSession").mock(
            return_value=httpx.Response(200, json={"ks": "full_ks"})
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_error_on_exception_response(self, auth_mock):
        """Test that API exception response raises KalturaAPIError."""
        respx.post("https://www.kaltura.com/api_v3/service/category/action/get").mock(
            return_value=httpx.Response(
                200,
                json={
                    "objectType": "KalturaAPIException",
                    "message": "Entry not found",
                    "code": "ENTRY_ID_NOT_FOUND",
                },
            )
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            with pytest.raises(KalturaAPIError) as exc_info:
                await client.get_category(999)
            assert exc_info.value.code == "ENTRY_ID_NOT_FOUND"

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_error_on_http_error(self, auth_mock):
        """Test that HTTP error raises KalturaAPIError."""
        respx.post("https://www.kaltura.com/api_v3/service/media/action/list").mock(
            return_value=httpx.Response(500, text="Internal server error")
        )

        async with KalturaClient(
            partner_id=12345,
            app_token_id="0_abc123",
            app_token="secret",
        ) as client:
            with pytest.raises(KalturaAPIError, match="API error: 500"):
                await client.list_media()


# ============================================================================
# MCP Tool Tests
# ============================================================================


class TestKalturaTools:
    """Tests for Kaltura MCP tool functions."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        """Set up mock environment variables for Kaltura."""
        with patch.dict(
            os.environ,
            {
                "KALTURA_PARTNER_ID": "12345",
                "KALTURA_APP_TOKEN_ID": "0_abc123",
                "KALTURA_APP_TOKEN": "secret_token",
            },
        ):
            yield

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mocks."""
        respx.post("https://www.kaltura.com/api_v3/service/session/action/startWidgetSession").mock(
            return_value=httpx.Response(200, json={"ks": "widget_ks"})
        )
        respx.post("https://www.kaltura.com/api_v3/service/appToken/action/startSession").mock(
            return_value=httpx.Response(200, json={"ks": "full_ks"})
        )

    @pytest.mark.asyncio
    async def test_list_kaltura_categories_missing_config(self):
        """Test that missing config returns error."""
        from epiphan_mcp.tools.kaltura import list_kaltura_categories

        with patch.dict(os.environ, {}, clear=True):
            result = await list_kaltura_categories()
            assert result.error is not None
            assert "Missing Kaltura configuration" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_kaltura_categories_success(self, auth_mock):
        """Test successful category listing via MCP tool."""
        from epiphan_mcp.tools.kaltura import list_kaltura_categories

        respx.post("https://www.kaltura.com/api_v3/service/category/action/list").mock(
            return_value=httpx.Response(
                200,
                json={"objects": [{"id": 1, "name": "Category 1"}]},
            )
        )

        result = await list_kaltura_categories()
        assert result.count == 1
        assert result.categories[0]["name"] == "Category 1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_kaltura_category_success(self, auth_mock):
        """Test successful category retrieval via MCP tool."""
        from epiphan_mcp.tools.kaltura import get_kaltura_category

        respx.post("https://www.kaltura.com/api_v3/service/category/action/get").mock(
            return_value=httpx.Response(200, json={"id": 123, "name": "Test"})
        )

        result = await get_kaltura_category(123)
        assert result.category["id"] == 123

    @pytest.mark.asyncio
    async def test_get_kaltura_category_missing_id(self):
        """Test that missing category_id returns error."""
        from epiphan_mcp.tools.kaltura import get_kaltura_category

        result = await get_kaltura_category(0)  # type: ignore
        assert result.error is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_kaltura_category_success(self, auth_mock):
        """Test successful category creation via MCP tool."""
        from epiphan_mcp.tools.kaltura import create_kaltura_category

        respx.post("https://www.kaltura.com/api_v3/service/category/action/add").mock(
            return_value=httpx.Response(200, json={"id": 456, "name": "New Folder"})
        )

        result = await create_kaltura_category("New Folder")
        assert result.category is not None
        assert result.message == "Created category 'New Folder'"

    @pytest.mark.asyncio
    async def test_create_kaltura_category_missing_name(self):
        """Test that missing name returns error."""
        from epiphan_mcp.tools.kaltura import create_kaltura_category

        result = await create_kaltura_category("")
        assert result.error is not None
        assert "name is required" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_kaltura_media_success(self, auth_mock):
        """Test successful media listing via MCP tool."""
        from epiphan_mcp.tools.kaltura import list_kaltura_media

        respx.post("https://www.kaltura.com/api_v3/service/media/action/list").mock(
            return_value=httpx.Response(
                200,
                json={"objects": [{"id": "0_abc", "name": "Video 1"}]},
            )
        )

        result = await list_kaltura_media()
        assert result.count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_kaltura_media_success(self, auth_mock):
        """Test successful media retrieval via MCP tool."""
        from epiphan_mcp.tools.kaltura import get_kaltura_media

        respx.post("https://www.kaltura.com/api_v3/service/media/action/get").mock(
            return_value=httpx.Response(
                200,
                json={"id": "0_abc123", "name": "Test Video", "status": 2},
            )
        )

        result = await get_kaltura_media("0_abc123")
        assert result.media["id"] == "0_abc123"
        assert result.media["status_name"] == "Ready"

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_kaltura_media_success(self, auth_mock):
        """Test successful media creation via MCP tool."""
        from epiphan_mcp.tools.kaltura import create_kaltura_media

        respx.post("https://www.kaltura.com/api_v3/service/media/action/add").mock(
            return_value=httpx.Response(200, json={"id": "0_new", "name": "Recording"})
        )

        result = await create_kaltura_media("Recording")
        assert result.message == "Created media entry 'Recording'"

    @pytest.mark.asyncio
    async def test_create_kaltura_media_missing_name(self):
        """Test that missing name returns error."""
        from epiphan_mcp.tools.kaltura import create_kaltura_media

        result = await create_kaltura_media("")
        assert "name is required" in result.error

    @pytest.mark.asyncio
    async def test_upload_to_kaltura_missing_file(self):
        """Test that missing file returns error."""
        from epiphan_mcp.tools.kaltura import upload_to_kaltura

        result = await upload_to_kaltura("/nonexistent/file.mp4")
        assert result.error is not None
        assert "File not found" in result.error

    @pytest.mark.asyncio
    async def test_upload_to_kaltura_missing_params(self):
        """Test that missing parameters return errors."""
        from epiphan_mcp.tools.kaltura import upload_to_kaltura

        result = await upload_to_kaltura("")
        assert "file_path is required" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_schedule_kaltura_event_success(self, auth_mock):
        """Test successful schedule event creation via MCP tool."""
        from epiphan_mcp.tools.kaltura import schedule_kaltura_event

        respx.post("https://www.kaltura.com/api_v3/service/scheduleEvent/action/add").mock(
            return_value=httpx.Response(
                200,
                json={"id": 789, "summary": "Physics 101"},
            )
        )

        result = await schedule_kaltura_event(
            name="Physics 101",
            start_time="2024-01-15T10:00:00",
            end_time="2024-01-15T11:00:00",
        )
        assert result.message == "Scheduled event 'Physics 101'"

    @pytest.mark.asyncio
    async def test_schedule_kaltura_event_missing_params(self):
        """Test that missing parameters return errors."""
        from epiphan_mcp.tools.kaltura import schedule_kaltura_event

        result = await schedule_kaltura_event("", "2024-01-15T10:00:00", "2024-01-15T11:00:00")
        assert "name is required" in result.error

        result = await schedule_kaltura_event("Test", "", "2024-01-15T11:00:00")
        assert "start_time is required" in result.error

        result = await schedule_kaltura_event("Test", "2024-01-15T10:00:00", "")
        assert "end_time is required" in result.error

    @pytest.mark.asyncio
    async def test_schedule_kaltura_event_invalid_datetime(self):
        """Test that invalid datetime returns error."""
        from epiphan_mcp.tools.kaltura import schedule_kaltura_event

        result = await schedule_kaltura_event("Test", "not-a-date", "2024-01-15T11:00:00")
        assert "Invalid datetime format" in result.error

    @pytest.mark.asyncio
    async def test_schedule_kaltura_event_end_before_start(self):
        """Test that end time before start time returns error."""
        from epiphan_mcp.tools.kaltura import schedule_kaltura_event

        result = await schedule_kaltura_event(
            "Test",
            "2024-01-15T12:00:00",
            "2024-01-15T11:00:00",
        )
        assert "end_time must be after start_time" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_kaltura_upload_status_success(self, auth_mock):
        """Test successful upload status check via MCP tool."""
        from epiphan_mcp.tools.kaltura import get_kaltura_upload_status

        respx.post("https://www.kaltura.com/api_v3/service/uploadToken/action/get").mock(
            return_value=httpx.Response(
                200,
                json={"id": "0_upload123", "status": 2, "uploadedFileSize": 1024000},
            )
        )

        result = await get_kaltura_upload_status("0_upload123")
        assert result.status == "FullUpload"
        assert result.uploaded_bytes == 1024000

    @pytest.mark.asyncio
    async def test_get_kaltura_upload_status_missing_id(self):
        """Test that missing upload_token_id returns error."""
        from epiphan_mcp.tools.kaltura import get_kaltura_upload_status

        result = await get_kaltura_upload_status("")
        assert "upload_token_id is required" in result.error


class TestKalturaToolsAuthErrors:
    """Tests for Kaltura MCP tools auth error handling."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        """Set up mock environment variables."""
        with patch.dict(
            os.environ,
            {
                "KALTURA_PARTNER_ID": "12345",
                "KALTURA_APP_TOKEN_ID": "0_abc123",
                "KALTURA_APP_TOKEN": "wrong_token",
            },
        ):
            yield

    @pytest.mark.asyncio
    @respx.mock
    async def test_auth_error_returns_error_dict(self):
        """Test that auth errors return error dict instead of raising."""
        from epiphan_mcp.tools.kaltura import list_kaltura_categories

        respx.post("https://www.kaltura.com/api_v3/service/session/action/startWidgetSession").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )

        result = await list_kaltura_categories()
        assert result.error is not None
        assert "Authentication failed" in result.error


class TestKalturaToolsInvalidPartnerID:
    """Tests for Kaltura MCP tools with invalid partner ID."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        """Set up mock environment with invalid partner ID."""
        with patch.dict(
            os.environ,
            {
                "KALTURA_PARTNER_ID": "not_a_number",
                "KALTURA_APP_TOKEN_ID": "0_abc123",
                "KALTURA_APP_TOKEN": "secret",
            },
        ):
            yield

    @pytest.mark.asyncio
    async def test_invalid_partner_id_returns_error(self):
        """Test that invalid partner ID returns error."""
        from epiphan_mcp.tools.kaltura import list_kaltura_categories

        result = await list_kaltura_categories()
        assert result.error is not None
        assert "must be a valid integer" in result.error
