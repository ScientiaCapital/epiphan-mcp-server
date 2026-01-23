"""Device status and information tools for Epiphan Pearl devices."""

import logging
from typing import Any

from ..client import PearlAPIError, PearlClient
from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


def get_client(device_id: str = "default") -> PearlClient:
    """
    Get a PearlClient for the specified device.

    Args:
        device_id: Device identifier (IP, hostname, "default", or index)

    Returns:
        Configured PearlClient instance.
    """
    settings = get_settings()
    host = settings.get_device_host(device_id)
    return PearlClient.from_settings(host, settings)


async def get_device_status(device_id: str = "default") -> dict[str, Any]:
    """
    Get the current status of an Epiphan Pearl device.

    Use this to check device health, storage levels, uptime, and active operations.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device,
                   or specify an IP address, hostname, or device index.

    Returns:
        Device status including:
        - Storage usage and availability
        - System uptime
        - CPU and memory usage
        - Firmware version
        - Current recording/streaming state
    """
    try:
        async with get_client(device_id) as client:
            status = await client.get_system_status()
            recorder_status = await client.get_recorder_status("recorder-1")

            return {
                "success": True,
                "device": client.host,
                "status": {
                    "uptime_hours": status.uptime_hours,
                    "storage": {
                        "total_gb": status.storage_total_gb,
                        "free_gb": status.storage_free_gb,
                        "used_percent": status.storage_used_percent,
                    },
                    "firmware": status.firmware_version,
                    "model": status.model,
                    "recording": recorder_status.state.value,
                },
            }
    except PearlAPIError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "device": device_id,
        }


async def list_devices() -> dict[str, Any]:
    """
    List all configured Epiphan Pearl devices.

    Returns the list of devices configured in the PEARL_DEVICES environment variable.

    Returns:
        List of device hostnames/IPs with their indices.
    """
    settings = get_settings()
    devices = settings.get_device_list()

    return {
        "success": True,
        "fleet_name": settings.fleet_name,
        "device_count": len(devices),
        "devices": [{"index": i, "host": host} for i, host in enumerate(devices)],
    }
