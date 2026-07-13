"""Fleet intelligence tools for Epiphan Pearl devices (Sprint 3).

AI-assisted fleet analysis built on top of the core fleet tools:
maintenance-window suggestion, issue prediction, and shift handoff.
Split out of fleet.py 2026-07-13 — imports the core fleet surface
one-directionally (no cycle).
"""

import logging
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..llm.providers import LLMError
from ..models import (
    FleetIssuePredictionResult,
    MaintenanceWindowResult,
    ShiftHandoffResult,
)
from . import fleet
from .fleet import _complete_with_provider, get_fleet_status

logger = logging.getLogger(__name__)

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
    settings = fleet.get_settings()

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
        current_activity = (
            f"Moderate activity: {recording_devices}/{online_devices} devices recording"
        )
    else:
        current_activity = "Low activity: No devices currently recording"

    # Build prompt for AI reasoning
    prompt = f"""Suggest an optimal maintenance window for an AV fleet.

Current Status:
- Time: {current_time.strftime("%H:%M")} on {day_of_week}
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
        ai_response = await _complete_with_provider(prompt, max_tokens=250)

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
            reasoning = (
                "No devices are currently recording, making this an ideal time for maintenance."
            )
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
        if (
            any(
                word in line_lower for word in ["tonight", "tomorrow", "weekend", "am", "pm", "now"]
            )
            and suggested_window == "Review fleet status manually"
        ):
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
    reasoning_lines = [
        line.strip() for line in lines if len(line.strip()) > 20 and ":" not in line[:15]
    ]
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
    settings = fleet.get_settings()
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
            predictions.append(
                {
                    "device": host,
                    "issue": "Device offline",
                    "timeframe": "Now",
                    "severity": "critical",
                    "action": "Check network connectivity and power immediately",
                }
            )
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
                    predictions.append(
                        {
                            "device": host,
                            "issue": f"Storage will be full in ~{hours_to_full:.0f} hours",
                            "timeframe": f"Within {min(hours_to_full, hours_ahead):.0f} hours",
                            "severity": severity,
                            "action": "Archive or delete old recordings",
                        }
                    )
                    devices_at_risk += 1
            elif storage_percent >= 75:
                predictions.append(
                    {
                        "device": host,
                        "issue": f"Storage at {storage_percent:.0f}% - limited capacity for new recordings",
                        "timeframe": "Before next recording session",
                        "severity": "warning",
                        "action": "Free up storage space",
                    }
                )
                devices_at_risk += 1

        # Health score prediction
        health_score = device.get("health_score", 100)
        if health_score < 60:
            predictions.append(
                {
                    "device": host,
                    "issue": f"Health score degraded ({health_score}/100)",
                    "timeframe": f"Within {hours_ahead} hours if unaddressed",
                    "severity": "warning",
                    "action": "Review health issues and remediate",
                }
            )
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

            summary = await _complete_with_provider(prompt, max_tokens=200)
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
    settings = fleet.get_settings()

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
            attention_required.append(
                {
                    "device": host,
                    "issue": "Device offline",
                    "priority": "high",
                }
            )
        elif device.get("health_score", 100) < 60:
            issues = device.get("health_issues", [])
            attention_required.append(
                {
                    "device": host,
                    "issue": issues[0] if issues else "Health score below threshold",
                    "priority": "medium",
                }
            )
        elif device.get("storage_percent", 0) > 85:
            attention_required.append(
                {
                    "device": host,
                    "issue": f"Storage at {device.get('storage_percent', 0):.0f}%",
                    "priority": "medium",
                }
            )

    # Generate AI summary
    current_time = datetime.now()
    # Use timedelta to correctly handle midnight crossing (e.g. 2am - 8h = 6pm yesterday)
    shift_start = (current_time - timedelta(hours=shift_hours)).replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    prompt = f"""Generate a shift handoff summary for an AV operations team.

Shift Period: {shift_start.strftime("%H:%M")} to {current_time.strftime("%H:%M")}
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
        summary = await _complete_with_provider(prompt, max_tokens=300)

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
    """Register fleet intelligence MCP tools."""
    server.tool()(generate_shift_handoff)
    server.tool()(predict_fleet_issues)
    server.tool()(suggest_maintenance_window)
