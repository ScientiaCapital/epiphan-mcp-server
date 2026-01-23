"""Tests for AI-powered MCP tools.

TDD approach: These tests were written BEFORE implementation fixes.
Tests use mocked Pearl client and LLM provider.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import respx
from httpx import Response

from epiphan_mcp.tools.ai_tools import (
    analyze_channel_scene,
    extract_text_from_preview,
    detect_layout_changes,
    check_video_quality,
    clear_change_detection_cache,
    get_analyzer,
    _get_channel_preview,
)
from epiphan_mcp.llm.config import LLMSettings


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_llm_settings():
    """Create mock LLM settings with mock mode enabled (isolated from env)."""
    return LLMSettings(mock_mode=True, _env_file=None)


@pytest.fixture
def mock_preview_image():
    """Return mock JPEG image data."""
    # Minimal valid JPEG header
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 100


@pytest.fixture
def mock_pearl_settings():
    """Mock Pearl settings."""
    with patch("epiphan_mcp.tools.ai_tools.get_settings") as mock:
        settings = MagicMock()
        settings.get_device_host.return_value = "192.168.1.100"
        settings.username = "admin"
        settings.password = "password"
        settings.use_https = False
        settings.verify_ssl = False
        settings.timeout = 30.0
        mock.return_value = settings
        yield mock


@pytest.fixture
def mock_pearl_client(mock_preview_image):
    """Mock Pearl client that returns preview images."""
    with patch("epiphan_mcp.tools.ai_tools.PearlClient") as mock_class:
        mock_client = AsyncMock()
        mock_client.get_channel_preview.return_value = mock_preview_image
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_analyzer():
    """Mock video analyzer with mock provider (isolated from env)."""
    with patch("epiphan_mcp.tools.ai_tools.get_analyzer") as mock:
        from epiphan_mcp.llm.analyzer import VideoAnalyzer
        analyzer = VideoAnalyzer(settings=LLMSettings(mock_mode=True, _env_file=None))
        mock.return_value = analyzer
        yield analyzer


# ============================================================
# analyze_channel_scene Tests
# ============================================================


class TestAnalyzeChannelScene:
    """Tests for analyze_channel_scene tool."""

    @pytest.mark.asyncio
    async def test_returns_success_dict(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should return dict with success=True on successful analysis."""
        result = await analyze_channel_scene(
            device_id="default",
            channel="1",
            analysis_type="scene_description",
        )

        assert isinstance(result, dict)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_includes_analysis_content(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should include analysis text in response."""
        result = await analyze_channel_scene(
            device_id="default",
            channel="1",
            analysis_type="scene_description",
        )

        assert "analysis" in result
        assert isinstance(result["analysis"], str)
        assert len(result["analysis"]) > 0

    @pytest.mark.asyncio
    async def test_includes_device_and_channel(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should include device_id and channel in response."""
        result = await analyze_channel_scene(
            device_id="my-device",
            channel="2",
            analysis_type="scene_description",
        )

        assert result["device_id"] == "my-device"
        assert result["channel"] == "2"

    @pytest.mark.asyncio
    async def test_includes_model_used(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should include model name in response."""
        result = await analyze_channel_scene(
            device_id="default",
            channel="1",
            analysis_type="scene_description",
        )

        assert "model_used" in result

    @pytest.mark.asyncio
    async def test_handles_text_extraction_type(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should handle text_extraction analysis type."""
        result = await analyze_channel_scene(
            device_id="default",
            channel="1",
            analysis_type="text_extraction",
        )

        assert result["success"] is True
        assert result["analysis_type"] == "text_extraction"

    @pytest.mark.asyncio
    async def test_handles_quality_check_type(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should handle quality_check analysis type."""
        result = await analyze_channel_scene(
            device_id="default",
            channel="1",
            analysis_type="quality_check",
        )

        assert result["success"] is True
        assert result["analysis_type"] == "quality_check"

    @pytest.mark.asyncio
    async def test_returns_error_on_pearl_failure(self, mock_pearl_settings):
        """Should return error dict when Pearl client fails."""
        with patch("epiphan_mcp.tools.ai_tools.PearlClient") as mock_class:
            mock_client = AsyncMock()
            mock_client.get_channel_preview.side_effect = Exception("Connection failed")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_class.return_value = mock_client

            result = await analyze_channel_scene(device_id="default", channel="1")

            assert result["success"] is False
            assert "error" in result


# ============================================================
# extract_text_from_preview Tests
# ============================================================


class TestExtractTextFromPreview:
    """Tests for extract_text_from_preview tool."""

    @pytest.mark.asyncio
    async def test_returns_success_with_text(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should return success with extracted text."""
        result = await extract_text_from_preview(
            device_id="default",
            channel="1",
        )

        assert result["success"] is True
        assert "text" in result
        assert isinstance(result["text"], str)

    @pytest.mark.asyncio
    async def test_includes_device_and_channel(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should include device and channel in response."""
        result = await extract_text_from_preview(
            device_id="test-device",
            channel="3",
        )

        assert result["device_id"] == "test-device"
        assert result["channel"] == "3"


# ============================================================
# detect_layout_changes Tests
# ============================================================


class TestDetectLayoutChanges:
    """Tests for detect_layout_changes tool."""

    @pytest.mark.asyncio
    async def test_first_call_reports_not_changed(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """First call should report no change (establishing baseline)."""
        # Clear any existing cache
        await clear_change_detection_cache()

        result = await detect_layout_changes(
            device_id="default",
            channel="1",
        )

        assert result["success"] is True
        assert result["changed"] is False

    @pytest.mark.asyncio
    async def test_includes_sensitivity_response(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should accept sensitivity parameter."""
        result = await detect_layout_changes(
            device_id="default",
            channel="1",
            sensitivity="high",
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_includes_hash_info(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should include hash information in response."""
        result = await detect_layout_changes(
            device_id="default",
            channel="1",
        )

        assert "current_hash" in result


# ============================================================
# check_video_quality Tests
# ============================================================


class TestCheckVideoQuality:
    """Tests for check_video_quality tool."""

    @pytest.mark.asyncio
    async def test_returns_quality_report(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should return a quality report."""
        result = await check_video_quality(
            device_id="default",
            channel="1",
        )

        assert result["success"] is True
        assert "quality_report" in result
        assert isinstance(result["quality_report"], str)

    @pytest.mark.asyncio
    async def test_includes_model_used(
        self, mock_pearl_settings, mock_pearl_client, mock_analyzer
    ):
        """Should include model name in response."""
        result = await check_video_quality(
            device_id="default",
            channel="1",
        )

        assert "model_used" in result


# ============================================================
# clear_change_detection_cache Tests
# ============================================================


class TestClearChangeDetectionCache:
    """Tests for clear_change_detection_cache tool."""

    @pytest.mark.asyncio
    async def test_returns_success(self):
        """Should return success on cache clear."""
        result = await clear_change_detection_cache()

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_accepts_device_and_channel(self):
        """Should accept device_id and channel parameters."""
        result = await clear_change_detection_cache(
            device_id="test-device",
            channel="1",
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_includes_cleared_info(self):
        """Should include info about what was cleared."""
        result = await clear_change_detection_cache()

        assert "cleared" in result or "message" in result


# ============================================================
# Integration Tests (with mock HTTP)
# ============================================================


class TestAIToolsIntegration:
    """Integration tests using respx to mock HTTP calls."""

    @pytest.fixture
    def mock_pearl_api(self, mock_preview_image):
        """Set up mock Pearl API routes."""
        with respx.mock(assert_all_called=False) as router:
            # Mock channel preview endpoint
            router.get("http://192.168.1.100/api/v2.0/channels/1/preview").mock(
                return_value=Response(200, content=mock_preview_image)
            )
            router.get("http://192.168.1.100/api/v2.0/channels/channel-1/preview").mock(
                return_value=Response(200, content=mock_preview_image)
            )
            yield router

    @pytest.mark.asyncio
    async def test_full_analysis_flow(
        self, mock_pearl_api, mock_pearl_settings
    ):
        """Test complete flow from Pearl API to analysis result."""
        # Use mock LLM settings (isolated from env)
        with patch("epiphan_mcp.tools.ai_tools.get_analyzer") as mock_get:
            from epiphan_mcp.llm.analyzer import VideoAnalyzer
            mock_get.return_value = VideoAnalyzer(
                settings=LLMSettings(mock_mode=True, _env_file=None)
            )

            result = await analyze_channel_scene(
                device_id="default",
                channel="1",
                analysis_type="scene_description",
            )

            # Verify we got a complete response
            assert result["success"] is True
            assert "analysis" in result
            assert "model_used" in result
            assert "timestamp" in result
