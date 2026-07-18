# ProAV Fleet Ontology — target schema for the context graph

Extends `lane-a-design-notes.md`. Date: 2026-07-18.

This doc scopes the graph to **fleet/ProAV concepts** — devices, incidents,
technicians, venues — rather than generic entities, so Lane A, Lane B, and the
future `GraphitiSink` converge on one schema. It does NOT change the
flat-sink-first posture (see design-notes decision #3). Nothing here is built
until a multi-hop query demands it; writing it down now is what keeps the
eventual build a sink swap instead of a redesign.

## Node types

| Node | Identity | Source lane | Notes |
|---|---|---|---|
| `Device` | `uuid5(host)` — never serial (design-notes #4) | A | Pearl, Pearl Mini/Nano/Duo/Nexus, EC20. The join point: Lane-A facts and Lane-B prose dedupe onto the SAME entity. |
| `Channel` / `Recorder` | `uuid5(host + kind + id)` | A | Child of `Device`; discovery cache (`tools/discovery.py`) already enumerates these. |
| `Firmware` | version string | A | Fact object, not just an attribute — enables "all devices that were on 4.14.x when X happened". |
| `Incident` | synthesized (deferred — design-notes #5) | A+B | `provenance` (telemetry / ticket / hybrid) is first-class. Telemetry correlator owns boundary/topology; ticket-LLM owns narrative. |
| `Fix` | from ticket/RMA resolution | B | What resolved an incident: firmware upgrade, config change, RMA swap, cabling. |
| `Technician` | person ref from tickets/field notes | B | Who touched what, when. |
| `Venue` / `Room` | site + room label | B (A later if location config exposed) | Where a device physically lives. `Site` groups rooms. |
| `Integration` | platform name | A | Panopto, Kaltura, Opencast, YuJa, Q-SYS, YouTube, Echo360, Cloud — which platforms a device publishes to. |
| `Vertical` | enum | B / config | higher-ed lecture capture, live events, broadcast, medical, courts. Tags sites/accounts, drives per-vertical queries. |

## Edge types (all bi-temporal: `valid_at` / `invalid_at` set in code, per design-notes)

- `Device -[HAS_STATUS]-> {online|offline|degraded}` — Lane A emits today (spike `status` relation)
- `Device -[RUNS_FIRMWARE]-> Firmware` — Lane A emits today (`firmware` relation)
- `Device -[STORAGE_BAND]-> {ok|warning|critical}` — Lane A emits today (`storage_band` relation)
- `Device -[IS_MODEL]-> model` — Lane A emits today (`model` relation)
- `Device -[LOCATED_IN]-> Room -[PART_OF]-> Site -[IN_VERTICAL]-> Vertical`
- `Device -[PUBLISHES_TO]-> Integration`
- `Incident -[AFFECTED]-> Device`, `Incident -[RESOLVED_BY]-> Fix`, `Fix -[PERFORMED_BY]-> Technician`
- `Technician -[VISITED]-> Site`

## The canonical multi-hop query (the YAGNI gate trigger)

> "Which devices on firmware X had storage incidents after technician Y's visit at venue Z?"

The day someone actually needs to run a query shaped like this — joining
Lane-A facts (firmware, storage transitions) with Lane-B entities (technician,
venue, incident) — is the day `GraphitiSink` gets built, via
`add_nodes_and_edges_bulk()` (never `add_triplet`), mapping the spike's
`(device_uuid, relation, value, observed_at)` events onto the edges above.

## What exists today vs. this target

- **Exists**: the four Lane-A relations, gated and persisted in `FlatSink`
  (`examples/lane_a_spike/`). They map 1:1 to the first four edges above.
- **Everything else** is Lane B (tickets, RMA notes, field notes via
  `graphiti.add_episode`) or the deferred incident-synthesis spike.
