"""Tests for LLM provider and video analyzer modules.

TDD approach: These tests were written BEFORE the implementation fixes.
"""

import pytest

from epiphan_mcp.llm.analyzer import (
    ANALYSIS_PROMPTS,
    AnalysisResult,
    VideoAnalyzer,
)
from epiphan_mcp.llm.config import (
    AnalysisType,
    LLMModel,
    LLMSettings,
)
from epiphan_mcp.llm.providers import (
    MockProvider,
    OpenRouterProvider,
    get_provider,
)

# ============================================================
# Config Tests
# ============================================================


class TestLLMModel:
    """Tests for LLMModel enum."""

    def test_vision_models_have_correct_format(self):
        """Vision model IDs should follow provider/model-name format."""
        vision_models = [
            LLMModel.CLAUDE_SONNET_4,
            LLMModel.GEMINI_20_FLASH,
            LLMModel.QWEN_VL_72B,
        ]
        for model in vision_models:
            assert "/" in model.value, f"{model.name} should have provider/model format"

    def test_deepseek_models_exist(self):
        """DeepSeek models should be available for cost optimization."""
        assert hasattr(LLMModel, "DEEPSEEK_V3")
        assert "deepseek" in LLMModel.DEEPSEEK_V3.value

    def test_qwen_vl_models_exist(self):
        """Qwen VL models should be available for OCR tasks."""
        assert hasattr(LLMModel, "QWEN_VL_72B")
        assert "qwen" in LLMModel.QWEN_VL_72B.value.lower()


class TestAnalysisType:
    """Tests for AnalysisType enum."""

    def test_all_analysis_types_have_prompts(self):
        """Every analysis type should have a corresponding prompt."""
        for analysis_type in AnalysisType:
            assert analysis_type in ANALYSIS_PROMPTS, (
                f"{analysis_type} missing from ANALYSIS_PROMPTS"
            )

    def test_text_extraction_type_exists(self):
        """TEXT_EXTRACTION type should exist for OCR."""
        assert AnalysisType.TEXT_EXTRACTION.value == "text_extraction"

    def test_quality_check_type_exists(self):
        """QUALITY_CHECK type should exist for video quality analysis."""
        assert AnalysisType.QUALITY_CHECK.value == "quality_check"


class TestLLMSettings:
    """Tests for LLMSettings configuration."""

    def test_default_settings_have_mock_mode_false(self):
        """Default settings should have mock_mode=False."""
        # Test the field default directly (avoids env loading)
        assert LLMSettings.model_fields["mock_mode"].default is False

    def test_settings_without_api_key_is_not_configured(self, isolated_llm_env):
        """Settings without API key should report as not configured."""
        settings = LLMSettings()  # Now safe with isolated env
        assert settings.is_configured is False

    def test_settings_with_mock_mode_is_configured(self, isolated_llm_env):
        """Settings with mock_mode should report as configured."""
        settings = LLMSettings(mock_mode=True)
        assert settings.is_configured is True

    def test_settings_with_api_key_is_configured(self, isolated_llm_env):
        """Settings with API key should report as configured."""
        settings = LLMSettings(openrouter_api_key="sk-test-key")
        assert settings.is_configured is True

    def test_ocr_model_defaults_to_qwen(self, isolated_llm_env):
        """OCR model should default to Qwen VL for best text extraction."""
        settings = LLMSettings()
        assert "qwen" in settings.ocr_model.lower()

    def test_quality_model_defaults_to_fast_model(self, isolated_llm_env):
        """Quality model should default to a fast model (Gemini Flash)."""
        settings = LLMSettings()
        assert (
            "gemini" in settings.quality_model.lower() or "flash" in settings.quality_model.lower()
        )


# ============================================================
# Provider Tests
# ============================================================


class TestMockProvider:
    """Tests for MockProvider."""

    @pytest.mark.asyncio
    async def test_analyze_image_returns_string(self):
        """Mock provider should return a string response."""
        provider = MockProvider()
        result = await provider.analyze_image(
            image_data=b"fake_image_data",
            prompt="Describe this image",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_analyze_image_responds_to_ocr_prompt(self):
        """Mock provider should return text-extraction response for OCR prompts."""
        provider = MockProvider()
        result = await provider.analyze_image(
            image_data=b"fake_image_data",
            prompt="Extract all text from this image",
        )
        assert "text" in result.lower() or "detected" in result.lower()

    @pytest.mark.asyncio
    async def test_analyze_image_responds_to_quality_prompt(self):
        """Mock provider should return quality assessment for quality prompts."""
        provider = MockProvider()
        result = await provider.analyze_image(
            image_data=b"fake_image_data",
            prompt="Assess the quality of this video frame",
        )
        assert "quality" in result.lower()

    @pytest.mark.asyncio
    async def test_complete_returns_string(self):
        """Mock provider complete() should return a string response."""
        provider = MockProvider()
        result = await provider.complete(prompt="What should I do?")
        assert isinstance(result, str)
        assert len(result) > 0


class TestOpenRouterProvider:
    """Tests for OpenRouterProvider."""

    @pytest.mark.asyncio
    async def test_raises_without_api_key_on_analyze(self, isolated_llm_env):
        """Should raise LLMAPIError when analyzing without API key."""
        from epiphan_mcp.llm.providers import LLMAPIError

        provider = OpenRouterProvider(api_key=None)

        with pytest.raises(LLMAPIError, match="API key"):
            # Need valid image data now due to validation
            jpeg_data = b"\xff\xd8\xff" + b"\x00" * 200
            await provider.analyze_image(jpeg_data, "prompt")

    def test_client_has_correct_headers(self, isolated_llm_env):
        """Client should have Authorization and required headers."""
        provider = OpenRouterProvider(api_key="sk-test-key")
        client = provider.client

        assert "Authorization" in client.headers
        assert "Bearer sk-test-key" in client.headers["Authorization"]

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self, isolated_llm_env):
        """Provider should clean up client when used as context manager."""
        async with OpenRouterProvider(api_key="sk-test") as provider:
            _ = provider.client  # Access client to create it
            assert provider._client is not None
        # After exiting, client should be closed
        assert provider._client is None


class TestImageValidation:
    """Tests for image validation."""

    def test_empty_image_raises_error(self):
        """Empty image data should raise ImageValidationError."""
        from epiphan_mcp.llm.providers import ImageValidationError, validate_image

        with pytest.raises(ImageValidationError, match="Empty"):
            validate_image(b"")

    def test_too_small_image_raises_error(self):
        """Image smaller than minimum should raise error."""
        from epiphan_mcp.llm.providers import ImageValidationError, validate_image

        with pytest.raises(ImageValidationError, match="too small"):
            validate_image(b"tiny")

    def test_valid_jpeg_returns_media_type(self):
        """Valid JPEG should return image/jpeg media type."""
        from epiphan_mcp.llm.providers import validate_image

        # JPEG magic bytes + padding
        jpeg_data = b"\xff\xd8\xff" + b"\x00" * 200
        assert validate_image(jpeg_data) == "image/jpeg"

    def test_valid_png_returns_media_type(self):
        """Valid PNG should return image/png media type."""
        from epiphan_mcp.llm.providers import validate_image

        # PNG magic bytes + padding
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
        assert validate_image(png_data) == "image/png"

    def test_unsupported_format_raises_error(self):
        """Unsupported image format should raise error."""
        from epiphan_mcp.llm.providers import ImageValidationError, validate_image

        # GIF magic bytes (not supported)
        gif_data = b"GIF89a" + b"\x00" * 200
        with pytest.raises(ImageValidationError, match="Unsupported"):
            validate_image(gif_data)


class TestLLMExceptions:
    """Tests for LLM exception hierarchy."""

    def test_llm_error_is_base_exception(self):
        """LLMError should be the base for all LLM exceptions."""
        from epiphan_mcp.llm.providers import (
            ImageValidationError,
            LLMAPIError,
            LLMConnectionError,
            LLMError,
        )

        assert issubclass(LLMConnectionError, LLMError)
        assert issubclass(LLMAPIError, LLMError)
        assert issubclass(ImageValidationError, LLMError)

    def test_api_error_has_status_code(self):
        """LLMAPIError should store status code."""
        from epiphan_mcp.llm.providers import LLMAPIError

        error = LLMAPIError("Test error", status_code=401)
        assert error.status_code == 401
        assert "Test error" in str(error)


class TestGetProvider:
    """Tests for get_provider factory function."""

    def test_returns_mock_when_mock_mode_enabled(self, isolated_llm_env):
        """Should return MockProvider when mock_mode is True."""
        settings = LLMSettings(mock_mode=True)
        provider = get_provider(settings)
        assert isinstance(provider, MockProvider)

    def test_returns_mock_when_no_api_key(self, isolated_llm_env):
        """Should return MockProvider when no API key configured."""
        settings = LLMSettings()  # No API key in isolated env
        provider = get_provider(settings)
        assert isinstance(provider, MockProvider)

    def test_returns_openrouter_when_api_key_present(self, isolated_llm_env):
        """Should return OpenRouterProvider when API key is configured."""
        settings = LLMSettings(openrouter_api_key="sk-test-key")
        provider = get_provider(settings)
        assert isinstance(provider, OpenRouterProvider)


# ============================================================
# Analyzer Tests
# ============================================================


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""

    def test_to_dict_includes_all_fields(self):
        """to_dict should include all required fields."""
        result = AnalysisResult(
            analysis_type=AnalysisType.SCENE_DESCRIPTION,
            content="Test content",
            model_used="test-model",
            image_hash="abc123",
        )
        data = result.to_dict()

        assert "analysis_type" in data
        assert "content" in data
        assert "model_used" in data
        assert "timestamp" in data
        assert "image_hash" in data

    def test_to_dict_serializes_enum_to_string(self):
        """analysis_type should be serialized as string value."""
        result = AnalysisResult(
            analysis_type=AnalysisType.TEXT_EXTRACTION,
            content="Test",
            model_used="test",
        )
        data = result.to_dict()
        assert data["analysis_type"] == "text_extraction"


class TestVideoAnalyzer:
    """Tests for VideoAnalyzer."""

    @pytest.fixture
    def mock_settings(self, isolated_llm_env):
        """Create mock settings for testing (isolated from env)."""
        return LLMSettings(mock_mode=True)

    @pytest.fixture
    def analyzer(self, mock_settings):
        """Create analyzer with mock provider."""
        return VideoAnalyzer(settings=mock_settings)

    @pytest.mark.asyncio
    async def test_analyze_scene_returns_result(self, analyzer):
        """analyze_scene should return an AnalysisResult."""
        result = await analyzer.analyze_scene(
            image_data=b"fake_image_data",
            analysis_type=AnalysisType.SCENE_DESCRIPTION,
        )
        assert isinstance(result, AnalysisResult)
        assert result.analysis_type == AnalysisType.SCENE_DESCRIPTION

    @pytest.mark.asyncio
    async def test_analyze_scene_includes_image_hash(self, analyzer):
        """analyze_scene should include image hash in result."""
        result = await analyzer.analyze_scene(
            image_data=b"fake_image_data",
        )
        assert result.image_hash is not None
        assert len(result.image_hash) > 0

    @pytest.mark.asyncio
    async def test_extract_text_uses_text_extraction_type(self, analyzer):
        """extract_text should use TEXT_EXTRACTION analysis type."""
        result = await analyzer.extract_text(image_data=b"fake_image")
        assert result.analysis_type == AnalysisType.TEXT_EXTRACTION

    @pytest.mark.asyncio
    async def test_check_quality_uses_quality_check_type(self, analyzer):
        """check_quality should use QUALITY_CHECK analysis type."""
        result = await analyzer.check_quality(image_data=b"fake_image")
        assert result.analysis_type == AnalysisType.QUALITY_CHECK

    @pytest.mark.asyncio
    async def test_detect_changes_first_call_not_changed(self, analyzer):
        """First call to detect_changes should report not changed."""
        result = await analyzer.detect_changes(
            channel_id="test-channel",
            image_data=b"fake_image",
        )
        assert result["changed"] is False
        assert result["change_type"] == "first_frame"

    @pytest.mark.asyncio
    async def test_detect_changes_same_image_not_changed(self, analyzer):
        """Same image twice should report not changed."""
        image_data = b"same_image_data"

        # First call
        await analyzer.detect_changes(
            channel_id="test-channel",
            image_data=image_data,
        )

        # Second call with same image
        result = await analyzer.detect_changes(
            channel_id="test-channel",
            image_data=image_data,
        )
        assert result["changed"] is False

    @pytest.mark.asyncio
    async def test_detect_changes_different_image_changed(self, analyzer):
        """Different image should report changed."""
        # First call
        await analyzer.detect_changes(
            channel_id="test-channel",
            image_data=b"image_one",
        )

        # Second call with different image
        result = await analyzer.detect_changes(
            channel_id="test-channel",
            image_data=b"image_two",
        )
        assert result["changed"] is True

    @pytest.mark.asyncio
    async def test_clear_cache_removes_channel(self, analyzer):
        """clear_cache should remove cached frames."""
        # Populate cache
        await analyzer.detect_changes(
            channel_id="test-channel",
            image_data=b"image_data",
        )

        # Clear cache
        analyzer.clear_cache("test-channel")

        # Next call should be "first_frame" again
        result = await analyzer.detect_changes(
            channel_id="test-channel",
            image_data=b"new_image",
        )
        assert result["change_type"] == "first_frame"

    @pytest.mark.asyncio
    async def test_hash_image_produces_consistent_hash(self, analyzer):
        """Same image should produce same hash."""
        image_data = b"test_image_content"
        hash1 = analyzer._hash_image(image_data)
        hash2 = analyzer._hash_image(image_data)
        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_hash_image_different_for_different_images(self, analyzer):
        """Different images should produce different hashes."""
        hash1 = analyzer._hash_image(b"image_one")
        hash2 = analyzer._hash_image(b"image_two")
        assert hash1 != hash2


# ============================================================
# Analysis Prompts Tests
# ============================================================


class TestAnalysisPrompts:
    """Tests for analysis prompt content."""

    def test_scene_description_prompt_asks_for_content_type(self):
        """Scene description prompt should ask about content type."""
        prompt = ANALYSIS_PROMPTS[AnalysisType.SCENE_DESCRIPTION]
        assert "content" in prompt.lower() or "type" in prompt.lower()

    def test_text_extraction_prompt_mentions_text(self):
        """Text extraction prompt should mention extracting text."""
        prompt = ANALYSIS_PROMPTS[AnalysisType.TEXT_EXTRACTION]
        assert "text" in prompt.lower()

    def test_quality_check_prompt_mentions_quality(self):
        """Quality check prompt should mention quality assessment."""
        prompt = ANALYSIS_PROMPTS[AnalysisType.QUALITY_CHECK]
        assert "quality" in prompt.lower()

    def test_presenter_detection_prompt_mentions_presenter(self):
        """Presenter detection prompt should mention presenter."""
        prompt = ANALYSIS_PROMPTS[AnalysisType.PRESENTER_DETECTION]
        assert "presenter" in prompt.lower() or "person" in prompt.lower()


# ============================================================
# OpenRouter Error Path Tests
# ============================================================


class TestOpenRouterNetworkErrors:
    """Tests for OpenRouter network error handling."""

    @pytest.fixture
    def valid_jpeg(self):
        """Valid JPEG image data for testing."""
        return b"\xff\xd8\xff" + b"\x00" * 200

    @pytest.mark.asyncio
    async def test_analyze_image_connection_error(self, isolated_llm_env, valid_jpeg, respx_mock):
        """Should raise LLMConnectionError on connection failure."""
        import httpx

        from epiphan_mcp.llm.providers import LLMConnectionError, OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        provider = OpenRouterProvider(api_key="sk-test-key")
        with pytest.raises(LLMConnectionError, match="connect"):
            await provider.analyze_image(valid_jpeg, "Describe this image")

    @pytest.mark.asyncio
    async def test_analyze_image_timeout_error(self, isolated_llm_env, valid_jpeg, respx_mock):
        """Should raise LLMConnectionError on timeout."""
        import httpx

        from epiphan_mcp.llm.providers import LLMConnectionError, OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        provider = OpenRouterProvider(api_key="sk-test-key")
        with pytest.raises(LLMConnectionError, match="Timeout"):
            await provider.analyze_image(valid_jpeg, "Describe this image")

    @pytest.mark.asyncio
    async def test_complete_connection_error(self, isolated_llm_env, respx_mock):
        """Should raise LLMConnectionError on connection failure for text completion."""
        import httpx

        from epiphan_mcp.llm.providers import LLMConnectionError, OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        provider = OpenRouterProvider(api_key="sk-test-key")
        with pytest.raises(LLMConnectionError, match="connect"):
            await provider.complete("What should I do?")

    @pytest.mark.asyncio
    async def test_complete_timeout_error(self, isolated_llm_env, respx_mock):
        """Should raise LLMConnectionError on timeout for text completion."""
        import httpx

        from epiphan_mcp.llm.providers import LLMConnectionError, OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        provider = OpenRouterProvider(api_key="sk-test-key")
        with pytest.raises(LLMConnectionError, match="Timeout"):
            await provider.complete("What should I do?")


class TestOpenRouterHTTPErrors:
    """Tests for OpenRouter HTTP status error handling."""

    @pytest.fixture
    def valid_jpeg(self):
        """Valid JPEG image data for testing."""
        return b"\xff\xd8\xff" + b"\x00" * 200

    @pytest.mark.asyncio
    async def test_analyze_image_api_error_401(self, isolated_llm_env, valid_jpeg, respx_mock):
        """Should raise LLMAPIError with status_code on 401."""
        import httpx

        from epiphan_mcp.llm.providers import LLMAPIError, OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(401, json={"error": "Invalid API key"})
        )

        provider = OpenRouterProvider(api_key="sk-invalid-key")
        with pytest.raises(LLMAPIError) as exc_info:
            await provider.analyze_image(valid_jpeg, "Describe this image")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_analyze_image_api_error_429(self, isolated_llm_env, valid_jpeg, respx_mock):
        """Should raise LLMAPIError with status_code on 429 rate limit."""
        import httpx

        from epiphan_mcp.llm.providers import LLMAPIError, OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(429, json={"error": "Rate limit exceeded"})
        )

        provider = OpenRouterProvider(api_key="sk-test-key")
        with pytest.raises(LLMAPIError) as exc_info:
            await provider.analyze_image(valid_jpeg, "Describe this image")
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_analyze_image_api_error_500(self, isolated_llm_env, valid_jpeg, respx_mock):
        """Should raise LLMAPIError with status_code on 500 server error."""
        import httpx

        from epiphan_mcp.llm.providers import LLMAPIError, OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(500, json={"error": "Internal server error"})
        )

        provider = OpenRouterProvider(api_key="sk-test-key")
        with pytest.raises(LLMAPIError) as exc_info:
            await provider.analyze_image(valid_jpeg, "Describe this image")
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_complete_api_error_401(self, isolated_llm_env, respx_mock):
        """Should raise LLMAPIError with status_code on 401 for text completion."""
        import httpx

        from epiphan_mcp.llm.providers import LLMAPIError, OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(401, json={"error": "Invalid API key"})
        )

        provider = OpenRouterProvider(api_key="sk-invalid-key")
        with pytest.raises(LLMAPIError) as exc_info:
            await provider.complete("What should I do?")
        assert exc_info.value.status_code == 401


class TestOpenRouterResponseParsing:
    """Tests for OpenRouter response parsing error handling."""

    @pytest.fixture
    def valid_jpeg(self):
        """Valid JPEG image data for testing."""
        return b"\xff\xd8\xff" + b"\x00" * 200

    @pytest.mark.asyncio
    async def test_analyze_image_missing_choices_field(
        self, isolated_llm_env, valid_jpeg, respx_mock
    ):
        """Should raise KeyError when 'choices' field is missing."""
        import httpx

        from epiphan_mcp.llm.providers import OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"id": "123", "object": "chat.completion"})
        )

        provider = OpenRouterProvider(api_key="sk-test-key")
        with pytest.raises(KeyError):
            await provider.analyze_image(valid_jpeg, "Describe this image")

    @pytest.mark.asyncio
    async def test_analyze_image_empty_choices_array(
        self, isolated_llm_env, valid_jpeg, respx_mock
    ):
        """Should raise IndexError when 'choices' array is empty."""
        import httpx

        from epiphan_mcp.llm.providers import OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": []})
        )

        provider = OpenRouterProvider(api_key="sk-test-key")
        with pytest.raises(IndexError):
            await provider.analyze_image(valid_jpeg, "Describe this image")

    @pytest.mark.asyncio
    async def test_complete_missing_choices_field(self, isolated_llm_env, respx_mock):
        """Should raise KeyError when 'choices' field is missing in text completion."""
        import httpx

        from epiphan_mcp.llm.providers import OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"id": "123"})
        )

        provider = OpenRouterProvider(api_key="sk-test-key")
        with pytest.raises(KeyError):
            await provider.complete("What should I do?")

    @pytest.mark.asyncio
    async def test_complete_empty_choices_array(self, isolated_llm_env, respx_mock):
        """Should raise IndexError when 'choices' array is empty in text completion."""
        import httpx

        from epiphan_mcp.llm.providers import OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": []})
        )

        provider = OpenRouterProvider(api_key="sk-test-key")
        with pytest.raises(IndexError):
            await provider.complete("What should I do?")


class TestOpenRouterEdgeCases:
    """Tests for OpenRouter edge cases."""

    @pytest.mark.asyncio
    async def test_complete_without_api_key(self, isolated_llm_env):
        """Should raise LLMAPIError when completing without API key."""
        from epiphan_mcp.llm.providers import LLMAPIError, OpenRouterProvider

        provider = OpenRouterProvider(api_key=None)
        with pytest.raises(LLMAPIError, match="API key"):
            await provider.complete("What should I do?")

    @pytest.mark.asyncio
    async def test_close_method_idempotent(self, isolated_llm_env):
        """Should be safe to call close() multiple times."""
        from epiphan_mcp.llm.providers import OpenRouterProvider

        provider = OpenRouterProvider(api_key="sk-test-key")
        # Access client to create it
        _ = provider.client
        assert provider._client is not None

        # Close twice - should not raise
        await provider.close()
        await provider.close()
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_error_chaining_preserved(self, isolated_llm_env, respx_mock):
        """Should preserve original exception in error chain."""
        import httpx

        from epiphan_mcp.llm.providers import LLMConnectionError, OpenRouterProvider

        respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("Original error")
        )

        provider = OpenRouterProvider(api_key="sk-test-key")
        try:
            await provider.complete("What should I do?")
        except LLMConnectionError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, httpx.ConnectError)
