#!/usr/bin/env python
"""Validate the unverified YuJa / Echo360 list endpoints against live tenants.

Some CMS list/collection paths are inferred from partial or gated docs (see the
UNVERIFIED markers in integrations/yuja.py and echo360.py). This script calls
each list endpoint against a real tenant and reports whether it returns data,
404s, or 401s — so the paths can be confirmed or corrected in one run.

Reads credentials from env (matching the server's config):
    YuJa:    YUJA_HOST, YUJA_AUTH_TOKEN
    Echo360: ECHO360_HOST, ECHO360_CLIENT_ID, ECHO360_CLIENT_SECRET

Usage:
    python scripts/validate_cms.py            # runs whichever creds are present
    python scripts/validate_cms.py --yuja     # only YuJa
    python scripts/validate_cms.py --echo360  # only Echo360

Exit code 0 if every attempted probe returned data; 1 otherwise.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Awaitable
from typing import Any


class Report:
    def __init__(self) -> None:
        self.ok = 0
        self.fail = 0
        self.skipped = 0

    async def probe(self, label: str, coro: Awaitable[Any]) -> None:
        try:
            result = await coro
            # list endpoints return (items, truncated) tuples
            if isinstance(result, tuple) and result and isinstance(result[0], list):
                items, truncated = result
                trunc = " (truncated)" if truncated else ""
                print(f"  PASS  {label:<28} -> {len(items)} item(s){trunc}")
            else:
                print(f"  PASS  {label:<28} -> {str(result)[:60]}")
            self.ok += 1
        except Exception as e:  # noqa: BLE001 - report anything for validation
            code = getattr(e, "status_code", None)
            detail = f"HTTP {code}: " if code else ""
            print(f"  FAIL  {label:<28} -> {detail}{type(e).__name__}: {e}")
            self.fail += 1


async def validate_yuja(rep: Report) -> None:
    host = os.getenv("YUJA_HOST")
    token = os.getenv("YUJA_AUTH_TOKEN")
    if not (host and token):
        print("YuJa: skipped (set YUJA_HOST + YUJA_AUTH_TOKEN to validate)\n")
        rep.skipped += 1
        return

    from epiphan_mcp.integrations.yuja import YuJaClient

    print(f"YuJa @ {host}:")
    async with YuJaClient(host=host, auth_token=token) as c:
        # list_videos may need /user or /group scoping; list_channels is highest-risk.
        await rep.probe("GET /services/media/videos", c.list_videos())
        await rep.probe("GET /services/channels", c.list_channels())
    print()


async def validate_echo360(rep: Report) -> None:
    host = os.getenv("ECHO360_HOST")
    cid = os.getenv("ECHO360_CLIENT_ID")
    secret = os.getenv("ECHO360_CLIENT_SECRET")
    if not (host and cid and secret):
        print("Echo360: skipped (set ECHO360_HOST + ECHO360_CLIENT_ID + "
              "ECHO360_CLIENT_SECRET to validate)\n")
        rep.skipped += 1
        return

    from epiphan_mcp.integrations.echo360 import Echo360Client

    print(f"Echo360 @ {host}:")
    async with Echo360Client(host=host, client_id=cid, client_secret=secret) as c:
        # /sections is confirmed; /courses is inferred — this checks both.
        await rep.probe("GET /public/api/v1/sections", c.list_sections())
        await rep.probe("GET /public/api/v1/courses", c.list_courses())
    print()


async def run(args: argparse.Namespace) -> int:
    rep = Report()
    run_yuja = args.yuja or not args.echo360
    run_echo = args.echo360 or not args.yuja

    print("\nCMS endpoint validation\n")
    if run_yuja:
        await validate_yuja(rep)
    if run_echo:
        await validate_echo360(rep)

    print(f"Summary: {rep.ok} passed, {rep.fail} failed, {rep.skipped} skipped.")
    if rep.fail:
        print("A FAIL on a list path means it is wrong/unsupported — check the "
              "vendor API guide (YuJa §5.2.x; Echo360 Swagger at <host>/api-documentation) "
              "and update the integration.")
    return 0 if rep.fail == 0 else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Validate CMS list endpoints against live tenants.")
    p.add_argument("--yuja", action="store_true", help="Validate YuJa only.")
    p.add_argument("--echo360", action="store_true", help="Validate Echo360 only.")
    args = p.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
