"""System control tools for Epiphan Pearl devices.

This module provides tools for system-level operations including
device reboot, shutdown, and system status information.
"""

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..audit import log_operation
from ..client import PearlAPIError
from ..models import SystemControlResult, SystemInfoResult
from .device import get_client
from .params import DeviceId

logger = logging.getLogger(__name__)

_Confirm = Annotated[
    bool,
    Field(
        description="Safety gate: must be explicitly True to proceed. Guards against "
        "accidental reboot/shutdown, which interrupts active recordings and streams."
    ),
]


async def reboot_device(
    device_id: DeviceId = "default",
    confirm: _Confirm = False,
) -> SystemControlResult:
    """
    Reboot an Epiphan Pearl device.

    WARNING: This will interrupt all active recordings and streams.
    You must set confirm=True to proceed.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        confirm: Safety gate - must be True to proceed. This prevents accidental reboots.

    Returns:
        Confirmation of reboot initiation.
    """
    if not confirm:
        return SystemControlResult(
            success=False,
            error="Safety check: set confirm=True to reboot. "
            "This will interrupt all active recordings and streams.",
        )

    try:
        async with get_client(device_id) as client:
            result = await client.reboot()
            log_operation("reboot", client.host, details={"device_id": device_id})
            return SystemControlResult(
                success=result.success,
                device=client.host,
                message=result.message or "Device is rebooting",
            )
    except PearlAPIError as e:
        log_operation("reboot", device_id, success=False, details={"error": str(e)})
        return SystemControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )
    except ValueError as e:
        log_operation("reboot", device_id, success=False, details={"error": str(e)})
        return SystemControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def shutdown_device(
    device_id: DeviceId = "default",
    confirm: _Confirm = False,
) -> SystemControlResult:
    """
    Shut down an Epiphan Pearl device.

    WARNING: This will power off the device. Physical access is required
    to power it back on. All active recordings and streams will be stopped.
    You must set confirm=True to proceed.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        confirm: Safety gate - must be True to proceed.

    Returns:
        Confirmation of shutdown initiation.
    """
    if not confirm:
        return SystemControlResult(
            success=False,
            error="Safety check: set confirm=True to shutdown. "
            "This will power off the device. Physical access is required to restart.",
        )

    try:
        async with get_client(device_id) as client:
            result = await client.shutdown()
            log_operation("shutdown", client.host, details={"device_id": device_id})
            return SystemControlResult(
                success=result.success,
                device=client.host,
                message=result.message or "Device is shutting down",
            )
    except PearlAPIError as e:
        log_operation("shutdown", device_id, success=False, details={"error": str(e)})
        return SystemControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )
    except ValueError as e:
        log_operation("shutdown", device_id, success=False, details={"error": str(e)})
        return SystemControlResult(
            success=False,
            error=str(e),
            device=device_id,
        )


async def get_system_info(device_id: DeviceId = "default") -> SystemInfoResult:
    """
    Get detailed system information for an Epiphan Pearl device.

    Returns comprehensive system status including hardware model, firmware,
    uptime, storage, CPU, memory, and temperature readings.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        System information including:
        - device_name, model, serial_number, firmware_version
        - uptime_seconds
        - storage_total_gb, storage_free_gb, storage_used_percent
        - cpu_usage, memory_usage, temperature
    """
    try:
        async with get_client(device_id) as client:
            status = await client.get_system_status()
            return SystemInfoResult(
                success=True,
                device=client.host,
                system=status.model_dump(),
            )
    except PearlAPIError as e:
        return SystemInfoResult(
            success=False,
            error=str(e),
            device=device_id,
        )
    except ValueError as e:
        return SystemInfoResult(
            success=False,
            error=str(e),
            device=device_id,
        )


def register(server: FastMCP) -> None:
    """Register system MCP tools."""
    server.tool()(get_system_info)
    server.tool()(reboot_device)
    server.tool()(shutdown_device)
