"""Unit tests for shared CMS upload helpers."""

import asyncio
import time

import pytest

from epiphan_mcp.integrations._upload import stream_file


class SlowFile:
    """File-like object whose reads block, simulating slow/network storage."""

    def __init__(self, chunks: list[bytes], read_delay: float = 0.05):
        self._chunks = list(chunks)
        self._read_delay = read_delay
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        time.sleep(self._read_delay)
        return self._chunks.pop(0) if self._chunks else b""

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "SlowFile":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class TestStreamFile:
    """Tests for stream_file()."""

    async def test_yields_all_chunks_in_order(self, tmp_path):
        """The full file arrives in chunk_size pieces, in order."""
        payload = b"0123456789" * 100
        f = tmp_path / "clip.mp4"
        f.write_bytes(payload)

        chunks = [chunk async for chunk in stream_file(f, chunk_size=256)]

        assert b"".join(chunks) == payload
        assert all(len(c) <= 256 for c in chunks)
        assert len(chunks) == 4  # 1000 bytes / 256

    async def test_reads_do_not_block_event_loop(self, monkeypatch):
        """Blocking file reads must run off the event loop.

        Uploads read from disk that may be slow or network-mounted; if
        reads run on the loop, every other coroutine (fleet ops, other
        uploads) stalls for the duration. A heartbeat task must keep
        ticking while stream_file chews through slow reads.
        """
        slow = SlowFile([b"x" * 10] * 10, read_delay=0.05)  # ~500ms of reads
        monkeypatch.setattr(
            "epiphan_mcp.integrations._upload.open",
            lambda *a, **k: slow,
            raising=False,
        )

        ticks = 0

        async def heartbeat() -> None:
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        hb = asyncio.create_task(heartbeat())
        try:
            async for _ in stream_file("whatever.bin"):
                pass
        finally:
            hb.cancel()

        # Sync reads on the loop yield ~0 ticks; threaded reads yield ~45.
        assert ticks >= 10, f"event loop starved during file reads ({ticks} ticks)"

    async def test_file_closed_after_streaming(self, monkeypatch):
        """The underlying file handle is closed when the stream is exhausted."""
        slow = SlowFile([b"data"], read_delay=0.0)
        monkeypatch.setattr(
            "epiphan_mcp.integrations._upload.open",
            lambda *a, **k: slow,
            raising=False,
        )

        async for _ in stream_file("whatever.bin"):
            pass

        assert slow.closed is True

    async def test_missing_file_raises(self, tmp_path):
        """A nonexistent path surfaces the OS error, not a silent empty stream."""
        with pytest.raises(OSError):
            async for _ in stream_file(tmp_path / "missing.mp4"):
                pass
