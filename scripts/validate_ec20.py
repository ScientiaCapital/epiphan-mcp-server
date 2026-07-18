#!/usr/bin/env python
"""Validate the EC20 camera CGI endpoints against real hardware.

The EC20 uses an HTTP-Digest CGI API (param.cgi / ptzctrl.cgi / vip), captured
from live hardware. This script exercises each client method against a real
camera and reports which respond, so the paths stay confirmed over firmware
revisions.

Read-only by default (status / tracking-status / preview). Pass --destructive
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

# Real endpoint per client method (captured from live hardware + web-UI JS).
PATHS = {
    "get_status": "GET /cgi-bin/param.cgi?get_device_conf+get_system_conf",
    "get_tracking_status": "GET /cgi-bin/param.cgi?get_target_status",
    "get_preview": "(unsupported: MJPEG WebSocket /ws/mjpeg)",
    "move": "GET /cgi-bin/ptzctrl.cgi?ptzcmd&<dir>&<pan>&<tilt>",
    "stop": "GET /cgi-bin/ptzctrl.cgi?ptzcmd&ptzstop",
    "zoom": "GET /cgi-bin/ptzctrl.cgi?ptzcmd&zoom<in|out>&<speed>",
    "zoom_stop": "GET /cgi-bin/ptzctrl.cgi?ptzcmd&zoomstop",
    "home": "GET /cgi-bin/ptzctrl.cgi?ptzcmd&home",
    "save_preset": "GET /cgi-bin/ptzctrl.cgi?ptzcmd&posset&<id>",
    "goto_preset": "GET /cgi-bin/ptzctrl.cgi?ptzcmd&poscall&<id>",
    "enable_tracking": "GET /cgi-bin/vip?set_ai_vip&1",
    "disable_tracking": "GET /cgi-bin/vip?set_ai_vip&0",
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
        await rep.probe("get_tracking_status", c.get_tracking_status())
        # get_preview is expected to fail (no HTTP frame endpoint) — reported for record.
        await rep.probe("get_preview", c.get_preview())

    if args.destructive:
        print("\nDestructive probes (camera will move):")
        async with factory() as c:
            # Nudge left briefly then stop, so the camera doesn't run away.
            await rep.probe("move", c.move("left", pan_speed=8, tilt_speed=8))
            await rep.probe("stop", c.stop())
            await rep.probe("zoom", c.zoom("in", speed=2))
            await rep.probe("zoom_stop", c.zoom_stop())
            await rep.probe("home", c.home())
            await rep.probe("save_preset", c.save_preset(preset_id=0))
            await rep.probe("goto_preset", c.goto_preset(preset_id=0))
            await rep.probe("enable_tracking", c.enable_tracking(mode="presenter"))
            await rep.probe("disable_tracking", c.disable_tracking())
    else:
        print("\n(Skipping destructive probes — pass --destructive to exercise "
              "movement/presets/tracking.)")

    print(f"\nSummary: {rep.ok} passed, {rep.fail} failed/unreachable.")
    print("get_preview is expected to FAIL (preview is a WebSocket MJPEG stream). "
          "Any OTHER FAIL/ERR means that path needs correcting in integrations/ec20.py.")
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
