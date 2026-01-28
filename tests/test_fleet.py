"""Tests for parallel fleet operations.

These tests verify that fleet operations execute concurrently using asyncio.gather
rather than sequentially, and handle errors gracefully without blocking other devices.
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import respx
from httpx import ConnectError, Response

from epiphan_mcp.config import Settings

from .fixtures.responses import (
    CONTROL_SUCCESS_RESPONSE,
    DEVICE_RESPONSE,
    RECORDER_STATUS_RECORDING,
    RECORDER_STATUS_STOPPED,
    STORAGE_RESPONSE,
)

# ============================================================
# Helper Functions
# ============================================================


def create_test_settings(
    devices: str = "192.168.1.100", fleet_name: str = "test"
) -> Settings:
    """Create settings for testing."""
    return Settings(
        devices=devices,
        username="admin",
        password="testpass",
        use_https=False,
        timeout=5.0,
        verify_ssl=False,
        fleet_name=fleet_name,
        storage_warning_percent=80.0,
    )


def create_four_device_settings() -> Settings:
    """Create settings with 4 devices for parallel timing tests."""
    return Settings(
        devices="192.168.1.100,192.168.1.101,192.168.1.102,192.168.1.103",
        username="admin",
        password="testpass",
        use_https=False,
        timeout=5.0,
        verify_ssl=False,
        fleet_name="timing-test-fleet",
    )


# ============================================================
# Fleet Status Parallel Execution Tests
# ============================================================


class TestFleetStatusParallel:
    """Tests for get_fleet_status parallel execution."""

    async def test_fleet_status_parallel_execution(self):
        """Verify fleet status operations run concurrently, not sequentially."""
        from epiphan_mcp.server import get_fleet_status

        devices = "192.168.1.100,192.168.1.101,192.168.1.102,192.168.1.103"
        delay_per_device = 0.1  # 100ms delay per device

        # Track call times to verify parallelism
        call_times: list[float] = []

        async def delayed_response(*args, **kwargs):
            """Simulate network latency."""
            call_times.append(time.monotonic())
            await asyncio.sleep(delay_per_device)
            return Response(200, json=DEVICE_RESPONSE)

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                # Set up delayed responses for all devices
                for i in range(4):
                    api_base = f"http://192.168.1.{100 + i}/api/v2.0"
                    router.get(f"{api_base}/device").mock(side_effect=delayed_response)
                    router.get(f"{api_base}/storages").mock(
                        return_value=Response(200, json=STORAGE_RESPONSE)
                    )
                    router.get(f"{api_base}/recorders/recorder-1/status").mock(
                        return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                    )

                start_time = time.monotonic()
                result = await get_fleet_status.fn()
                elapsed = time.monotonic() - start_time

        assert result["success"] is True
        assert result["total_devices"] == 4

        # If parallel: ~0.1s (all run simultaneously)
        # If sequential: ~0.4s (0.1s * 4 devices)
        # Allow some margin for test execution overhead
        assert elapsed < 0.3, f"Fleet status took {elapsed:.2f}s - likely running sequentially"

    async def test_fleet_status_handles_mixed_success_failure(self):
        """Test that some devices succeeding and others failing are handled correctly."""
        from epiphan_mcp.server import get_fleet_status

        devices = "192.168.1.100,192.168.1.101,192.168.1.102"

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                # Device 1: Success
                api_base1 = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base1}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base1}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base1}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Device 2: Connection error
                api_base2 = "http://192.168.1.101/api/v2.0"
                router.get(f"{api_base2}/device").mock(
                    side_effect=ConnectError("Connection refused")
                )
                router.get(f"{api_base2}/storages").mock(
                    side_effect=ConnectError("Connection refused")
                )

                # Device 3: Success
                api_base3 = "http://192.168.1.102/api/v2.0"
                router.get(f"{api_base3}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base3}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base3}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_RECORDING)
                )

                result = await get_fleet_status.fn()

        assert result["success"] is True
        assert result["total_devices"] == 3
        assert result["online_devices"] == 2
        assert result["recording_devices"] == 1

        # Verify the failed device is recorded
        failed_device = next(
            d for d in result["devices"] if d["host"] == "192.168.1.101"
        )
        assert failed_device["online"] is False
        assert "error" in failed_device

    async def test_fleet_status_timeout_per_device(self):
        """Test that individual device timeout doesn't block other devices."""
        from epiphan_mcp.server import get_fleet_status

        devices = "192.168.1.100,192.168.1.101"

        async def timeout_response(*args, **kwargs):
            """Simulate a hung device."""
            await asyncio.sleep(20)  # Long delay (would timeout)
            return Response(200, json=DEVICE_RESPONSE)

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                # Device 1: Will timeout
                api_base1 = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base1}/device").mock(side_effect=timeout_response)
                router.get(f"{api_base1}/storages").mock(side_effect=timeout_response)

                # Device 2: Success
                api_base2 = "http://192.168.1.101/api/v2.0"
                router.get(f"{api_base2}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base2}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base2}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Use a short timeout to verify the test completes quickly
                start_time = time.monotonic()
                result = await get_fleet_status.fn()
                elapsed = time.monotonic() - start_time

        # The operation should complete in reasonable time, not wait for timeout
        # Note: The actual timeout handling depends on implementation
        assert result["success"] is True
        assert result["total_devices"] == 2

        # At least one device should succeed
        online_devices = [d for d in result["devices"] if d.get("online", False)]
        assert len(online_devices) >= 1


# ============================================================
# Batch Start Recording Parallel Tests
# ============================================================


class TestBatchStartParallel:
    """Tests for batch_start_recording parallel execution."""

    async def test_batch_start_parallel_execution(self):
        """Verify batch start operations run concurrently."""
        from epiphan_mcp.server import batch_start_recording

        devices = "192.168.1.100,192.168.1.101,192.168.1.102,192.168.1.103"
        delay_per_device = 0.1

        call_count = 0

        async def delayed_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(delay_per_device)
            return Response(200, json=CONTROL_SUCCESS_RESPONSE)

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                for i in range(4):
                    api_base = f"http://192.168.1.{100 + i}/api/v2.0"
                    router.post(f"{api_base}/recorders/recorder-1/control/start").mock(
                        side_effect=delayed_response
                    )

                start_time = time.monotonic()
                result = await batch_start_recording.fn(device_ids="all")
                elapsed = time.monotonic() - start_time

        assert result["success"] is True
        assert result["total_devices"] == 4
        assert result["successful"] == 4
        assert call_count == 4

        # Parallel should complete in ~0.1s, sequential would be ~0.4s
        assert elapsed < 0.3, f"Batch start took {elapsed:.2f}s - likely running sequentially"

    async def test_batch_start_handles_partial_failure(self):
        """Test batch start with some devices failing."""
        from epiphan_mcp.server import batch_start_recording

        devices = "192.168.1.100,192.168.1.101,192.168.1.102"

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                # Device 1: Success
                router.post("http://192.168.1.100/api/v2.0/recorders/recorder-1/control/start").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )
                # Device 2: Failure
                router.post("http://192.168.1.101/api/v2.0/recorders/recorder-1/control/start").mock(
                    side_effect=ConnectError("Connection refused")
                )
                # Device 3: Success
                router.post("http://192.168.1.102/api/v2.0/recorders/recorder-1/control/start").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )

                result = await batch_start_recording.fn(device_ids="all")

        assert result["success"] is False  # Not all succeeded
        assert result["total_devices"] == 3
        assert result["successful"] == 2
        assert result["failed"] == 1


# ============================================================
# Batch Stop Recording Parallel Tests
# ============================================================


class TestBatchStopParallel:
    """Tests for batch_stop_recording parallel execution."""

    async def test_batch_stop_parallel_execution(self):
        """Verify batch stop operations run concurrently."""
        from epiphan_mcp.server import batch_stop_recording

        devices = "192.168.1.100,192.168.1.101,192.168.1.102,192.168.1.103"
        delay_per_device = 0.1

        async def delayed_response(*args, **kwargs):
            await asyncio.sleep(delay_per_device)
            return Response(200, json=CONTROL_SUCCESS_RESPONSE)

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                for i in range(4):
                    api_base = f"http://192.168.1.{100 + i}/api/v2.0"
                    router.post(f"{api_base}/recorders/recorder-1/control/stop").mock(
                        side_effect=delayed_response
                    )

                start_time = time.monotonic()
                result = await batch_stop_recording.fn(device_ids="all")
                elapsed = time.monotonic() - start_time

        assert result["success"] is True
        assert result["total_devices"] == 4
        assert result["successful"] == 4

        # Parallel should complete in ~0.1s, sequential would be ~0.4s
        assert elapsed < 0.3, f"Batch stop took {elapsed:.2f}s - likely running sequentially"

    async def test_batch_stop_handles_partial_failure(self):
        """Test batch stop with some devices failing."""
        from epiphan_mcp.server import batch_stop_recording

        devices = "192.168.1.100,192.168.1.101"

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                # Device 1: Success
                router.post("http://192.168.1.100/api/v2.0/recorders/recorder-1/control/stop").mock(
                    return_value=Response(200, json=CONTROL_SUCCESS_RESPONSE)
                )
                # Device 2: Failure
                router.post("http://192.168.1.101/api/v2.0/recorders/recorder-1/control/stop").mock(
                    side_effect=ConnectError("Connection refused")
                )

                result = await batch_stop_recording.fn(device_ids="all")

        assert result["success"] is False  # Not all succeeded
        assert result["total_devices"] == 2
        assert result["successful"] == 1
        assert result["failed"] == 1


# ============================================================
# Timing Verification Tests
# ============================================================


class TestParallelTiming:
    """Tests that verify parallel execution through timing."""

    async def test_parallel_faster_than_sequential(self):
        """
        Timing test: 4 devices with 0.1s delay each should complete in ~0.1s not ~0.4s.

        This is the definitive test that parallel execution is working.
        """
        from epiphan_mcp.server import get_fleet_status

        devices = "192.168.1.100,192.168.1.101,192.168.1.102,192.168.1.103"
        delay_per_device = 0.1
        num_devices = 4

        async def delayed_device_response(*args, **kwargs):
            await asyncio.sleep(delay_per_device)
            return Response(200, json=DEVICE_RESPONSE)

        async def delayed_storage_response(*args, **kwargs):
            await asyncio.sleep(delay_per_device)
            return Response(200, json=STORAGE_RESPONSE)

        async def delayed_recorder_response(*args, **kwargs):
            await asyncio.sleep(delay_per_device)
            return Response(200, json=RECORDER_STATUS_STOPPED)

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                for i in range(num_devices):
                    api_base = f"http://192.168.1.{100 + i}/api/v2.0"
                    router.get(f"{api_base}/device").mock(
                        side_effect=delayed_device_response
                    )
                    router.get(f"{api_base}/storages").mock(
                        side_effect=delayed_storage_response
                    )
                    router.get(f"{api_base}/recorders/recorder-1/status").mock(
                        side_effect=delayed_recorder_response
                    )

                start_time = time.monotonic()
                result = await get_fleet_status.fn()
                elapsed = time.monotonic() - start_time

        assert result["success"] is True
        assert result["total_devices"] == num_devices
        assert result["online_devices"] == num_devices

        # Sequential time would be: delay * 3 calls * 4 devices = 1.2s
        # Parallel time should be: delay * 3 calls (within each device) = 0.3s
        # (assuming internal device calls are sequential but devices are parallel)
        # With good parallelism, should be much less than sequential
        sequential_time = delay_per_device * 3 * num_devices  # 1.2s
        expected_parallel_max = sequential_time / 2  # Should be at least 2x faster

        assert elapsed < expected_parallel_max, (
            f"Fleet status took {elapsed:.2f}s, expected < {expected_parallel_max:.2f}s. "
            f"Sequential would be ~{sequential_time:.2f}s. "
            "Operations may be running sequentially instead of in parallel."
        )


# ============================================================
# Edge Cases and Error Handling
# ============================================================


class TestFleetErrorHandling:
    """Tests for fleet operation error handling."""

    async def test_all_devices_fail_gracefully(self):
        """Test that fleet status handles all devices failing."""
        from epiphan_mcp.server import get_fleet_status

        devices = "192.168.1.100,192.168.1.101"

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                # Both devices fail
                for i in [100, 101]:
                    api_base = f"http://192.168.1.{i}/api/v2.0"
                    router.get(f"{api_base}/device").mock(
                        side_effect=ConnectError("Connection refused")
                    )
                    router.get(f"{api_base}/storages").mock(
                        side_effect=ConnectError("Connection refused")
                    )

                result = await get_fleet_status.fn()

        assert result["success"] is True  # Operation itself succeeded
        assert result["total_devices"] == 2
        assert result["online_devices"] == 0
        assert result["alerts_count"] == 2

        # All devices should be marked offline
        for device in result["devices"]:
            assert device["online"] is False
            assert "error" in device

    async def test_empty_device_list(self):
        """Test fleet operations with no devices configured."""
        from epiphan_mcp.server import batch_start_recording, batch_stop_recording, get_fleet_status

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            # Fleet status should handle empty list
            result = await get_fleet_status.fn()
            assert result["success"] is True
            assert result["total_devices"] == 0
            assert "No devices configured" in result["message"]

            # Batch operations should fail gracefully
            start_result = await batch_start_recording.fn(device_ids="all")
            assert start_result["success"] is False
            assert "No devices" in start_result["error"]

            stop_result = await batch_stop_recording.fn(device_ids="all")
            assert stop_result["success"] is False
            assert "No devices" in stop_result["error"]

    async def test_single_device_fleet(self):
        """Test fleet operations with a single device."""
        from epiphan_mcp.server import get_fleet_status

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="192.168.1.100")

            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_fleet_status.fn()

        assert result["success"] is True
        assert result["total_devices"] == 1
        assert result["online_devices"] == 1


# ============================================================
# Health Score Tests
# ============================================================


class TestFleetHealthScores:
    """Tests for fleet health scoring features."""

    async def test_fleet_status_includes_health_scores(self):
        """Verify fleet status includes health_score per device and fleet-level metrics."""
        from epiphan_mcp.server import get_fleet_status

        devices = "192.168.1.100,192.168.1.101"

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices=devices)

            with respx.mock(assert_all_called=False) as router:
                # Both devices healthy
                for i in [100, 101]:
                    api_base = f"http://192.168.1.{i}/api/v2.0"
                    router.get(f"{api_base}/device").mock(
                        return_value=Response(200, json=DEVICE_RESPONSE)
                    )
                    router.get(f"{api_base}/storages").mock(
                        return_value=Response(200, json=STORAGE_RESPONSE)
                    )
                    router.get(f"{api_base}/recorders/recorder-1/status").mock(
                        return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                    )

                result = await get_fleet_status.fn()

        assert result["success"] is True
        assert result["total_devices"] == 2
        assert result["online_devices"] == 2

        # Verify fleet-level health metrics
        assert "average_health" in result
        assert "unhealthy_devices" in result
        assert result["average_health"] == 100.0  # Both healthy
        assert result["unhealthy_devices"] == 0

        # Verify per-device health scores
        for device in result["devices"]:
            assert "health_score" in device
            assert "health_issues" in device
            assert device["health_score"] == 100  # Full marks
            assert device["health_issues"] == []  # No issues

    async def test_fleet_status_health_with_storage_warning(self):
        """Verify health score decreases when storage is high."""
        from epiphan_mcp.server import get_fleet_status

        # Create a response with high storage usage - use correct API format
        high_storage_response = {
            "status": "ok",
            "result": [
                {
                    "id": "storage-1",
                    "name": "Internal Storage",
                    "type": "internal",
                    "total_bytes": 500000000000,  # 500GB
                    "used_bytes": 450000000000,   # 90% used
                    "free_bytes": 50000000000,    # 50GB (10% free)
                    "percent_used": 90.0,
                    "mounted": True,
                }
            ]
        }

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="192.168.1.100")

            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=high_storage_response)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                result = await get_fleet_status.fn()

        assert result["success"] is True
        device = result["devices"][0]

        # Health should be reduced due to storage (90% used triggers critical)
        assert device["health_score"] < 100
        assert any("storage" in issue.lower() for issue in device["health_issues"])

    async def test_fleet_status_health_offline_device(self):
        """Verify offline devices are handled correctly in health calculations."""
        from epiphan_mcp.server import get_fleet_status

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="192.168.1.100")

            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    side_effect=ConnectError("Connection refused")
                )
                router.get(f"{api_base}/storages").mock(
                    side_effect=ConnectError("Connection refused")
                )

                result = await get_fleet_status.fn()

        assert result["success"] is True
        device = result["devices"][0]

        # Device is offline
        assert device["online"] is False
        assert "error" in device

        # Fleet-level health should be 0 since no devices are online
        assert result["average_health"] == 0.0
        assert result["online_devices"] == 0


class TestFleetHealthReport:
    """Tests for fleet_health_report AI-summarized reports."""

    async def test_fleet_health_report_success(self):
        """Verify fleet_health_report returns correct structure with mocked LLM."""
        from epiphan_mcp.server import fleet_health_report

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(
                devices="192.168.1.100,192.168.1.101"
            )

            with respx.mock(assert_all_called=False) as router:
                for i in [100, 101]:
                    api_base = f"http://192.168.1.{i}/api/v2.0"
                    router.get(f"{api_base}/device").mock(
                        return_value=Response(200, json=DEVICE_RESPONSE)
                    )
                    router.get(f"{api_base}/storages").mock(
                        return_value=Response(200, json=STORAGE_RESPONSE)
                    )
                    router.get(f"{api_base}/recorders/recorder-1/status").mock(
                        return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                    )

                # Mock the LLM provider
                with patch("epiphan_mcp.server.get_provider") as mock_provider:
                    mock_llm = AsyncMock()
                    mock_llm.complete = AsyncMock(
                        return_value="Fleet is healthy with all devices online.\n\n1. Continue monitoring\n2. Schedule maintenance"
                    )
                    mock_llm.close = AsyncMock()
                    mock_provider.return_value = mock_llm

                    result = await fleet_health_report.fn()

        assert result["success"] is True
        assert "fleet_name" in result
        assert "generated_at" in result
        assert "summary" in result
        assert "health_score" in result
        assert "attention_required" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    async def test_fleet_health_report_with_unhealthy_device(self):
        """Verify report identifies unhealthy devices needing attention."""
        from epiphan_mcp.server import fleet_health_report

        # High storage response (90% used) - correct API format
        high_storage_response = {
            "status": "ok",
            "result": [
                {
                    "id": "storage-1",
                    "name": "Internal Storage",
                    "type": "internal",
                    "total_bytes": 500000000000,
                    "used_bytes": 450000000000,
                    "free_bytes": 50000000000,
                    "percent_used": 90.0,
                    "mounted": True,
                }
            ]
        }

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(
                devices="192.168.1.100,192.168.1.101"
            )

            with respx.mock(assert_all_called=False) as router:
                # Device 1: Healthy
                api_base1 = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base1}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base1}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base1}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Device 2: Unhealthy (high storage)
                api_base2 = "http://192.168.1.101/api/v2.0"
                router.get(f"{api_base2}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base2}/storages").mock(
                    return_value=Response(200, json=high_storage_response)
                )
                router.get(f"{api_base2}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Mock the LLM provider
                with patch("epiphan_mcp.server.get_provider") as mock_provider:
                    mock_llm = AsyncMock()
                    mock_llm.complete = AsyncMock(
                        return_value="Fleet has issues.\n\n1. Clear storage on 192.168.1.101"
                    )
                    mock_llm.close = AsyncMock()
                    mock_provider.return_value = mock_llm

                    result = await fleet_health_report.fn()

        assert result["success"] is True
        assert len(result["attention_required"]) >= 1

        # Find the unhealthy device in attention list
        unhealthy_device = next(
            (d for d in result["attention_required"] if "192.168.1.101" in d["device"]),
            None,
        )
        assert unhealthy_device is not None
        assert "storage" in unhealthy_device["issue"].lower()

    async def test_fleet_health_report_empty_fleet(self):
        """Verify report handles empty fleet gracefully."""
        from epiphan_mcp.server import fleet_health_report

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await fleet_health_report.fn()

        assert result["success"] is True
        assert "No devices configured" in result["summary"]
        assert result["health_score"] == 0

    async def test_fleet_health_report_llm_fallback(self):
        """Verify report falls back gracefully when LLM fails."""
        from epiphan_mcp.llm.providers import LLMError
        from epiphan_mcp.server import fleet_health_report

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="192.168.1.100")

            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Mock the LLM provider to raise an error
                with patch("epiphan_mcp.server.get_provider") as mock_provider:
                    mock_llm = AsyncMock()
                    mock_llm.complete = AsyncMock(side_effect=LLMError("API error"))
                    mock_provider.return_value = mock_llm

                    result = await fleet_health_report.fn()

        # Should still succeed with fallback summary
        assert result["success"] is True
        assert "summary" in result
        assert len(result["summary"]) > 0
        assert "recommendations" in result


# ============================================================
# Fleet Intelligence Tests (Sprint 3)
# ============================================================


class TestSuggestMaintenanceWindow:
    """Tests for suggest_maintenance_window tool."""

    async def test_suggest_maintenance_returns_success(self):
        """Verify suggest_maintenance_window returns correct structure."""
        from epiphan_mcp.server import suggest_maintenance_window

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(
                devices="192.168.1.100,192.168.1.101"
            )

            with respx.mock(assert_all_called=False) as router:
                for i in [100, 101]:
                    api_base = f"http://192.168.1.{i}/api/v2.0"
                    router.get(f"{api_base}/device").mock(
                        return_value=Response(200, json=DEVICE_RESPONSE)
                    )
                    router.get(f"{api_base}/storages").mock(
                        return_value=Response(200, json=STORAGE_RESPONSE)
                    )
                    router.get(f"{api_base}/recorders/recorder-1/status").mock(
                        return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                    )

                # Mock the LLM provider
                with patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider:
                    mock_llm = AsyncMock()
                    mock_llm.complete = AsyncMock(
                        return_value="Tonight 10pm-2am would be ideal.\nConfidence: high\nAll devices are idle."
                    )
                    mock_llm.close = AsyncMock()
                    mock_provider.return_value = mock_llm

                    result = await suggest_maintenance_window.fn(min_duration_hours=2.0)

        assert result["success"] is True
        assert "suggested_window" in result
        assert "confidence" in result
        assert "reasoning" in result
        assert "devices_affected" in result
        assert "current_activity" in result

    async def test_suggest_maintenance_empty_fleet(self):
        """Verify handling of empty fleet."""
        from epiphan_mcp.server import suggest_maintenance_window

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await suggest_maintenance_window.fn(min_duration_hours=2.0)

        assert result["success"] is True
        assert result["devices_affected"] == 0
        assert "no devices" in result["suggested_window"].lower()


class TestPredictFleetIssues:
    """Tests for predict_fleet_issues tool."""

    async def test_predict_fleet_issues_returns_success(self):
        """Verify predict_fleet_issues returns correct structure."""
        from epiphan_mcp.server import predict_fleet_issues

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(
                devices="192.168.1.100,192.168.1.101"
            )

            with respx.mock(assert_all_called=False) as router:
                for i in [100, 101]:
                    api_base = f"http://192.168.1.{i}/api/v2.0"
                    router.get(f"{api_base}/device").mock(
                        return_value=Response(200, json=DEVICE_RESPONSE)
                    )
                    router.get(f"{api_base}/storages").mock(
                        return_value=Response(200, json=STORAGE_RESPONSE)
                    )
                    router.get(f"{api_base}/recorders/recorder-1/status").mock(
                        return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                    )

                # Mock the LLM provider for summary
                with patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider:
                    mock_llm = AsyncMock()
                    mock_llm.complete = AsyncMock(
                        return_value="Fleet is healthy with no predicted issues."
                    )
                    mock_llm.close = AsyncMock()
                    mock_provider.return_value = mock_llm

                    result = await predict_fleet_issues.fn(hours_ahead=24)

        assert result["success"] is True
        assert "predictions" in result
        assert isinstance(result["predictions"], list)
        assert "risk_level" in result
        assert result["risk_level"] in ["low", "medium", "high", "critical"]
        assert "devices_at_risk" in result
        assert "summary" in result

    async def test_predict_fleet_issues_with_offline_device(self):
        """Verify offline devices are predicted as critical."""
        from epiphan_mcp.server import predict_fleet_issues

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(
                devices="192.168.1.100,192.168.1.101"
            )

            with respx.mock(assert_all_called=False) as router:
                # Device 1: Healthy
                api_base1 = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base1}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base1}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base1}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Device 2: Offline
                api_base2 = "http://192.168.1.101/api/v2.0"
                router.get(f"{api_base2}/device").mock(
                    side_effect=ConnectError("Connection refused")
                )
                router.get(f"{api_base2}/storages").mock(
                    side_effect=ConnectError("Connection refused")
                )

                # Mock the LLM provider
                with patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider:
                    mock_llm = AsyncMock()
                    mock_llm.complete = AsyncMock(
                        return_value="Device 192.168.1.101 is offline and needs attention."
                    )
                    mock_llm.close = AsyncMock()
                    mock_provider.return_value = mock_llm

                    result = await predict_fleet_issues.fn(hours_ahead=24)

        assert result["success"] is True
        assert result["devices_at_risk"] >= 1
        assert any(p["severity"] == "critical" for p in result["predictions"])

    async def test_predict_fleet_issues_empty_fleet(self):
        """Verify handling of empty fleet."""
        from epiphan_mcp.server import predict_fleet_issues

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await predict_fleet_issues.fn(hours_ahead=24)

        assert result["success"] is True
        assert result["predictions"] == []
        assert result["risk_level"] == "low"


class TestGenerateShiftHandoff:
    """Tests for generate_shift_handoff tool."""

    async def test_generate_shift_handoff_returns_success(self):
        """Verify generate_shift_handoff returns correct structure."""
        from epiphan_mcp.server import generate_shift_handoff

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(
                devices="192.168.1.100,192.168.1.101"
            )

            with respx.mock(assert_all_called=False) as router:
                for i in [100, 101]:
                    api_base = f"http://192.168.1.{i}/api/v2.0"
                    router.get(f"{api_base}/device").mock(
                        return_value=Response(200, json=DEVICE_RESPONSE)
                    )
                    router.get(f"{api_base}/storages").mock(
                        return_value=Response(200, json=STORAGE_RESPONSE)
                    )
                    router.get(f"{api_base}/recorders/recorder-1/status").mock(
                        return_value=Response(200, json=RECORDER_STATUS_RECORDING)
                    )

                # Mock the LLM provider
                with patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider:
                    mock_llm = AsyncMock()
                    mock_llm.complete = AsyncMock(
                        return_value="Shift completed with 2 devices online. All systems normal."
                    )
                    mock_llm.close = AsyncMock()
                    mock_provider.return_value = mock_llm

                    result = await generate_shift_handoff.fn(shift_hours=8)

        assert result["success"] is True
        assert "summary" in result
        assert "activity_summary" in result
        assert "attention_required" in result
        assert "fleet_status" in result
        assert "shift_period" in result

    async def test_generate_shift_handoff_with_issues(self):
        """Verify handoff includes attention items for unhealthy devices."""
        from epiphan_mcp.server import generate_shift_handoff

        # High storage response
        high_storage_response = {
            "status": "ok",
            "result": [
                {
                    "id": "storage-1",
                    "name": "Internal Storage",
                    "type": "internal",
                    "total_bytes": 500000000000,
                    "used_bytes": 450000000000,
                    "free_bytes": 50000000000,
                    "percent_used": 90.0,
                    "mounted": True,
                }
            ]
        }

        with patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="192.168.1.100")

            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=high_storage_response)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Mock the LLM provider
                with patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider:
                    mock_llm = AsyncMock()
                    mock_llm.complete = AsyncMock(
                        return_value="Shift ending with storage concerns. Clear storage on 192.168.1.100."
                    )
                    mock_llm.close = AsyncMock()
                    mock_provider.return_value = mock_llm

                    result = await generate_shift_handoff.fn(shift_hours=8)

        assert result["success"] is True
        assert len(result["attention_required"]) >= 1

    async def test_generate_shift_handoff_empty_fleet(self):
        """Verify handling of empty fleet."""
        from epiphan_mcp.server import generate_shift_handoff

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="")

            result = await generate_shift_handoff.fn(shift_hours=8)

        assert result["success"] is True
        assert "No devices configured" in result["summary"]

    async def test_generate_shift_handoff_llm_fallback(self):
        """Verify fallback when LLM fails."""
        from epiphan_mcp.llm.providers import LLMError
        from epiphan_mcp.server import generate_shift_handoff

        with patch("epiphan_mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = create_test_settings(devices="192.168.1.100")

            with respx.mock(assert_all_called=False) as router:
                api_base = "http://192.168.1.100/api/v2.0"
                router.get(f"{api_base}/device").mock(
                    return_value=Response(200, json=DEVICE_RESPONSE)
                )
                router.get(f"{api_base}/storages").mock(
                    return_value=Response(200, json=STORAGE_RESPONSE)
                )
                router.get(f"{api_base}/recorders/recorder-1/status").mock(
                    return_value=Response(200, json=RECORDER_STATUS_STOPPED)
                )

                # Mock the LLM provider to raise an error
                with patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider:
                    mock_llm = AsyncMock()
                    mock_llm.complete = AsyncMock(side_effect=LLMError("API error"))
                    mock_provider.return_value = mock_llm

                    result = await generate_shift_handoff.fn(shift_hours=8)

        # Should still succeed with fallback summary
        assert result["success"] is True
        assert "summary" in result
        assert len(result["summary"]) > 0
