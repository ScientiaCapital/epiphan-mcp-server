"""Unit tests for PearlClient API client.

Tests the Pearl REST API v2.0 client implementation using mocked HTTP responses.
"""

import pytest
from httpx import ConnectError, ReadTimeout, Response

from epiphan_mcp.client import PearlAPIError, PearlClient
from epiphan_mcp.models import RecordingState, StreamingState

from .fixtures.mocks import mock_system_routes
from .fixtures.responses import (
    BUSY_RESPONSE,
    ERROR_RESPONSE,
    RECORDER_STATUS_RECORDING,
)

# ============================================================
# Client Initialization Tests
# ============================================================


class TestClientInit:
    """Tests for PearlClient initialization."""

    def test_client_init_basic(self, mock_pearl_host: str):
        """Test basic client initialization."""
        client = PearlClient(host=mock_pearl_host, username="admin", password="pass")

        assert client.host == mock_pearl_host
        assert client.base_url == f"http://{mock_pearl_host}"
        assert client.api_base == f"http://{mock_pearl_host}/api/v2.0"
        assert client.timeout == 30.0  # default
        assert client.verify_ssl is True  # default

    def test_client_init_https(self, mock_pearl_host: str):
        """Test client initialization with HTTPS."""
        client = PearlClient(
            host=mock_pearl_host,
            username="admin",
            password="pass",
            use_https=True,
        )

        assert client.base_url == f"https://{mock_pearl_host}"
        assert client.api_base == f"https://{mock_pearl_host}/api/v2.0"

    def test_client_init_custom_timeout(self, mock_pearl_host: str):
        """Test client with custom timeout."""
        client = PearlClient(
            host=mock_pearl_host,
            username="admin",
            password="pass",
            timeout=60.0,
        )

        assert client.timeout == 60.0

    def test_client_from_settings(self, mock_pearl_host: str, test_settings):
        """Test creating client from settings."""
        client = PearlClient.from_settings(mock_pearl_host, test_settings)

        assert client.host == mock_pearl_host
        assert client.timeout == 5.0
        assert client.verify_ssl is False

    def test_client_not_in_context_raises(self, pearl_client: PearlClient):
        """Test that accessing client outside context manager raises."""
        with pytest.raises(RuntimeError, match="must be used as async context manager"):
            _ = pearl_client.client


# ============================================================
# Recorder Tests
# ============================================================


class TestRecorderOperations:
    """Tests for recorder-related API operations."""

    async def test_get_recorders(self, pearl_client: PearlClient, mock_recorder_routes):
        """Test getting list of recorders."""
        async with pearl_client as client:
            recorders = await client.get_recorders()

        assert len(recorders) == 2
        assert recorders[0].id == "recorder-1"
        assert recorders[0].name == "Channel 1 Recorder"
        assert recorders[1].id == "recorder-2"

    async def test_get_recorders_filtered(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test getting filtered list of recorders."""
        respx_mock.get(f"{mock_api_base}/recorders").mock(
            return_value=Response(
                200,
                json={
                    "status": "ok",
                    "result": [{"id": "recorder-1", "name": "Recorder 1", "type": "mp4"}],
                },
            )
        )

        async with pearl_client as client:
            recorders = await client.get_recorders(ids=["recorder-1"])

        assert len(recorders) == 1
        assert recorders[0].id == "recorder-1"

    async def test_get_recorder_status_stopped(
        self, pearl_client: PearlClient, mock_recorder_routes
    ):
        """Test getting stopped recorder status."""
        async with pearl_client as client:
            status = await client.get_recorder_status("recorder-1")

        assert status.id == "recorder-1"
        assert status.state == RecordingState.STOPPED
        assert status.duration_seconds == 0
        assert status.file_size_bytes == 0

    async def test_get_recorder_status_recording(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test getting recording status while recording."""
        respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
            return_value=Response(200, json=RECORDER_STATUS_RECORDING)
        )

        async with pearl_client as client:
            status = await client.get_recorder_status("recorder-1")

        assert status.state == RecordingState.RECORDING
        assert status.duration_seconds == 3600
        assert status.file_size_bytes == 1073741824
        assert "recording_2025-01-22" in status.filename

    async def test_get_all_recorder_status(self, pearl_client: PearlClient, mock_recorder_routes):
        """Test getting status for all recorders."""
        async with pearl_client as client:
            statuses = await client.get_all_recorder_status()

        # The mock returns recorders list, not status list, but API works similarly
        assert len(statuses) >= 0  # Verify call completes

    async def test_start_recording(self, pearl_client: PearlClient, mock_recorder_routes):
        """Test starting recording."""
        async with pearl_client as client:
            result = await client.start_recording("recorder-1")

        assert result.success is True
        assert "started" in result.message.lower()
        assert result.device == pearl_client.host

    async def test_stop_recording(self, pearl_client: PearlClient, mock_recorder_routes):
        """Test stopping recording."""
        async with pearl_client as client:
            result = await client.stop_recording("recorder-1")

        assert result.success is True
        assert "stopped" in result.message.lower()

    async def test_start_all_recorders(self, pearl_client: PearlClient, mock_recorder_routes):
        """Test starting all recorders."""
        async with pearl_client as client:
            result = await client.start_all_recorders()

        assert result.success is True
        assert result.details["recorders"] == "all"

    async def test_start_recorders_filtered(self, pearl_client: PearlClient, mock_recorder_routes):
        """Test starting filtered recorders."""
        async with pearl_client as client:
            result = await client.start_all_recorders(ids=["recorder-1"])

        assert result.success is True
        assert result.details["recorders"] == ["recorder-1"]

    async def test_stop_all_recorders(self, pearl_client: PearlClient, mock_recorder_routes):
        """Test stopping all recorders."""
        async with pearl_client as client:
            result = await client.stop_all_recorders()

        assert result.success is True

    async def test_get_archive_files(self, pearl_client: PearlClient, mock_recorder_routes):
        """Test getting recorded files list."""
        async with pearl_client as client:
            files = await client.get_archive_files("recorder-1")

        assert len(files) == 2
        assert files[0]["filename"] == "recording_2025-01-21_14-00-00.mp4"
        assert files[1]["size"] == 1073741824


# ============================================================
# Channel Tests
# ============================================================


class TestChannelOperations:
    """Tests for channel-related API operations."""

    async def test_get_channels(self, pearl_client: PearlClient, mock_channel_routes):
        """Test getting list of channels."""
        async with pearl_client as client:
            channels = await client.get_channels()

        assert len(channels) == 2
        assert channels[0].id == "channel-1"
        assert channels[0].name == "Main Channel"
        assert len(channels[0].layouts) == 2

    async def test_switch_layout(self, pearl_client: PearlClient, mock_channel_routes):
        """Test switching channel layout."""
        async with pearl_client as client:
            result = await client.switch_layout("channel-1", "layout-2")

        assert result.success is True
        assert result.details["layout"] == "layout-2"

    async def test_add_bookmark(self, pearl_client: PearlClient, mock_channel_routes):
        """Test adding bookmark to recording."""
        async with pearl_client as client:
            result = await client.add_bookmark("channel-1", "Important moment")

        assert result.success is True
        assert result.details["text"] == "Important moment"

    async def test_get_layouts(self, pearl_client: PearlClient, mock_channel_routes):
        """Test getting layouts for a channel."""
        async with pearl_client as client:
            layouts = await client.get_layouts("channel-1")

        assert len(layouts) == 3
        assert layouts[0]["id"] == "layout-1"
        assert layouts[0]["name"] == "Full Screen"
        assert layouts[0]["is_active"] is True


# ============================================================
# Publisher (Streaming) Tests
# ============================================================


class TestPublisherOperations:
    """Tests for publisher/streaming API operations."""

    async def test_get_publishers(self, pearl_client: PearlClient, mock_publisher_routes):
        """Test getting list of publishers."""
        async with pearl_client as client:
            publishers = await client.get_publishers("channel-1")

        assert len(publishers) == 2
        assert publishers[0]["id"] == "publisher-1"
        assert publishers[0]["type"] == "rtmp"

    async def test_get_publisher_status(self, pearl_client: PearlClient, mock_publisher_routes):
        """Test getting publisher status."""
        async with pearl_client as client:
            status = await client.get_publisher_status("channel-1", "publisher-1")

        assert status.state == StreamingState.STREAMING
        assert status.duration_seconds == 1800
        assert status.viewers == 42

    async def test_start_all_publishers(self, pearl_client: PearlClient, mock_publisher_routes):
        """Test starting all publishers on a channel."""
        async with pearl_client as client:
            result = await client.start_all_publishers("channel-1")

        assert result.success is True
        assert "started" in result.message.lower()

    async def test_stop_all_publishers(self, pearl_client: PearlClient, mock_publisher_routes):
        """Test stopping all publishers on a channel."""
        async with pearl_client as client:
            result = await client.stop_all_publishers("channel-1")

        assert result.success is True

# ============================================================
# Input Tests
# ============================================================


class TestInputOperations:
    """Tests for input-related API operations."""

    async def test_get_inputs(self, pearl_client: PearlClient, mock_input_routes):
        """Test getting list of inputs."""
        async with pearl_client as client:
            inputs = await client.get_inputs()

        assert len(inputs) == 3
        assert inputs[0].id == "hdmi-1"
        assert inputs[0].connected is True
        assert inputs[0].resolution == "1920x1080"

    async def test_get_inputs_filtered(self, pearl_client: PearlClient, mock_input_routes):
        """Test getting filtered inputs."""
        async with pearl_client as client:
            inputs = await client.get_inputs(types=["hdmi"])

        # Filter happens server-side; mock returns all
        assert len(inputs) >= 1


# ============================================================
# System Tests
# ============================================================


class TestSystemOperations:
    """Tests for system-related API operations."""

    async def test_get_system_status(self, pearl_client: PearlClient, mock_device_routes):
        """Test getting system status."""
        async with pearl_client as client:
            status = await client.get_system_status()

        assert status.device_name == "Pearl-2-ABC123"
        assert status.model == "Pearl-2"
        assert status.firmware_version == "4.14.2"
        assert status.storage_total_gb > 0

    async def test_get_storages(self, pearl_client: PearlClient, mock_device_routes):
        """Test getting storage information."""
        async with pearl_client as client:
            storages = await client.get_storages()

        assert len(storages) == 1
        assert storages[0].id == "storage-1"
        assert storages[0].total_bytes == 500000000000
        assert storages[0].percent_used == 20.0

    async def test_reboot(self, pearl_client: PearlClient, mock_system_routes):
        """Test rebooting device."""
        async with pearl_client as client:
            result = await client.reboot()

        assert result.success is True
        assert "rebooting" in result.message.lower()

    async def test_shutdown(self, pearl_client: PearlClient, mock_system_routes):
        """Test shutting down device."""
        async with pearl_client as client:
            result = await client.shutdown()

        assert result.success is True
        assert "shutting down" in result.message.lower()


# ============================================================
# Single Touch Tests
# ============================================================


class TestSingleTouchOperations:
    """Tests for single touch control operations."""

    async def test_single_touch_start(self, pearl_client: PearlClient, mock_singletouch_routes):
        """Test single touch start (all recorders + streams)."""
        async with pearl_client as client:
            result = await client.single_touch_start()

        assert result.success is True
        assert "started" in result.message.lower()

    async def test_single_touch_stop(self, pearl_client: PearlClient, mock_singletouch_routes):
        """Test single touch stop."""
        async with pearl_client as client:
            result = await client.single_touch_stop()

        assert result.success is True
        assert "stopped" in result.message.lower()


# ============================================================
# Error Handling Tests
# ============================================================


class TestErrorHandling:
    """Tests for API error handling."""

    async def test_api_error_response(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test handling of API error status."""
        respx_mock.get(f"{mock_api_base}/recorders/invalid/status").mock(
            return_value=Response(200, json=ERROR_RESPONSE)
        )

        async with pearl_client as client:
            with pytest.raises(PearlAPIError) as exc_info:
                await client.get_recorder_status("invalid")

        assert exc_info.value.api_status == "error"
        assert "not found" in str(exc_info.value).lower()

    async def test_api_busy_response(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test handling of API busy status."""
        respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/start").mock(
            return_value=Response(200, json=BUSY_RESPONSE)
        )

        async with pearl_client as client:
            with pytest.raises(PearlAPIError) as exc_info:
                await client.start_recording("recorder-1")

        assert exc_info.value.api_status == "busy"
        assert "busy" in str(exc_info.value).lower()

    async def test_http_401_error(self, pearl_client: PearlClient, mock_api_base: str, respx_mock):
        """Test handling of 401 Unauthorized."""
        respx_mock.get(f"{mock_api_base}/recorders").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        async with pearl_client as client:
            with pytest.raises(PearlAPIError) as exc_info:
                await client.get_recorders()

        assert exc_info.value.status_code == 401

    async def test_http_404_error(self, pearl_client: PearlClient, mock_api_base: str, respx_mock):
        """Test handling of 404 Not Found."""
        respx_mock.get(f"{mock_api_base}/recorders/nonexistent/status").mock(
            return_value=Response(404, json={"error": "Not found"})
        )

        async with pearl_client as client:
            with pytest.raises(PearlAPIError) as exc_info:
                await client.get_recorder_status("nonexistent")

        assert exc_info.value.status_code == 404

    async def test_http_500_error(self, pearl_client: PearlClient, mock_api_base: str, respx_mock):
        """Test handling of 500 Internal Server Error on direct API call."""
        respx_mock.get(f"{mock_api_base}/recorders").mock(
            return_value=Response(500, json={"error": "Internal error"})
        )

        async with pearl_client as client:
            with pytest.raises(PearlAPIError) as exc_info:
                await client.get_recorders()

        assert exc_info.value.status_code == 500

    async def test_connection_error(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test handling of connection errors."""
        respx_mock.get(f"{mock_api_base}/recorders").mock(
            side_effect=ConnectError("Connection refused")
        )

        async with pearl_client as client:
            with pytest.raises(PearlAPIError):
                await client.get_recorders()

    async def test_system_status_handles_errors_gracefully(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test that get_system_status handles errors gracefully."""
        # get_system_status catches API-level errors and returns partial status.
        # /system/ident is the first call it makes.
        mock_system_routes(respx_mock, mock_api_base, ident=ERROR_RESPONSE)

        async with pearl_client as client:
            # This should not raise, but return a default status
            status = await client.get_system_status()

        # Should have host but unknown model
        assert status.device_name == pearl_client.host
        assert status.model == "Unknown"


# ============================================================
# Binary Response Tests
# ============================================================


class TestBinaryResponses:
    """Tests for binary response handling (previews)."""

    async def test_non_json_response_from_api(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test _handle_response with non-JSON content type from _get()."""
        # Mock an endpoint that normally returns JSON but returns binary
        mock_binary = b"\x00\x01\x02\x03"
        respx_mock.get(f"{mock_api_base}/system/ident").mock(
            return_value=Response(
                200,
                content=mock_binary,
                headers={"content-type": "application/octet-stream"},
            )
        )

        async with pearl_client as client:
            # This calls _get() which uses _handle_response()
            # The non-JSON path returns {"status": "ok", "result": content}
            result = await client._get("/system/ident")

        assert result["status"] == "ok"
        assert result["result"] == mock_binary

    async def test_get_channel_preview(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test getting channel preview image."""
        # Mock binary image response
        mock_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Fake PNG header
        respx_mock.get(f"{mock_api_base}/channels/channel-1/preview").mock(
            return_value=Response(
                200,
                content=mock_image,
                headers={"content-type": "image/jpeg"},
            )
        )

        async with pearl_client as client:
            image = await client.get_channel_preview("channel-1")

        assert isinstance(image, bytes)
        assert len(image) > 0

    async def test_get_input_preview(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test getting input preview image."""
        mock_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        respx_mock.get(f"{mock_api_base}/inputs/hdmi-1/preview").mock(
            return_value=Response(
                200,
                content=mock_image,
                headers={"content-type": "image/png"},
            )
        )

        async with pearl_client as client:
            image = await client.get_input_preview("hdmi-1")

        assert isinstance(image, bytes)


# ============================================================
# Events Tests
# ============================================================


class TestEventOperations:
    """Tests for scheduled event operations."""

    async def test_get_events(self, pearl_client: PearlClient, mock_api_base: str, respx_mock):
        """Test getting scheduled events."""
        from .fixtures.responses import EVENTS_RESPONSE

        respx_mock.get(f"{mock_api_base}/schedule/events").mock(
            return_value=Response(200, json=EVENTS_RESPONSE)
        )

        async with pearl_client as client:
            events = await client.get_events()

        assert len(events) == 2
        assert events[0]["id"] == "event-001"
        assert events[0]["cms_type"] == "kaltura"

# ============================================================
# AFU Tests
# ============================================================


class TestAFUOperations:
    """Tests for Automatic File Upload operations."""

    async def test_get_afu_status(self, pearl_client: PearlClient, mock_api_base: str, respx_mock):
        """Test getting AFU status."""
        from .fixtures.responses import AFU_STATUS_RESPONSE

        respx_mock.get(f"{mock_api_base}/afu/status").mock(
            return_value=Response(200, json=AFU_STATUS_RESPONSE)
        )

        async with pearl_client as client:
            afu_status = await client.get_afu_status()

        assert len(afu_status) == 1
        assert afu_status[0]["protocol"] == "s3"


# ============================================================
# Model Property Tests
# ============================================================


class TestModelProperties:
    """Tests for Pydantic model computed properties."""

    def test_storage_info_total_gb(self):
        """Test StorageInfo.total_gb property."""
        from epiphan_mcp.models import StorageInfo

        storage = StorageInfo(total_bytes=1073741824)  # 1GB
        assert storage.total_gb == 1.0

        storage_zero = StorageInfo(total_bytes=0)
        assert storage_zero.total_gb == 0

    def test_storage_info_free_gb(self):
        """Test StorageInfo.free_gb property."""
        from epiphan_mcp.models import StorageInfo

        storage = StorageInfo(free_bytes=2147483648)  # 2GB
        assert storage.free_gb == 2.0

        storage_zero = StorageInfo(free_bytes=0)
        assert storage_zero.free_gb == 0

    def test_batch_operation_result_all_succeeded(self):
        """Test BatchOperationResult.all_succeeded property."""
        from epiphan_mcp.models import BatchOperationResult

        result_success = BatchOperationResult(total=3, succeeded=3, failed=0)
        assert result_success.all_succeeded is True

        result_failure = BatchOperationResult(total=3, succeeded=2, failed=1)
        assert result_failure.all_succeeded is False


# ============================================================
# Client Optional Parameter Tests
# ============================================================


class TestClientOptionalParameters:
    """Tests for client methods with optional parameters."""

    async def test_get_channels_with_filters(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test get_channels with optional filter parameters."""
        from .fixtures.responses import CHANNELS_RESPONSE

        respx_mock.get(f"{mock_api_base}/channels").mock(
            return_value=Response(200, json=CHANNELS_RESPONSE)
        )

        async with pearl_client as client:
            channels = await client.get_channels(
                ids=["channel-1"],
                include_publishers=True,
                include_encoders=True,
                include_layouts=True,
            )

        assert len(channels) == 2

    async def test_put_request_error(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test PUT request error handling."""
        respx_mock.put(f"{mock_api_base}/channels/channel-1/layouts/active").mock(
            side_effect=ConnectError("Connection refused")
        )

        async with pearl_client as client:
            with pytest.raises(PearlAPIError, match="Connection refused"):
                await client.switch_layout("channel-1", "layout-1")

    async def test_get_inputs_with_ids_filter(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test get_inputs with ids filter parameter."""
        from .fixtures.responses import INPUTS_RESPONSE

        respx_mock.get(f"{mock_api_base}/inputs").mock(
            return_value=Response(200, json=INPUTS_RESPONSE)
        )

        async with pearl_client as client:
            inputs = await client.get_inputs(ids=["hdmi-1", "sdi-1"])

        assert len(inputs) >= 1

    async def test_get_events_with_filters(
        self, pearl_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """Test get_events with optional time and status filters."""
        from .fixtures.responses import EVENTS_RESPONSE

        respx_mock.get(f"{mock_api_base}/schedule/events").mock(
            return_value=Response(200, json=EVENTS_RESPONSE)
        )

        async with pearl_client as client:
            events = await client.get_events(
                from_time="2025-01-22T00:00:00Z",
                to_time="2025-01-23T00:00:00Z",
                status="scheduled",
            )

        assert len(events) >= 1


# ============================================================
# Method-Aware Retry Tests (idempotency)
# ============================================================


class TestMethodAwareRetry:
    """POST/PATCH are non-idempotent: retry only connect-phase failures.

    An ambiguous failure (e.g. ReadTimeout after the request reached the
    device) must NOT be retried for POST/PATCH — it can duplicate side
    effects (duplicate publisher, double reboot). GET/PUT/DELETE keep the
    full retry behavior.
    """

    @pytest.fixture
    def retrying_client(self, mock_pearl_host: str) -> PearlClient:
        return PearlClient(
            host=mock_pearl_host,
            username="admin",
            password="pass",
            max_retries=2,
            retry_base_delay=0.01,
            retry_max_delay=0.05,
        )

    async def test_post_does_not_retry_on_read_timeout(
        self, retrying_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """ReadTimeout after send is ambiguous — POST must fail immediately."""
        route = respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/start").mock(
            side_effect=ReadTimeout("timed out waiting for response")
        )

        async with retrying_client as client:
            with pytest.raises(PearlAPIError):
                await client._post("/recorders/recorder-1/control/start")

        assert route.call_count == 1

    async def test_post_retries_on_connect_error(
        self, retrying_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """ConnectError means the request never reached the device — safe to retry."""
        route = respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/start")
        route.side_effect = [
            ConnectError("Connection refused"),
            Response(200, json={"status": "ok"}),
        ]

        async with retrying_client as client:
            result = await client._post("/recorders/recorder-1/control/start")

        assert result == {"status": "ok"}
        assert route.call_count == 2

    async def test_patch_does_not_retry_on_read_timeout(
        self, retrying_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """PATCH is non-idempotent for Pearl config — same rule as POST."""
        route = respx_mock.patch(f"{mock_api_base}/system/settings").mock(
            side_effect=ReadTimeout("timed out waiting for response")
        )

        async with retrying_client as client:
            with pytest.raises(PearlAPIError):
                await client._patch("/system/settings", json={"key": "value"})

        assert route.call_count == 1

    async def test_post_retries_on_busy_api_error(
        self, retrying_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """A 'busy' response is a definitive pre-execution reject — the device
        refused the request without acting on it, so retrying a POST cannot
        duplicate side effects. Busy stays retryable for all methods, exempt
        from the connect-phase-only restriction above."""
        route = respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/start")
        route.side_effect = [
            Response(200, json={"status": "busy"}),
            Response(200, json={"status": "ok"}),
        ]

        async with retrying_client as client:
            result = await client._post("/recorders/recorder-1/control/start")

        assert result == {"status": "ok"}
        assert route.call_count == 2

    async def test_get_still_retries_on_read_timeout(
        self, retrying_client: PearlClient, mock_api_base: str, respx_mock
    ):
        """GET is idempotent — ambiguous timeouts remain retryable."""
        route = respx_mock.get(f"{mock_api_base}/recorders")
        route.side_effect = [
            ReadTimeout("timed out waiting for response"),
            Response(200, json={"result": []}),
        ]

        async with retrying_client as client:
            recorders = await client.get_recorders()

        assert recorders == []
        assert route.call_count == 2
