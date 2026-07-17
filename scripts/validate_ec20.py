#!/usr/bin/env python
"""Validate the EC20 camera REST endpoints against real hardware.

The EC20 client's endpoint PATHS are best-effort placeholders (Epiphan publishes
no REST reference). This script exercises each one against a real camera and
reports which respond, so paths can be confirmed or corrected in one run.

Read-only by default (status / position / presets / preview). Pass --destructive
to also exercise movement, presets, and tracking (these MOVE the camera).

Usage:
    python scripts/validate_ec20.py --host 192.168.1.50 --password secret
    python scripts/validate_ec20.py --host 192.168.1.50 --password secret --destructive

Env fallbacks: EC20_USERNAME, EC20_PASSWORD.
Exit code 0 if every attempted probe returned a 2xx; 1 otherwise.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Awaitable
from typing import Any

from dotenv import load_dotenv

from epiphan_mcp.integrations.ec20 import (
    EC20APIError,
    EC20AuthError,
    EC20Client,
    EC20ConnectionError,
)

# Pick up credentials from .env, like the server does.
load_dotenv()

# Documented path per client method, for the report (see ec20.py TODO).
PATHS = {
    "get_status": "GET /api/status",
    "get_position": "GET /api/ptz/position",
    "get_presets": "GET /api/ptz/presets",
    "get_preview": "GET /api/preview",
    "pan": "POST /api/ptz/pan",
    "tilt": "POST /api/ptz/tilt",
    "zoom": "POST /api/ptz/zoom",
    "home": "POST /api/ptz/home",
    "save_preset": "POST /api/ptz/preset/save",
    "goto_preset": "POST /api/ptz/preset/goto",
    "enable_tracking": "POST /api/tracking/enable",
    "disable_tracking": "POST /api/tracking/disable",
}


class Report:
    def __init__(self) -> None:
        self.ok = 0
        self.fail = 0

    async def probe(self, name: str, coro: Awaitable[Any]) -> None:
        path = PATHS.get(name, name)
        try:
            result = await coro
            preview = (
                f"{len(result)} bytes"
                if isinstance(result, bytes)
                else str(result)[:80]
            )
            print(f"  PASS  {name:<18} {path:<32} -> {preview}")
            self.ok += 1
        except EC20AuthError as e:
            print(f"  AUTH  {name:<18} {path:<32} -> {e}")
            self.fail += 1
        except EC20APIError as e:
            code = getattr(e, "status_code", "?")
            print(f"  FAIL  {name:<18} {path:<32} -> HTTP {code}: {e}")
            self.fail += 1
        except EC20ConnectionError as e:
            print(f"  CONN  {name:<18} {path:<32} -> {e}")
            self.fail += 1
        except Exception as e:  # noqa: BLE001 - report anything unexpected
            print(f"  ERR   {name:<18} {path:<32} -> {type(e).__name__}: {e}")
            self.fail += 1


async def run(args: argparse.Namespace) -> int:
    rep = Report()

    def factory() -> EC20Client:
        return EC20Client(
            host=args.host,
            username=args.username,
            password=args.password,
            use_https=args.https,
            timeout=args.timeout,
        )

    print(f"\nEC20 validation against {args.host} "
          f"({'HTTPS' if args.https else 'HTTP'}; note: 443 is disabled on current firmware)\n")

    print("Read-only probes:")
    async with factory() as c:
        await rep.probe("get_status", c.get_status())
        await rep.probe("get_position", c.get_position())
        await rep.probe("get_presets", c.get_presets())
        await rep.probe("get_preview", c.get_preview())

    if args.destructive:
        print("\nDestructive probes (camera will move):")
        async with factory() as c:
            await rep.probe("pan", c.pan(degrees=5, speed=30))
            await rep.probe("tilt", c.tilt(degrees=5, speed=30))
            await rep.probe("zoom", c.zoom(level=2))
            await rep.probe("home", c.home())
            await rep.probe("save_preset", c.save_preset(preset_id=0, name="validate"))
            await rep.probe("goto_preset", c.goto_preset(preset_id=0))
            await rep.probe("enable_tracking", c.enable_tracking(mode="presenter"))
            await rep.probe("disable_tracking", c.disable_tracking())
    else:
        print("\n(Skipping destructive probes — pass --destructive to exercise "
              "movement/presets/tracking.)")

    print(f"\nSummary: {rep.ok} passed, {rep.fail} failed/unreachable.")
    print("Any FAIL/ERR means that path is wrong or unsupported — capture the real "
          "path from the camera web UI dev-tools and update integrations/ec20.py.")
    return 0 if rep.fail == 0 else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Validate EC20 REST endpoints against hardware.")
    p.add_argument("--host", required=True, help="EC20 camera IP or hostname.")
    p.add_argument("--username", default=os.getenv("EC20_USERNAME", "admin"))
    p.add_argument("--password", default=os.getenv("EC20_PASSWORD", ""))
    p.add_argument("--https", action="store_true", help="Use HTTPS (likely unsupported).")
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument(
        "--destructive",
        action="store_true",
        help="Also exercise movement/preset/tracking endpoints (moves the camera).",
    )
    args = p.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
