"""Predictive maintenance tools for Epiphan Pearl devices."""

import logging
from typing import Any

from fastmcp import FastMCP

from ..client import PearlAPIError
from .device import get_client
from .discovery import get_default_recorder

logger = logging.getLogger(__name__)


async def predict_storage_full(
    device_id: str = "default", recorder: int | None = None, assumed_bitrate_mbps: float = 8.0
) -> dict[str, Any]:
    """
    Predict when device storage will be full based on current recording rate.

    This is a predictive maintenance tool that helps prevent storage issues
    by estimating time remaining before storage fills up.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.
        recorder: Recorder number (1-based) to check for active recording.
                  Auto-detected if not specified.
        assumed_bitrate_mbps: Assumed recording bitrate in Mbps if not actively recording.
                              Default 8.0 Mbps is typical for 1080p H.264.

    Returns:
        Storage prediction including:
        - hours_until_full: Estimated hours until storage is full
        - storage_free_gb: Current free storage in GB
        - storage_total_gb: Total storage capacity in GB
        - is_recording: Whether currently recording
        - bitrate_mbps: Actual or assumed recording bitrate
        - warning: True if storage is critically low (<10%)
    """
    if recorder is None:
        recorder = await get_default_recorder(device_id)
    try:
        async with get_client(device_id) as client:
            # Get storage info
            storage_status = await client.get_system_status()
            free_bytes = storage_status.storage_free_gb * 1024 * 1024 * 1024

            # Get recording status for bitrate
            recorder_id = f"recorder-{recorder}"
            recorder_status = await client.get_recorder_status(recorder_id)
            is_recording = recorder_status.state.value == "recording"

            # Use actual bitrate if recording, otherwise use assumed
            bitrate_bps: float = (
                recorder_status.bitrate
                if is_recording and recorder_status.bitrate
                else assumed_bitrate_mbps * 1_000_000
            )

            bitrate_mbps = bitrate_bps / 1_000_000
            bytes_per_hour = bitrate_bps / 8 * 3600  # bits/sec -> bytes/hour

            # Calculate hours until full
            hours_until_full = (
                free_bytes / bytes_per_hour if bytes_per_hour > 0 else float("inf")
            )

            # Determine warning status (>= 90% used or < 2 hours remaining)
            storage_used_percent = storage_status.storage_used_percent or 0
            warning = storage_used_percent >= 90 or hours_until_full < 2

            return {
                "success": True,
                "device": client.host,
                "hours_until_full": round(hours_until_full, 1),
                "storage_free_gb": round(storage_status.storage_free_gb, 1),
                "storage_total_gb": round(storage_status.storage_total_gb, 1),
                "storage_used_percent": round(storage_used_percent, 1),
                "is_recording": is_recording,
                "bitrate_mbps": round(bitrate_mbps, 1),
                "warning": warning,
                "recommendation": (
                    "Storage critically low - archive or delete recordings"
                    if warning
                    else "Storage capacity is sufficient"
                ),
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


async def get_device_health_score(device_id: str = "default") -> dict[str, Any]:
    """
    Calculate an overall health score for a Pearl device (0-100).

    This AI-powered tool aggregates multiple health indicators into a single
    score, making it easy to identify devices that need attention.

    Args:
        device_id: Device identifier. Use "default" for the primary configured device.

    Returns:
        Health assessment including:
        - score: Overall health score 0-100 (higher is better)
        - categories: Breakdown by category (storage, recording, etc.)
        - issues: List of any detected issues
        - is_recording: Whether device is currently recording
        - recommendation: Suggested action if any issues found
    """
    recorder = await get_default_recorder(device_id)
    try:
        async with get_client(device_id) as client:
            issues: list[str] = []
            category_scores: dict[str, dict[str, Any]] = {}

            # Get device and storage info
            storage_status = await client.get_system_status()

            # Storage health (50 points max)
            storage_used_percent = storage_status.storage_used_percent or 0
            if storage_used_percent >= 90:
                storage_score = 10  # Critical
                storage_healthy = False
                issues.append(f"Storage critically low: {storage_used_percent:.0f}% used")
            elif storage_used_percent >= 75:
                storage_score = 30  # Warning
                storage_healthy = False
                issues.append(f"Storage running low: {storage_used_percent:.0f}% used")
            else:
                storage_score = 50  # Healthy
                storage_healthy = True

            category_scores["storage"] = {
                "score": storage_score,
                "max": 50,
                "healthy": storage_healthy,
                "used_percent": round(storage_used_percent, 1),
            }

            # Recording health (50 points max)
            try:
                recorder_status = await client.get_recorder_status(f"recorder-{recorder}")
                is_recording = recorder_status.state.value == "recording"
                recording_score = 50  # Healthy - device is responsive
                recording_healthy = True
            except PearlAPIError:
                is_recording = False
                recording_score = 25  # Degraded - couldn't check recorder
                recording_healthy = False
                issues.append("Could not check recorder status")

            category_scores["recording"] = {
                "score": recording_score,
                "max": 50,
                "healthy": recording_healthy,
                "is_recording": is_recording,
            }

            # Calculate total score
            total_score = sum(cat["score"] for cat in category_scores.values())

            # Generate recommendation
            if total_score >= 80:
                recommendation = "Device is healthy - no action needed"
            elif total_score >= 60:
                recommendation = "Device has minor issues - review when convenient"
            elif total_score >= 40:
                recommendation = "Device needs attention - address issues soon"
            else:
                recommendation = "Device is unhealthy - immediate attention required"

            return {
                "success": True,
                "device": client.host,
                "score": total_score,
                "categories": category_scores,
                "issues": issues,
                "is_recording": is_recording,
                "recommendation": recommendation,
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
    """Register maintenance MCP tools."""
    server.tool()(get_device_health_score)
    server.tool()(predict_storage_full)
