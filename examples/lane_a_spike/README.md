# Lane-A adapter spike — MCP telemetry → state-change facts

The **deterministic lane** of the two-lane fleet context-graph design. It turns the
`SystemStatus` that `PearlClient.get_system_status()` already returns into
**state-change facts** — emitting a fact *only* when a field actually transitions, never
on a repeated heartbeat. No LLM: fleet-state supersession must be reproducible and
auditable.

```
per-device poll ──▶ LaneAAdapter
   get_system_status   │  derive state (online / firmware / model / storage_band)
                       │  edge-triggered gate: diff vs last-known
                       ▼
                     Sink  ──▶ FlatSink (sqlite: append-only events + current-state)
                              └▶ (future) GraphitiSink — see "Next step"
```

## Run

```bash
# No hardware — scripted sequence + self-checks (default; exits non-zero on failure):
python examples/lane_a_spike/run.py --synthetic

# Against real devices in .env (PEARL_DEVICES / PEARL_USERNAME / PEARL_PASSWORD):
python examples/lane_a_spike/run.py --live

# Demo mode — durable store + poll loop + temporal history (Ctrl-C to stop):
python examples/lane_a_spike/run.py --live --db demo.db --watch 5 --history
```

`--live` extras: `--db PATH` makes the sink durable, so the gate's last-known state
survives across runs — re-running against unchanged devices emits **0 facts** (the gate,
observable live). `--watch [SECONDS]` keeps polling (default 5s); provoke a transition
(unplug the network, upgrade firmware) and watch exactly one fact per change appear.
`--history` prints the append-only `state_events` log — "what changed, when, from what".
These flags are rejected with `--synthetic`: the self-test's exact-count assertions
require a fresh in-memory store.

The `--synthetic` run is the spike's self-test: it drives one device through
online → firmware upgrade → within-band storage move → band crossing → offline →
recover, and asserts the gate emits **exactly** the right facts (0 on identical polls,
1 per real transition), holds "≤1 open state per (device, relation)", and keeps identity
stable across online/offline.

## Design decisions this spike locked in

- **Identity = `uuid5(host)`, not serial.** Serial is often empty on Pearl v2.0 and is
  *unavailable when the device is offline*, so keying on serial forks a second identity
  for the same device on an offline blip — the synthetic run caught exactly this. The
  configured host is always present and stable; serial is an attribute, not the key.
- **Band crossings, not raw percentages.** `storage_used_percent` is bucketed into
  ok / warning (≥75) / critical (≥90) — mirroring `tools/fleet.py` — so a device that
  drifts 20%→30% emits nothing; only crossing a band edge is a fact.
- **Offline touches only `status`.** When unreachable we can't observe firmware/storage,
  so those facts are left intact and aren't falsely superseded by a blip.
- **The gate's "last-known state" comes from the sink**, not a separate cache — one store,
  no drift.
- **Raw metrics stay out.** CPU/mem/temp/exact-% belong in a TSDB; the graph/flat store
  holds entities + state-change facts only.

## Next step (deliberately deferred — YAGNI gate)

A `GraphitiSink` implementing the same `Sink` protocol drops in without touching the
adapter. Build it **only when a concrete multi-hop query exists that flat SQL can't do
cheaply** (currently speculative). When you do, per the research + devil's-advocate
review (see `docs/lane-a-design-notes.md`):

- Use Graphiti's own **deterministic** persistence — construct `EntityNode` / `EntityEdge`
  with `valid_at` / `invalid_at` / `expired_at` set in code and persist via
  `add_nodes_and_edges_bulk()` inside one transaction that closes the prior open edge and
  opens the new one. **Do NOT call `add_triplet` / `resolve_extracted_edge`** — in a
  populated graph that path runs a small-model LLM call per changed fact to adjudicate
  supersession, which is non-deterministic and unwanted for fleet state.
- Configure Graphiti with **Anthropic or local Ollama** + a local embedder (the project's
  No-OpenAI rule); an LLM/embedder is mandatory even for triplet-only use.
- Reserve LLM ingestion (`add_episode`) for **Lane B** prose (tickets/RMA/field notes),
  pinning device identity so tickets converge onto the same host-keyed device.
