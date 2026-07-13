"""Unit tests for retry logic with exponential backoff.

TDD tests for the with_retry() function that handles transient failures
in HTTP requests to Pearl devices.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from epiphan_mcp.client import PearlAPIError
from epiphan_mcp.retry import with_retry

# ============================================================
# Basic Retry Behavior Tests
# ============================================================


class TestRetryBasicBehavior:
    """Tests for basic retry functionality."""

    async def test_retry_succeeds_first_try(self):
        """Operation succeeds immediately, no retry needed."""
        operation = AsyncMock(return_value={"status": "ok", "result": "success"})

        result = await with_retry(operation, max_retries=3)

        assert result == {"status": "ok", "result": "success"}
        assert operation.call_count == 1

    async def test_retry_succeeds_second_try(self):
        """First attempt fails, second succeeds."""
        operation = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                {"status": "ok", "result": "success"},
            ]
        )

        with patch("epiphan_mcp.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(operation, max_retries=3, base_delay=1.0)

        assert result == {"status": "ok", "result": "success"}
        assert operation.call_count == 2

    async def test_retry_succeeds_third_try(self):
        """First two attempts fail, third succeeds."""
        operation = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                httpx.TimeoutException("Request timed out"),
                {"status": "ok", "result": "success"},
            ]
        )

        with patch("epiphan_mcp.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(operation, max_retries=3, base_delay=1.0)

        assert result == {"status": "ok", "result": "success"}
        assert operation.call_count == 3

    async def test_retry_exhausts_all_attempts(self):
        """All retries fail, raises last exception."""
        operation = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with (
            patch("epiphan_mcp.retry.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(httpx.ConnectError, match="Connection refused"),
        ):
            await with_retry(operation, max_retries=3, base_delay=1.0)

        # Initial attempt + 3 retries = 4 total attempts
        assert operation.call_count == 4


# ============================================================
# Exponential Backoff Timing Tests
# ============================================================


class TestExponentialBackoff:
    """Tests for exponential backoff timing."""

    async def test_retry_exponential_backoff_timing(self):
        """Verify delays grow exponentially, with ±50% jitter around each step."""
        operation = AsyncMock(
            side_effect=[
                httpx.ConnectError("fail 1"),
                httpx.ConnectError("fail 2"),
                httpx.ConnectError("fail 3"),
                {"status": "ok", "result": "success"},
            ]
        )

        sleep_times = []

        async def mock_sleep(seconds: float) -> None:
            sleep_times.append(seconds)

        with patch("epiphan_mcp.retry.asyncio.sleep", side_effect=mock_sleep):
            result = await with_retry(operation, max_retries=3, base_delay=1.0)

        assert result == {"status": "ok", "result": "success"}
        # Base delays are 1.0, 2.0, 4.0, each jittered into [0.5x, 1.5x]
        assert len(sleep_times) == 3
        assert 0.5 <= sleep_times[0] <= 1.5
        assert 1.0 <= sleep_times[1] <= 3.0
        assert 2.0 <= sleep_times[2] <= 6.0

    async def test_retry_respects_max_delay(self):
        """Delay never exceeds max_delay."""
        operation = AsyncMock(
            side_effect=[
                httpx.ConnectError("fail 1"),
                httpx.ConnectError("fail 2"),
                httpx.ConnectError("fail 3"),
                httpx.ConnectError("fail 4"),
                httpx.ConnectError("fail 5"),
                {"status": "ok", "result": "success"},
            ]
        )

        sleep_times = []

        async def mock_sleep(seconds: float) -> None:
            sleep_times.append(seconds)

        with patch("epiphan_mcp.retry.asyncio.sleep", side_effect=mock_sleep):
            result = await with_retry(operation, max_retries=5, base_delay=1.0, max_delay=3.0)

        assert result == {"status": "ok", "result": "success"}
        # Base delays 1, 2, 4, 8, 16 are capped at 3.0 before AND after
        # jitter — max_delay is a hard ceiling regardless of jitter.
        for delay in sleep_times:
            assert delay <= 3.0

        # First delay is base 1.0 jittered into [0.5, 1.5]
        assert 0.5 <= sleep_times[0] <= 1.5
        # Later delays hit the cap: jittered into [1.5, 3.0] (never above)
        assert 1.5 <= sleep_times[4] <= 3.0


# ============================================================
# Exception Filtering Tests
# ============================================================


class TestExceptionFiltering:
    """Tests for exception type filtering."""

    async def test_retry_only_retries_specified_exceptions(self):
        """Only retry httpx.RequestError, httpx.TimeoutException."""
        # Test with ConnectError (subclass of RequestError) - should retry
        operation_connect = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                {"status": "ok", "result": "success"},
            ]
        )

        with patch("epiphan_mcp.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(operation_connect, max_retries=3)

        assert result == {"status": "ok", "result": "success"}
        assert operation_connect.call_count == 2

        # Test with TimeoutException - should retry
        operation_timeout = AsyncMock(
            side_effect=[
                httpx.TimeoutException("Request timed out"),
                {"status": "ok", "result": "success"},
            ]
        )

        with patch("epiphan_mcp.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(operation_timeout, max_retries=3)

        assert result == {"status": "ok", "result": "success"}
        assert operation_timeout.call_count == 2

    async def test_retry_passes_through_non_retryable(self):
        """Other exceptions bubble up immediately."""
        # ValueError should not be retried
        operation = AsyncMock(side_effect=ValueError("Invalid value"))

        with pytest.raises(ValueError, match="Invalid value"):
            await with_retry(operation, max_retries=3)

        # Only called once - no retry
        assert operation.call_count == 1

    async def test_retry_passes_through_keyboard_interrupt(self):
        """KeyboardInterrupt should not be retried."""
        operation = AsyncMock(side_effect=KeyboardInterrupt())

        with pytest.raises(KeyboardInterrupt):
            await with_retry(operation, max_retries=3)

        assert operation.call_count == 1

    async def test_retry_passes_through_http_status_error(self):
        """HTTPStatusError (4xx, 5xx) should not be retried by default."""
        mock_request = httpx.Request("GET", "http://test.local/api")
        mock_response = httpx.Response(404, request=mock_request)

        operation = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found", request=mock_request, response=mock_response
            )
        )

        with pytest.raises(httpx.HTTPStatusError):
            await with_retry(operation, max_retries=3)

        # HTTPStatusError is not in default retryable exceptions
        assert operation.call_count == 1


# ============================================================
# Busy API Status Tests
# ============================================================


class TestBusyAPIStatus:
    """Tests for Pearl API 'busy' status handling."""

    async def test_retry_with_busy_api_status(self):
        """Retry when API returns 'busy' status."""
        operation = AsyncMock(
            side_effect=[
                PearlAPIError("Resource busy", status_code=200, api_status="busy"),
                {"status": "ok", "result": "success"},
            ]
        )

        with patch("epiphan_mcp.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(operation, max_retries=3)

        assert result == {"status": "ok", "result": "success"}
        assert operation.call_count == 2

    async def test_retry_exhausts_on_persistent_busy(self):
        """All retries fail with busy status."""
        operation = AsyncMock(
            side_effect=PearlAPIError("Resource busy", status_code=200, api_status="busy")
        )

        with (
            patch("epiphan_mcp.retry.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(PearlAPIError) as exc_info,
        ):
            await with_retry(operation, max_retries=3)

        assert exc_info.value.api_status == "busy"
        # Initial + 3 retries = 4 attempts
        assert operation.call_count == 4

    async def test_no_retry_on_api_error_status(self):
        """Do not retry on API 'error' status (non-transient)."""
        operation = AsyncMock(
            side_effect=PearlAPIError("Invalid recorder ID", status_code=404, api_status="error")
        )

        with pytest.raises(PearlAPIError) as exc_info:
            await with_retry(operation, max_retries=3)

        assert exc_info.value.api_status == "error"
        # No retry - just one call
        assert operation.call_count == 1


# ============================================================
# Custom Configuration Tests
# ============================================================


class TestCustomConfiguration:
    """Tests for custom retry configuration."""

    async def test_retry_with_zero_max_retries(self):
        """No retries when max_retries=0."""
        operation = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(httpx.ConnectError):
            await with_retry(operation, max_retries=0)

        # Only initial attempt
        assert operation.call_count == 1

    async def test_retry_with_custom_base_delay(self):
        """Custom base delay is used correctly."""
        operation = AsyncMock(
            side_effect=[
                httpx.ConnectError("fail"),
                {"status": "ok", "result": "success"},
            ]
        )

        sleep_times = []

        async def mock_sleep(seconds: float) -> None:
            sleep_times.append(seconds)

        with patch("epiphan_mcp.retry.asyncio.sleep", side_effect=mock_sleep):
            await with_retry(operation, max_retries=1, base_delay=0.5)

        # Base 0.5 jittered into [0.25, 0.75]
        assert 0.25 <= sleep_times[0] <= 0.75

    async def test_retry_with_custom_retryable_exceptions(self):
        """Custom retryable exceptions work correctly."""
        # Create operation that raises RuntimeError
        operation = AsyncMock(
            side_effect=[
                RuntimeError("Custom error"),
                {"status": "ok", "result": "success"},
            ]
        )

        # RuntimeError should not be retried with default exceptions
        with pytest.raises(RuntimeError):
            await with_retry(operation, max_retries=3)

        assert operation.call_count == 1

        # Reset mock
        operation.reset_mock()
        operation.side_effect = [
            RuntimeError("Custom error"),
            {"status": "ok", "result": "success"},
        ]

        # RuntimeError should be retried with custom exceptions
        with patch("epiphan_mcp.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(
                operation,
                max_retries=3,
                retryable_exceptions=(RuntimeError,),
            )

        assert result == {"status": "ok", "result": "success"}
        assert operation.call_count == 2


# ============================================================
# Logging Tests
# ============================================================


class TestRetryLogging:
    """Tests for retry logging behavior."""

    async def test_retry_logs_attempts(self):
        """Verify logging on retry attempts."""
        operation = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                {"status": "ok", "result": "success"},
            ]
        )

        with (
            patch("epiphan_mcp.retry.asyncio.sleep", new_callable=AsyncMock),
            patch("epiphan_mcp.retry.logger") as mock_logger,
        ):
            await with_retry(operation, max_retries=3, base_delay=1.0)

            # Should log warning on retry
            assert mock_logger.warning.called


# ============================================================
# Integration-style Tests
# ============================================================


class TestRetryIntegration:
    """Integration-style tests for retry behavior."""

    async def test_retry_mixed_failures(self):
        """Handle mix of different failure types."""
        operation = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                httpx.TimeoutException("Timeout"),
                PearlAPIError("Busy", api_status="busy"),
                {"status": "ok", "result": "success"},
            ]
        )

        with patch("epiphan_mcp.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(operation, max_retries=3)

        assert result == {"status": "ok", "result": "success"}
        assert operation.call_count == 4

    async def test_retry_preserves_operation_result(self):
        """Ensure operation result is preserved through retry."""
        expected_result = {
            "status": "ok",
            "result": {
                "id": "recorder-1",
                "state": "recording",
                "duration": 3600,
            },
        }
        operation = AsyncMock(
            side_effect=[
                httpx.ConnectError("fail"),
                expected_result,
            ]
        )

        with patch("epiphan_mcp.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(operation, max_retries=3)

        assert result == expected_result
        assert result["result"]["state"] == "recording"
