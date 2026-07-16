"""Curated tool subsets for the local-model agent.

130 tool schemas will blow the context window of — and badly degrade tool-calling
in — small local models. These profiles expose a sensible subset so a model only
sees the tools it needs for a given task.

Use ``--profile smoke`` on constrained hardware (e.g. an 8 GB machine running a 3B
model), ``core`` for everyday driving, and ``all`` only on capable hardware with a
strong tool-calling model (e.g. Qwen2.5 14B on 24 GB).
"""

from __future__ import annotations

# Minimal set — proves connectivity and single-tool dispatch on small models.
SMOKE = [
    "get_device_status",
    "list_devices",
    "get_recording_status",
    "start_recording",
    "stop_recording",
]

# Everyday driving — recording, streaming, layouts, fleet status, single-touch.
CORE = SMOKE + [
    "list_recorders",
    "get_all_recorder_status",
    "start_all_recorders",
    "stop_all_recorders",
    "start_stream",
    "stop_stream",
    "get_stream_status",
    "list_channels",
    "list_layouts",
    "switch_layout",
    "single_touch_start",
    "single_touch_stop",
    "get_fleet_status",
    "get_device_health_score",
    "pearl_discover_device",
]

# Sentinel: expose every registered tool. None == no filtering.
ALL = None

PROFILES: dict[str, list[str] | None] = {
    "smoke": SMOKE,
    "core": CORE,
    "all": ALL,
}


def select(profile: str, available: list[str]) -> list[str] | None:
    """Return the tool names to expose for ``profile``.

    Returns ``None`` to mean "expose everything". Any name in a profile that is not
    actually registered on the server is dropped (with the caller free to warn).
    """
    if profile not in PROFILES:
        raise ValueError(
            f"Unknown profile {profile!r}. Choose from: {', '.join(PROFILES)}"
        )
    wanted = PROFILES[profile]
    if wanted is None:
        return None
    available_set = set(available)
    return [name for name in wanted if name in available_set]
