"""LLM provider implementations for video analysis."""

import base64
import logging
from abc import ABC, abstractmethod
from types import TracebackType

import httpx

from epiphan_mcp.llm.config import LLMSettings, get_llm_settings

logger = logging.getLogger(__name__)

# Minimum valid image sizes (magic bytes)
MIN_JPEG_SIZE = 107  # Minimum valid JPEG
MIN_PNG_SIZE = 67  # Minimum valid PNG


class LLMError(Exception):
    """Base exception for LLM provider errors."""

    pass


class LLMConnectionError(LLMError):
    """Error connecting to LLM provider."""

    pass


class LLMAPIError(LLMError):
    """Error from LLM provider API."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ImageValidationError(LLMError):
    """Invalid image data provided."""

    pass


def validate_image(image_data: bytes) -> str:
    """
    Validate image data and return media type.

    Args:
        image_data: Binary image data

    Returns:
        Media type string (image/jpeg or image/png)

    Raises:
        ImageValidationError: If image data is invalid
    """
    if not image_data:
        raise ImageValidationError("Empty image data provided")

    if len(image_data) < MIN_PNG_SIZE:
        raise ImageValidationError(
            f"Image data too small ({len(image_data)} bytes). Minimum is {MIN_PNG_SIZE} bytes."
        )

    # Check magic bytes
    if image_data[:3] == b"\xff\xd8\xff":
        if len(image_data) < MIN_JPEG_SIZE:
            raise ImageValidationError(f"JPEG image too small ({len(image_data)} bytes)")
        return "image/jpeg"
    elif image_data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    else:
        raise ImageValidationError("Unsupported image format. Expected JPEG or PNG.")


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 1000,
    ) -> str:
        """
        Analyze an image with a vision model.

        Args:
            image_data: Binary image data (JPEG/PNG)
            prompt: Analysis prompt
            model: Model to use (provider-specific)
            max_tokens: Maximum response tokens

        Returns:
            Model's text response
        """
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 1000,
    ) -> str:
        """
        Text completion without images.

        Args:
            prompt: Text prompt
            model: Model to use
            max_tokens: Maximum response tokens

        Returns:
            Model's text response
        """
        pass


class _OpenAICompatibleProvider(LLMProvider):
    """
    Shared base for providers speaking the OpenAI Chat Completions API.

    Both OpenRouter (cloud) and Ollama (local) expose an OpenAI-compatible
    ``/chat/completions`` endpoint with the same request/response shape, so the
    request building, error mapping, and response parsing live here. Subclasses
    provide the base URL / headers (``_build_client``), a display name for error
    messages (``provider_name``), and any readiness check (``_preflight``).
    """

    provider_name: str = "LLM"

    def __init__(self, settings: LLMSettings | None = None):
        self._settings = settings or get_llm_settings()
        self._client: httpx.AsyncClient | None = None

    def _build_client(self) -> httpx.AsyncClient:
        """Construct the HTTP client (base URL + headers). Subclass overrides."""
        raise NotImplementedError

    def _preflight(self) -> None:
        """Raise if the provider is not ready to make a request. Optional override."""
        return None

    async def __aenter__(self) -> "_OpenAICompatibleProvider":
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager, ensuring client cleanup."""
        await self.close()

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = self._build_client()
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _post_chat(self, payload: dict[str, object]) -> str:
        """POST a chat-completions payload and return the message content."""
        try:
            response = await self.client.post("/chat/completions", json=payload)
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Failed to connect to {self.provider_name}: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise LLMConnectionError(
                f"Timeout connecting to {self.provider_name}: {e}"
            ) from e

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise LLMAPIError(
                f"{self.provider_name} API error: {e.response.text}",
                status_code=e.response.status_code,
            ) from e

        data = response.json()
        content: str = data["choices"][0]["message"]["content"]
        return content

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 1000,
    ) -> str:
        """
        Analyze image using a vision model via the OpenAI-compatible endpoint.

        Raises:
            ImageValidationError: If image data is invalid
            LLMConnectionError: If connection to the provider fails
            LLMAPIError: If the provider returns an error response
        """
        self._preflight()

        # Validate image and get media type
        media_type = validate_image(image_data)

        model = model or self._settings.default_vision_model
        max_tokens = min(max_tokens, self._settings.max_tokens_per_request)

        # Encode image as base64 data URL
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        logger.debug(f"Analyzing image with model {model}")

        return await self._post_chat(
            {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_b64}",
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            }
        )

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 1000,
    ) -> str:
        """
        Text completion via the OpenAI-compatible endpoint.

        Raises:
            LLMConnectionError: If connection to the provider fails
            LLMAPIError: If the provider returns an error response
        """
        self._preflight()

        model = model or self._settings.default_text_model
        max_tokens = min(max_tokens, self._settings.max_tokens_per_request)

        logger.debug(f"Text completion with model {model}")

        return await self._post_chat(
            {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            }
        )


class OpenRouterProvider(_OpenAICompatibleProvider):
    """
    OpenRouter API provider for multi-model access.

    OpenRouter provides a unified API to access 300+ models from different
    providers (Anthropic, Google, DeepSeek, etc.) with a single API key.

    Can be used as an async context manager for automatic resource cleanup:

        async with OpenRouterProvider() as provider:
            result = await provider.analyze_image(...)
    """

    provider_name = "OpenRouter"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        settings: LLMSettings | None = None,
    ):
        """
        Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key (or from settings)
            base_url: API base URL (or from settings)
            settings: LLM settings instance
        """
        super().__init__(settings)
        self._api_key = api_key or self._settings.openrouter_api_key
        self._base_url = base_url or self._settings.openrouter_base_url

    def _preflight(self) -> None:
        if not self._api_key:
            raise LLMAPIError(
                "OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable."
            )

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "HTTP-Referer": "https://github.com/ScientiaCapital/epiphan-mcp-server",
                "X-Title": "Epiphan Pearl MCP Server",
            },
            timeout=60.0,
        )


class OllamaProvider(_OpenAICompatibleProvider):
    """
    Ollama provider for local models (no API key, nothing leaves the machine).

    Ollama exposes an OpenAI-compatible endpoint at ``/v1/chat/completions``, so
    this reuses the shared request/response handling. The model must be pulled
    locally (e.g. ``ollama pull qwen2.5vl:7b`` for vision, ``qwen2.5:14b`` for
    text) and named via the ``LLM_*_MODEL`` env vars using Ollama tags.

        async with OllamaProvider() as provider:
            result = await provider.analyze_image(...)
    """

    provider_name = "Ollama"

    def __init__(
        self,
        base_url: str | None = None,
        settings: LLMSettings | None = None,
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama OpenAI-compatible base URL (or from settings)
            settings: LLM settings instance
        """
        super().__init__(settings)
        self._base_url = base_url or self._settings.ollama_base_url

    def _build_client(self) -> httpx.AsyncClient:
        # Ollama ignores auth; no OpenRouter-style headers needed.
        return httpx.AsyncClient(base_url=self._base_url, timeout=60.0)


class MockProvider(LLMProvider):
    """
    Mock provider for testing without API calls.

    Returns realistic-looking responses for development and testing.
    """

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 1000,
    ) -> str:
        """Return mock image analysis."""
        image_size = len(image_data)
        logger.debug(f"Mock analyzing image ({image_size} bytes)")

        # Generate contextual mock responses based on prompt keywords
        prompt_lower = prompt.lower()

        if "text" in prompt_lower or "ocr" in prompt_lower:
            return (
                "Detected text in image:\n"
                "- Title: 'Introduction to Machine Learning'\n"
                "- Subtitle: 'Chapter 3: Neural Networks'\n"
                "- Footer: 'Page 42 of 120'\n"
                "Confidence: High"
            )
        elif "presenter" in prompt_lower or "person" in prompt_lower:
            return (
                "Scene analysis:\n"
                "- 1 person detected (presenter)\n"
                "- Position: Center-right of frame\n"
                "- Facing: Camera (frontal view)\n"
                "- Activity: Speaking/presenting\n"
                "- Background: Presentation slides visible"
            )
        elif "quality" in prompt_lower:
            return (
                "Video quality assessment:\n"
                "- Resolution: Appears to be 1080p\n"
                "- Lighting: Good, even illumination\n"
                "- Focus: Sharp\n"
                "- Audio sync: N/A (image only)\n"
                "- Issues: None detected\n"
                "Overall quality: Excellent"
            )
        else:
            return (
                "Scene description:\n"
                "The image shows a professional presentation setup. "
                "A presenter is visible on the right side of the frame, "
                "standing in front of a screen displaying slides. "
                "The room appears to be a lecture hall or conference room "
                "with good lighting conditions. The presentation content "
                "appears to be educational or technical in nature."
            )

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 1000,
    ) -> str:
        """Return mock text completion."""
        logger.debug("Mock text completion")
        return (
            "Based on my analysis of the video production context, "
            "I recommend the following actions:\n"
            "1. Continue recording with current settings\n"
            "2. Monitor audio levels for consistency\n"
            "3. Consider switching to presenter-focused layout"
        )


def get_provider(settings: LLMSettings | None = None) -> LLMProvider:
    """
    Get appropriate LLM provider based on configuration.

    Selection order:
      1. ``LLM_MOCK_MODE=true`` -> MockProvider (no network).
      2. ``LLM_PROVIDER=ollama`` -> OllamaProvider (local, no API key).
      3. OpenRouter if an API key is set; otherwise MockProvider fallback.

    Args:
        settings: Optional settings override

    Returns:
        Configured LLM provider instance
    """
    settings = settings or get_llm_settings()

    if settings.mock_mode:
        logger.info("Using mock LLM provider (LLM_MOCK_MODE=true)")
        return MockProvider()

    if settings.llm_provider == "ollama":
        logger.info("Using Ollama LLM provider (local models)")
        return OllamaProvider(settings=settings)

    if settings.llm_provider not in ("openrouter", "mock"):
        logger.warning(
            f"Unknown LLM_PROVIDER={settings.llm_provider!r} — expected "
            "'openrouter', 'ollama', or 'mock'. Falling back to OpenRouter/mock."
        )

    if not settings.openrouter_api_key:
        logger.warning(
            "No OPENROUTER_API_KEY configured, using mock provider. "
            "Set OPENROUTER_API_KEY for real AI analysis, or LLM_PROVIDER=ollama "
            "for local models."
        )
        return MockProvider()

    logger.info("Using OpenRouter LLM provider")
    return OpenRouterProvider(settings=settings)
