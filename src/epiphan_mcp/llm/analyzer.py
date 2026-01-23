"""Video frame analysis using LLM vision models."""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime

from epiphan_mcp.llm.config import AnalysisType, LLMSettings, get_llm_settings
from epiphan_mcp.llm.providers import LLMProvider, get_provider

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of a video frame analysis."""

    analysis_type: AnalysisType
    content: str
    model_used: str
    timestamp: datetime = field(default_factory=datetime.now)
    image_hash: str | None = None
    confidence: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary for JSON serialization."""
        return {
            "analysis_type": self.analysis_type.value,
            "content": self.content,
            "model_used": self.model_used,
            "timestamp": self.timestamp.isoformat(),
            "image_hash": self.image_hash,
            "confidence": self.confidence,
        }


# Analysis prompts for different types
ANALYSIS_PROMPTS = {
    AnalysisType.SCENE_DESCRIPTION: """Analyze this video frame from a live video production.
Describe:
1. What type of content is shown (presentation, lecture, interview, etc.)
2. Key visual elements (presenters, slides, graphics)
3. Composition and framing
4. Any notable details

Be concise and factual.""",
    AnalysisType.CONTENT_DETECTION: """Analyze this video frame for content classification.
Identify:
1. Content type (educational, corporate, entertainment, etc.)
2. Subject matter if identifiable
3. Audience type this appears targeted at
4. Any branding or logos visible

Keep response brief and structured.""",
    AnalysisType.QUALITY_CHECK: """Assess the technical quality of this video frame.
Check for:
1. Image clarity and focus
2. Lighting conditions (over/underexposed areas)
3. Framing issues (headroom, rule of thirds)
4. Any visible artifacts or problems
5. Overall production quality rating (Poor/Fair/Good/Excellent)

Provide actionable feedback.""",
    AnalysisType.TEXT_EXTRACTION: """Extract all visible text from this video frame.
Include:
1. Main titles or headings
2. Body text or bullet points
3. Lower thirds or name graphics
4. Any watermarks or logos with text
5. Screen content if showing presentation/document

Format as a structured list. Note if text is partially visible or unclear.""",
    AnalysisType.PRESENTER_DETECTION: """Analyze presenter presence in this video frame.
Identify:
1. Number of people visible
2. Position in frame (left, center, right)
3. Whether they appear to be speaking
4. Presenter vs audience members
5. Eye contact with camera

Note any concerns for production (framing, visibility).""",
}


class VideoAnalyzer:
    """
    Analyzes video frames using LLM vision models.

    Provides high-level analysis functions for video production use cases.
    Supports multiple analysis types and change detection.
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        settings: LLMSettings | None = None,
    ):
        """
        Initialize video analyzer.

        Args:
            provider: LLM provider instance (auto-created if None)
            settings: LLM settings (uses defaults if None)
        """
        self._settings = settings or get_llm_settings()
        self._provider = provider or get_provider(self._settings)

        # Cache for change detection
        self._last_frames: dict[str, tuple[str, bytes]] = {}

    @staticmethod
    def _hash_image(image_data: bytes) -> str:
        """Generate hash for image data."""
        return hashlib.sha256(image_data).hexdigest()[:16]

    async def analyze_scene(
        self,
        image_data: bytes,
        analysis_type: AnalysisType = AnalysisType.SCENE_DESCRIPTION,
        custom_prompt: str | None = None,
    ) -> AnalysisResult:
        """
        Analyze a video frame.

        Args:
            image_data: Binary image data (JPEG/PNG)
            analysis_type: Type of analysis to perform
            custom_prompt: Override default prompt for this analysis type

        Returns:
            AnalysisResult with analysis content
        """
        prompt = custom_prompt or ANALYSIS_PROMPTS.get(
            analysis_type,
            ANALYSIS_PROMPTS[AnalysisType.SCENE_DESCRIPTION],
        )

        image_hash = self._hash_image(image_data)

        # Select optimal model based on analysis type
        if analysis_type == AnalysisType.TEXT_EXTRACTION:
            model = self._settings.ocr_model  # Qwen excels at OCR
        elif analysis_type == AnalysisType.QUALITY_CHECK:
            model = self._settings.quality_model  # Fast, cheap
        else:
            model = self._settings.default_vision_model

        logger.info(f"Analyzing frame (hash={image_hash}) with {analysis_type.value} using {model}")

        content = await self._provider.analyze_image(
            image_data=image_data,
            prompt=prompt,
            model=model,
        )

        return AnalysisResult(
            analysis_type=analysis_type,
            content=content,
            model_used=model,
            image_hash=image_hash,
        )

    async def extract_text(self, image_data: bytes) -> AnalysisResult:
        """
        Extract text from video frame (OCR).

        Args:
            image_data: Binary image data

        Returns:
            AnalysisResult with extracted text
        """
        return await self.analyze_scene(
            image_data=image_data,
            analysis_type=AnalysisType.TEXT_EXTRACTION,
        )

    async def check_quality(self, image_data: bytes) -> AnalysisResult:
        """
        Check video frame quality.

        Args:
            image_data: Binary image data

        Returns:
            AnalysisResult with quality assessment
        """
        return await self.analyze_scene(
            image_data=image_data,
            analysis_type=AnalysisType.QUALITY_CHECK,
        )

    async def detect_presenter(self, image_data: bytes) -> AnalysisResult:
        """
        Detect presenter in video frame.

        Args:
            image_data: Binary image data

        Returns:
            AnalysisResult with presenter detection info
        """
        return await self.analyze_scene(
            image_data=image_data,
            analysis_type=AnalysisType.PRESENTER_DETECTION,
        )

    async def detect_changes(
        self,
        channel_id: str,
        image_data: bytes,
        sensitivity: str = "medium",
    ) -> dict[str, str | bool | None]:
        """
        Detect if video content has changed significantly.

        Uses image hashing for quick comparison, with optional LLM analysis
        for semantic change detection.

        Args:
            channel_id: Channel identifier for tracking
            image_data: Current frame data
            sensitivity: "low", "medium", or "high"
                - low: Only detect major scene changes
                - medium: Detect slide changes, presenter movement
                - high: Detect any visible changes

        Returns:
            dict with:
                - changed: bool indicating if change detected
                - change_type: Description of change (if any)
                - previous_hash: Hash of previous frame
                - current_hash: Hash of current frame
        """
        current_hash = self._hash_image(image_data)

        # Check if we have a previous frame for this channel
        previous = self._last_frames.get(channel_id)

        if previous is None:
            # First frame for this channel
            self._last_frames[channel_id] = (current_hash, image_data)
            return {
                "changed": False,
                "change_type": "first_frame",
                "previous_hash": None,
                "current_hash": current_hash,
                "message": "First frame captured for this channel",
            }

        previous_hash, previous_data = previous

        # Quick hash comparison
        if current_hash == previous_hash:
            return {
                "changed": False,
                "change_type": "none",
                "previous_hash": previous_hash,
                "current_hash": current_hash,
                "message": "No change detected (identical frames)",
            }

        # Hash differs - frames are different
        # For medium/high sensitivity, use LLM to describe the change
        change_description = "Frame content changed"

        if sensitivity in ("medium", "high"):
            # Ask LLM to describe the change
            prompt = """Compare these observations about two video frames from the same channel.

The frame content has changed. Based on a video production context, describe:
1. What type of change likely occurred (scene change, slide advance, presenter movement, etc.)
2. How significant is this change for production purposes
3. Any recommended actions

Be concise."""

            try:
                change_description = await self._provider.analyze_image(
                    image_data=image_data,
                    prompt=prompt,
                )
            except Exception as e:
                logger.warning(f"LLM change analysis failed: {e}")
                change_description = "Frame changed (LLM analysis unavailable)"

        # Update cached frame
        self._last_frames[channel_id] = (current_hash, image_data)

        return {
            "changed": True,
            "change_type": "content_change",
            "previous_hash": previous_hash,
            "current_hash": current_hash,
            "message": change_description,
        }

    def clear_cache(self, channel_id: str | None = None) -> None:
        """
        Clear cached frames.

        Args:
            channel_id: Specific channel to clear, or None for all
        """
        if channel_id:
            self._last_frames.pop(channel_id, None)
        else:
            self._last_frames.clear()

    async def close(self) -> None:
        """Clean up resources."""
        if hasattr(self._provider, "close"):
            await self._provider.close()
