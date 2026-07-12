"""Tests for Q-SYS integration.

Tests cover:
- QSysClient TCP connection handling
- JSON-RPC message format and parsing
- Keep-alive mechanism
- PIN authentication
- Component discovery and control
- MCP tool wrappers
"""

import asyncio
import json
import os
from unittest.mock import AsyncMock, patch

import pytest

from epiphan_mcp.integrations.qsys import (
    QSysAuthError,
    QSysClient,
    QSysConnectionError,
    QSysRPCError,
)

# ============================================================================
# Mock TCP Stream Helpers
# ============================================================================


class MockStreamReader:
    """Mock asyncio.StreamReader for testing."""

    def __init__(self, responses: list[dict] | None = None):
        self.responses = responses or []
        self.response_index = 0
        self._closed = False

    async def read(self, n: int) -> bytes:
        """Return next mock response as null-terminated JSON."""
        if self._closed or self.response_index >= len(self.responses):
            return b""

        response = self.responses[self.response_index]
        self.response_index += 1
        return json.dumps(response).encode("utf-8") + b"\0"

    def add_response(self, response: dict) -> None:
        """Add a response to the queue."""
        self.responses.append(response)


class MockStreamWriter:
    """Mock asyncio.StreamWriter for testing."""

    def __init__(self):
        self.written: list[bytes] = []
        self._closed = False

    def write(self, data: bytes) -> None:
        """Record written data."""
        self.written.append(data)

    async def drain(self) -> None:
        """Mock drain."""
        pass

    def close(self) -> None:
        """Mark as closed."""
        self._closed = True

    async def wait_closed(self) -> None:
        """Mock wait_closed."""
        pass

    def get_requests(self) -> list[dict]:
        """Parse written data as JSON requests."""
        requests = []
        for data in self.written:
            # Remove null terminator
            if data.endswith(b"\0"):
                data = data[:-1]
            requests.append(json.loads(data.decode("utf-8")))
        return requests


# ============================================================================
# QSysClient Connection Tests
# ============================================================================


class TestQSysClientConnection:
    """Tests for QSysClient connection handling."""

    def test_client_init_defaults(self):
        """Test client initialization with defaults."""
        client = QSysClient(host="192.168.1.50")
        assert client.host == "192.168.1.50"
        assert client.port == 1710
        assert client.pin == ""
        assert client.timeout == 30.0
        assert client.keepalive_interval == 50.0

    def test_client_init_custom(self):
        """Test client initialization with custom values."""
        client = QSysClient(
            host="10.0.0.1",
            port=1711,
            pin="1234",
            timeout=60.0,
            keepalive_interval=30.0,
        )
        assert client.host == "10.0.0.1"
        assert client.port == 1711
        assert client.pin == "1234"
        assert client.timeout == 60.0
        assert client.keepalive_interval == 30.0

    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """Test that connection timeout raises QSysConnectionError."""
        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = TimeoutError()

            client = QSysClient(host="192.168.1.50", timeout=1.0)
            with pytest.raises(QSysConnectionError, match="timeout"):
                await client.connect()

    @pytest.mark.asyncio
    async def test_connection_refused(self):
        """Test that connection refused raises QSysConnectionError."""
        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = OSError("Connection refused")

            client = QSysClient(host="192.168.1.50")
            with pytest.raises(QSysConnectionError, match="Connection refused"):
                await client.connect()


# ============================================================================
# QSysClient JSON-RPC Tests
# ============================================================================


class TestQSysClientRPC:
    """Tests for QSysClient JSON-RPC handling."""

    @pytest.mark.asyncio
    async def test_request_format(self):
        """Test that requests follow JSON-RPC 2.0 format with null terminator."""
        reader = MockStreamReader([{"jsonrpc": "2.0", "id": 1, "result": {"test": "value"}}])
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", keepalive_interval=3600)
            await client.connect()

            # Make a request
            result = await client._send_request("TestMethod", {"param": "value"})

            # Verify response
            assert result == {"test": "value"}

            # Verify request format
            requests = writer.get_requests()
            assert len(requests) == 1
            assert requests[0]["jsonrpc"] == "2.0"
            assert requests[0]["method"] == "TestMethod"
            assert requests[0]["params"] == {"param": "value"}
            assert "id" in requests[0]

            # Verify null terminator was sent
            assert writer.written[0].endswith(b"\0")

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_rpc_error_handling(self):
        """Test that RPC errors raise QSysRPCError."""
        reader = MockStreamReader(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {"code": -32600, "message": "Invalid Request"},
                }
            ]
        )
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", keepalive_interval=3600)
            await client.connect()

            with pytest.raises(QSysRPCError, match="Invalid Request"):
                await client._send_request("BadMethod", {})

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_request_id_increments(self):
        """Test that request IDs increment for each request."""
        # The read loop runs in background, so we need a reader that provides
        # responses on-demand to avoid timing issues.
        writer = MockStreamWriter()

        class InfiniteReader:
            """Reader that provides responses on-demand."""

            def __init__(self):
                self._response_id = 0

            async def read(self, n: int) -> bytes:
                # Small delay to allow write to happen first
                await asyncio.sleep(0.01)
                self._response_id += 1
                response = {"jsonrpc": "2.0", "id": self._response_id, "result": {}}
                return json.dumps(response).encode("utf-8") + b"\0"

        reader = InfiniteReader()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", timeout=1.0, keepalive_interval=3600)
            await client.connect()

            await client._send_request("Method1", {})
            await client._send_request("Method2", {})
            await client._send_request("Method3", {})

            requests = writer.get_requests()
            ids = [r["id"] for r in requests]
            # IDs should be sequential starting from 1
            assert ids == [1, 2, 3]

            await client.disconnect()


# ============================================================================
# QSysClient Authentication Tests
# ============================================================================


class TestQSysClientAuth:
    """Tests for QSysClient PIN authentication."""

    @pytest.mark.asyncio
    async def test_logon_with_pin(self):
        """Test that PIN authentication sends Logon request."""
        reader = MockStreamReader([{"jsonrpc": "2.0", "id": 1, "result": {"success": True}}])
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", pin="1234", keepalive_interval=3600)
            await client.connect()

            requests = writer.get_requests()
            assert len(requests) >= 1
            assert requests[0]["method"] == "Logon"
            assert requests[0]["params"]["Password"] == "1234"

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_logon_failure(self):
        """Test that PIN authentication failure raises QSysAuthError."""
        reader = MockStreamReader(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {"code": -32603, "message": "Invalid PIN"},
                }
            ]
        )
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", pin="wrong", keepalive_interval=3600)
            with pytest.raises(QSysAuthError, match="authentication failed"):
                await client.connect()


# ============================================================================
# QSysClient Component Operations Tests
# ============================================================================


class TestQSysClientComponents:
    """Tests for QSysClient component operations."""

    @pytest.mark.asyncio
    async def test_discover_components(self):
        """Test component discovery."""
        reader = MockStreamReader(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": [
                        {"Name": "Pearl_Recorder", "Type": "PearlPlugin"},
                        {"Name": "Pearl_Layout", "Type": "PearlPlugin"},
                        {"Name": "Audio_Mixer", "Type": "Mixer"},
                    ],
                }
            ]
        )
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", keepalive_interval=3600)
            await client.connect()

            components = await client.discover_components(name_filter="Pearl")
            assert len(components) == 2
            assert components[0]["Name"] == "Pearl_Recorder"
            assert components[1]["Name"] == "Pearl_Layout"

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_discover_all_components(self):
        """Test discovering all components without filter."""
        reader = MockStreamReader(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": [
                        {"Name": "Pearl_Recorder", "Type": "PearlPlugin"},
                        {"Name": "Audio_Mixer", "Type": "Mixer"},
                    ],
                }
            ]
        )
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", keepalive_interval=3600)
            await client.connect()

            components = await client.discover_components(name_filter="")
            assert len(components) == 2

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_get_component(self):
        """Test getting component values."""
        reader = MockStreamReader(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "Name": "Pearl_Recorder",
                        "Controls": [
                            {"Name": "is_recording", "Value": 1},
                            {"Name": "is_streaming", "Value": 0},
                        ],
                    },
                }
            ]
        )
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", keepalive_interval=3600)
            await client.connect()

            result = await client.get_component(
                "Pearl_Recorder",
                controls=["is_recording", "is_streaming"],
            )
            assert result["Name"] == "Pearl_Recorder"
            assert len(result["Controls"]) == 2

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_set_component(self):
        """Test setting component values."""
        reader = MockStreamReader([{"jsonrpc": "2.0", "id": 1, "result": {"success": True}}])
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", keepalive_interval=3600)
            await client.connect()

            await client.set_component("Pearl_Recorder", {"start_recording": 1})

            requests = writer.get_requests()
            set_request = requests[0]
            assert set_request["method"] == "Component.Set"
            assert set_request["params"]["Name"] == "Pearl_Recorder"
            assert set_request["params"]["Controls"] == [{"Name": "start_recording", "Value": 1}]

            await client.disconnect()


# ============================================================================
# QSysClient Pearl Operations Tests
# ============================================================================


class TestQSysClientPearlOps:
    """Tests for QSysClient Pearl-specific operations."""

    @pytest.mark.asyncio
    async def test_get_pearl_status(self):
        """Test getting Pearl status through Q-SYS."""
        reader = MockStreamReader(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "Name": "Pearl_Recorder",
                        "Controls": [
                            {"Name": "is_recording", "Value": 1},
                            {"Name": "is_streaming", "Value": 0},
                            {"Name": "current_layout", "Value": 2, "String": "Picture-in-Picture"},
                        ],
                    },
                }
            ]
        )
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", keepalive_interval=3600)
            await client.connect()

            status = await client.get_pearl_status("Pearl_Recorder")
            assert status["is_recording"] is True
            assert status["is_streaming"] is False
            assert status["current_layout"] == "Picture-in-Picture"

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_start_recording(self):
        """Test starting recording through Q-SYS."""
        reader = MockStreamReader([{"jsonrpc": "2.0", "id": 1, "result": {"success": True}}])
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", keepalive_interval=3600)
            await client.connect()

            await client.start_recording("Pearl_Recorder")

            requests = writer.get_requests()
            assert requests[0]["method"] == "Component.Set"
            assert {"Name": "start_recording", "Value": 1} in requests[0]["params"]["Controls"]

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_stop_recording(self):
        """Test stopping recording through Q-SYS."""
        reader = MockStreamReader([{"jsonrpc": "2.0", "id": 1, "result": {"success": True}}])
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", keepalive_interval=3600)
            await client.connect()

            await client.stop_recording("Pearl_Recorder")

            requests = writer.get_requests()
            assert {"Name": "stop_recording", "Value": 1} in requests[0]["params"]["Controls"]

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_switch_layout(self):
        """Test switching layout through Q-SYS."""
        reader = MockStreamReader([{"jsonrpc": "2.0", "id": 1, "result": {"success": True}}])
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            client = QSysClient(host="192.168.1.50", keepalive_interval=3600)
            await client.connect()

            await client.switch_layout("2", "Pearl_Layout")

            requests = writer.get_requests()
            assert requests[0]["params"]["Name"] == "Pearl_Layout"
            assert {"Name": "layout_id", "Value": "2"} in requests[0]["params"]["Controls"]

            await client.disconnect()


# ============================================================================
# MCP Tool Tests
# ============================================================================


class TestQSysTools:
    """Tests for Q-SYS MCP tool functions."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        """Set up mock environment variables for Q-SYS."""
        with patch.dict(
            os.environ,
            {
                "QSYS_CORE_IP": "192.168.1.50",
                "QSYS_PORT": "1710",
            },
        ):
            yield

    @pytest.mark.asyncio
    async def test_list_qsys_components_missing_config(self):
        """Test that missing config returns error."""
        from epiphan_mcp.tools.qsys import list_qsys_components

        with patch.dict(os.environ, {}, clear=True):
            result = await list_qsys_components()
            assert result.error is not None
            assert "Missing Q-SYS configuration" in result.error

    @pytest.mark.asyncio
    async def test_list_qsys_components_success(self):
        """Test successful component listing via MCP tool."""
        from epiphan_mcp.tools.qsys import list_qsys_components

        reader = MockStreamReader(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": [
                        {"Name": "Pearl_Recorder", "Type": "PearlPlugin"},
                    ],
                }
            ]
        )
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            result = await list_qsys_components()
            assert result.count == 1
            assert result.components[0]["Name"] == "Pearl_Recorder"

    @pytest.mark.asyncio
    async def test_qsys_get_pearl_status_success(self):
        """Test successful Pearl status retrieval via MCP tool."""
        from epiphan_mcp.tools.qsys import qsys_get_pearl_status

        reader = MockStreamReader(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "Name": "Pearl_Recorder",
                        "Controls": [
                            {"Name": "is_recording", "Value": 1},
                            {"Name": "is_streaming", "Value": 0},
                            {"Name": "current_layout", "Value": 1, "String": "Default"},
                        ],
                    },
                }
            ]
        )
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            result = await qsys_get_pearl_status("Pearl_Recorder")
            assert result.status["is_recording"] is True
            assert result.status["is_streaming"] is False

    @pytest.mark.asyncio
    async def test_qsys_get_pearl_status_missing_component(self):
        """Test that missing component_name returns error."""
        from epiphan_mcp.tools.qsys import qsys_get_pearl_status

        result = await qsys_get_pearl_status("")
        assert result.error is not None
        assert "component_name is required" in result.error

    @pytest.mark.asyncio
    async def test_qsys_start_recording_success(self):
        """Test successful recording start via MCP tool."""
        from epiphan_mcp.tools.qsys import qsys_start_recording

        reader = MockStreamReader([{"jsonrpc": "2.0", "id": 1, "result": {"success": True}}])
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            result = await qsys_start_recording("Pearl_Recorder")
            assert result.success is True
            assert "Recording started" in result.message

    @pytest.mark.asyncio
    async def test_qsys_stop_recording_success(self):
        """Test successful recording stop via MCP tool."""
        from epiphan_mcp.tools.qsys import qsys_stop_recording

        reader = MockStreamReader([{"jsonrpc": "2.0", "id": 1, "result": {"success": True}}])
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            result = await qsys_stop_recording("Pearl_Recorder")
            assert result.success is True
            assert "Recording stopped" in result.message

    @pytest.mark.asyncio
    async def test_qsys_switch_layout_success(self):
        """Test successful layout switch via MCP tool."""
        from epiphan_mcp.tools.qsys import qsys_switch_layout

        reader = MockStreamReader([{"jsonrpc": "2.0", "id": 1, "result": {"success": True}}])
        writer = MockStreamWriter()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = (reader, writer)

            result = await qsys_switch_layout("2", "Pearl_Layout")
            assert result.success is True
            assert "Layout switched" in result.message

    @pytest.mark.asyncio
    async def test_qsys_switch_layout_missing_params(self):
        """Test that missing parameters return errors."""
        from epiphan_mcp.tools.qsys import qsys_switch_layout

        result = await qsys_switch_layout("", "Pearl_Layout")
        assert result.error is not None
        assert "layout_id is required" in result.error

        result = await qsys_switch_layout("2", "")
        assert result.error is not None
        assert "component_name is required" in result.error


class TestQSysToolsConnectionErrors:
    """Tests for Q-SYS MCP tools connection error handling."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        """Set up mock environment variables."""
        with patch.dict(
            os.environ,
            {
                "QSYS_CORE_IP": "192.168.1.50",
            },
        ):
            yield

    @pytest.mark.asyncio
    async def test_connection_error_returns_error_dict(self):
        """Test that connection errors return error dict instead of raising."""
        from epiphan_mcp.tools.qsys import list_qsys_components

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = OSError("Connection refused")

            result = await list_qsys_components()
            assert result.error is not None
            assert "Connection failed" in result.error

    @pytest.mark.asyncio
    async def test_auth_error_returns_error_dict(self):
        """Test that auth errors return error dict instead of raising."""
        from epiphan_mcp.tools.qsys import list_qsys_components

        reader = MockStreamReader(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {"code": -32603, "message": "Invalid PIN"},
                }
            ]
        )
        writer = MockStreamWriter()

        with patch.dict(os.environ, {"QSYS_PIN": "wrong"}):
            with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_connect:
                mock_connect.return_value = (reader, writer)

                result = await list_qsys_components()
                assert result.error is not None
                assert "Authentication failed" in result.error
