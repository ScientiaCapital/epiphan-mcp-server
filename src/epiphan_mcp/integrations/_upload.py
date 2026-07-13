"""Shared upload helpers for CMS integration clients."""

from collections.abc import AsyncIterator
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024


async def stream_file(file_path: Path | str, chunk_size: int = _CHUNK_SIZE) -> AsyncIterator[bytes]:
    """Yield a file's bytes in chunks for httpx streaming uploads.

    httpx.AsyncClient requires an async byte stream as ``content=`` — a
    plain file object is a sync iterable and raises at request time
    (the bug that silently broke every real Panopto upload).
    """
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk
