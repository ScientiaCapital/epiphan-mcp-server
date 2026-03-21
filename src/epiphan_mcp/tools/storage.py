"""Storage and input tools for Epiphan Pearl devices."""

import logging
from typing import Any

from fastmcp import FastMCP

from ..client import PearlAPIError
from .device import get_client

logger = logging.getLogger(__name__)


async def list_inputs(device_id: str = "default") -> dict[str, Any]:
    """
    List available input sources on an Epiphan Pearl device.

    Input sources include HDMI, SDI, USB, and network inputs that can be
    used in channel layouts.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        List of input sources including:
        - Input ID and name
        - Input type (HDMI, SDI, etc.)
        - Connection status
        - Resolution and format info
    """
    try:
        async with get_client(device_id) as client:
            inputs = await client.get_inputs()
            return {
                "success": True,
                "device": client.host,
                "total_inputs": len(inputs),
                "inputs": [inp.model_dump() for inp in inputs],
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


async def get_storage_report(device_id: str = "default") -> dict[str, Any]:
    """
    Get detailed storage information from an Epiphan Pearl device.

    Provides comprehensive storage details for capacity planning and monitoring.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        Storage report including:
        - Storage ID and type
        - Total capacity in bytes and GB
        - Free space in bytes and GB
        - Used percentage
        - Mount point and status
    """
    try:
        async with get_client(device_id) as client:
            storages = await client.get_storages()
            storage_list = []
            total_bytes = 0
            free_bytes = 0

            for storage in storages:
                storage_data = storage.model_dump()
                storage_list.append(storage_data)
                total_bytes += storage.total_bytes or 0
                free_bytes += storage.free_bytes or 0

            used_bytes = total_bytes - free_bytes
            used_percent = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0

            return {
                "success": True,
                "device": client.host,
                "total_storages": len(storages),
                "storages": storage_list,
                "summary": {
                    "total_bytes": total_bytes,
                    "total_gb": round(total_bytes / (1024**3), 2),
                    "free_bytes": free_bytes,
                    "free_gb": round(free_bytes / (1024**3), 2),
                    "used_bytes": used_bytes,
                    "used_gb": round(used_bytes / (1024**3), 2),
                    "used_percent": round(used_percent, 1),
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


async def get_afu_status(device_id: str = "default") -> dict[str, Any]:
    """
    Get status of Automatic File Upload (AFU) destinations on an Epiphan Pearl device.

    AFU automatically uploads completed recordings to cloud storage or network
    destinations (S3, FTP, SFTP, Aspera, etc.).

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        AFU status including:
        - Destination ID and name
        - Protocol (s3, ftp, sftp, aspera, etc.)
        - Current state (idle, uploading, error)
        - Queue count (files waiting to upload)
        - Destination URL
    """
    try:
        async with get_client(device_id) as client:
            afu_status = await client.get_afu_status()

            # Calculate summary stats
            total_queued = sum(item.get("queue_count", 0) for item in afu_status)
            uploading_count = sum(1 for item in afu_status if item.get("state") == "uploading")
            error_count = sum(1 for item in afu_status if item.get("state") == "error")

            return {
                "success": True,
                "device": client.host,
                "total_destinations": len(afu_status),
                "destinations": afu_status,
                "summary": {
                    "total_queued_files": total_queued,
                    "uploading_count": uploading_count,
                    "error_count": error_count,
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


def register(server: FastMCP) -> None:
    """Register storage MCP tools."""
    server.tool()(get_afu_status)
    server.tool()(get_storage_report)
    server.tool()(list_inputs)
