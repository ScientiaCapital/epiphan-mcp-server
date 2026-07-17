#!/usr/bin/env python
"""Drive the Lane-A adapter.

    # No hardware — scripted sequence + self-checks (default; CI-usable):
    python examples/lane_a_spike/run.py --synthetic

    # Against real devices in .env (PEARL_DEVICES/USERNAME/PASSWORD):
    python examples/lane_a_spike/run.py --live
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from adapter import LaneAAdapter, device_uuid
from dotenv import load_dotenv
from sink import FlatSink

from epiphan_mcp.models import SystemStatus

load_dotenv()  # pick up PEARL_* from .env for --live


def _status(fw: str = "4.17.0", pct: float = 20.0, model: str = "Pearl-2",
            serial: str = "ABC123") -> SystemStatus:
    return SystemStatus(
        device_name="Pearl",
        model=model,
        serial_number=serial,
        firmware_version=fw,
        storage_used_percent=pct,
    )


def run_synthetic() -> int:
    """Feed a scripted sequence and assert the gate behaves exactly."""
    sink = FlatSink(":memory:")
    adapter = LaneAAdapter(sink)
    host = "192.168.1.100"
    failures: list[str] = []

    def check(label: str, got: int, want: int) -> None:
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: emitted {got}, expected {want}")
        if not ok:
            failures.append(label)

    # 1. first observation: status, firmware, model, storage_band -> 4 facts
    check("first poll (4 new facts)", len(adapter.ingest(host, _status())), 4)
    # 2. identical poll: the gate suppresses everything
    check("identical poll (gate)", len(adapter.ingest(host, _status())), 0)
    # 3. firmware upgrade -> 1
    check("firmware upgrade", len(adapter.ingest(host, _status(fw="4.18.0"))), 1)
    # 4. storage moves 20%->30% but stays in 'ok' band -> 0 (band crossings only)
    check("within-band storage", len(adapter.ingest(host, _status(fw="4.18.0", pct=30.0))), 0)
    # 5. storage crosses into 'critical' (95%) -> 1
    check("storage band crossing", len(adapter.ingest(host, _status(fw="4.18.0", pct=95.0))), 1)
    # 6. device unreachable -> 1 (status only; firmware/storage untouched)
    check("offline transition", len(adapter.ingest(host, None)), 1)
    # 7. back online, same fw/storage -> only status flips back (1)
    check("recover online", len(adapter.ingest(host, _status(fw="4.18.0", pct=95.0))), 1)

    # Invariant: exactly one current_state row per (device, relation).
    rows = sink.current_rows()
    keys = [(r["device_uuid"], r["relation"]) for r in rows]
    check("one open state per (device,relation)", len(keys), len(set(keys)))

    # Identity: keyed on host, so distinct hosts are distinct devices and the same
    # host is one device whether online or offline.
    u1 = device_uuid("192.168.1.50")
    u2 = device_uuid("192.168.1.51")
    check("distinct hosts distinct ids", 1 if u1 != u2 else 0, 1)
    check("host id stable", 1 if device_uuid("192.168.1.50") == u1 else 0, 1)

    print(f"\nEvents recorded: {len(sink.all_events())}")
    _print_state(sink)

    if failures:
        print(f"\nSYNTHETIC SELF-TEST FAILED: {', '.join(failures)}")
        return 1
    print("\nSYNTHETIC SELF-TEST PASSED — gate, supersession, and identity behave.")
    return 0


async def run_live() -> int:
    """Poll real devices once and feed the adapter."""
    from epiphan_mcp.client import PearlAPIError, PearlClient
    from epiphan_mcp.config import get_settings

    settings = get_settings()
    hosts = settings.get_device_list()
    if not hosts:
        print("No devices configured. Set PEARL_DEVICES in .env.", file=sys.stderr)
        return 2

    sink = FlatSink(":memory:")
    adapter = LaneAAdapter(sink)
    for host in hosts:
        client = PearlClient.from_settings(host, settings)
        try:
            async with client:
                status = await client.get_system_status()
            emitted = adapter.ingest(host, status)
        except PearlAPIError as exc:
            emitted = adapter.ingest(host, None)  # unreachable -> offline fact
            print(f"[warn] {host} unreachable: {exc}", file=sys.stderr)
        print(f"{host}: {len(emitted)} state-change fact(s)")

    print(f"\nEvents recorded: {len(sink.all_events())}")
    _print_state(sink)
    return 0


def _print_state(sink: FlatSink) -> None:
    print("\nCurrent state (device / relation = value):")
    for r in sink.current_rows():
        print(f"  {r['device_uuid'][:8]}  {r['relation']:<13} = {r['value']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Lane-A adapter spike driver.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--synthetic", action="store_true", help="Scripted self-test (default).")
    mode.add_argument("--live", action="store_true", help="Poll real devices from .env.")
    args = parser.parse_args()

    if args.live:
        return asyncio.run(run_live())
    return run_synthetic()


if __name__ == "__main__":
    raise SystemExit(main())
