"""Pytest configuration and shared fixtures.

Uses respx for HTTP mocking with httpx async client.
"""

from contextlib import contextmanager
from unittest.mock import patch

import pytest
import respx
from httpx import Response

from epiphan_mcp.client import PearlClient
from epiphan_mcp.config import Settings
from epiphan_mcp.tools.fleet import _reset_fleet_semaphore

# ============================================================
# Fleet Semaphore Isolation
# ============================================================


@pytest.fixture(autouse=True)
def _reset_semaphore_between_tests():
    """Reset the fleet semaphore before each test to prevent state leakage."""
    _reset_fleet_semaphore()
    yield
    _reset_fleet_semaphore()


# ============================================================
# Settings Patch Helper
# ============================================================


@contextmanager
def patch_settings(settings: Settings):
    """
    Context manager that patches get_settings in all tool modules.

    Since tool implementations are now in separate modules, we need to
    patch get_settings at each location where it's imported.

    Args:
        settings: The Settings instance to use for the test.

    Yields:
        Control to the test code.
    """
    # Modules that actually call get_settings()
    patch_locations = [
        "epiphan_mcp.tools.device.get_settings",  # get_client(), list_devices()
        "epiphan_mcp.tools.fleet.get_settings",  # Fleet operations
        "epiphan_mcp.tools.ai_tools.get_settings",  # AI tools
    ]

    patches = [patch(loc, return_value=settings) for loc in patch_locations]

    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()


# ============================================================
# Environment Isolation for LLM Tests
# ============================================================


@pytest.fixture
def isolated_llm_env(monkeypatch):
    """
    Isolate LLM settings from environment variables.

    Use this fixture when testing LLM config to ensure tests don't
    pick up real API keys from the environment.
    """
    # Remove any LLM-related env vars
    env_vars_to_clear = [
        "OPENROUTER_API_KEY",
        "LLM_MOCK_MODE",
        "LLM_VISION_MODEL",
        "LLM_TEXT_MODEL",
        "LLM_OCR_MODEL",
        "LLM_QUALITY_MODEL",
        "LLM_MAX_TOKENS",
        "LLM_RATE_LIMIT",
    ]
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)

    # Also clear the lru_cache on get_llm_settings
    from epiphan_mcp.llm.config import get_llm_settings

    get_llm_settings.cache_clear()

    yield

    # Clear cache again after test
    get_llm_settings.cache_clear()


from .fixtures.responses import (
    ARCHIVE_FILES_RESPONSE,
    CHANNELS_RESPONSE,
    CONTROL_SUCCESS_RESPONSE,
    DEVICE_RESPONSE,
    INPUTS_RESPONSE,
    LAYOUTS_RESPONSE,
    PUBLISHER_STATUS_STOPPED,
    PUBLISHER_STATUS_STREAMING,
    PUBLISHERS_RESPONSE,
    RECORDER_STATUS_RECORDING,
    RECORDER_STATUS_STOPPED,
    RECORDERS_RESPONSE,
    STORAGE_RESPONSE,
)

# ============================================================
# Configuration Fixtures
# ============================================================


@pytest.fixture
def mock_pearl_host() -> str:
    """Return a mock Pearl host for testing."""
    return "192.168.1.100"


@pytest.fixture
def mock_pearl_host_secondary() -> str:
    """Return a secondary mock Pearl host for fleet testing."""
    return "192.168.1.101"


@pytest.fixture
def test_settings(mock_pearl_host: str, mock_pearl_host_secondary: str) -> Settings:
    """Create test settings with mock devices."""
    return Settings(
        devices=f"{mock_pearl_host},{mock_pearl_host_secondary}",
        username="admin",
        password="testpass",
        use_https=False,
        timeout=5.0,
        verify_ssl=False,
        fleet_name="test-fleet",
    )


@pytest.fixture
def single_device_settings(mock_pearl_host: str) -> Settings:
    """Create test settings with a single device."""
    return Settings(
        devices=mock_pearl_host,
        username="admin",
        password="testpass",
        use_https=False,
        timeout=5.0,
        verify_ssl=False,
        fleet_name="single-device",
    )


@pytest.fixture
def empty_settings() -> Settings:
    """Create test settings with no devices configured."""
    return Settings(
        devices="",
        username="admin",
        password="testpass",
        fleet_name="empty-fleet",
    )


# ============================================================
# Client Fixtures
# ============================================================


@pytest.fixture
def pearl_client(mock_pearl_host: str) -> PearlClient:
    """Create a PearlClient instance for testing.

    Note: max_retries=0 disables retry logic for faster unit tests.
    """
    return PearlClient(
        host=mock_pearl_host,
        username="admin",
        password="testpass",
        use_https=False,
        timeout=5.0,
        verify_ssl=False,
        max_retries=0,  # Disable retries for unit tests
    )


@pytest.fixture
def pearl_client_from_settings(mock_pearl_host: str, test_settings: Settings) -> PearlClient:
    """Create a PearlClient from settings."""
    return PearlClient.from_settings(mock_pearl_host, test_settings)


# ============================================================
# Mock Router Fixtures
# ============================================================


@pytest.fixture
def mock_api_base(mock_pearl_host: str) -> str:
    """Return the mock API base URL."""
    return f"http://{mock_pearl_host}/api/v2.0"


@pytest.fixture
def respx_mock():
    """
    Provide a respx mock router that allows unmatched requests to pass through.

    Most tests should use this fixture and add specific route mocks.
    """
    with respx.mock(assert_all_called=False) as router:
        yield router


# ============================================================
# Pre-configured Mock Responses
# ============================================================


@pytest.fixture
def mock_device_routes(respx_mock, mock_api_base: str):
    """Set up mock routes for device/system endpoints."""
    respx_mock.get(f"{mock_api_base}/device").mock(return_value=Response(200, json=DEVICE_RESPONSE))
    respx_mock.get(f"{mock_api_base}/storages").mock(
        return_value=Response(200, json=STORAGE_RESPONSE)
    )
    return respx_mock


@pytest.fixture
def mock_recorder_routes(respx_mock, mock_api_base: str):
    """Set up mock routes for recorder endpoints."""
    respx_mock.get(f"{mock_api_base}/recorders").mock(
        return_value=Response(200, json=RECORDERS_RESPONSE)
    )
    respx_mock.get(f"{mock_api_base}/recorders/status").mock(
        return_value=Response(200, json={"status": "ok", "result": RECORDERS_RESPONSE["result"]})
    )
    # Individual recorder routes
    respx_mock.get(f"{mock_api_base}/recorders/recorder-1/status").mock(
        return_value=Response(200, json=RECORDER_STATUS_STOPPED)
    )
    respx_mock.get(f"{mock_api_base}/recorders/1/status").mock(
        return_value=Response(200, json=RECORDER_STATUS_STOPPED)
    )
    respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/start").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    respx_mock.post(f"{mock_api_base}/recorders/1/control/start").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    respx_mock.post(f"{mock_api_base}/recorders/recorder-1/control/stop").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    respx_mock.post(f"{mock_api_base}/recorders/1/control/stop").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    # Archive files
    respx_mock.get(f"{mock_api_base}/recorders/recorder-1/archive/files").mock(
        return_value=Response(200, json=ARCHIVE_FILES_RESPONSE)
    )
    # Batch control
    respx_mock.post(f"{mock_api_base}/recorders/control/start").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    respx_mock.post(f"{mock_api_base}/recorders/control/stop").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    return respx_mock


@pytest.fixture
def mock_channel_routes(respx_mock, mock_api_base: str):
    """Set up mock routes for channel endpoints."""
    respx_mock.get(f"{mock_api_base}/channels").mock(
        return_value=Response(200, json=CHANNELS_RESPONSE)
    )
    # Layout switching
    respx_mock.put(f"{mock_api_base}/channels/channel-1/layouts/active").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    respx_mock.put(f"{mock_api_base}/channels/1/layouts/active").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    # Bookmarks
    respx_mock.post(f"{mock_api_base}/channels/channel-1/bookmarks").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    # Layouts
    respx_mock.get(f"{mock_api_base}/channels/channel-1/layouts").mock(
        return_value=Response(200, json=LAYOUTS_RESPONSE)
    )
    return respx_mock


@pytest.fixture
def mock_publisher_routes(respx_mock, mock_api_base: str):
    """Set up mock routes for publisher/streaming endpoints."""
    respx_mock.get(f"{mock_api_base}/channels/channel-1/publishers").mock(
        return_value=Response(200, json=PUBLISHERS_RESPONSE)
    )
    respx_mock.get(f"{mock_api_base}/channels/1/publishers").mock(
        return_value=Response(200, json=PUBLISHERS_RESPONSE)
    )
    # Publisher status
    respx_mock.get(f"{mock_api_base}/channels/channel-1/publishers/publisher-1/status").mock(
        return_value=Response(200, json=PUBLISHER_STATUS_STREAMING)
    )
    # Start/stop all publishers
    respx_mock.post(f"{mock_api_base}/channels/channel-1/publishers/control/start").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    respx_mock.post(f"{mock_api_base}/channels/1/publishers/control/start").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    respx_mock.post(f"{mock_api_base}/channels/channel-1/publishers/control/stop").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    respx_mock.post(f"{mock_api_base}/channels/1/publishers/control/stop").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    # Individual publisher control
    respx_mock.post(
        f"{mock_api_base}/channels/channel-1/publishers/publisher-1/control/start"
    ).mock(return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE))
    respx_mock.post(f"{mock_api_base}/channels/channel-1/publishers/publisher-1/control/stop").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    return respx_mock


@pytest.fixture
def mock_input_routes(respx_mock, mock_api_base: str):
    """Set up mock routes for input endpoints."""
    respx_mock.get(f"{mock_api_base}/inputs").mock(return_value=Response(200, json=INPUTS_RESPONSE))
    return respx_mock


@pytest.fixture
def mock_system_routes(respx_mock, mock_api_base: str):
    """Set up mock routes for system control endpoints."""
    respx_mock.post(f"{mock_api_base}/system/control/reboot").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    respx_mock.post(f"{mock_api_base}/system/control/shutdown").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    return respx_mock


@pytest.fixture
def mock_singletouch_routes(respx_mock, mock_api_base: str):
    """Set up mock routes for single touch control."""
    respx_mock.post(f"{mock_api_base}/singletouch/control/start").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    respx_mock.post(f"{mock_api_base}/singletouch/control/stop").mock(
        return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
    )
    return respx_mock


@pytest.fixture
def mock_all_routes(
    mock_device_routes,
    mock_recorder_routes,
    mock_channel_routes,
    mock_publisher_routes,
    mock_input_routes,
    mock_system_routes,
    mock_singletouch_routes,
):
    """Set up all mock routes for comprehensive testing."""
    return mock_device_routes


# ============================================================
# Mock Response Data Fixtures
# ============================================================


@pytest.fixture
def mock_device_response() -> dict:
    """Return mock device response."""
    return DEVICE_RESPONSE


@pytest.fixture
def mock_storage_response() -> dict:
    """Return mock storage response."""
    return STORAGE_RESPONSE


@pytest.fixture
def mock_recorder_status_stopped() -> dict:
    """Return mock recorder status (stopped)."""
    return RECORDER_STATUS_STOPPED


@pytest.fixture
def mock_recorder_status_recording() -> dict:
    """Return mock recorder status (recording)."""
    return RECORDER_STATUS_RECORDING


@pytest.fixture
def mock_publisher_status_stopped() -> dict:
    """Return mock publisher status (stopped)."""
    return PUBLISHER_STATUS_STOPPED


@pytest.fixture
def mock_publisher_status_streaming() -> dict:
    """Return mock publisher status (streaming)."""
    return PUBLISHER_STATUS_STREAMING
