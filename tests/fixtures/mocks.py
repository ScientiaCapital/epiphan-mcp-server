"""Reusable respx route helpers for Pearl v2.0 system endpoints.

`get_system_status` (used by get_device_status and per-device by get_fleet_status)
calls several documented system endpoints — /system/ident, /system/firmware,
/system/storages, and /system/storages/{stid}/status. This helper registers all
of them on a respx router in one call so tests don't repeat the boilerplate.
"""

from __future__ import annotations

import re
from typing import Any

from httpx import Response

from .responses import (
    FIRMWARE_RESPONSE,
    IDENT_RESPONSE,
    STORAGE_STATUS_RESPONSE,
    STORAGES_LIST_RESPONSE,
)


def mock_system_routes(
    router: Any,
    api_base: str,
    *,
    ident: dict[str, Any] = IDENT_RESPONSE,
    ident_status: int = 200,
    ident_side_effect: Any = None,
    firmware: dict[str, Any] = FIRMWARE_RESPONSE,
    storages: dict[str, Any] = STORAGES_LIST_RESPONSE,
    storage_status: dict[str, Any] = STORAGE_STATUS_RESPONSE,
) -> Any:
    """Register the Pearl v2.0 system-info routes used by get_system_status.

    Pass ``ident_side_effect`` (e.g. httpx.ConnectError / a callable) to simulate
    an unreachable or slow device — get_system_status calls /system/ident first,
    so a raising side_effect there exercises the offline/timeout path. Pass
    ``ident_status`` (e.g. 500) to simulate an API/HTTP error on that first call.
    The firmware/storages routes are still registered (harmless when ident fails).
    """
    ident_route = router.get(f"{api_base}/system/ident")
    if ident_side_effect is not None:
        ident_route.mock(side_effect=ident_side_effect)
    else:
        ident_route.mock(return_value=Response(ident_status, json=ident))

    router.get(f"{api_base}/system/firmware").mock(
        return_value=Response(200, json=firmware)
    )
    router.get(f"{api_base}/system/storages").mock(
        return_value=Response(200, json=storages)
    )
    router.get(url__regex=rf"{re.escape(api_base)}/system/storages/[^/]+/status").mock(
        return_value=Response(200, json=storage_status)
    )
    return router
