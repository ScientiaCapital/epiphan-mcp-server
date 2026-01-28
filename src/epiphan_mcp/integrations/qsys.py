"""Q-SYS Core JSON-RPC client for Pearl device integration.

This module provides an async TCP client for Q-SYS Core processors, enabling:
- JSON-RPC 2.0 over TCP communication (port 1710)
- Component discovery and control for Pearl devices
- Automatic keep-alive (NoOp) to maintain connection
- Optional PIN authentication

Q-SYS is a professional AV control platform by QSC. When configured with Pearl
plugins, it can control Epiphan Pearl devices through a unified interface.

Protocol Reference:
- Messages are JSON-RPC 2.0 format, null-terminated (\\0)
- Keep-alive required every 60 seconds (NoOp method)
- Default port: 1710

Example:
    ```python
    async with QSysClient(host="192.168.1.50") as client:
        components = await client.discover_components()
        await client.set_component("Pearl_Recorder", {"start_recording": 1})
    ```
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class QSysConnectionError(Exception):
    """Connection error with Q-SYS Core."""

    pass


class QSysAuthError(Exception):
    """Authentication error with Q-SYS Core."""

    pass


class QSysRPCError(Exception):
    """JSON-RPC error from Q-SYS Core."""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


@dataclass
class QSysClient:
    """Async JSON-RPC client for Q-SYS Core.

    Implements JSON-RPC 2.0 over TCP with null-terminated messages.
    Maintains connection with automatic keep-alive.

    Attributes:
        host: Q-SYS Core IP address or hostname
        port: TCP port (default 1710)
        pin: Optional PIN for authentication
        timeout: Connection timeout in seconds
        keepalive_interval: Seconds between NoOp keep-alive messages
    """

    host: str
    port: int = 1710
    pin: str = ""
    timeout: float = 30.0
    keepalive_interval: float = 50.0  # Must be < 60 seconds

    # Private state
    _reader: asyncio.StreamReader | None = field(default=None, repr=False)
    _writer: asyncio.StreamWriter | None = field(default=None, repr=False)
    _request_id: int = field(default=0, repr=False)
    _keepalive_task: asyncio.Task[None] | None = field(default=None, repr=False)
    _pending_requests: dict[int, asyncio.Future[dict[str, Any]]] = field(
        default_factory=dict, repr=False
    )
    _reader_task: asyncio.Task[None] | None = field(default=None, repr=False)
    _connected: bool = field(default=False, repr=False)

    async def __aenter__(self) -> "QSysClient":
        """Async context manager entry - connect and authenticate."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - disconnect cleanly."""
        await self.disconnect()

    async def connect(self) -> None:
        """Establish TCP connection to Q-SYS Core.

        Raises:
            QSysConnectionError: If connection fails
            QSysAuthError: If PIN authentication fails
        """
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            self._connected = True
            logger.info(f"Connected to Q-SYS Core at {self.host}:{self.port}")

            # Start response reader task
            self._reader_task = asyncio.create_task(self._read_responses())

            # Authenticate if PIN provided
            if self.pin:
                await self._logon()

            # Start keep-alive task
            self._keepalive_task = asyncio.create_task(self._keep_alive())

        except TimeoutError as e:
            raise QSysConnectionError(
                f"Connection timeout to Q-SYS Core at {self.host}:{self.port}"
            ) from e
        except OSError as e:
            raise QSysConnectionError(
                f"Failed to connect to Q-SYS Core at {self.host}:{self.port}: {e}"
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from Q-SYS Core."""
        self._connected = False

        # Cancel keep-alive task
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None

        # Cancel reader task
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        # Close writer
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None

        self._reader = None
        logger.info(f"Disconnected from Q-SYS Core at {self.host}")

    async def _logon(self) -> None:
        """Authenticate with PIN.

        Raises:
            QSysAuthError: If authentication fails
        """
        try:
            response = await self._send_request("Logon", {"User": "", "Password": self.pin})
            if response.get("error"):
                raise QSysAuthError(f"PIN authentication failed: {response['error']}")
            logger.info("Q-SYS PIN authentication successful")
        except QSysRPCError as e:
            raise QSysAuthError(f"PIN authentication failed: {e}") from e

    async def _keep_alive(self) -> None:
        """Send periodic NoOp to maintain connection."""
        while self._connected:
            try:
                await asyncio.sleep(self.keepalive_interval)
                if self._connected:
                    await self._send_request("NoOp", {})
                    logger.debug("Q-SYS keep-alive sent")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Keep-alive failed: {e}")
                break

    async def _read_responses(self) -> None:
        """Read and dispatch responses from Q-SYS Core."""
        buffer = b""
        while self._connected and self._reader:
            try:
                data = await self._reader.read(4096)
                if not data:
                    logger.warning("Q-SYS Core closed connection")
                    break

                buffer += data

                # Process complete messages (null-terminated)
                while b"\0" in buffer:
                    message, buffer = buffer.split(b"\0", 1)
                    if message:
                        await self._handle_response(message.decode("utf-8"))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading Q-SYS response: {e}")
                break

    async def _handle_response(self, message: str) -> None:
        """Handle a complete JSON-RPC response."""
        try:
            response = json.loads(message)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Q-SYS: {e}")
            return

        # Check if this is a response to a pending request
        request_id = response.get("id")
        if request_id is not None and request_id in self._pending_requests:
            future = self._pending_requests.pop(request_id)
            if not future.done():
                future.set_result(response)
        else:
            # Unsolicited notification (e.g., component change)
            logger.debug(f"Q-SYS notification: {response.get('method', 'unknown')}")

    def _next_request_id(self) -> int:
        """Generate unique request ID."""
        self._request_id += 1
        return self._request_id

    async def _send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Send JSON-RPC request and await response.

        Args:
            method: RPC method name
            params: Method parameters
            timeout: Response timeout (defaults to self.timeout)

        Returns:
            Response result dict

        Raises:
            QSysConnectionError: If not connected
            QSysRPCError: If RPC returns error
        """
        if not self._writer or not self._connected:
            raise QSysConnectionError("Not connected to Q-SYS Core")

        request_id = self._next_request_id()
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id,
            "params": params or {},
        }

        # Create future for response
        future: asyncio.Future[dict[str, Any]] = asyncio.Future()
        self._pending_requests[request_id] = future

        # Send null-terminated message
        message = json.dumps(request) + "\0"
        self._writer.write(message.encode("utf-8"))
        await self._writer.drain()

        logger.debug(f"Q-SYS request: {method} (id={request_id})")

        # Wait for response
        try:
            response = await asyncio.wait_for(
                future,
                timeout=timeout or self.timeout,
            )
        except TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise QSysRPCError(f"Request timeout: {method}") from None

        # Check for error
        if "error" in response:
            error = response["error"]
            code = error.get("code") if isinstance(error, dict) else None
            message = error.get("message", str(error)) if isinstance(error, dict) else str(error)
            raise QSysRPCError(message, code=code)

        return response.get("result", {})

    # =========================================================================
    # Component Operations
    # =========================================================================

    async def discover_components(self, name_filter: str = "Pearl") -> list[dict[str, Any]]:
        """Discover components, optionally filtered by name.

        Args:
            name_filter: Filter components containing this string (default "Pearl")

        Returns:
            List of component info dicts with Name, Type, etc.
        """
        result = await self._send_request("Component.GetComponents", {})
        components = result if isinstance(result, list) else []

        if name_filter:
            components = [
                c for c in components
                if name_filter.lower() in c.get("Name", "").lower()
            ]

        return components

    async def get_component(
        self,
        name: str,
        controls: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get component status/values.

        Args:
            name: Component name (e.g., "Pearl_Recorder")
            controls: Specific controls to get (None for all)

        Returns:
            Component status with control values
        """
        params: dict[str, Any] = {"Name": name}
        if controls:
            params["Controls"] = [{"Name": c} for c in controls]

        return await self._send_request("Component.Get", params)

    async def set_component(
        self,
        name: str,
        controls: dict[str, Any],
    ) -> dict[str, Any]:
        """Set component control values.

        Args:
            name: Component name (e.g., "Pearl_Recorder")
            controls: Dict of control name -> value (e.g., {"start_recording": 1})

        Returns:
            Result of set operation
        """
        control_list = [{"Name": k, "Value": v} for k, v in controls.items()]
        params = {"Name": name, "Controls": control_list}
        return await self._send_request("Component.Set", params)

    # =========================================================================
    # Pearl-Specific Operations
    # =========================================================================

    async def get_pearl_status(self, component_name: str = "Pearl_Recorder") -> dict[str, Any]:
        """Get Pearl recording/streaming status from Q-SYS component.

        Args:
            component_name: Name of Pearl component in Q-SYS design

        Returns:
            Status dict with is_recording, is_streaming, etc.
        """
        result = await self.get_component(
            component_name,
            controls=["is_recording", "is_streaming", "current_layout"],
        )

        # Parse controls into friendly dict
        controls = result.get("Controls", [])
        status: dict[str, Any] = {
            "component": component_name,
        }

        for control in controls:
            name = control.get("Name", "")
            value = control.get("Value")
            string = control.get("String", "")

            if name == "is_recording":
                status["is_recording"] = bool(value)
            elif name == "is_streaming":
                status["is_streaming"] = bool(value)
            elif name == "current_layout":
                status["current_layout"] = string or str(value)

        return status

    async def start_recording(self, component_name: str = "Pearl_Recorder") -> dict[str, Any]:
        """Start recording via Q-SYS Pearl component.

        Args:
            component_name: Name of Pearl component

        Returns:
            Result of start operation
        """
        return await self.set_component(component_name, {"start_recording": 1})

    async def stop_recording(self, component_name: str = "Pearl_Recorder") -> dict[str, Any]:
        """Stop recording via Q-SYS Pearl component.

        Args:
            component_name: Name of Pearl component

        Returns:
            Result of stop operation
        """
        return await self.set_component(component_name, {"stop_recording": 1})

    async def switch_layout(
        self,
        layout_id: str | int,
        component_name: str = "Pearl_Layout",
    ) -> dict[str, Any]:
        """Switch Pearl layout via Q-SYS component.

        Args:
            layout_id: Layout ID or index to switch to
            component_name: Name of Pearl layout component

        Returns:
            Result of layout switch
        """
        return await self.set_component(component_name, {"layout_id": layout_id})
