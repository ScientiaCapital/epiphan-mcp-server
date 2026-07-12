"""Tests for Epiphan Cloud MCP tool functions.

Tests cover:
- Configuration validation (missing/present env vars)
- All 12 tool functions (success paths and error cases)
- Input validation (missing required parameters)
"""

import os
from unittest.mock import patch

import pytest
import respx
from httpx import Response

from epiphan_mcp.tools.cloud import (
    cloud_apply_preset,
    cloud_batch_command,
    cloud_delete_device,
    cloud_get_device,
    cloud_get_preview,
    cloud_get_settings,
    cloud_get_user,
    cloud_list_devices,
    cloud_pair_device,
    cloud_rename_device,
    cloud_run_command,
    cloud_unpair_device,
)

MOCK_TOKEN = "test-token-abc"
MOCK_HOST = "go.epiphan.cloud"
BASE_URL = f"https://{MOCK_HOST}/front/api/v2"


# ============================================================================
# Configuration Validation Tests
# ============================================================================


class TestCloudConfigValidation:
    """Tests for cloud configuration validation."""

    @pytest.mark.asyncio
    async def test_missing_token_returns_error(self):
        """Missing EPIPHAN_CLOUD_TOKEN returns error dict."""
        with patch.dict(os.environ, {}, clear=True):
            result = await cloud_list_devices()
            assert "error" in result
            assert "EPIPHAN_CLOUD_TOKEN" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_token_all_tools(self):
        """All tools return error when token is missing."""
        with patch.dict(os.environ, {}, clear=True):
            result = await cloud_get_user()
            assert "error" in result

            result = await cloud_get_device(device_id="d1")
            assert "error" in result

            result = await cloud_pair_device(pairing_code="ABC", name="Test")
            assert "error" in result

            result = await cloud_run_command(device_id="d1", command="recording.start")
            assert "error" in result


# ============================================================================
# cloud_get_user Tests
# ============================================================================


class TestCloudGetUser:
    """Tests for cloud_get_user tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_user_success(self):
        respx.get(f"{BASE_URL}/users/me").mock(
            return_value=Response(200, json={"id": "u1", "email": "test@test.com"})
        )
        result = await cloud_get_user()
        assert result["user"]["id"] == "u1"
        assert result["user"]["email"] == "test@test.com"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_user_auth_error(self):
        respx.get(f"{BASE_URL}/users/me").mock(
            return_value=Response(401, json={"error": "unauthorized"})
        )
        result = await cloud_get_user()
        assert "error" in result
        assert "Authentication" in result["error"]


# ============================================================================
# cloud_list_devices Tests
# ============================================================================


class TestCloudListDevices:
    """Tests for cloud_list_devices tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_devices_success(self):
        respx.get(f"{BASE_URL}/devices").mock(
            return_value=Response(200, json=[{"id": "d1", "name": "Pearl-1", "status": "online"}])
        )
        result = await cloud_list_devices()
        assert result["count"] == 1
        assert result["devices"][0]["id"] == "d1"

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_devices_empty(self):
        respx.get(f"{BASE_URL}/devices").mock(return_value=Response(200, json=[]))
        result = await cloud_list_devices()
        assert result["count"] == 0
        assert result["devices"] == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_devices_api_error(self):
        respx.get(f"{BASE_URL}/devices").mock(
            return_value=Response(500, json={"error": "internal"})
        )
        result = await cloud_list_devices()
        assert "error" in result


# ============================================================================
# cloud_get_device Tests
# ============================================================================


class TestCloudGetDevice:
    """Tests for cloud_get_device tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_device_success(self):
        respx.get(f"{BASE_URL}/devices/d1").mock(
            return_value=Response(200, json={"id": "d1", "name": "Pearl-1", "status": "online"})
        )
        result = await cloud_get_device(device_id="d1")
        assert result["device"]["name"] == "Pearl-1"

    @pytest.mark.asyncio
    async def test_get_device_missing_id(self):
        result = await cloud_get_device(device_id="")
        assert "error" in result
        assert "device_id" in result["error"]


# ============================================================================
# cloud_pair_device Tests
# ============================================================================


class TestCloudPairDevice:
    """Tests for cloud_pair_device tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_pair_device_success(self):
        respx.post(f"{BASE_URL}/devices/pair").mock(
            return_value=Response(200, json={"id": "d-new", "name": "New Pearl"})
        )
        result = await cloud_pair_device(pairing_code="ABC123", name="New Pearl")
        assert result["device"]["id"] == "d-new"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_pair_device_missing_code(self):
        result = await cloud_pair_device(pairing_code="", name="Test")
        assert "error" in result
        assert "pairing_code" in result["error"]

    @pytest.mark.asyncio
    async def test_pair_device_missing_name(self):
        result = await cloud_pair_device(pairing_code="ABC", name="")
        assert "error" in result
        assert "name" in result["error"]


# ============================================================================
# cloud_unpair_device Tests
# ============================================================================


class TestCloudUnpairDevice:
    """Tests for cloud_unpair_device tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_unpair_device_success(self):
        respx.post(f"{BASE_URL}/devices/d1/unpair").mock(return_value=Response(200, json={}))
        result = await cloud_unpair_device(device_id="d1")
        assert "message" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_unpair_device_missing_id(self):
        result = await cloud_unpair_device(device_id="")
        assert "error" in result


# ============================================================================
# cloud_delete_device Tests
# ============================================================================


class TestCloudDeleteDevice:
    """Tests for cloud_delete_device tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_delete_device_success(self):
        respx.delete(f"{BASE_URL}/devices/d1").mock(return_value=Response(200, json={}))
        result = await cloud_delete_device(device_id="d1")
        assert "message" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_device_missing_id(self):
        result = await cloud_delete_device(device_id="")
        assert "error" in result


# ============================================================================
# cloud_rename_device Tests
# ============================================================================


class TestCloudRenameDevice:
    """Tests for cloud_rename_device tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_rename_device_success(self):
        respx.post(f"{BASE_URL}/devices/d1/rename").mock(return_value=Response(200, json={}))
        result = await cloud_rename_device(device_id="d1", new_name="Pearl Room 2")
        assert "message" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_rename_device_missing_id(self):
        result = await cloud_rename_device(device_id="", new_name="Test")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_rename_device_missing_name(self):
        result = await cloud_rename_device(device_id="d1", new_name="")
        assert "error" in result


# ============================================================================
# cloud_run_command Tests
# ============================================================================


class TestCloudRunCommand:
    """Tests for cloud_run_command tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_run_command_success(self):
        respx.post(f"{BASE_URL}/devices/d1/task").mock(
            return_value=Response(200, json={"status": "ok"})
        )
        result = await cloud_run_command(device_id="d1", command="recording.start")
        assert result["result"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_run_command_missing_id(self):
        result = await cloud_run_command(device_id="", command="recording.start")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_run_command_missing_command(self):
        result = await cloud_run_command(device_id="d1", command="")
        assert "error" in result


# ============================================================================
# cloud_batch_command Tests
# ============================================================================


class TestCloudBatchCommand:
    """Tests for cloud_batch_command tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_batch_command_success(self):
        respx.post(f"{BASE_URL}/devices/batch_task").mock(
            return_value=Response(200, json={"status": "ok", "results": []})
        )
        result = await cloud_batch_command(device_ids="d1,d2", command="recording.start")
        assert result["result"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_batch_command_missing_ids(self):
        result = await cloud_batch_command(device_ids="", command="recording.start")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_batch_command_missing_command(self):
        result = await cloud_batch_command(device_ids="d1,d2", command="")
        assert "error" in result


# ============================================================================
# cloud_get_settings Tests
# ============================================================================


class TestCloudGetSettings:
    """Tests for cloud_get_settings tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_settings_success(self):
        settings_data = {"video": {"codec": "h264"}, "audio": {"codec": "aac"}}
        respx.get(f"{BASE_URL}/devices/d1/settings").mock(
            return_value=Response(200, json=settings_data)
        )
        result = await cloud_get_settings(device_id="d1")
        assert "video" in result["settings"]

    @pytest.mark.asyncio
    async def test_get_settings_missing_id(self):
        result = await cloud_get_settings(device_id="")
        assert "error" in result


# ============================================================================
# cloud_get_preview Tests
# ============================================================================


class TestCloudGetPreview:
    """Tests for cloud_get_preview tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_preview_success(self):
        respx.get(f"{BASE_URL}/devices/d1/preview").mock(
            return_value=Response(
                200,
                content=b"\xff\xd8\xff\xe0",
                headers={"content-type": "image/jpeg"},
            )
        )
        result = await cloud_get_preview(device_id="d1")
        assert "image_base64" in result
        assert result["content_type"] == "image/jpeg"

    @pytest.mark.asyncio
    async def test_get_preview_missing_id(self):
        result = await cloud_get_preview(device_id="")
        assert "error" in result


# ============================================================================
# cloud_apply_preset Tests
# ============================================================================


class TestCloudApplyPreset:
    """Tests for cloud_apply_preset tool function."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        with patch.dict(os.environ, {"EPIPHAN_CLOUD_TOKEN": MOCK_TOKEN}):
            yield

    @respx.mock
    @pytest.mark.asyncio
    async def test_apply_cloud_preset_success(self):
        respx.put(f"{BASE_URL}/devices/d1/presets/cloud").mock(
            return_value=Response(200, json={"status": "ok"})
        )
        result = await cloud_apply_preset(
            device_id="d1", preset_name="HD Recording", preset_type="cloud"
        )
        assert "error" not in result
        assert "message" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_apply_local_preset_success(self):
        respx.put(f"{BASE_URL}/devices/d1/presets/local").mock(
            return_value=Response(200, json={"status": "ok"})
        )
        result = await cloud_apply_preset(
            device_id="d1", preset_name="Custom Layout", preset_type="local"
        )
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_apply_preset_missing_id(self):
        result = await cloud_apply_preset(device_id="", preset_name="Test", preset_type="cloud")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_apply_preset_missing_name(self):
        result = await cloud_apply_preset(device_id="d1", preset_name="", preset_type="cloud")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_apply_preset_invalid_type(self):
        result = await cloud_apply_preset(device_id="d1", preset_name="Test", preset_type="invalid")
        assert "error" in result
