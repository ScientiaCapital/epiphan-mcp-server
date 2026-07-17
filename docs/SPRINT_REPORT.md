# Sprint Report: Audit, Research & Architecture

> **⚠️ SUPERSEDED — historical snapshot (2026-02-08).**
> Numbers below (113 tools, 674 tests, v1.0.0, 9 integrations) reflect that date and are
> no longer current; the security findings listed as open have since been fixed.
> For current status see the top-level [README](../README.md) and [CLAUDE.md](../CLAUDE.md).

**Date**: 2026-02-08
**Sprint**: Codebase Audit + Market Research + Architecture Planning
**Status**: Complete (read-only sprint, no code changes)

---

## Executive Summary

Five specialized agents audited the Epiphan Pearl MCP Server v1.0.0 across security, code quality, competitive landscape, GTM positioning, and package architecture. A Devil's Advocate agent challenged all outputs.

**Top-line findings**:
- **1 Critical** security issue (device_id allows arbitrary host connections)
- **Code quality 7.2/10** — consistent patterns but DRY violations and test gaps
- **Zero direct MCP competitors** for professional AV hardware (verified)
- **Package split is architecturally clean but premature** — ship monolith first
- **GTM projections were 3-5x too optimistic** — revised to honest numbers

---

## 1. Security Audit

### Severity Summary (Post-DA Review)

| Severity | Count | Issues |
|----------|-------|--------|
| **Critical** | 1 | Arbitrary host injection via `device_id` parameter |
| **High** | 2 | Audit logging never activated; concurrency semaphore hardcoded |
| **Medium** | 4 | SSRF to Pearl devices; SSL warning missing; error message leaks; stream keys in logs |
| **Low** | 5 | Default empty password; single timeout; OAuth retry; Q-SYS PIN plaintext; no `repr=False` |

### Critical: Arbitrary Host Injection (C1)

**Location**: `config.py:176`, `tools/device.py:23`

`get_device_host()` returns `device_id` directly as hostname when it doesn't match "default" or a numeric index. An attacker controlling the MCP client can pass `device_id="attacker.com"` and the server will connect to it with Pearl credentials.

**Combined with H1 (no audit logging)**, this creates an unlogged proxy for internal network attacks.

**Fix**: Validate `device_id` against configured device list before any network operation.

### High: Ghost Audit Logging (H1)

**Location**: `audit.py` (exists but never imported)

`audit.py` defines `log_operation()` and `SENSITIVE_OPERATIONS` including reboot, shutdown, delete. **No tool or server module imports it.** Zero forensic trail for destructive operations.

**Fix**: Import and call `audit.log_operation()` in all destructive tool functions.

### High: Hardcoded Concurrency Limit (H2)

**Location**: `server.py:376`

`FLEET_SEMAPHORE = asyncio.Semaphore(10)` — not configurable. May cause issues with large fleets (50+ devices).

**Fix**: Make configurable via `PEARL_MAX_CONCURRENT_OPS` env var.

### Security Checklist

| Check | Result |
|-------|--------|
| No hardcoded credentials | PASS |
| Configurable timeouts | PASS |
| SSL defaults safe | PASS |
| Input validation on tool params | **FAIL** (C1) |
| Audit logging on destructive ops | **FAIL** (H1) |
| Concurrency limiter | PARTIAL (hardcoded) |
| No command injection in URLs | PASS |
| Auth tokens not leaked | PARTIAL |
| No SSRF vectors | **FAIL** (Medium — targets Pearl, not server) |

### CVE Scan Results

| Package | Version | CVE | Severity | Fix |
|---------|---------|-----|----------|-----|
| pip | 24.0 | CVE-2025-8869 | Medium | Upgrade to 25.3+ |
| pip | 24.0 | CVE-2026-1703 | Medium | Upgrade to 26.0+ |
| python-multipart | 0.0.21 | CVE-2026-24486 | Medium | Upgrade to 0.0.22+ |

**Note**: `python-multipart` is a transitive dependency via `mcp` SDK, not directly used. `pip` CVEs are tooling-only.

### Secrets Scan

**gitleaks**: 36 commits scanned, 1.31 MB, **0 leaks found**.

---

## 2. Code Quality Audit

### Overall Score: 7.2/10

| Category | Score | Notes |
|----------|-------|-------|
| Tool Registration | 8/10 | Consistent import-and-wrap pattern; 4 fleet tools have inline logic |
| Error Handling | 7/10 | Consistent per-integration but uses different exception types (not normalized) |
| Async Patterns | 9/10 | No blocking calls, proper context managers, correct `asyncio.gather` |
| Type Hints | 7/10 | Full coverage but `dict[str, Any]` overused |
| Test Coverage | 6/10 | 674 tests (90%+ tool coverage, <30% edge case coverage) |
| Code Duplication | 5/10 | ~1,700 lines duplicate docstrings (DA notes: MCP requires this) |
| API Boundary | 7/10 | `tools/__init__.py` missing 15 tools from `__all__` |

### Key Issues

1. **`tools/__init__.py` incomplete**: 15 tools missing from `__all__` exports (all 10 EC20 + 5 AI tools). External Python imports fail for these tools.

2. **Test gaps**: No edge case tests (malformed input, concurrent ops, resource exhaustion). No security tests. No mutation testing.

3. **DRY violations**: Error handling boilerplate repeated in all 113 tool functions. DA argues docstring duplication is necessary for MCP protocol.

4. **Fleet tools break pattern**: `batch_start_recording`, `batch_stop_recording`, `fleet_health_report`, `get_fleet_status` have 50-200 lines of inline business logic in server.py instead of delegating to tool modules.

### Priority Fixes

1. **Fix C1** (Critical): Add device_id allowlist validation
2. **Fix H1**: Actually call `audit.log_operation()` in destructive tools
3. **Fix `__init__.py`**: Add 15 missing tools to `__all__`
4. **Add edge case tests**: Invalid inputs, timeouts, concurrent operations
5. **Extract fleet logic**: Move inline server.py fleet code to `tools/fleet.py`

---

## 3. Competitive Landscape

### Verified Claims

| Claim | Verdict | Evidence |
|-------|---------|----------|
| 17,075+ MCP servers | **TRUE** (17,057 on Glama.ai) | ~50% may be low-quality (PulseMCP curates to 8,250) |
| Zero AV hardware MCP competitors | **TRUE** with nuance | Xyte has AV *management* MCP (different category) |
| MCP donated to Linux Foundation | **TRUE** | Dec 9, 2025 via Agentic AI Foundation |
| Major vendor support | **TRUE** | OpenAI, Google, Microsoft, AWS confirmed |
| 12-18 month first-mover window | **OVERTURNED** | DA says 3-6 months; MCP server wrapping an existing API takes 2-4 weeks |
| $4.8B market size | **UNVERIFIABLE** | TAM vs SAM confusion; real SAM is "Epiphan Pearl users who want AI" |

### Competitive Map

| Competitor | Type | Threat Level |
|------------|------|-------------|
| **Xyte MCP Server** | AV device management (monitoring/ticketing) | Adjacent — different problem space |
| **OBS MCP** | Consumer streaming software control | Not competitive — different market entirely |
| **Crestron/Extron APIs** | Proprietary AV automation | Alternative solutions, not MCP |
| **Epiphan themselves** | Could build official MCP server | **Biggest threat** — internal to vendor |
| **agentic-obs** | OBS control (69 MCP tools) | Consumer only |

### Honest Positioning

- **TRUE**: "First MCP server for professional video production hardware"
- **TRUE**: "Zero direct competitors in MCP registries"
- **MISLEADING**: "Zero competitive alternatives" (Crestron APIs, Extron, custom scripts exist)
- **OVERSTATED**: "12-18 month window" (3-6 months realistic)

---

## 4. GTM Positioning

### Positioning Statement (Revised)

> **For university AV teams and corporate IT departments** who manage fleets of 5+ Epiphan Pearl video capture devices, **Pearl Copilot is an AI-native control layer** that enables natural language management of recording, streaming, and fleet operations. **Unlike manual dashboards or custom scripts**, Pearl Copilot lets you ask "What's broken?" and get instant fleet-wide diagnostics. **Because it's the only MCP server for professional AV hardware** with cross-platform orchestration across Pearl + CMS + cameras.

### ICP (Revised per DA)

| Segment | Score | Change |
|---------|-------|--------|
| Higher Ed AV Directors | 4.4/5 | Broadened to 5+ devices (was 20+) |
| Corporate L&D/Comms | 4.4/5 | No change |
| Healthcare Sim Centers | 3.9/5 | No change |
| Houses of Worship | 2.7/5 | Deprioritized |

### Value Prop (Revised per DA)

| Metric | Original | Revised (Honest) |
|--------|----------|-------------------|
| Weekly time saved | 10 hrs | 2-3 hrs |
| Annual value | $49,000 | ~$10,000 |
| License cost | $5,000/yr | $5,000/yr |
| ROI | 880% | ~95% |
| Payback | 1.4 months | ~6 months |

### Registry Strategy (Focused)

| Registry | Priority | Timeline |
|----------|----------|----------|
| **PyPI** | P0 | Week 1 — `git tag v1.0.0` triggers CI |
| **Official MCP Registry** | P0 | Week 2 — `server.json` + CLI submission |
| **Awesome MCP Servers** | P1 | Week 1 — GitHub PR |
| **GitHub Topics** | P1 | Immediate |
| Smithery.ai | P2 | Week 3 |
| Glama.ai / PulseMCP | P3 | Auto-sync from Official Registry |

### GitHub Stars (Revised per DA)

| Timeframe | Original Target | Revised Target |
|-----------|----------------|----------------|
| Month 1 | 200 | 30-50 |
| Month 6 | 1,000 | 100-200 |
| Year 1 | — | 200-300 |

---

## 5. Architecture: Package Split

### Verdict: Don't Split Now

The architecture review found **zero cross-dependencies** between core Pearl tools and integration tools. The split is technically trivial. But it's **premature**.

**Why not now**:
1. Zero PyPI downloads — optimize for adoption, not organization
2. Users must configure 2 MCP servers (worse UX)
3. 2x maintenance overhead (CI, releases, docs)
4. FastMCP multi-server patterns still evolving

**When to split** (future v2.0 criteria):
- 1,000+ PyPI downloads/month
- 3+ GitHub issues requesting separate packages
- Enterprise licensing requires separation
- Package size problematic for edge deployment

### Split-Ready Architecture

```
Package 1 (epiphan-mcp): 77 tools
├── Pearl REST API (46 tools)
├── EC20 PTZ Camera (10 tools)
├── Epiphan Cloud (12 tools)
├── AI Analysis (9 tools)
└── Shared: config.py, client.py, models.py, retry.py, llm/

Package 2 (epiphan-mcp-integrations): 36 tools
├── Panopto (9 tools)
├── Kaltura (9 tools)
├── Opencast (9 tools)
├── Q-SYS (5 tools)
└── YouTube (4 tools)
   Dependencies: fastmcp, httpx only (NO core dependency)
```

**Migration path**: v1.0 monolith now → v1.5 deprecation warnings → v2.0 split.

---

## 6. Sprint Metrics

### Project Snapshot

| Metric | Value |
|--------|-------|
| Source lines | 17,598 |
| Test lines | 15,041 (0.85 ratio) |
| Test functions | 674 passed, 7 skipped |
| MCP tools | 113 |
| Integrations | 9 platforms |
| Runtime deps | 5 |
| Commits | 36 over 16 days |
| Velocity | 2.25 commits/day |
| Secrets found | 0 |
| Critical CVEs | 0 (3 Medium in transitive deps) |

### Sprint Execution

| Phase | Tasks | Agents | Duration |
|-------|-------|--------|----------|
| Phase 1 | Security + Research + Metrics | 3 parallel | ~4 min |
| Gate 1 | Devil's Advocate Phase 1 | 1 | ~17 min |
| Phase 2 | Code Quality + GTM | 2 parallel | ~4 min |
| Gate 2 + Phase 3 | DA Phase 2 + Architecture | 2 parallel | ~10 min |
| Phase 4 | Synthesis + Verification | Lead | — |

---

## 7. Action Items (Priority Order)

### Pre-Launch (Must Fix)

- [ ] **C1**: Add device_id allowlist validation in `config.py:get_device_host()`
- [ ] **H1**: Wire up `audit.log_operation()` in destructive tools (reboot, shutdown, delete, unpair)
- [ ] Fix `tools/__init__.py` — add 15 missing tools to `__all__`
- [ ] Upgrade `pip` to 26.0+ in dev environment

### Launch (Week 1-2)

- [ ] Tag v1.0.0 and trigger PyPI publish
- [ ] Create `server.json` for Official MCP Registry
- [ ] Add GitHub topics: `mcp`, `mcp-server`, `epiphan`, `video-capture`
- [ ] Submit PR to awesome-mcp-servers

### Post-Launch (Month 1)

- [ ] Add edge case tests (target: 30% → 60% edge coverage)
- [ ] Make concurrency semaphore configurable
- [ ] Add security tests for device_id validation
- [ ] Create demo video for registry listings
- [ ] Extract fleet inline logic from server.py to tools/fleet.py

### Future (v2.0)

- [ ] Evaluate package split based on adoption data
- [ ] Add rate limiting per MCP tool
- [ ] Implement response Pydantic models (replace `dict[str, Any]`)
- [ ] Normalize error types across integrations
