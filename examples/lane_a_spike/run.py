#!/usr/bin/env python
"""Drive the Lane-A adapter.

    # No hardware — scripted sequence + self-checks (default; CI-usable):
    python examples/lane_a_spike/run.py --synthetic

    # Against real devices in .env (PEARL_DEVICES/USERNAME/PASSWORD), one poll:
    python examples/lane_a_spike/run.py --live

    # Demo mode: durable store + poll loop (Ctrl-C to stop) + full event history:
    python examples/lane_a_spike/run.py --live --db demo.db --watch 5 --history
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


async def _poll_hosts(adapter: LaneAAdapter, hosts: list[str]) -> int:
    """Poll every configured device once; return the number of facts emitted."""
    from epiphan_mcp.client import PearlAPIError, PearlClient
    from epiphan_mcp.config import get_settings

    settings = get_settings()
    total = 0
    for host in hosts:
        client = PearlClient.from_settings(host, settings)
        try:
            async with client:
                status = await client.get_system_status()
            emitted = adapter.ingest(host, status)
        except PearlAPIError as exc:
            emitted = adapter.ingest(host, None)  # unreachable -> offline fact
            print(f"[warn] {host} unreachable: {exc}", file=sys.stderr)
        for ev in emitted:
            print(f"  FACT {host}: {ev.relation}: {ev.old_value} -> {ev.new_value}")
        print(f"{host}: {len(emitted)} state-change fact(s)")
        total += len(emitted)
    return total


async def run_live(db: str, watch: float | None, history: bool) -> int:
    """Poll real devices and feed the adapter — once, or on a --watch loop.

    With --db the sink is durable, so the gate's last-known state survives across
    runs: a re-run against unchanged devices emits 0 facts (the gate, live).
    """
    from epiphan_mcp.config import get_settings

    settings = get_settings()
    hosts = settings.get_device_list()
    if not hosts:
        print("No devices configured. Set PEARL_DEVICES in .env.", file=sys.stderr)
        return 2

    sink = FlatSink(db)
    adapter = LaneAAdapter(sink)

    if watch is None:
        await _poll_hosts(adapter, hosts)
    else:
        print(f"Watching {len(hosts)} device(s) every {watch:g}s — Ctrl-C to stop.")
        cycle = 0
        try:
            while True:
                cycle += 1
                print(f"\n--- poll #{cycle} ---")
                await _poll_hosts(adapter, hosts)
                await asyncio.sleep(watch)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print(f"\nStopped after {cycle} poll(s).")

    print(f"\nEvents recorded this run's store: {len(sink.all_events())}")
    _print_state(sink)
    if history:
        _print_history(sink)
    return 0


def _print_state(sink: FlatSink) -> None:
    print("\nCurrent state (device / relation = value):")
    for r in sink.current_rows():
        print(f"  {r['device_uuid'][:8]}  {r['relation']:<13} = {r['value']}")


def _print_history(sink: FlatSink) -> None:
    """The temporal fact log: what changed, when, from what."""
    print("\nEvent history (append-only state_events):")
    for r in sink.all_events():
        old = r["old_value"] if r["old_value"] is not None else "∅"
        print(
            f"  {r['valid_at']}  {r['host']:<15} {r['relation']:<13} "
            f"{old} -> {r['new_value']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Lane-A adapter spike driver.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--synthetic", action="store_true", help="Scripted self-test (default).")
    mode.add_argument("--live", action="store_true", help="Poll real devices from .env.")
    parser.add_argument(
        "--db", default=":memory:", metavar="PATH",
        help="Sqlite path for a durable store (--live only; default in-memory).",
    )
    parser.add_argument(
        "--watch", nargs="?", type=float, const=5.0, default=None, metavar="SECONDS",
        help="Keep polling every SECONDS (default 5) until Ctrl-C (--live only).",
    )
    parser.add_argument(
        "--history", action="store_true",
        help="Print the full state_events log at the end (--live only).",
    )
    args = parser.parse_args()

    if not args.live and (args.db != ":memory:" or args.watch is not None or args.history):
        # The synthetic self-test must stay in-memory and single-pass: persisted
        # state from a prior run would change what the gate emits and break its
        # exact-count assertions.
        parser.error("--db/--watch/--history require --live")

    if args.live:
        try:
            return asyncio.run(run_live(args.db, args.watch, args.history))
        except KeyboardInterrupt:
            # asyncio.run re-raises KeyboardInterrupt after the (handled)
            # cancellation — the loop already printed its summary; exit clean.
            return 0
    return run_synthetic()


if __name__ == "__main__":
    raise SystemExit(main())
