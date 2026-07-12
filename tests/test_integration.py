"""Integration tests for real Epiphan Pearl devices.

These tests are SKIPPED by default - they require:
1. Real Pearl hardware on the network
2. PEARL_DEVICES, PEARL_USERNAME, PEARL_PASSWORD set
3. Pytest marker: pytest -m integration

Run with: pytest tests/test_integration.py -m integration -v
"""

import os

import pytest

# Skip all tests in this module unless explicitly running integration tests
pytestmark = pytest.mark.skipif(
    os.environ.get("PEARL_DEVICES") is None,
    reason="Integration tests require PEARL_DEVICES environment variable",
)


@pytest.fixture
def real_settings():
    """Get settings from environment for real device tests."""
    from epiphan_mcp.config import Settings

    return Settings(
        devices=os.environ.get("PEARL_DEVICES", ""),
        username=os.environ.get("PEARL_USERNAME", "admin"),
        password=os.environ.get("PEARL_PASSWORD", ""),
        use_https=os.environ.get("PEARL_USE_HTTPS", "false").lower() == "true",
        timeout=float(os.environ.get("PEARL_TIMEOUT", "10")),
        verify_ssl=os.environ.get("PEARL_VERIFY_SSL", "false").lower() == "true",
    )


# ============================================================
# Device Connectivity Tests
# ============================================================


class TestRealDeviceConnectivity:
    """Test basic connectivity to real Pearl devices."""

    @pytest.mark.integration
    async def test_device_status(self, real_settings):
        """Test getting status from a real device."""
        from epiphan_mcp.client import PearlClient

        host = real_settings.get_device_list()[0]
        async with PearlClient.from_settings(host, real_settings) as client:
            status = await client.get_system_status()

        assert status.storage_total_gb > 0
        assert status.storage_free_gb >= 0
        assert 0 <= status.storage_used_percent <= 100

    @pytest.mark.integration
    async def test_recorder_status(self, real_settings):
        """Test getting recorder status from a real device."""
        from epiphan_mcp.client import PearlClient

        host = real_settings.get_device_list()[0]
        async with PearlClient.from_settings(host, real_settings) as client:
            recorder = await client.get_recorder_status("recorder-1")

        assert recorder.state is not None
        assert recorder.state.value in ("stopped", "recording", "paused")


# ============================================================
# Fleet Health Tests
# ============================================================


class TestRealFleetHealth:
    """Test fleet health features against real devices."""

    @pytest.mark.integration
    async def test_fleet_status_with_health(self, real_settings, monkeypatch):
        """Test get_fleet_status returns health scores for real devices."""
        from epiphan_mcp.server import get_fleet_status

        # Patch settings to use real config
        monkeypatch.setattr("epiphan_mcp.server.get_settings", lambda: real_settings)

        result = await get_fleet_status.fn()

        assert result.success is True
        assert result.total_devices >= 1
        assert hasattr(result, "average_health")
        assert hasattr(result, "unhealthy_devices")

        # Check per-device health
        for device in result.devices:
            if device.get("online"):
                assert "health_score" in device
                assert 0 <= device["health_score"] <= 100
                assert "health_issues" in device

    @pytest.mark.integration
    async def test_fleet_health_report(self, real_settings, monkeypatch):
        """Test fleet_health_report generates AI summary for real devices."""
        from epiphan_mcp.server import fleet_health_report

        # Patch settings to use real config
        monkeypatch.setattr("epiphan_mcp.server.get_settings", lambda: real_settings)

        result = await fleet_health_report.fn()

        assert result.success is True
        assert result.summary is not None
        assert len(result.summary) > 0
        assert result.health_score is not None
        assert isinstance(result.recommendations, list)


# ============================================================
# Recording Control Tests (Destructive - Use Caution)
# ============================================================


class TestRealRecordingControl:
    """Test recording control on real devices.

    WARNING: These tests actually start/stop recordings!
    Only run when you have a test device that's safe to control.
    """

    @pytest.mark.integration
    @pytest.mark.destructive
    async def test_start_stop_recording(self, real_settings, monkeypatch):
        """Test starting and stopping recording on a real device."""
        from epiphan_mcp.server import get_recording_status, start_recording, stop_recording

        monkeypatch.setattr("epiphan_mcp.server.get_settings", lambda: real_settings)

        # Start recording
        start_result = await start_recording.fn(device_id="default", recorder=1)
        assert start_result.success is True

        # Check status
        status = await get_recording_status.fn(device_id="default", recorder=1)
        assert status.state == "recording"

        # Stop recording
        stop_result = await stop_recording.fn(device_id="default", recorder=1)
        assert stop_result.success is True


# ============================================================
# AI Analysis Tests (Requires OPENROUTER_API_KEY)
# ============================================================


@pytest.mark.skipif(
    os.environ.get("OPENROUTER_API_KEY") is None,
    reason="AI tests require OPENROUTER_API_KEY",
)
class TestRealAIAnalysis:
    """Test AI-powered analysis against real devices."""

    @pytest.mark.integration
    async def test_analyze_channel_scene(self, real_settings, monkeypatch):
        """Test AI scene analysis on a real channel."""
        from epiphan_mcp.server import analyze_channel_scene

        monkeypatch.setattr("epiphan_mcp.server.get_settings", lambda: real_settings)

        result = await analyze_channel_scene.fn(
            device_id="default",
            channel="1",
            analysis_type="scene_description",
        )

        assert result.success is True
        assert result.analysis is not None
        assert len(result.analysis) > 50  # Meaningful description

    @pytest.mark.integration
    async def test_check_video_quality(self, real_settings, monkeypatch):
        """Test AI quality check on a real channel."""
        from epiphan_mcp.server import check_video_quality

        monkeypatch.setattr("epiphan_mcp.server.get_settings", lambda: real_settings)

        result = await check_video_quality.fn(device_id="default", channel="1")

        assert result.success is True
        assert result.quality_report is not None
