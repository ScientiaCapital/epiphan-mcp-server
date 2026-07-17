"""Lane-A adapter: MCP device status -> edge-triggered state-change facts.

This is the deterministic lane of the two-lane ingestion design. It consumes the
`SystemStatus` that `PearlClient.get_system_status()` already returns, derives a small
state tuple, and emits a fact ONLY when a field actually transitions (the gate). No LLM
is involved — fleet-state supersession must be reproducible and auditable.

The adapter is a pure consumer of status output: it does not touch client.py, and it is
sink-agnostic (see sink.Sink).
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from sink import Sink, StateEvent, utcnow_iso

from epiphan_mcp.models import SystemStatus

# Stable namespace for device UUIDs (uuid5 => same input always yields same id =>
# a device is "found by id", so no dedup/resolution is ever needed).
NS_DEVICE = uuid5(NAMESPACE_URL, "epiphan-mcp:device")

# Storage bands mirror the health thresholds in tools/fleet.py (>=90 / >=75).
STORAGE_CRITICAL = 90.0
STORAGE_WARNING = 75.0


def storage_band(used_percent: float) -> str:
    """Bucket a storage percentage into a band. Emit band crossings, not raw %."""
    if used_percent >= STORAGE_CRITICAL:
        return "critical"
    if used_percent >= STORAGE_WARNING:
        return "warning"
    return "ok"


def device_uuid(host: str) -> str:
    """Stable device identity, keyed on the configured host.

    Serial would seem the natural key, but it is often empty on Pearl v2.0 endpoints
    AND is entirely unavailable when the device is offline. Keying on serial therefore
    produces a DIFFERENT id for the same device depending on reachability — the spike's
    synthetic run caught exactly this (offline observation forked a second identity).
    The host is always present (it is how the device is addressed) and stable, so it is
    the identity; serial is carried as an attribute, not the key.
    """
    return str(uuid5(NS_DEVICE, host))


class LaneAAdapter:
    """Turns a stream of SystemStatus observations into state-change facts."""

    def __init__(self, sink: Sink) -> None:
        self._sink = sink

    def derive_state(self, status: SystemStatus | None) -> dict[str, str]:
        """Observable state tuple. When offline we can only observe status."""
        if status is None:
            return {"status": "offline"}
        return {
            "status": "online",
            "firmware": status.firmware_version or "unknown",
            "model": status.model or "unknown",
            "storage_band": storage_band(status.storage_used_percent),
        }

    def ingest(
        self,
        host: str,
        status: SystemStatus | None,
        *,
        valid_at: str | None = None,
    ) -> list[StateEvent]:
        """Diff the observation against last-known state; emit one fact per change.

        Pass `status=None` for an unreachable device (the offline signal). Only the
        relations actually observed are diffed, so an offline blip does not falsely
        supersede firmware/storage facts recorded while the device was up.
        """
        dev = device_uuid(host)
        derived = self.derive_state(status)
        last = self._sink.last_state(dev)
        when = valid_at or utcnow_iso()

        emitted: list[StateEvent] = []
        for relation, new_value in derived.items():
            old_value = last.get(relation)
            if old_value != new_value:
                event = StateEvent(
                    device_uuid=dev,
                    host=host,
                    relation=relation,
                    old_value=old_value,
                    new_value=new_value,
                    valid_at=when,
                )
                self._sink.record(event)
                emitted.append(event)
        return emitted
