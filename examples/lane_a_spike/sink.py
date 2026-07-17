"""Sinks for Lane-A state-change facts.

The adapter emits a `StateEvent` on every real state transition. A `Sink` persists
those events and answers "what is this device's last-known state?" so the adapter's
edge-triggered gate can tell a real change from a repeated heartbeat.

`FlatSink` (stdlib sqlite3, zero deps) is the spike's default: an append-only
`state_events` log + a `current_state` table whose PRIMARY KEY (device_uuid, relation)
enforces the "≤1 open state per (device, relation)" invariant deterministically — the
same invariant a future graph sink must uphold, proven here cheaply.

The `Sink` protocol is the seam a future `GraphitiSink` drops into (see README).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


def utcnow_iso() -> str:
    """UTC timestamp, ISO-8601."""
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class StateEvent:
    """One deterministic Lane-A fact: a device's `relation` changed to `new_value`."""

    device_uuid: str
    host: str
    relation: str  # "status" | "firmware" | "model" | "storage_band"
    old_value: str | None
    new_value: str
    valid_at: str  # observation time (event/valid time), ISO-8601


class Sink(Protocol):
    """What the adapter needs from a persistence backend."""

    def last_state(self, device_uuid: str) -> dict[str, str]:
        """Current value per relation for a device (empty if unseen)."""
        ...

    def record(self, event: StateEvent) -> None:
        """Persist a state-change fact and advance the current state."""
        ...


class FlatSink:
    """Append-only events + current-state view, backed by sqlite3."""

    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS state_events (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                device_uuid  TEXT NOT NULL,
                host         TEXT NOT NULL,
                relation     TEXT NOT NULL,
                old_value    TEXT,
                new_value    TEXT NOT NULL,
                valid_at     TEXT NOT NULL,
                recorded_at  TEXT NOT NULL
            );
            -- PRIMARY KEY enforces exactly one open state per (device, relation).
            CREATE TABLE IF NOT EXISTS current_state (
                device_uuid  TEXT NOT NULL,
                relation     TEXT NOT NULL,
                value        TEXT NOT NULL,
                valid_at     TEXT NOT NULL,
                PRIMARY KEY (device_uuid, relation)
            );
            """
        )
        self._conn.commit()

    def last_state(self, device_uuid: str) -> dict[str, str]:
        rows = self._conn.execute(
            "SELECT relation, value FROM current_state WHERE device_uuid = ?",
            (device_uuid,),
        ).fetchall()
        return {r["relation"]: r["value"] for r in rows}

    def record(self, event: StateEvent) -> None:
        self._conn.execute(
            "INSERT INTO state_events "
            "(device_uuid, host, relation, old_value, new_value, valid_at, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event.device_uuid,
                event.host,
                event.relation,
                event.old_value,
                event.new_value,
                event.valid_at,
                utcnow_iso(),
            ),
        )
        # Close-open supersession, atomically: the upsert replaces the prior open
        # state for this (device, relation) — never two open rows.
        self._conn.execute(
            "INSERT INTO current_state (device_uuid, relation, value, valid_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(device_uuid, relation) "
            "DO UPDATE SET value = excluded.value, valid_at = excluded.valid_at",
            (event.device_uuid, event.relation, event.new_value, event.valid_at),
        )
        self._conn.commit()

    # --- read helpers for display / assertions ---

    def all_events(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM state_events ORDER BY id"
        ).fetchall()

    def current_rows(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM current_state ORDER BY device_uuid, relation"
        ).fetchall()
