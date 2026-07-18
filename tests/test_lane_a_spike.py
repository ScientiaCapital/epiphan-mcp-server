"""Regression tests for the Lane-A adapter spike (examples/lane_a_spike/).

Pytest port of the spike's synthetic self-test (run.py --synthetic), so the
adapter's gate/supersession/identity behavior is guarded by CI. No hardware,
no LLM — the whole point of Lane A is determinism.

The spike is a self-contained example (its modules import each other by bare
name), so its directory is added to sys.path here rather than packaging it.
"""

import sys
from pathlib import Path

import pytest

SPIKE_DIR = Path(__file__).resolve().parent.parent / "examples" / "lane_a_spike"
sys.path.insert(0, str(SPIKE_DIR))

from adapter import LaneAAdapter, device_uuid, storage_band  # noqa: E402
from sink import FlatSink  # noqa: E402

from epiphan_mcp.models import SystemStatus  # noqa: E402


def _status(
    fw: str = "4.17.0",
    pct: float = 20.0,
    model: str = "Pearl-2",
    serial: str = "ABC123",
) -> SystemStatus:
    return SystemStatus(
        device_name="Pearl",
        model=model,
        serial_number=serial,
        firmware_version=fw,
        storage_used_percent=pct,
    )


@pytest.fixture
def sink() -> FlatSink:
    return FlatSink(":memory:")


@pytest.fixture
def adapter(sink: FlatSink) -> LaneAAdapter:
    return LaneAAdapter(sink)


HOST = "192.168.1.100"


class TestGate:
    """Edge-triggered gate: one fact per real transition, zero on heartbeats."""

    def test_first_poll_emits_all_four_relations(self, adapter: LaneAAdapter) -> None:
        emitted = adapter.ingest(HOST, _status())
        assert len(emitted) == 4
        assert {e.relation for e in emitted} == {
            "status",
            "firmware",
            "model",
            "storage_band",
        }

    def test_identical_poll_is_suppressed(self, adapter: LaneAAdapter) -> None:
        adapter.ingest(HOST, _status())
        assert adapter.ingest(HOST, _status()) == []

    def test_firmware_upgrade_emits_one_fact(self, adapter: LaneAAdapter) -> None:
        adapter.ingest(HOST, _status())
        emitted = adapter.ingest(HOST, _status(fw="4.18.0"))
        assert len(emitted) == 1
        assert emitted[0].relation == "firmware"
        assert emitted[0].old_value == "4.17.0"
        assert emitted[0].new_value == "4.18.0"

    def test_within_band_storage_move_is_suppressed(self, adapter: LaneAAdapter) -> None:
        adapter.ingest(HOST, _status(pct=20.0))
        assert adapter.ingest(HOST, _status(pct=30.0)) == []

    def test_storage_band_crossing_emits_one_fact(self, adapter: LaneAAdapter) -> None:
        adapter.ingest(HOST, _status(pct=20.0))
        emitted = adapter.ingest(HOST, _status(pct=95.0))
        assert len(emitted) == 1
        assert emitted[0].relation == "storage_band"
        assert emitted[0].new_value == "critical"


class TestOffline:
    """Offline observations touch only `status` — never falsely supersede facts."""

    def test_offline_transition_touches_only_status(self, adapter: LaneAAdapter) -> None:
        adapter.ingest(HOST, _status())
        emitted = adapter.ingest(HOST, None)
        assert [e.relation for e in emitted] == ["status"]
        assert emitted[0].new_value == "offline"

    def test_firmware_and_storage_survive_offline_blip(
        self, adapter: LaneAAdapter, sink: FlatSink
    ) -> None:
        adapter.ingest(HOST, _status(fw="4.18.0", pct=95.0))
        adapter.ingest(HOST, None)
        state = sink.last_state(device_uuid(HOST))
        assert state["firmware"] == "4.18.0"
        assert state["storage_band"] == "critical"

    def test_recovery_emits_only_status_when_nothing_else_changed(
        self, adapter: LaneAAdapter
    ) -> None:
        adapter.ingest(HOST, _status(fw="4.18.0", pct=95.0))
        adapter.ingest(HOST, None)
        emitted = adapter.ingest(HOST, _status(fw="4.18.0", pct=95.0))
        assert [e.relation for e in emitted] == ["status"]
        assert emitted[0].new_value == "online"


class TestSupersession:
    """FlatSink invariant: exactly one open state per (device, relation)."""

    def test_one_open_state_per_device_relation(
        self, adapter: LaneAAdapter, sink: FlatSink
    ) -> None:
        adapter.ingest(HOST, _status())
        adapter.ingest(HOST, _status(fw="4.18.0", pct=95.0))
        adapter.ingest(HOST, None)
        adapter.ingest(HOST, _status(fw="4.18.0", pct=95.0))
        keys = [(r["device_uuid"], r["relation"]) for r in sink.current_rows()]
        assert len(keys) == len(set(keys))

    def test_events_log_is_append_only(self, adapter: LaneAAdapter, sink: FlatSink) -> None:
        adapter.ingest(HOST, _status())
        adapter.ingest(HOST, _status(fw="4.18.0"))
        events = sink.all_events()
        assert len(events) == 5  # 4 initial + 1 upgrade — nothing rewritten
        assert [r["id"] for r in events] == sorted(r["id"] for r in events)


class TestIdentity:
    """Identity = uuid5(host): stable across reachability, distinct per host."""

    def test_distinct_hosts_get_distinct_ids(self) -> None:
        assert device_uuid("192.168.1.50") != device_uuid("192.168.1.51")

    def test_host_id_is_stable(self) -> None:
        assert device_uuid("192.168.1.50") == device_uuid("192.168.1.50")

    def test_identity_stable_across_offline_blip(
        self, adapter: LaneAAdapter, sink: FlatSink
    ) -> None:
        adapter.ingest(HOST, _status())
        adapter.ingest(HOST, None)
        adapter.ingest(HOST, _status())
        assert len({r["device_uuid"] for r in sink.current_rows()}) == 1


class TestStorageBand:
    """Band thresholds mirror tools/fleet.py (warning >=75, critical >=90)."""

    @pytest.mark.parametrize(
        ("pct", "band"),
        [
            (0.0, "ok"),
            (74.9, "ok"),
            (75.0, "warning"),
            (89.9, "warning"),
            (90.0, "critical"),
            (100.0, "critical"),
        ],
    )
    def test_band_thresholds(self, pct: float, band: str) -> None:
        assert storage_band(pct) == band
