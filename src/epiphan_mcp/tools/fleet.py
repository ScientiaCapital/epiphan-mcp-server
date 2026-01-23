"""Fleet management tools for Epiphan Pearl devices.

Fleet operations execute in parallel using asyncio.gather for improved performance.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from ..client import PearlClient
from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


# ============================================================
# Parallel Fleet Execution Helper
# ============================================================


async def _execute_on_fleet(
    hosts: list[str],
    operation: Callable[[PearlClient], Awaitable[dict[str, Any]]],
    settings: Settings,
    timeout_per_device: float = 10.0,
) -> list[dict[str, Any]]:
    """
    Execute operation on all devices in parallel using asyncio.gather.

    Args:
        hosts: List of device hostnames/IPs to operate on.
        operation: Async function that takes a PearlClient and returns a result dict.
        settings: Settings instance for creating clients.
        timeout_per_device: Timeout in seconds for each device operation.

    Returns:
        List of results from each device, in the same order as hosts.
        Failed operations return dicts with host, success=False, online=False,
        error message, and alert dict.
    """

    async def _device_op(host: str) -> dict[str, Any]:
        """Execute operation on a single device with timeout and error handling."""
        try:
            async with asyncio.timeout(timeout_per_device):
                async with PearlClient.from_settings(host, settings) as client:
                    return await operation(client)
        except TimeoutError:
            return {
                "host": host,
                "success": False,
                "online": False,
                "error": "Device timeout",
                "alert": {
                    "device": host,
                    "severity": "error",
                    "message": "Device timeout",
                },
            }
        except Exception as e:
            return {
                "host": host,
                "success": False,
                "online": False,
                "error": str(e),
                "alert": {
                    "device": host,
                    "severity": "error",
                    "message": f"Device offline: {e}",
                },
            }

    tasks = [_device_op(host) for host in hosts]
    return await asyncio.gather(*tasks, return_exceptions=False)


# ============================================================
# Fleet Status
# ============================================================


async def get_fleet_status() -> dict[str, Any]:
    """
    Get status of all configured Epiphan Pearl devices.

    This provides a fleet-wide view of device health and activity.
    Operations are executed in parallel for improved performance.

    Returns:
        Summary of fleet status including:
        - Total devices configured
        - Devices online/offline
        - Devices currently recording
        - Devices currently streaming
        - Any alerts or issues
    """
    settings = get_settings()
    devices = settings.get_device_list()

    if not devices:
        return {
            "success": True,
            "fleet_name": settings.fleet_name,
            "total_devices": 0,
            "message": "No devices configured. Set PEARL_DEVICES environment variable.",
        }

    async def _get_device_status(client: PearlClient) -> dict[str, Any]:
        """Get status for a single device."""
        host = client.host
        try:
            status = await client.get_system_status()
            recorder = await client.get_recorder_status("recorder-1")

            result: dict[str, Any] = {
                "host": host,
                "online": True,
                "recording": recorder.state.value == "recording",
                "storage_percent": status.storage_used_percent,
            }

            # Check for storage alerts
            if status.storage_used_percent > settings.storage_warning_percent:
                result["alert"] = {
                    "device": host,
                    "severity": "warning",
                    "message": f"Storage at {status.storage_used_percent:.1f}%",
                }

            return result
        except Exception as e:
            return {
                "host": host,
                "online": False,
                "error": str(e),
                "alert": {
                    "device": host,
                    "severity": "error",
                    "message": f"Device offline: {e}",
                },
            }

    # Execute on all devices in parallel
    raw_results = await _execute_on_fleet(
        hosts=devices,
        operation=_get_device_status,
        settings=settings,
        timeout_per_device=settings.timeout,
    )

    # Aggregate results
    results = []
    alerts = []
    online_count = 0
    recording_count = 0

    for raw_result in raw_results:
        # Extract alert if present
        alert = raw_result.pop("alert", None)
        if alert:
            alerts.append(alert)

        results.append(raw_result)

        if raw_result.get("online", False):
            online_count += 1
        if raw_result.get("recording", False):
            recording_count += 1

    return {
        "success": True,
        "fleet_name": settings.fleet_name,
        "total_devices": len(devices),
        "online_devices": online_count,
        "recording_devices": recording_count,
        "alerts_count": len(alerts),
        "devices": results,
        "alerts": alerts,
    }


# ============================================================
# Batch Recording Control
# ============================================================


async def batch_start_recording(device_ids: str = "all") -> dict[str, Any]:
    """
    Start recording on multiple Epiphan Pearl devices.

    Operations are executed in parallel for improved performance.

    Args:
        device_ids: Comma-separated list of device IDs, or "all" for all devices.

    Returns:
        Results for each device.
    """
    settings = get_settings()

    if device_ids == "all":
        hosts = settings.get_device_list()
    else:
        hosts = [d.strip() for d in device_ids.split(",")]

    if not hosts:
        return {
            "success": False,
            "error": "No devices specified",
        }

    async def _start_recording(client: PearlClient) -> dict[str, Any]:
        """Start recording on a single device."""
        host = client.host
        try:
            await client.start_recording("recorder-1")
            return {"device": host, "success": True}
        except Exception as e:
            return {"device": host, "success": False, "error": str(e)}

    # Execute on all devices in parallel
    results = await _execute_on_fleet(
        hosts=hosts,
        operation=_start_recording,
        settings=settings,
        timeout_per_device=settings.timeout,
    )

    # Count successes
    success_count = sum(1 for r in results if r.get("success", False))

    return {
        "success": success_count == len(hosts),
        "total_devices": len(hosts),
        "successful": success_count,
        "failed": len(hosts) - success_count,
        "results": results,
    }


async def batch_stop_recording(device_ids: str = "all") -> dict[str, Any]:
    """
    Stop recording on multiple Epiphan Pearl devices.

    Operations are executed in parallel for improved performance.

    Args:
        device_ids: Comma-separated list of device IDs, or "all" for all devices.

    Returns:
        Results for each device.
    """
    settings = get_settings()

    if device_ids == "all":
        hosts = settings.get_device_list()
    else:
        hosts = [d.strip() for d in device_ids.split(",")]

    if not hosts:
        return {
            "success": False,
            "error": "No devices specified",
        }

    async def _stop_recording(client: PearlClient) -> dict[str, Any]:
        """Stop recording on a single device."""
        host = client.host
        try:
            await client.stop_recording("recorder-1")
            return {"device": host, "success": True}
        except Exception as e:
            return {"device": host, "success": False, "error": str(e)}

    # Execute on all devices in parallel
    results = await _execute_on_fleet(
        hosts=hosts,
        operation=_stop_recording,
        settings=settings,
        timeout_per_device=settings.timeout,
    )

    # Count successes
    success_count = sum(1 for r in results if r.get("success", False))

    return {
        "success": success_count == len(hosts),
        "total_devices": len(hosts),
        "successful": success_count,
        "failed": len(hosts) - success_count,
        "results": results,
    }
