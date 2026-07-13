"""Retry logic with exponential backoff for Pearl API requests.

Handles transient network failures and API 'busy' responses with
configurable exponential backoff.
"""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _is_busy_api_error(exc: Exception) -> bool:
    """Check if exception is a Pearl API 'busy' status error."""
    # Import here to avoid circular dependency
    from .client import PearlAPIError

    return isinstance(exc, PearlAPIError) and exc.api_status == "busy"


async def with_retry(
    operation: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple[type[Exception], ...] = (
        httpx.RequestError,
        httpx.TimeoutException,
    ),
) -> T:
    """
    Execute operation with exponential backoff retry.

    Automatically retries on transient network failures and Pearl API
    'busy' responses. Uses exponential backoff with configurable delays.

    Args:
        operation: Async callable to execute (no arguments).
        max_retries: Maximum number of retry attempts after initial failure.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay cap in seconds.
        retryable_exceptions: Tuple of exception types to retry on.

    Returns:
        The result of the operation.

    Raises:
        The last exception if all retries are exhausted.

    Example:
        async def fetch_status():
            async with client:
                return await client.get_recorder_status("recorder-1")

        result = await with_retry(fetch_status, max_retries=3)
    """
    last_exception: Exception | None = None
    attempt = 0
    total_attempts = max_retries + 1  # Initial attempt + retries

    while attempt < total_attempts:
        try:
            return await operation()
        except Exception as exc:
            # Check if this exception should be retried. A Pearl 'busy' API
            # error is a definitive pre-execution reject — the device refused
            # the request without acting on it — so retrying cannot duplicate
            # side effects. It is therefore exempt from the connect-phase-only
            # restriction that callers apply to non-idempotent POST/PATCH via
            # retryable_exceptions (see client._CONNECT_PHASE_RETRYABLE).
            should_retry = isinstance(exc, retryable_exceptions) or _is_busy_api_error(exc)

            if not should_retry:
                # Non-retryable exception - propagate immediately
                raise

            last_exception = exc
            attempt += 1

            if attempt < total_attempts:
                # Exponential backoff with jitter — without jitter, N fleet
                # devices hit by the same network blip retry in lockstep.
                # Re-capped after jitter so max_delay stays a hard ceiling.
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                delay = min(delay * random.uniform(0.5, 1.5), max_delay)

                logger.warning(
                    f"Retry attempt {attempt}/{max_retries} after {delay:.1f}s "
                    f"due to: {type(exc).__name__}: {exc}"
                )

                await asyncio.sleep(delay)
            else:
                # All retries exhausted
                logger.error(
                    f"All {max_retries} retries exhausted. Last error: {type(exc).__name__}: {exc}"
                )

    # Should never reach here, but satisfy type checker
    if last_exception:
        raise last_exception

    raise RuntimeError("Unexpected state in retry logic")
