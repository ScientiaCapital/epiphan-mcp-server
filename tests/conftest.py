"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def mock_pearl_host() -> str:
    """Return a mock Pearl host for testing."""
    return "192.168.1.100"


@pytest.fixture
def mock_pearl_response() -> dict:
    """Return a mock Pearl API response."""
    return {
        "rec_enabled": "on",
        "publish_type": "0",
        "framesize": "1920x1080",
    }
