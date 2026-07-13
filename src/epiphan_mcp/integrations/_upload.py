"""Shared upload helpers for CMS integration clients."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024


async def stream_file(file_path: Path | str, chunk_size: int = _CHUNK_SIZE) -> AsyncIterator[bytes]:
    """Yield a file's bytes in chunks for httpx streaming uploads.

    httpx.AsyncClient requires an async byte stream as ``content=`` — a
    plain file object is a sync iterable and raises at request time
    (the bug that silently broke every real Panopto upload).

    Reads run in a worker thread: recordings can live on slow or
    network-mounted storage, and a blocking read on the event loop would
    stall every other operation for its duration.
    """
    f = await asyncio.to_thread(open, file_path, "rb")
    try:
        while chunk := await asyncio.to_thread(f.read, chunk_size):
            yield chunk
    finally:
        await asyncio.to_thread(f.close)
