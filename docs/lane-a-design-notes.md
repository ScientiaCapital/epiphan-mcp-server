# Lane-A / Fleet Context Graph — design decision record

Captures the research + devil's-advocate outcome behind the Lane-A adapter spike
(`examples/lane_a_spike/`), so the reasoning isn't lost. Date: 2026-07-16.
Source design: "Fleet Context Graph — Two-Lane Ingestion" (T. Kipper, 2026-07-12).

## The idea
Route fleet data into one temporal context graph by **data ambiguity**: structured
telemetry rides a deterministic, LLM-free lane (Lane A); human text (tickets/RMA/notes)
rides a semantic lane where an LLM earns its cost (Lane B, `graphiti.add_episode`).
`epiphan-mcp-server`'s `get_system_status` / `get_fleet_status` ARE the Lane-A source.

## What we verified about Graphiti (getzep, `main` / graphiti-core 0.29.x)
- **`add_triplet` is NOT LLM-free in a populated graph.** Its dedup short-circuit only
  fires when the edge's hybrid search returns no matches; supersession guarantees a match
  (the prior edge semantically matches the new fact in the same group), so a small-model
  LLM call runs per *changed* fact to decide which edge is contradicted. Unchanged
  re-writes hit a verbatim fast-path (free), and the timestamp LLM call is skipped when
  `valid_at` is set — so it's "≥1 small-model call per changed fact", not per write.
- **There IS a deterministic, LLM-free path** (the key devil's-advocate correction):
  Graphiti's own public `EntityEdge.save()` / `add_nodes_and_edges_bulk()` persist nodes
  and edges with **zero LLM** — they're what `add_triplet` itself calls to write. So the
  future graph sink reuses Graphiti's model + Neo4j schema/index bootstrap + temporal
  fields (`valid_at`/`invalid_at`/`expired_at`/`created_at`/`expired_at`) and does its
  own supersession — no raw Cypher from scratch, and never `resolve_extracted_edge`.
- Backends: Neo4j 5.26+ / FalkorDB / Neptune (Kuzu deprecated). An LLM + embedder are
  mandatory even for triplet-only use → must configure **Anthropic or local Ollama** +
  a local embedder to honor the repo's No-OpenAI rule.

## Decisions
1. **Deterministic Lane A.** Don't let an LLM adjudicate fleet-state supersession — it's
   non-reproducible. The justification is **latency + reproducibility + auditability**,
   NOT dollar cost (local Ollama makes per-write inference ≈ $0 anyway; the research's
   cost framing was demoted).
2. **The real savings come from the state-change gate**, not from "LLM-free writes."
   Edge-triggered gating turns O(telemetry) → O(state changes); that 3–4 orders-of-
   magnitude win is a property of gating and is achievable with or without Graphiti.
3. **Flat sink first (YAGNI gate).** ~0 production users, a TSDB already exists, and the
   GTM Neo4j Aura was found sleeping this session. A flat append-only events store +
   current-state view answers "current firmware/status" and "what changed when" today.
   Stand up the graph only when a concrete **multi-hop query** demands it — currently
   speculative, so deferred.
4. **Identity = `uuid5(host)`.** The spike proved `uuid5(serial or host)` is unstable:
   serial is often empty and absent when offline, so it forks a second identity on an
   offline blip. Host is always present and stable.
5. **Incident synthesis is unowned and harder than "deterministic" implies.** Deferred:
   a later spike does time-window + device-key correlation (Event → Alert → Incident),
   with `Incident.provenance` (telemetry / ticket / hybrid) first-class. Telemetry
   correlator authoritative for boundary/topology; ticket-LLM for narrative/root-cause.

## Is Graphiti even right?
For a ~90% deterministic / ~10% prose workload, do **not** route the deterministic 90%
through Graphiti's LLM ingestion. Options: (a) plain Neo4j + Graphiti's deterministic
persistence primitives for Lane A, Graphiti/`add_episode` for Lane B prose only; or
(b) skip the graph entirely until a multi-hop query justifies it (current choice).
Graphiti earns its complexity only when most sources are genuinely unstructured and you
need its bi-temporal + hybrid-retrieval machinery over prose.

See `examples/lane_a_spike/` for the working deterministic Lane-A adapter + flat sink.
Target node/edge schema for the eventual graph: `proav-ontology.md` (ProAV-vertical
ontology, direction set 2026-07-18 — graph effort is fleet/ProAV, not sales/GTM).
