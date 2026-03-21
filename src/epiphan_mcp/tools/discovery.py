"""Device resource discovery with session-scoped caching for Epiphan Pearl."""

import logging
import re
import time
from typing import Any

from fastmcp import FastMCP

from ..client import PearlAPIError
from .device import get_client

logger = logging.getLogger(__name__)

# Cache TTL in seconds (5 minutes)
_CACHE_TTL = 300.0

# Session-scoped caches: {device_host: data}
_device_cache: dict[str, dict[str, Any]] = {}
_cache_timestamps: dict[str, float] = {}


def _parse_resource_number(resource_id: str) -> int:
    """Extract the integer from a resource ID like 'recorder-1' or 'channel-2'."""
    match = re.search(r"(\d+)$", resource_id)
    return int(match.group(1)) if match else 1


def _is_cache_valid(host: str) -> bool:
    """Check if cached data for a device is still fresh."""
    if host not in _cache_timestamps:
        return False
    return (time.monotonic() - _cache_timestamps[host]) < _CACHE_TTL


async def discover_device(device_id: str = "default") -> dict[str, Any]:
    """
    Discover available recorders, channels, and inputs on a Pearl device.

    Results are cached per device for 5 minutes. Use pearl_clear_discovery_cache
    to force a refresh.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device,
                   or specify an IP address, hostname, or device index.

    Returns:
        Device capabilities including lists of recorders, channels, and inputs
        with their IDs and names.
    """
    try:
        async with get_client(device_id) as client:
            host = client.host

            if _is_cache_valid(host):
                return {"success": True, "device": host, "cached": True, **_device_cache[host]}

            recorders = await client.get_recorders()
            channels = await client.get_channels()
            inputs = await client.get_inputs()

            data = {
                "recorders": [
                    {"id": r.id, "name": r.name, "type": r.type, "channel_id": r.channel_id}
                    for r in recorders
                ],
                "channels": [
                    {"id": c.id, "name": c.name}
                    for c in channels
                ],
                "inputs": [
                    {"id": i.id, "name": i.name, "type": i.type, "connected": i.connected}
                    for i in inputs
                ],
            }

            _device_cache[host] = data
            _cache_timestamps[host] = time.monotonic()

            return {"success": True, "device": host, "cached": False, **data}

    except Exception as e:
        logger.debug("Discovery failed for %s: %s", device_id, e)
        return {"success": False, "error": str(e), "device": device_id}


async def get_default_recorder(device_id: str = "default") -> int:
    """Get first available recorder number (1-based), fallback to 1."""
    result = await discover_device(device_id)
    if result.get("success") and result.get("recorders"):
        return _parse_resource_number(result["recorders"][0]["id"])
    return 1


async def get_default_channel(device_id: str = "default") -> int:
    """Get first available channel number (1-based), fallback to 1."""
    result = await discover_device(device_id)
    if result.get("success") and result.get("channels"):
        return _parse_resource_number(result["channels"][0]["id"])
    return 1


async def clear_discovery_cache(device_id: str | None = None) -> dict[str, Any]:
    """
    Clear the device discovery cache.

    Use this when device configuration changes (recorders/channels added or removed)
    to force re-discovery on the next tool call.

    Args:
        device_id: Device to clear cache for. If None, clears all cached devices.

    Returns:
        Confirmation of cache clearance with count of entries removed.
    """
    if device_id is not None:
        try:
            async with get_client(device_id) as client:
                host = client.host
        except (PearlAPIError, ValueError):
            host = device_id

        removed = 0
        if host in _device_cache:
            del _device_cache[host]
            del _cache_timestamps[host]
            removed = 1
        return {
            "success": True,
            "cleared": device_id,
            "entries_removed": removed,
        }
    else:
        count = len(_device_cache)
        _device_cache.clear()
        _cache_timestamps.clear()
        return {
            "success": True,
            "cleared": "all",
            "entries_removed": count,
        }


def register(server: FastMCP) -> None:
    """Register discovery MCP tools."""
    server.tool(name="pearl_discover_device")(discover_device)
    server.tool(name="pearl_clear_discovery_cache")(clear_discovery_cache)
