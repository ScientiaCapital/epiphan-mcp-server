"""AI-powered MCP tools for video analysis."""

import asyncio
import logging
from typing import Any, Literal

from epiphan_mcp.client import PearlClient
from epiphan_mcp.config import get_settings
from epiphan_mcp.llm.analyzer import VideoAnalyzer
from epiphan_mcp.llm.config import AnalysisType

logger = logging.getLogger(__name__)

# Module-level analyzer instance (lazy initialization with lock for thread safety)
_analyzer: VideoAnalyzer | None = None
_analyzer_lock = asyncio.Lock()


async def get_analyzer() -> VideoAnalyzer:
    """Get or create the video analyzer instance (thread-safe)."""
    global _analyzer
    if _analyzer is None:
        async with _analyzer_lock:
            # Double-check after acquiring lock
            if _analyzer is None:
                _analyzer = VideoAnalyzer()
    return _analyzer


async def _get_channel_preview(device_id: str, channel: str) -> bytes:
    """
    Fetch channel preview image from Pearl device.

    Args:
        device_id: Device identifier
        channel: Channel ID (e.g., "1", "2")

    Returns:
        Binary image data
    """
    settings = get_settings()
    host = settings.get_device_host(device_id)

    async with PearlClient(
        host=host,
        username=settings.username,
        password=settings.password,
        use_https=settings.use_https,
        verify_ssl=settings.verify_ssl,
        timeout=settings.timeout,
    ) as client:
        return await client.get_channel_preview(
            channel_id=channel,
            resolution="1280x720",  # Higher res for better analysis
            format="jpg",
        )


async def analyze_channel_scene(
    device_id: str = "default",
    channel: str = "1",
    analysis_type: Literal[
        "scene_description",
        "content_detection",
        "quality_check",
        "text_extraction",
        "presenter_detection",
    ] = "scene_description",
) -> dict[str, Any]:
    """
    Analyze the current scene on a Pearl channel using AI.

    Uses a vision model to understand what's currently being captured,
    enabling intelligent automation and monitoring.

    Args:
        device_id: Pearl device identifier (default: first configured device)
        channel: Channel ID to analyze (e.g., "1", "2")
        analysis_type: Type of analysis to perform:
            - scene_description: General description of the scene
            - content_detection: Classify content type and subject
            - quality_check: Technical quality assessment
            - text_extraction: OCR to extract visible text
            - presenter_detection: Detect and describe presenters

    Returns:
        dict containing:
            - success: bool
            - analysis: Analysis result text
            - analysis_type: Type of analysis performed
            - model_used: LLM model used
            - device_id: Device that was analyzed
            - channel: Channel that was analyzed
            - error: Error message if failed

    Example:
        >>> result = await analyze_channel_scene(
        ...     device_id="default",
        ...     channel="1",
        ...     analysis_type="quality_check"
        ... )
        >>> print(result["analysis"])
        "Video quality assessment: Resolution appears to be 1080p..."
    """
    try:
        # Get preview image from Pearl
        logger.info(f"Fetching preview from device={device_id}, channel={channel}")
        image_data = await _get_channel_preview(device_id, channel)

        # Map string to enum
        analysis_enum = AnalysisType(analysis_type)

        # Analyze with LLM
        analyzer = await get_analyzer()
        result = await analyzer.analyze_scene(
            image_data=image_data,
            analysis_type=analysis_enum,
        )

        return {
            "success": True,
            "analysis": result.content,
            "analysis_type": result.analysis_type.value,
            "model_used": result.model_used,
            "timestamp": result.timestamp.isoformat(),
            "image_hash": result.image_hash,
            "device_id": device_id,
            "channel": channel,
        }

    except Exception as e:
        logger.exception(f"Scene analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "device_id": device_id,
            "channel": channel,
        }


async def extract_text_from_preview(
    device_id: str = "default",
    channel: str = "1",
) -> dict[str, Any]:
    """
    Extract visible text from a Pearl channel preview using OCR.

    Uses AI vision to read text from presentations, slides, lower thirds,
    and other on-screen graphics. Useful for automated captioning,
    content indexing, and slide detection.

    Args:
        device_id: Pearl device identifier
        channel: Channel ID to analyze

    Returns:
        dict containing:
            - success: bool
            - text: Extracted text content
            - model_used: LLM model used
            - device_id: Device that was analyzed
            - channel: Channel that was analyzed
            - error: Error message if failed

    Example:
        >>> result = await extract_text_from_preview(channel="1")
        >>> print(result["text"])
        "Title: Introduction to Machine Learning..."
    """
    try:
        image_data = await _get_channel_preview(device_id, channel)

        analyzer = await get_analyzer()
        result = await analyzer.extract_text(image_data)

        return {
            "success": True,
            "text": result.content,
            "model_used": result.model_used,
            "timestamp": result.timestamp.isoformat(),
            "image_hash": result.image_hash,
            "device_id": device_id,
            "channel": channel,
        }

    except Exception as e:
        logger.exception(f"Text extraction failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "device_id": device_id,
            "channel": channel,
        }


async def detect_layout_changes(
    device_id: str = "default",
    channel: str = "1",
    sensitivity: Literal["low", "medium", "high"] = "medium",
) -> dict[str, Any]:
    """
    Detect if the channel content has changed since last check.

    Monitors a channel for significant changes like scene transitions,
    slide advances, or presenter movement. Useful for automated
    recording triggers and event logging.

    Uses efficient image hashing for quick comparisons, with optional
    AI analysis to describe the nature of changes.

    Args:
        device_id: Pearl device identifier
        channel: Channel ID to monitor
        sensitivity: Change detection sensitivity:
            - low: Only detect major scene changes
            - medium: Detect slide changes, presenter movement
            - high: Detect any visible changes

    Returns:
        dict containing:
            - success: bool
            - changed: bool indicating if change was detected
            - change_type: Type of change detected
            - message: Description of the change
            - previous_hash: Hash of previous frame
            - current_hash: Hash of current frame
            - device_id: Device that was monitored
            - channel: Channel that was monitored
            - error: Error message if failed

    Example:
        >>> # First call establishes baseline
        >>> result = await detect_layout_changes(channel="1")
        >>> print(result["changed"])  # False (first frame)

        >>> # Later call detects changes
        >>> result = await detect_layout_changes(channel="1")
        >>> if result["changed"]:
        ...     print(result["message"])  # "Slide advanced to new content"
    """
    try:
        image_data = await _get_channel_preview(device_id, channel)

        # Use device_id:channel as the cache key
        cache_key = f"{device_id}:{channel}"

        analyzer = await get_analyzer()
        result = await analyzer.detect_changes(
            channel_id=cache_key,
            image_data=image_data,
            sensitivity=sensitivity,
        )

        return {
            "success": True,
            "device_id": device_id,
            "channel": channel,
            **result,
        }

    except Exception as e:
        logger.exception(f"Change detection failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "device_id": device_id,
            "channel": channel,
        }


async def check_video_quality(
    device_id: str = "default",
    channel: str = "1",
) -> dict[str, Any]:
    """
    Check video quality on a Pearl channel.

    Analyzes the current frame for technical quality issues like
    poor lighting, focus problems, framing issues, and artifacts.
    Provides actionable feedback for production improvement.

    Args:
        device_id: Pearl device identifier
        channel: Channel ID to check

    Returns:
        dict containing:
            - success: bool
            - quality_report: Detailed quality assessment
            - model_used: LLM model used
            - device_id: Device that was analyzed
            - channel: Channel that was analyzed
            - error: Error message if failed

    Example:
        >>> result = await check_video_quality(channel="1")
        >>> print(result["quality_report"])
        "Video quality assessment:
        - Lighting: Good, even illumination
        - Focus: Sharp
        - Issues: None detected
        Overall quality: Excellent"
    """
    try:
        image_data = await _get_channel_preview(device_id, channel)

        analyzer = await get_analyzer()
        result = await analyzer.check_quality(image_data)

        return {
            "success": True,
            "quality_report": result.content,
            "model_used": result.model_used,
            "timestamp": result.timestamp.isoformat(),
            "image_hash": result.image_hash,
            "device_id": device_id,
            "channel": channel,
        }

    except Exception as e:
        logger.exception(f"Quality check failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "device_id": device_id,
            "channel": channel,
        }


async def clear_change_detection_cache(
    device_id: str | None = None,
    channel: str | None = None,
) -> dict[str, Any]:
    """
    Clear the change detection cache.

    Resets the stored frames used for change detection. Useful when
    starting a new monitoring session or after known content changes.

    Args:
        device_id: Specific device to clear (None for all)
        channel: Specific channel to clear (None for all on device)

    Returns:
        dict with success status and cleared channels
    """
    try:
        analyzer = await get_analyzer()

        if device_id and channel:
            cache_key = f"{device_id}:{channel}"
            analyzer.clear_cache(cache_key)
            cleared = [cache_key]
        elif device_id:
            # Clear all channels for this device
            # This is a simple implementation - clears everything
            analyzer.clear_cache()
            cleared = ["all"]
        else:
            analyzer.clear_cache()
            cleared = ["all"]

        return {
            "success": True,
            "cleared": cleared,
            "message": f"Change detection cache cleared for: {cleared}",
        }

    except Exception as e:
        logger.exception(f"Cache clear failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def detect_recording_issues(
    device_id: str = "default",
    channel: str = "1",
) -> dict[str, Any]:
    """
    Detect video quality issues during an active recording.

    Performs proactive monitoring by analyzing the current frame for common
    production problems. Use this during recordings to catch issues early
    before they affect the entire capture.

    Checks for:
    - Black frames (camera off, signal loss)
    - Frozen video (static image, no motion)
    - Poor lighting (too dark, overexposed)
    - Focus issues (blurry, soft image)
    - Framing problems (empty frame, cut-off subjects)

    Args:
        device_id: Pearl device identifier
        channel: Channel ID to monitor

    Returns:
        dict containing:
            - success: bool
            - issues_detected: bool - True if any problems found
            - issues: list of detected issues with severity
            - quality_score: 0-100 overall quality rating
            - recommendation: Suggested action if issues found
            - device_id: Device that was checked
            - channel: Channel that was checked

    Example:
        >>> result = await detect_recording_issues(device_id="room-201", channel="1")
        >>> if result["issues_detected"]:
        ...     print(f"Alert: {result['issues'][0]['description']}")
    """
    try:
        image_data = await _get_channel_preview(device_id, channel)

        analyzer = await get_analyzer()

        # Use quality check analysis to detect issues
        result = await analyzer.analyze_scene(
            image_data=image_data,
            analysis_type=AnalysisType.QUALITY_CHECK,
        )

        # Parse the quality report for specific issues
        issues = _parse_quality_issues(result.content)
        issues_detected = len(issues) > 0

        # Calculate quality score based on issues
        quality_score = _calculate_quality_score(issues)

        # Generate recommendation
        if quality_score >= 80:
            recommendation = "Video quality is good - no action needed"
        elif quality_score >= 60:
            recommendation = "Minor issues detected - monitor and adjust if needed"
        elif quality_score >= 40:
            recommendation = "Quality issues detected - consider pausing to fix"
        else:
            recommendation = "Significant issues detected - immediate attention required"

        return {
            "success": True,
            "issues_detected": issues_detected,
            "issues": issues,
            "quality_score": quality_score,
            "recommendation": recommendation,
            "model_used": result.model_used,
            "timestamp": result.timestamp.isoformat(),
            "device_id": device_id,
            "channel": channel,
        }

    except Exception as e:
        logger.exception(f"Recording issue detection failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "device_id": device_id,
            "channel": channel,
        }


def _parse_quality_issues(quality_report: str) -> list[dict[str, Any]]:
    """Parse quality report text to extract specific issues."""
    issues = []
    report_lower = quality_report.lower()

    # Check for common issues mentioned in the report
    issue_patterns = [
        ("black", "Black frame detected", "critical", "Check camera power and signal connection"),
        ("dark", "Poor lighting - too dark", "warning", "Increase lighting or adjust camera settings"),
        ("overexposed", "Overexposure detected", "warning", "Reduce lighting or adjust exposure"),
        ("blur", "Focus issue - image is blurry", "warning", "Check camera focus settings"),
        ("frozen", "Video appears frozen", "critical", "Check signal source and cable connections"),
        ("empty", "Frame appears empty", "warning", "Verify camera is pointed at subject"),
        ("cut off", "Subject may be cut off", "info", "Adjust camera framing"),
        ("noise", "Video noise detected", "info", "Consider improving lighting"),
    ]

    for keyword, description, severity, action in issue_patterns:
        if keyword in report_lower:
            issues.append({
                "type": keyword,
                "description": description,
                "severity": severity,
                "action": action,
            })

    return issues


def _calculate_quality_score(issues: list[dict[str, Any]]) -> int:
    """Calculate quality score based on detected issues."""
    score = 100

    severity_penalties = {
        "critical": 40,
        "warning": 15,
        "info": 5,
    }

    for issue in issues:
        severity = issue.get("severity", "info")
        penalty = severity_penalties.get(severity, 5)
        score -= penalty

    return max(0, score)
