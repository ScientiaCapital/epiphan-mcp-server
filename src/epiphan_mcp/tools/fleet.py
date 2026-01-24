"""Fleet management tools for Epiphan Pearl devices.

Fleet operations execute in parallel using asyncio.gather for improved performance.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from ..client import PearlClient
from ..config import Settings, get_settings
from ..llm.providers import LLMError, get_provider

logger = logging.getLogger(__name__)


# ============================================================
# Health Score Calculation
# ============================================================


def _calculate_health_score(
    storage_used_percent: float,
    recorder_accessible: bool = True,
) -> dict[str, Any]:
    """
    Calculate health score for a device (0-100).

    Scoring breakdown:
    - Storage health: 50 points max
    - Recording system health: 50 points max

    Args:
        storage_used_percent: Current storage usage percentage
        recorder_accessible: Whether recorder status was accessible

    Returns:
        Dict with score (0-100), issues list, and category breakdown
    """
    issues: list[str] = []
    categories: dict[str, dict[str, Any]] = {}

    # Storage health (50 points max)
    if storage_used_percent >= 90:
        storage_score = 10  # Critical
        issues.append(f"Storage critically low: {storage_used_percent:.0f}% used")
    elif storage_used_percent >= 75:
        storage_score = 30  # Warning
        issues.append(f"Storage running low: {storage_used_percent:.0f}% used")
    else:
        storage_score = 50  # Healthy

    categories["storage"] = {
        "score": storage_score,
        "max": 50,
        "used_percent": round(storage_used_percent, 1),
    }

    # Recording system health (50 points max)
    if recorder_accessible:
        recording_score = 50
    else:
        recording_score = 25
        issues.append("Could not check recorder status")

    categories["recording"] = {
        "score": recording_score,
        "max": 50,
    }

    total_score = storage_score + recording_score

    return {
        "score": total_score,
        "issues": issues,
        "categories": categories,
    }


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
        """Get status for a single device including health score."""
        host = client.host
        try:
            status = await client.get_system_status()
            recorder_accessible = True
            try:
                recorder = await client.get_recorder_status("recorder-1")
                is_recording = recorder.state.value == "recording"
            except Exception:
                recorder_accessible = False
                is_recording = False

            # Calculate health score
            health = _calculate_health_score(
                storage_used_percent=status.storage_used_percent,
                recorder_accessible=recorder_accessible,
            )

            result: dict[str, Any] = {
                "host": host,
                "online": True,
                "recording": is_recording,
                "storage_percent": status.storage_used_percent,
                "health_score": health["score"],
                "health_issues": health["issues"],
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
                "health_score": 0,
                "health_issues": [f"Device offline: {e}"],
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
    health_scores = []

    for raw_result in raw_results:
        # Extract alert if present
        alert = raw_result.pop("alert", None)
        if alert:
            alerts.append(alert)

        results.append(raw_result)

        if raw_result.get("online", False):
            online_count += 1
            health_scores.append(raw_result.get("health_score", 0))
        if raw_result.get("recording", False):
            recording_count += 1

    # Calculate fleet-level health metrics
    average_health = (
        sum(health_scores) / len(health_scores) if health_scores else 0.0
    )
    unhealthy_count = len([s for s in health_scores if s < 60])

    return {
        "success": True,
        "fleet_name": settings.fleet_name,
        "total_devices": len(devices),
        "online_devices": online_count,
        "recording_devices": recording_count,
        "average_health": round(average_health, 1),
        "unhealthy_devices": unhealthy_count,
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


# ============================================================
# Fleet Health Report
# ============================================================


async def fleet_health_report() -> dict[str, Any]:
    """
    Generate AI-summarized fleet health report.

    Returns natural language summary with:
    - Fleet health overview
    - Devices needing attention
    - Prioritized recommendations

    Returns:
        Structured report with AI-generated summary and actionable recommendations.
    """
    settings = get_settings()

    # Get fleet status with health scores
    fleet_status = await get_fleet_status()

    if not fleet_status.get("success"):
        return {
            "success": False,
            "error": "Failed to get fleet status",
        }

    total_devices = fleet_status.get("total_devices", 0)

    if total_devices == 0:
        return {
            "success": True,
            "fleet_name": settings.fleet_name,
            "generated_at": datetime.now().isoformat(),
            "summary": "No devices configured in fleet.",
            "health_score": 0,
            "attention_required": [],
            "recommendations": ["Configure devices in PEARL_DEVICES environment variable."],
        }

    # Extract devices needing attention
    attention_required: list[dict[str, str]] = []
    for device in fleet_status.get("devices", []):
        host = device.get("host", "unknown")

        if not device.get("online", False):
            attention_required.append({
                "device": host,
                "issue": "Device offline",
                "action": "Check network connectivity and power",
            })
        elif device.get("health_score", 100) < 60:
            issues = device.get("health_issues", [])
            issue_str = issues[0] if issues else "Health score below threshold"
            attention_required.append({
                "device": host,
                "issue": issue_str,
                "action": _get_action_for_issue(issue_str),
            })
        elif device.get("storage_percent", 0) > settings.storage_warning_percent:
            attention_required.append({
                "device": host,
                "issue": f"Storage at {device.get('storage_percent', 0):.0f}%",
                "action": "Archive or delete old recordings",
            })

    # Build prompt for AI summary
    online = fleet_status.get("online_devices", 0)
    recording = fleet_status.get("recording_devices", 0)
    avg_health = fleet_status.get("average_health", 0)

    prompt = f"""Generate a brief fleet health summary for an IT administrator.

Fleet Status:
- Fleet name: {settings.fleet_name}
- Total devices: {total_devices}
- Online: {online}
- Currently recording: {recording}
- Average health score: {avg_health}/100

Devices needing attention: {len(attention_required)}
{_format_attention_list(attention_required)}

Provide:
1. A 1-2 sentence summary of fleet health
2. Top 2-3 prioritized recommendations (if any issues exist)

Keep the response concise and actionable. Use plain language."""

    # Generate AI summary
    try:
        provider = get_provider()
        ai_response = await provider.complete(prompt, max_tokens=300)
        if hasattr(provider, "close"):
            await provider.close()

        # Parse AI response for summary and recommendations
        summary, recommendations = _parse_ai_response(ai_response, attention_required)
    except LLMError as e:
        logger.warning(f"LLM summarization failed: {e}")
        # Fallback to basic summary
        summary = _generate_fallback_summary(fleet_status)
        recommendations = _generate_fallback_recommendations(attention_required)

    return {
        "success": True,
        "fleet_name": settings.fleet_name,
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "health_score": round(avg_health),
        "devices_online": online,
        "devices_recording": recording,
        "attention_required": attention_required,
        "recommendations": recommendations,
    }


def _get_action_for_issue(issue: str) -> str:
    """Get recommended action for a health issue."""
    issue_lower = issue.lower()
    if "storage" in issue_lower:
        return "Archive or delete old recordings to free space"
    elif "recorder" in issue_lower:
        return "Check recorder configuration and restart if needed"
    elif "offline" in issue_lower:
        return "Check network connectivity and power"
    return "Investigate and resolve the issue"


def _format_attention_list(attention_required: list[dict[str, str]]) -> str:
    """Format attention list for prompt."""
    if not attention_required:
        return "None - all devices healthy"
    lines = []
    for item in attention_required[:5]:  # Limit to top 5
        lines.append(f"- {item['device']}: {item['issue']}")
    return "\n".join(lines)


def _parse_ai_response(
    response: str,
    attention_required: list[dict[str, str]],
) -> tuple[str, list[str]]:
    """Parse AI response to extract summary and recommendations."""
    lines = response.strip().split("\n")

    # First non-empty line(s) are usually the summary
    summary_lines = []
    recommendations = []
    in_recommendations = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for recommendation markers
        if any(
            line.lower().startswith(prefix)
            for prefix in ["recommendation", "1.", "2.", "3.", "-", "*"]
        ):
            in_recommendations = True

        if in_recommendations:
            # Clean up recommendation line
            cleaned = line.lstrip("0123456789.-*) ")
            if cleaned and len(cleaned) > 5:
                recommendations.append(cleaned)
        else:
            summary_lines.append(line)

    summary = " ".join(summary_lines[:2]) if summary_lines else "Fleet status retrieved."

    # Use AI recommendations or generate from attention list
    if not recommendations and attention_required:
        recommendations = [item["action"] for item in attention_required[:3]]

    return summary, recommendations[:3]


def _generate_fallback_summary(fleet_status: dict[str, Any]) -> str:
    """Generate basic summary without AI."""
    online = fleet_status.get("online_devices", 0)
    total = fleet_status.get("total_devices", 0)
    recording = fleet_status.get("recording_devices", 0)
    avg_health = fleet_status.get("average_health", 0)

    if online == 0:
        return "All devices are offline. Check network connectivity."
    elif avg_health >= 80:
        return f"Fleet healthy. {online}/{total} devices online, {recording} recording."
    elif avg_health >= 60:
        return f"Fleet has minor issues. {online}/{total} devices online, average health {avg_health:.0f}%."
    else:
        return f"Fleet needs attention. {online}/{total} devices online, average health {avg_health:.0f}%."


def _generate_fallback_recommendations(
    attention_required: list[dict[str, str]],
) -> list[str]:
    """Generate basic recommendations without AI."""
    if not attention_required:
        return ["Continue monitoring fleet health."]

    recommendations = []
    seen_actions = set()
    for item in attention_required:
        action = item["action"]
        if action not in seen_actions:
            recommendations.append(action)
            seen_actions.add(action)
        if len(recommendations) >= 3:
            break

    return recommendations
