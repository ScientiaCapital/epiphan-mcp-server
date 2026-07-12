"""Fleet management tools for Epiphan Pearl devices.

Fleet operations execute in parallel using asyncio.gather for improved performance.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..client import PearlClient
from ..config import Settings, get_settings
from ..llm.providers import LLMError, get_provider
from ..models import (
    BatchRecordingResult,
    FleetHealthReportResult,
    FleetIssuePredictionResult,
    FleetStatusResult,
    MaintenanceWindowResult,
    ShiftHandoffResult,
)
from .discovery import get_default_recorder
from .params import DeviceIds

logger = logging.getLogger(__name__)

# Security: Configurable concurrency limit for fleet operations
_fleet_semaphore: asyncio.Semaphore | None = None


def _get_fleet_semaphore() -> asyncio.Semaphore:
    """Get or create the fleet semaphore from config.

    Note on thread safety: This lazy-init pattern has a theoretical TOCTOU
    race in multi-threaded contexts.  However, FastMCP runs a single-threaded
    asyncio event loop, so only one coroutine executes this function at a time.
    No lock is needed.
    """
    global _fleet_semaphore
    if _fleet_semaphore is None:
        settings = get_settings()
        _fleet_semaphore = asyncio.Semaphore(settings.max_concurrent_ops)
    return _fleet_semaphore


def _reset_fleet_semaphore() -> None:
    """Reset the fleet semaphore so it re-reads config on next access.

    Call this in tests to prevent state leaking between test cases.
    """
    global _fleet_semaphore
    _fleet_semaphore = None


# ============================================================
# Health Score Calculation
# ============================================================


def _calculate_health_score(
    storage_used_percent: float,
    recorder_accessible: bool = True,
    storage_weight: int = 50,
    recording_weight: int = 50,
) -> dict[str, Any]:
    """
    Calculate health score for a device (0-100).

    Scoring breakdown is configurable via weights (should sum to 100):
    - Storage health: ``storage_weight`` points max
    - Recording system health: ``recording_weight`` points max

    Args:
        storage_used_percent: Current storage usage percentage
        recorder_accessible: Whether recorder status was accessible
        storage_weight: Max points for storage health (from config)
        recording_weight: Max points for recording health (from config)

    Returns:
        Dict with score (0-100), issues list, and category breakdown
    """
    issues: list[str] = []
    categories: dict[str, dict[str, Any]] = {}

    # Storage health (storage_weight points max)
    if storage_used_percent >= 90:
        storage_score = round(storage_weight * 0.2)  # Critical: 20% of weight
        issues.append(f"Storage critically low: {storage_used_percent:.0f}% used")
    elif storage_used_percent >= 75:
        storage_score = round(storage_weight * 0.6)  # Warning: 60% of weight
        issues.append(f"Storage running low: {storage_used_percent:.0f}% used")
    else:
        storage_score = storage_weight  # Healthy: full weight

    categories["storage"] = {
        "score": storage_score,
        "max": storage_weight,
        "used_percent": round(storage_used_percent, 1),
    }

    # Recording system health (recording_weight points max)
    if recorder_accessible:
        recording_score = recording_weight
    else:
        recording_score = round(recording_weight * 0.5)
        issues.append("Could not check recorder status")

    categories["recording"] = {
        "score": recording_score,
        "max": recording_weight,
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

    Concurrency is limited by the fleet semaphore (configurable via
    PEARL_MAX_CONCURRENT_OPS) to prevent overwhelming the network or
    devices with too many simultaneous connections.

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
        """Execute operation on a single device with semaphore, timeout, and error handling."""
        async with _get_fleet_semaphore():
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


async def get_fleet_status() -> FleetStatusResult:
    """
    Get status of ALL configured Epiphan Pearl devices in one parallel call.

    Use this instead of calling get_device_status once per device: it queries
    every configured device concurrently and returns a single fleet-wide rollup
    of health and activity. Offline devices are cancelled after
    fleet_timeout_per_device seconds so they don't stall the whole call.

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
        return FleetStatusResult(
            success=True,
            fleet_name=settings.fleet_name,
            total_devices=0,
            message="No devices configured. Set PEARL_DEVICES environment variable.",
        )

    async def _get_device_status(client: PearlClient) -> dict[str, Any]:
        """Get status for a single device including health score."""
        host = client.host
        try:
            status = await client.get_system_status()
            recorder_accessible = True
            try:
                recorder_num = await get_default_recorder(host)
                recorder = await client.get_recorder_status(f"recorder-{recorder_num}")
                is_recording = recorder.state.value == "recording"
            except Exception:
                recorder_accessible = False
                is_recording = False

            # Calculate health score using configurable weights
            health = _calculate_health_score(
                storage_used_percent=status.storage_used_percent,
                recorder_accessible=recorder_accessible,
                storage_weight=settings.health_score_storage_weight,
                recording_weight=settings.health_score_recording_weight,
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
        timeout_per_device=settings.fleet_timeout_per_device,
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

    return FleetStatusResult(
        success=True,
        fleet_name=settings.fleet_name,
        total_devices=len(devices),
        online_devices=online_count,
        recording_devices=recording_count,
        average_health=round(average_health, 1),
        unhealthy_devices=unhealthy_count,
        alerts_count=len(alerts),
        devices=results,
        alerts=alerts,
    )


# ============================================================
# Batch Recording Control
# ============================================================


async def batch_start_recording(device_ids: DeviceIds = "all") -> BatchRecordingResult:
    """
    Start recording on ALL (or several) Epiphan Pearl devices in one parallel call.

    Use this instead of calling start_recording once per device: it fans out to
    every target device concurrently and returns one batch result. Offline
    devices are cancelled after fleet_timeout_per_device seconds.

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
        return BatchRecordingResult(
            success=False,
            error="No devices specified",
        )

    async def _start_recording(client: PearlClient) -> dict[str, Any]:
        """Start recording on a single device."""
        host = client.host
        try:
            recorder_num = await get_default_recorder(host)
            await client.start_recording(f"recorder-{recorder_num}")
            return {"device": host, "success": True}
        except Exception as e:
            return {"device": host, "success": False, "error": str(e)}

    # Execute on all devices in parallel
    results = await _execute_on_fleet(
        hosts=hosts,
        operation=_start_recording,
        settings=settings,
        timeout_per_device=settings.fleet_timeout_per_device,
    )

    # Count successes
    success_count = sum(1 for r in results if r.get("success", False))

    return BatchRecordingResult(
        success=success_count == len(hosts),
        total_devices=len(hosts),
        successful=success_count,
        failed=len(hosts) - success_count,
        results=results,
    )


async def batch_stop_recording(device_ids: DeviceIds = "all") -> BatchRecordingResult:
    """
    Stop recording on ALL (or several) Epiphan Pearl devices in one parallel call.

    Use this instead of calling stop_recording once per device: it fans out to
    every target device concurrently and returns one batch result. Offline
    devices are cancelled after fleet_timeout_per_device seconds.

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
        return BatchRecordingResult(
            success=False,
            error="No devices specified",
        )

    async def _stop_recording(client: PearlClient) -> dict[str, Any]:
        """Stop recording on a single device."""
        host = client.host
        try:
            recorder_num = await get_default_recorder(host)
            await client.stop_recording(f"recorder-{recorder_num}")
            return {"device": host, "success": True}
        except Exception as e:
            return {"device": host, "success": False, "error": str(e)}

    # Execute on all devices in parallel
    results = await _execute_on_fleet(
        hosts=hosts,
        operation=_stop_recording,
        settings=settings,
        timeout_per_device=settings.fleet_timeout_per_device,
    )

    # Count successes
    success_count = sum(1 for r in results if r.get("success", False))

    return BatchRecordingResult(
        success=success_count == len(hosts),
        total_devices=len(hosts),
        successful=success_count,
        failed=len(hosts) - success_count,
        results=results,
    )


# ============================================================
# Fleet Health Report
# ============================================================


async def fleet_health_report() -> FleetHealthReportResult:
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

    if not fleet_status.success:
        return FleetHealthReportResult(
            success=False,
            error="Failed to get fleet status",
        )

    total_devices = fleet_status.total_devices

    if total_devices == 0:
        return FleetHealthReportResult(
            success=True,
            fleet_name=settings.fleet_name,
            generated_at=datetime.now().isoformat(),
            summary="No devices configured in fleet.",
            health_score=0,
            attention_required=[],
            recommendations=["Configure devices in PEARL_DEVICES environment variable."],
        )

    # Extract devices needing attention
    attention_required: list[dict[str, str]] = []
    for device in fleet_status.devices:
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
    online = fleet_status.online_devices
    recording = fleet_status.recording_devices
    avg_health = fleet_status.average_health

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

    return FleetHealthReportResult(
        success=True,
        fleet_name=settings.fleet_name,
        generated_at=datetime.now().isoformat(),
        summary=summary,
        health_score=round(avg_health),
        devices_online=online,
        devices_recording=recording,
        attention_required=attention_required,
        recommendations=recommendations,
    )


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


def _generate_fallback_summary(fleet_status: FleetStatusResult) -> str:
    """Generate basic summary without AI."""
    online = fleet_status.online_devices
    total = fleet_status.total_devices
    recording = fleet_status.recording_devices
    avg_health = fleet_status.average_health

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


# ============================================================
# Fleet Intelligence Tools (Sprint 3)
# ============================================================


async def suggest_maintenance_window(
    min_duration_hours: Annotated[
        float,
        Field(description="Minimum maintenance window duration needed, in hours."),
    ] = 2.0,
) -> MaintenanceWindowResult:
    """
    Suggest optimal maintenance window based on fleet usage patterns.

    Analyzes current fleet status and recording schedules to recommend
    the best time for maintenance with minimal disruption.

    Args:
        min_duration_hours: Minimum maintenance window duration needed.

    Returns:
        dict containing:
            - success: bool
            - suggested_window: Recommended time window
            - confidence: How confident in the recommendation (high/medium/low)
            - reasoning: Explanation for the suggestion
            - devices_affected: Number of devices that would be impacted
            - current_activity: Summary of current fleet activity
    """
    settings = get_settings()

    # Get current fleet status
    fleet_status = await get_fleet_status()

    if not fleet_status.success:
        return MaintenanceWindowResult(
            success=False,
            error="Failed to get fleet status",
        )

    total_devices = fleet_status.total_devices
    online_devices = fleet_status.online_devices
    recording_devices = fleet_status.recording_devices

    if total_devices == 0:
        return MaintenanceWindowResult(
            success=True,
            suggested_window="Any time - no devices configured",
            confidence="high",
            reasoning="No devices in fleet to maintain.",
            devices_affected=0,
            current_activity="No activity",
        )

    # Build context for AI analysis
    current_time = datetime.now()
    hour_of_day = current_time.hour
    day_of_week = current_time.strftime("%A")

    # Determine current activity level
    activity_percent = (recording_devices / online_devices * 100) if online_devices > 0 else 0

    if activity_percent > 50:
        current_activity = f"High activity: {recording_devices}/{online_devices} devices recording"
    elif activity_percent > 0:
        current_activity = f"Moderate activity: {recording_devices}/{online_devices} devices recording"
    else:
        current_activity = "Low activity: No devices currently recording"

    # Build prompt for AI reasoning
    prompt = f"""Suggest an optimal maintenance window for an AV fleet.

Current Status:
- Time: {current_time.strftime('%H:%M')} on {day_of_week}
- Total devices: {total_devices}
- Online: {online_devices}
- Currently recording: {recording_devices}
- Activity level: {current_activity}

Maintenance requirement: {min_duration_hours} hours minimum

Consider typical AV usage patterns:
- Weekday business hours (9am-5pm): Likely high activity
- Early morning/late evening: Usually low activity
- Weekends: Varies by environment

Provide:
1. A specific time window suggestion (e.g., "Tonight 10pm-2am" or "This weekend Saturday 6am-10am")
2. Confidence level (high/medium/low)
3. Brief reasoning (2-3 sentences)

Keep response concise and actionable."""

    try:
        provider = get_provider()
        ai_response = await provider.complete(prompt, max_tokens=250)
        if hasattr(provider, "close"):
            await provider.close()

        # Parse AI response
        suggested_window, confidence, reasoning = _parse_maintenance_suggestion(
            ai_response, current_activity, recording_devices
        )

    except LLMError as e:
        logger.warning(f"LLM suggestion failed: {e}")
        # Fallback to simple logic
        if recording_devices == 0:
            suggested_window = "Now - no active recordings"
            confidence = "high"
            reasoning = "No devices are currently recording, making this an ideal time for maintenance."
        elif hour_of_day >= 22 or hour_of_day < 6:
            suggested_window = "Current window (late night)"
            confidence = "medium"
            reasoning = "Late night hours typically have lower AV activity."
        else:
            suggested_window = "Tonight after 10pm local time"
            confidence = "medium"
            reasoning = "Daytime hours often have higher activity; evening maintenance minimizes disruption."

    return MaintenanceWindowResult(
        success=True,
        fleet_name=settings.fleet_name,
        suggested_window=suggested_window,
        confidence=confidence,
        reasoning=reasoning,
        devices_affected=online_devices,
        current_activity=current_activity,
        generated_at=datetime.now().isoformat(),
    )


def _parse_maintenance_suggestion(
    response: str, current_activity: str, recording_count: int
) -> tuple[str, str, str]:
    """Parse AI response for maintenance window suggestion."""
    lines = response.strip().split("\n")

    suggested_window = "Review fleet status manually"
    confidence = "medium"
    reasoning = "Unable to parse AI response - review current activity."

    for line in lines:
        line_lower = line.lower()
        # Look for time-related suggestions
        if any(word in line_lower for word in ["tonight", "tomorrow", "weekend", "am", "pm", "now"]) and suggested_window == "Review fleet status manually":
                # Clean up the line
                suggested_window = line.strip().lstrip("1234567890.-*) ")
                if len(suggested_window) < 5:
                    suggested_window = "Review fleet status manually"

        # Look for confidence indicators
        if "high" in line_lower and "confidence" in line_lower:
            confidence = "high"
        elif "low" in line_lower and "confidence" in line_lower:
            confidence = "low"

    # Build reasoning from remaining content
    reasoning_lines = [line.strip() for line in lines if len(line.strip()) > 20 and ":" not in line[:15]]
    if reasoning_lines:
        reasoning = " ".join(reasoning_lines[:2])

    return suggested_window, confidence, reasoning


async def predict_fleet_issues(
    hours_ahead: Annotated[
        int,
        Field(description="How many hours ahead to predict (e.g. 24, 48, or 72)."),
    ] = 24,
) -> FleetIssuePredictionResult:
    """
    Predict fleet issues for the next 24/48/72 hours.

    Analyzes current health scores, storage trends, and patterns to
    forecast potential problems before they occur.

    Args:
        hours_ahead: How many hours ahead to predict (24, 48, or 72).

    Returns:
        dict containing:
            - success: bool
            - predictions: List of predicted issues with timeframes
            - risk_level: Overall risk level (low/medium/high/critical)
            - devices_at_risk: Count of devices with predicted issues
            - summary: AI-generated summary of predictions
    """
    settings = get_settings()
    devices = settings.get_device_list()

    if not devices:
        return FleetIssuePredictionResult(
            success=True,
            fleet_name=settings.fleet_name,
            predictions=[],
            risk_level="low",
            devices_at_risk=0,
            summary="No devices configured in fleet.",
        )

    # Get detailed status for each device
    fleet_status = await get_fleet_status()

    if not fleet_status.success:
        return FleetIssuePredictionResult(
            success=False,
            error="Failed to get fleet status",
        )

    predictions: list[dict[str, Any]] = []
    devices_at_risk = 0

    # Analyze each device for potential issues
    for device in fleet_status.devices:
        host = device.get("host", "unknown")

        if not device.get("online", False):
            predictions.append({
                "device": host,
                "issue": "Device offline",
                "timeframe": "Now",
                "severity": "critical",
                "action": "Check network connectivity and power immediately",
            })
            devices_at_risk += 1
            continue

        # Storage prediction
        storage_percent = device.get("storage_percent", 0)
        is_recording = device.get("recording", False)

        if storage_percent > 0:
            # Estimate hours until full based on typical recording rate
            # Assume 8 Mbps recording = ~3.6 GB/hour
            free_percent = 100 - storage_percent
            if is_recording:
                # Estimate based on typical recording rate
                hours_to_full = (free_percent / 100) * 1000 / 3.6  # Rough estimate
                if hours_to_full < hours_ahead:
                    severity = "critical" if hours_to_full < 4 else "warning"
                    predictions.append({
                        "device": host,
                        "issue": f"Storage will be full in ~{hours_to_full:.0f} hours",
                        "timeframe": f"Within {min(hours_to_full, hours_ahead):.0f} hours",
                        "severity": severity,
                        "action": "Archive or delete old recordings",
                    })
                    devices_at_risk += 1
            elif storage_percent >= 75:
                predictions.append({
                    "device": host,
                    "issue": f"Storage at {storage_percent:.0f}% - limited capacity for new recordings",
                    "timeframe": "Before next recording session",
                    "severity": "warning",
                    "action": "Free up storage space",
                })
                devices_at_risk += 1

        # Health score prediction
        health_score = device.get("health_score", 100)
        if health_score < 60:
            predictions.append({
                "device": host,
                "issue": f"Health score degraded ({health_score}/100)",
                "timeframe": f"Within {hours_ahead} hours if unaddressed",
                "severity": "warning",
                "action": "Review health issues and remediate",
            })
            if host not in [p["device"] for p in predictions[:-1]]:
                devices_at_risk += 1

    # Determine overall risk level
    critical_count = len([p for p in predictions if p["severity"] == "critical"])
    warning_count = len([p for p in predictions if p["severity"] == "warning"])

    if critical_count > 0:
        risk_level = "critical"
    elif warning_count > len(devices) * 0.3:
        risk_level = "high"
    elif warning_count > 0:
        risk_level = "medium"
    else:
        risk_level = "low"

    # Generate AI summary
    try:
        if predictions:
            prompt = f"""Summarize fleet issue predictions for an IT administrator.

Fleet: {settings.fleet_name}
Total devices: {len(devices)}
Devices at risk: {devices_at_risk}
Time horizon: {hours_ahead} hours

Predicted issues:
{_format_predictions(predictions[:5])}

Provide a 2-3 sentence executive summary focusing on:
1. Most urgent issues
2. Recommended priority actions

Keep it actionable and concise."""

            provider = get_provider()
            summary = await provider.complete(prompt, max_tokens=200)
            if hasattr(provider, "close"):
                await provider.close()
        else:
            summary = f"No issues predicted for the next {hours_ahead} hours. Fleet is operating normally."

    except LLMError as e:
        logger.warning(f"LLM summary failed: {e}")
        if predictions:
            summary = f"{devices_at_risk} device(s) have predicted issues within {hours_ahead} hours. Review predictions list for details."
        else:
            summary = f"No issues predicted for the next {hours_ahead} hours."

    return FleetIssuePredictionResult(
        success=True,
        fleet_name=settings.fleet_name,
        hours_ahead=hours_ahead,
        predictions=predictions,
        risk_level=risk_level,
        devices_at_risk=devices_at_risk,
        total_devices=len(devices),
        summary=summary,
        generated_at=datetime.now().isoformat(),
    )


def _format_predictions(predictions: list[dict[str, Any]]) -> str:
    """Format predictions for prompt."""
    if not predictions:
        return "None"
    lines = []
    for p in predictions:
        lines.append(f"- {p['device']}: {p['issue']} ({p['severity']})")
    return "\n".join(lines)


async def generate_shift_handoff(
    shift_hours: Annotated[
        int,
        Field(description="Length of the shift to summarize, in hours."),
    ] = 8,
) -> ShiftHandoffResult:
    """
    Generate end-of-shift handoff summary for AV operations teams.

    Creates a comprehensive summary of fleet activity, resolved issues,
    and items requiring attention for the next shift.

    Args:
        shift_hours: Length of shift to summarize (default 8 hours).

    Returns:
        dict containing:
            - success: bool
            - summary: AI-generated shift summary
            - activity_summary: Recording/streaming statistics
            - issues_resolved: Issues addressed during shift
            - attention_required: Items for next shift
            - fleet_status: Current fleet health snapshot
    """
    settings = get_settings()

    # Get current fleet status
    fleet_status = await get_fleet_status()

    if not fleet_status.success:
        return ShiftHandoffResult(
            success=False,
            error="Failed to get fleet status",
        )

    total_devices = fleet_status.total_devices
    online_devices = fleet_status.online_devices
    recording_devices = fleet_status.recording_devices
    avg_health = fleet_status.average_health
    alerts = fleet_status.alerts

    if total_devices == 0:
        return ShiftHandoffResult(
            success=True,
            fleet_name=settings.fleet_name,
            summary="No devices configured in fleet.",
            activity_summary={},
            issues_resolved=[],
            attention_required=[],
            fleet_status=fleet_status.model_dump(),
        )

    # Build activity summary
    activity_summary = {
        "devices_online": f"{online_devices}/{total_devices}",
        "devices_recording": recording_devices,
        "average_health": f"{avg_health:.0f}/100",
        "alerts_active": len(alerts),
    }

    # Identify items needing attention
    attention_required: list[dict[str, str]] = []
    for device in fleet_status.devices:
        host = device.get("host", "unknown")

        if not device.get("online", False):
            attention_required.append({
                "device": host,
                "issue": "Device offline",
                "priority": "high",
            })
        elif device.get("health_score", 100) < 60:
            issues = device.get("health_issues", [])
            attention_required.append({
                "device": host,
                "issue": issues[0] if issues else "Health score below threshold",
                "priority": "medium",
            })
        elif device.get("storage_percent", 0) > 85:
            attention_required.append({
                "device": host,
                "issue": f"Storage at {device.get('storage_percent', 0):.0f}%",
                "priority": "medium",
            })

    # Generate AI summary
    current_time = datetime.now()
    # Use timedelta to correctly handle midnight crossing (e.g. 2am - 8h = 6pm yesterday)
    shift_start = (current_time - timedelta(hours=shift_hours)).replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    prompt = f"""Generate a shift handoff summary for an AV operations team.

Shift Period: {shift_start.strftime('%H:%M')} to {current_time.strftime('%H:%M')}
Fleet: {settings.fleet_name}

Current Status:
- Devices online: {online_devices}/{total_devices}
- Devices recording: {recording_devices}
- Fleet health: {avg_health:.0f}/100
- Active alerts: {len(alerts)}

Items needing attention: {len(attention_required)}
{_format_attention_items(attention_required)}

Generate a professional shift handoff summary including:
1. One-line status overview
2. Key activity highlights (what went well)
3. Items requiring attention for next shift
4. Any recommendations

Keep it concise (4-5 sentences) and professional."""

    try:
        provider = get_provider()
        summary = await provider.complete(prompt, max_tokens=300)
        if hasattr(provider, "close"):
            await provider.close()

    except LLMError as e:
        logger.warning(f"LLM summary failed: {e}")
        # Fallback summary
        if attention_required:
            summary = (
                f"Shift ending with {online_devices}/{total_devices} devices online. "
                f"Fleet health at {avg_health:.0f}%. "
                f"{len(attention_required)} item(s) require attention: "
                f"{attention_required[0]['issue']} on {attention_required[0]['device']}."
            )
        else:
            summary = (
                f"Shift ending with {online_devices}/{total_devices} devices online. "
                f"Fleet health at {avg_health:.0f}%. "
                "All systems operating normally. No issues to hand off."
            )

    return ShiftHandoffResult(
        success=True,
        fleet_name=settings.fleet_name,
        shift_period=f"{shift_start.strftime('%H:%M')} - {current_time.strftime('%H:%M')}",
        summary=summary,
        activity_summary=activity_summary,
        issues_resolved=[],  # Would track in persistent state
        attention_required=attention_required,
        fleet_status={
            "online": online_devices,
            "total": total_devices,
            "recording": recording_devices,
            "health": round(avg_health),
        },
        generated_at=datetime.now().isoformat(),
    )


def _format_attention_items(items: list[dict[str, str]]) -> str:
    """Format attention items for prompt."""
    if not items:
        return "None - all systems normal"
    lines = []
    for item in items[:5]:
        lines.append(f"- {item['device']}: {item['issue']} (priority: {item['priority']})")
    return "\n".join(lines)


def register(server: FastMCP) -> None:
    """Register fleet MCP tools."""
    server.tool()(batch_start_recording)
    server.tool()(batch_stop_recording)
    server.tool()(fleet_health_report)
    server.tool()(generate_shift_handoff)
    server.tool()(get_fleet_status)
    server.tool()(predict_fleet_issues)
    server.tool()(suggest_maintenance_window)
