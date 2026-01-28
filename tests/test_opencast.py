"""Tests for Opencast integration.

Tests cover:
- OpencastClient connection and authentication
- Series management operations
- Event management operations
- Ingest workflow
- Capture scheduling
- Dublin Core metadata generation
- MCP tool wrappers
"""

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import httpx
import pytest
import respx

from epiphan_mcp.integrations.opencast import (
    OpencastAPIError,
    OpencastAuthError,
    OpencastClient,
    _build_dublin_core,
)


# ============================================================================
# Dublin Core Tests
# ============================================================================


class TestDublinCore:
    """Tests for Dublin Core XML generation."""

    def test_build_dublin_core_minimal(self):
        """Test building Dublin Core with minimal fields."""
        xml = _build_dublin_core(title="Test Recording")
        assert "<?xml version" in xml
        # Check for title content (namespace prefix may vary)
        assert ">Test Recording<" in xml
        assert "http://purl.org/dc/terms/" in xml

    def test_build_dublin_core_full(self):
        """Test building Dublin Core with all fields."""
        xml = _build_dublin_core(
            title="Physics Lecture 5",
            creator="Dr. Smith",
            description="Wave mechanics introduction",
            series_id="series-123",
            spatial="Room 201",
            start_date=datetime(2024, 1, 15, 10, 0),
            language="en",
            license="CC-BY",
            contributor="TA Johnson",
            subject="Physics",
        )

        # Check for content values (namespace prefixes may vary with ElementTree)
        assert ">Physics Lecture 5<" in xml
        assert ">Dr. Smith<" in xml
        assert ">Wave mechanics introduction<" in xml
        assert ">series-123<" in xml
        assert ">Room 201<" in xml
        assert ">en<" in xml
        assert ">CC-BY<" in xml
        assert ">TA Johnson<" in xml
        assert ">Physics<" in xml
        assert "2024-01-15T10:00:00" in xml  # created date

    def test_build_dublin_core_empty_fields_omitted(self):
        """Test that empty fields are not included."""
        xml = _build_dublin_core(title="Test", creator="", description="")
        assert ">Test<" in xml
        # Empty values should not be included
        assert "creator" not in xml.lower() or "><" not in xml.split("creator")[1][:20]
        assert "description" not in xml.lower()


# ============================================================================
# OpencastClient Initialization Tests
# ============================================================================


class TestOpencastClientInit:
    """Tests for OpencastClient initialization."""

    def test_client_init_defaults(self):
        """Test client initialization with defaults."""
        client = OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        )
        assert client.host == "opencast.example.edu"
        assert client.use_https is True
        assert client.api_base == "https://opencast.example.edu/api"
        assert client.ingest_base == "https://opencast.example.edu/ingest"

    def test_client_init_http(self):
        """Test client initialization with HTTP."""
        client = OpencastClient(
            host="opencast.local",
            username="admin",
            password="secret",
            use_https=False,
        )
        assert client.api_base == "http://opencast.local/api"

    def test_client_init_with_default_series(self):
        """Test client initialization with default series."""
        client = OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
            default_series="series-uuid-123",
        )
        assert client.default_series == "series-uuid-123"


# ============================================================================
# OpencastClient Authentication Tests
# ============================================================================


class TestOpencastClientAuth:
    """Tests for OpencastClient authentication."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_success(self):
        """Test successful authentication."""
        respx.get("https://opencast.example.edu/api/info/me").mock(
            return_value=httpx.Response(
                200,
                json={"username": "admin", "roles": ["ROLE_ADMIN"]},
            )
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            assert client._client is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_invalid_credentials(self):
        """Test authentication with invalid credentials."""
        respx.get("https://opencast.example.edu/api/info/me").mock(
            return_value=httpx.Response(401)
        )

        with pytest.raises(OpencastAuthError, match="Invalid credentials"):
            async with OpencastClient(
                host="opencast.example.edu",
                username="admin",
                password="wrong",
            ):
                pass

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_insufficient_permissions(self):
        """Test authentication with insufficient permissions."""
        respx.get("https://opencast.example.edu/api/info/me").mock(
            return_value=httpx.Response(403)
        )

        with pytest.raises(OpencastAuthError, match="Insufficient permissions"):
            async with OpencastClient(
                host="opencast.example.edu",
                username="viewer",
                password="secret",
            ):
                pass


# ============================================================================
# OpencastClient Series Tests
# ============================================================================


class TestOpencastClientSeries:
    """Tests for OpencastClient series operations."""

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mock for all series tests."""
        respx.get("https://opencast.example.edu/api/info/me").mock(
            return_value=httpx.Response(200, json={"username": "admin"})
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_series(self, auth_mock):
        """Test listing series."""
        respx.get("https://opencast.example.edu/api/series").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"identifier": "series-1", "title": "Physics 101"},
                    {"identifier": "series-2", "title": "Chemistry 201"},
                ],
            )
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            series = await client.list_series()
            assert len(series) == 2
            assert series[0]["title"] == "Physics 101"

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_series_with_filter(self, auth_mock):
        """Test listing series with text filter."""
        route = respx.get("https://opencast.example.edu/api/series").mock(
            return_value=httpx.Response(200, json=[])
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            await client.list_series(filter_text="Physics")

        assert "filter=title%3APhysics" in str(route.calls[0].request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_series(self, auth_mock):
        """Test getting a specific series."""
        respx.get("https://opencast.example.edu/api/series/series-123").mock(
            return_value=httpx.Response(
                200,
                json={"identifier": "series-123", "title": "Test Series"},
            )
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            series = await client.get_series("series-123")
            assert series["identifier"] == "series-123"

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_series(self, auth_mock):
        """Test creating a series."""
        respx.post("https://opencast.example.edu/api/series").mock(
            return_value=httpx.Response(
                201,
                json={"identifier": "new-series-456"},
            )
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            result = await client.create_series(
                title="New Course",
                description="Course description",
                creator="Dr. Jones",
            )
            assert result["identifier"] == "new-series-456"


# ============================================================================
# OpencastClient Events Tests
# ============================================================================


class TestOpencastClientEvents:
    """Tests for OpencastClient event operations."""

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mock for all event tests."""
        respx.get("https://opencast.example.edu/api/info/me").mock(
            return_value=httpx.Response(200, json={"username": "admin"})
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_events(self, auth_mock):
        """Test listing events."""
        respx.get("https://opencast.example.edu/api/events").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"identifier": "event-1", "title": "Lecture 1"},
                    {"identifier": "event-2", "title": "Lecture 2"},
                ],
            )
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            events = await client.list_events()
            assert len(events) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_events_filtered_by_series(self, auth_mock):
        """Test listing events filtered by series."""
        route = respx.get("https://opencast.example.edu/api/events").mock(
            return_value=httpx.Response(200, json=[])
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            await client.list_events(series_id="series-123")

        assert "filter=is_part_of%3Aseries-123" in str(route.calls[0].request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_event(self, auth_mock):
        """Test getting a specific event."""
        respx.get("https://opencast.example.edu/api/events/event-123").mock(
            return_value=httpx.Response(
                200,
                json={
                    "identifier": "event-123",
                    "title": "Test Event",
                    "duration": 3600,
                },
            )
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            event = await client.get_event("event-123")
            assert event["identifier"] == "event-123"
            assert event["duration"] == 3600

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_event(self, auth_mock):
        """Test deleting an event."""
        respx.delete("https://opencast.example.edu/api/events/event-123").mock(
            return_value=httpx.Response(204)
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            result = await client.delete_event("event-123")
            assert result is True


# ============================================================================
# OpencastClient Ingest Tests
# ============================================================================


class TestOpencastClientIngest:
    """Tests for OpencastClient ingest operations."""

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mock for all ingest tests."""
        respx.get("https://opencast.example.edu/api/info/me").mock(
            return_value=httpx.Response(200, json={"username": "admin"})
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_ingest_recording(self, auth_mock, tmp_path):
        """Test ingesting a recording."""
        # Create test file
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video content")

        respx.post("https://opencast.example.edu/ingest/addMediaPackage/fast").mock(
            return_value=httpx.Response(200, text="workflow-instance-123")
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            result = await client.ingest_recording(
                file_path=test_file,
                title="Test Recording",
                series_id="series-123",
                creator="Test User",
            )
            assert result["success"] is True
            assert result["workflow_id"] == "workflow-instance-123"

    @pytest.mark.asyncio
    @respx.mock
    async def test_ingest_file_not_found(self, auth_mock):
        """Test ingest with non-existent file."""
        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            with pytest.raises(OpencastAPIError, match="File not found"):
                await client.ingest_recording(
                    file_path="/nonexistent/file.mp4",
                    title="Test",
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_ingest_status(self, auth_mock):
        """Test getting ingest workflow status."""
        respx.get("https://opencast.example.edu/api/workflow/workflow-123").mock(
            return_value=httpx.Response(
                200,
                json={
                    "state": "RUNNING",
                    "operations": [
                        {"id": "ingest", "state": "SUCCEEDED"},
                        {"id": "encode", "state": "RUNNING"},
                    ],
                },
            )
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            status = await client.get_ingest_status("workflow-123")
            assert status["state"] == "RUNNING"


# ============================================================================
# OpencastClient Scheduling Tests
# ============================================================================


class TestOpencastClientScheduling:
    """Tests for OpencastClient capture scheduling."""

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mock for all scheduling tests."""
        respx.get("https://opencast.example.edu/api/info/me").mock(
            return_value=httpx.Response(200, json={"username": "admin"})
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_schedule_capture(self, auth_mock):
        """Test scheduling a capture event."""
        respx.post("https://opencast.example.edu/api/events").mock(
            return_value=httpx.Response(
                201,
                json={"identifier": "scheduled-event-123"},
            )
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            result = await client.schedule_capture(
                title="Scheduled Lecture",
                start_time=datetime(2024, 1, 15, 10, 0),
                end_time=datetime(2024, 1, 15, 11, 0),
                capture_agent="pearl-room-101",
                series_id="series-123",
            )
            assert result["identifier"] == "scheduled-event-123"


# ============================================================================
# OpencastClient Error Handling Tests
# ============================================================================


class TestOpencastClientErrors:
    """Tests for OpencastClient error handling."""

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mock."""
        respx.get("https://opencast.example.edu/api/info/me").mock(
            return_value=httpx.Response(200, json={"username": "admin"})
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_not_found_error(self, auth_mock):
        """Test 404 error handling."""
        respx.get("https://opencast.example.edu/api/events/nonexistent").mock(
            return_value=httpx.Response(404)
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            with pytest.raises(OpencastAPIError, match="not found"):
                await client.get_event("nonexistent")

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_error(self, auth_mock):
        """Test 500 error handling."""
        respx.get("https://opencast.example.edu/api/series").mock(
            return_value=httpx.Response(500, text="Internal server error")
        )

        async with OpencastClient(
            host="opencast.example.edu",
            username="admin",
            password="secret",
        ) as client:
            with pytest.raises(OpencastAPIError, match="500"):
                await client.list_series()


# ============================================================================
# MCP Tool Tests
# ============================================================================


class TestOpencastTools:
    """Tests for Opencast MCP tool functions."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        """Set up mock environment variables for Opencast."""
        with patch.dict(
            os.environ,
            {
                "OPENCAST_HOST": "opencast.example.edu",
                "OPENCAST_USERNAME": "admin",
                "OPENCAST_PASSWORD": "secret",
            },
        ):
            yield

    @pytest.fixture
    def auth_mock(self):
        """Set up auth mock."""
        respx.get("https://opencast.example.edu/api/info/me").mock(
            return_value=httpx.Response(200, json={"username": "admin"})
        )

    @pytest.mark.asyncio
    async def test_list_opencast_series_missing_config(self):
        """Test that missing config returns error."""
        from epiphan_mcp.tools.opencast import list_opencast_series

        with patch.dict(os.environ, {}, clear=True):
            result = await list_opencast_series()
            assert "error" in result
            assert "Missing Opencast configuration" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_opencast_series_success(self, auth_mock):
        """Test successful series listing via MCP tool."""
        from epiphan_mcp.tools.opencast import list_opencast_series

        respx.get("https://opencast.example.edu/api/series").mock(
            return_value=httpx.Response(
                200,
                json=[{"identifier": "s1", "title": "Series 1"}],
            )
        )

        result = await list_opencast_series()
        assert result["count"] == 1
        assert result["series"][0]["title"] == "Series 1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_opencast_series_success(self, auth_mock):
        """Test successful series retrieval via MCP tool."""
        from epiphan_mcp.tools.opencast import get_opencast_series

        respx.get("https://opencast.example.edu/api/series/series-123").mock(
            return_value=httpx.Response(200, json={"identifier": "series-123"})
        )

        result = await get_opencast_series("series-123")
        assert result["series"]["identifier"] == "series-123"

    @pytest.mark.asyncio
    async def test_get_opencast_series_missing_id(self):
        """Test that missing series_id returns error."""
        from epiphan_mcp.tools.opencast import get_opencast_series

        result = await get_opencast_series("")
        assert "series_id is required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_opencast_series_success(self, auth_mock):
        """Test successful series creation via MCP tool."""
        from epiphan_mcp.tools.opencast import create_opencast_series

        respx.post("https://opencast.example.edu/api/series").mock(
            return_value=httpx.Response(201, json={"identifier": "new-series"})
        )

        result = await create_opencast_series("New Series")
        assert "series" in result
        assert "Created series" in result["message"]

    @pytest.mark.asyncio
    async def test_create_opencast_series_missing_title(self):
        """Test that missing title returns error."""
        from epiphan_mcp.tools.opencast import create_opencast_series

        result = await create_opencast_series("")
        assert "title is required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_opencast_events_success(self, auth_mock):
        """Test successful event listing via MCP tool."""
        from epiphan_mcp.tools.opencast import list_opencast_events

        respx.get("https://opencast.example.edu/api/events").mock(
            return_value=httpx.Response(
                200,
                json=[{"identifier": "e1", "title": "Event 1"}],
            )
        )

        result = await list_opencast_events()
        assert result["count"] == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_opencast_event_success(self, auth_mock):
        """Test successful event retrieval via MCP tool."""
        from epiphan_mcp.tools.opencast import get_opencast_event

        respx.get("https://opencast.example.edu/api/events/event-123").mock(
            return_value=httpx.Response(200, json={"identifier": "event-123"})
        )

        result = await get_opencast_event("event-123")
        assert result["event"]["identifier"] == "event-123"

    @pytest.mark.asyncio
    async def test_ingest_to_opencast_missing_params(self):
        """Test that missing parameters return errors."""
        from epiphan_mcp.tools.opencast import ingest_to_opencast

        result = await ingest_to_opencast("", "Title")
        assert "file_path is required" in result["error"]

        result = await ingest_to_opencast("/path/to/file.mp4", "")
        assert "title is required" in result["error"]

    @pytest.mark.asyncio
    async def test_ingest_to_opencast_file_not_found(self):
        """Test that non-existent file returns error."""
        from epiphan_mcp.tools.opencast import ingest_to_opencast

        result = await ingest_to_opencast("/nonexistent/file.mp4", "Title")
        assert "File not found" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_schedule_opencast_capture_success(self, auth_mock):
        """Test successful capture scheduling via MCP tool."""
        from epiphan_mcp.tools.opencast import schedule_opencast_capture

        respx.post("https://opencast.example.edu/api/events").mock(
            return_value=httpx.Response(201, json={"identifier": "scheduled-123"})
        )

        result = await schedule_opencast_capture(
            title="Scheduled Event",
            start_time="2024-01-15T10:00:00",
            end_time="2024-01-15T11:00:00",
            capture_agent="pearl-101",
        )
        assert "event" in result
        assert "Scheduled capture" in result["message"]

    @pytest.mark.asyncio
    async def test_schedule_opencast_capture_missing_params(self):
        """Test that missing parameters return errors."""
        from epiphan_mcp.tools.opencast import schedule_opencast_capture

        result = await schedule_opencast_capture("", "2024-01-15T10:00:00", "2024-01-15T11:00:00", "agent")
        assert "title is required" in result["error"]

        result = await schedule_opencast_capture("Title", "", "2024-01-15T11:00:00", "agent")
        assert "start_time is required" in result["error"]

        result = await schedule_opencast_capture("Title", "2024-01-15T10:00:00", "", "agent")
        assert "end_time is required" in result["error"]

        result = await schedule_opencast_capture("Title", "2024-01-15T10:00:00", "2024-01-15T11:00:00", "")
        assert "capture_agent is required" in result["error"]

    @pytest.mark.asyncio
    async def test_schedule_opencast_capture_invalid_datetime(self):
        """Test that invalid datetime returns error."""
        from epiphan_mcp.tools.opencast import schedule_opencast_capture

        result = await schedule_opencast_capture("Title", "not-a-date", "2024-01-15T11:00:00", "agent")
        assert "Invalid datetime format" in result["error"]

    @pytest.mark.asyncio
    async def test_schedule_opencast_capture_end_before_start(self):
        """Test that end time before start time returns error."""
        from epiphan_mcp.tools.opencast import schedule_opencast_capture

        result = await schedule_opencast_capture(
            "Title",
            "2024-01-15T12:00:00",
            "2024-01-15T11:00:00",
            "agent",
        )
        assert "end_time must be after start_time" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_opencast_event_success(self, auth_mock):
        """Test successful event deletion via MCP tool."""
        from epiphan_mcp.tools.opencast import delete_opencast_event

        respx.delete("https://opencast.example.edu/api/events/event-123").mock(
            return_value=httpx.Response(204)
        )

        result = await delete_opencast_event("event-123")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_opencast_event_missing_id(self):
        """Test that missing event_id returns error."""
        from epiphan_mcp.tools.opencast import delete_opencast_event

        result = await delete_opencast_event("")
        assert "event_id is required" in result["error"]


class TestOpencastToolsAuthErrors:
    """Tests for Opencast MCP tools auth error handling."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        """Set up mock environment variables."""
        with patch.dict(
            os.environ,
            {
                "OPENCAST_HOST": "opencast.example.edu",
                "OPENCAST_USERNAME": "admin",
                "OPENCAST_PASSWORD": "wrong",
            },
        ):
            yield

    @pytest.mark.asyncio
    @respx.mock
    async def test_auth_error_returns_error_dict(self):
        """Test that auth errors return error dict instead of raising."""
        from epiphan_mcp.tools.opencast import list_opencast_series

        respx.get("https://opencast.example.edu/api/info/me").mock(
            return_value=httpx.Response(401)
        )

        result = await list_opencast_series()
        assert "error" in result
        assert "Authentication failed" in result["error"]
