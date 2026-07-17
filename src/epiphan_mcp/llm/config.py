"""Configuration for LLM providers."""

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMModel(str, Enum):
    """Available LLM models via OpenRouter.

    Model IDs follow OpenRouter format: provider/model-name
    See https://openrouter.ai/models for current list.

    For AV/video production use cases:
    - Scene analysis: QWEN_VL_72B or GEMINI_25_FLASH (best vision)
    - OCR/text extraction: QWEN_VL_72B (multilingual, strong OCR)
    - Quality checks: GEMINI_20_FLASH (fast, cost-effective)
    - Reasoning: DEEPSEEK_V3 or CLAUDE_SONNET_4 (complex decisions)
    """

    # ==========================================================================
    # VISION MODELS (VLMs) - For video frame analysis
    # ==========================================================================

    # Anthropic Claude - Premium quality, best reasoning with images
    CLAUDE_SONNET_4 = "anthropic/claude-sonnet-4"
    CLAUDE_SONNET_35 = "anthropic/claude-3.5-sonnet"
    CLAUDE_HAIKU_35 = "anthropic/claude-3.5-haiku"  # Fast, cheap vision

    # Google Gemini - Fast, good for streaming analysis
    GEMINI_25_FLASH = "google/gemini-2.5-flash-preview"  # Best balance
    GEMINI_20_FLASH = "google/gemini-2.0-flash-001"  # Stable, proven

    # Qwen VL (Alibaba) - Best Chinese VLM, excellent OCR
    QWEN_VL_72B = "qwen/qwen2.5-vl-72b-instruct"  # Top-tier vision
    QWEN_VL_7B = "qwen/qwen2-vl-7b-instruct"  # Lightweight, fast
    QWEN3_VL = "qwen/qwen3-vl-32b"  # Latest, agentic features

    # DeepSeek Vision - Emerging, cost-effective
    DEEPSEEK_VL = "deepseek/deepseek-vl-7b-chat"  # Scientific reasoning
    DEEPSEEK_JANUS = "deepseek/janus-pro-7b"  # Multimodal generation

    # ==========================================================================
    # TEXT MODELS - For reasoning, no image input
    # ==========================================================================

    # DeepSeek - Cost leader (~70% cheaper than Claude)
    DEEPSEEK_V3 = "deepseek/deepseek-chat-v3-0324"  # Best value
    DEEPSEEK_R1 = "deepseek/deepseek-r1"  # Deep reasoning

    # Google Gemini - Long context
    GEMINI_25_PRO = "google/gemini-2.5-pro-preview"  # 1M context

    # Qwen Text - Strong multilingual
    QWEN3_MAX = "qwen/qwen3-max"  # 100+ languages


class AnalysisType(str, Enum):
    """Types of video analysis."""

    SCENE_DESCRIPTION = "scene_description"
    CONTENT_DETECTION = "content_detection"
    QUALITY_CHECK = "quality_check"
    TEXT_EXTRACTION = "text_extraction"
    PRESENTER_DETECTION = "presenter_detection"


class LLMSettings(BaseSettings):
    """LLM provider settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,  # Allow both field name and alias in constructor
    )

    # Provider selection
    llm_provider: str = Field(
        default="openrouter",
        validation_alias="LLM_PROVIDER",
        description="Which LLM backend to use: 'openrouter' (cloud), 'ollama' (local), "
        "or 'mock'. Ollama needs no API key.",
    )

    # OpenRouter configuration
    # Use validation_alias for env var names (allows constructor args to work)
    openrouter_api_key: str | None = Field(
        default=None,
        validation_alias="OPENROUTER_API_KEY",
        description="OpenRouter API key for multi-model access",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias="OPENROUTER_BASE_URL",
        description="OpenRouter API base URL",
    )

    # Ollama configuration (local models — no API key required)
    ollama_base_url: str = Field(
        default="http://localhost:11434/v1",
        validation_alias="OLLAMA_BASE_URL",
        description="Ollama OpenAI-compatible base URL (local models)",
    )

    # Model selection - defaults optimized for AV production
    default_vision_model: str = Field(
        default=LLMModel.GEMINI_20_FLASH.value,
        validation_alias="LLM_VISION_MODEL",
        description="Default model for vision tasks (scene analysis, OCR)",
    )
    default_text_model: str = Field(
        default=LLMModel.DEEPSEEK_V3.value,
        validation_alias="LLM_TEXT_MODEL",
        description="Default model for text-only tasks (reasoning, decisions)",
    )
    ocr_model: str = Field(
        default=LLMModel.QWEN_VL_72B.value,
        validation_alias="LLM_OCR_MODEL",
        description="Model for text extraction (OCR) - Qwen excels here",
    )
    quality_model: str = Field(
        default=LLMModel.GEMINI_20_FLASH.value,
        validation_alias="LLM_QUALITY_MODEL",
        description="Model for quick quality checks (fast, cheap)",
    )

    # Cost controls
    max_tokens_per_request: int = Field(
        default=1000,
        validation_alias="LLM_MAX_TOKENS",
        description="Maximum tokens per LLM request",
    )
    max_requests_per_minute: int = Field(
        default=20,
        validation_alias="LLM_RATE_LIMIT",
        description="Maximum requests per minute",
    )

    # Feature flags
    mock_mode: bool = Field(
        default=False,
        validation_alias="LLM_MOCK_MODE",
        description="Use mock responses instead of real API calls",
    )

    @property
    def is_configured(self) -> bool:
        """Check if LLM is properly configured."""
        return (
            self.openrouter_api_key is not None
            or self.mock_mode
            or self.llm_provider == "ollama"
        )


@lru_cache
def get_llm_settings() -> LLMSettings:
    """Get cached LLM settings instance."""
    return LLMSettings()
