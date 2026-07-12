# Epiphan MCP Server - Feature Backlog

**Last Updated**: 2026-02-05
**Status**: Production Ready + Pearl Discovery Tools Complete

> ⚠️ **Stale (flagged 2026-07-12):** counts below ("101 tools", P0 launch items) pre-date
> current reality (115 tools; CI format/lint gates exist). Needs a cleanup pass.

## Active: Typed-Schema Conversion (2026-07-12)
Converting all tool modules from `dict[str, Any]` returns to typed Pydantic
params + return models (enforced by `tests/test_tool_schemas.py` `NOT_YET_CONVERTED`
ratchet + a model-field wire-compat guard). **Done (16/21):** fleet, device, system,
recording, storage, discovery, layout, maintenance, streaming, inputs, qsys, youtube,
opencast, panopto, kaltura. **Remaining (5):** ai_tools, cloud, ec20, publishers,
schedule. Recipe + YuJa/Echo360 integration plan in PROJECT_CONTEXT "Tomorrow" handoff.

## Active: New video-CMS integrations (researched 2026-07-12)
Build order: **YuJa first** (static token, 2-step signed-URL upload, live Epiphan
partnership), then **Echo360** (GA summer 2026, dual OAuth2+Basic auth). Canvas/Moodle
= lighter publish-to-LMS tools later. Mirror the `integrations/panopto.py` pattern.
Open Qs: internal Echo360 API spec/sandbox? Canvas Studio vs Files? Moodle version targeting?

## Active: GTM LMS-migration wedge (time-sensitive)
May-2026 Canvas breach + Anthology/Blackboard fallout → LMS-migration wave. Pull
Higher-Ed accounts (HubSpot/Apollo), flag Canvas/Blackboard shops for lecture-capture
re-integration outreach. Owner: Tim. Fresh while breach signal holds.

---

## Implementation Status Summary

| Phase | Status | Tools | Notes |
|-------|--------|-------|-------|
| Phase 1: MVP | ✅ Complete | 5 | Device, recording control |
| Phase 2: Streaming & Layout | ✅ Complete | 15 | +6 publisher CRUD tools |
| Phase 3: Fleet Management | ✅ Complete | 6 | Parallel ops, health reports |
| Phase 4: AI Analysis | ✅ Complete | 9 | **MOAT BUILDER** + fleet intelligence |
| Phase 4.2: CMS Integration | ✅ Complete | 27 | Panopto (9) + Kaltura (9) + Opencast (9) |
| Phase 4.3: Input/Output Mgmt | ✅ Complete | 5 | Network inputs, output routing |
| Phase 4.4: AV Control | ✅ Complete | 9 | Q-SYS (5) + YouTube (4) |
| Phase 5: Security Hardening | ✅ Complete | - | Audit logging, concurrency limits |
| **Phase 6: EC20 PTZ** | ✅ Complete | 10 | PTZ camera control |
| **Phase 7: Discovery & System** | ✅ Complete | 9 | list_recorders, previews, system control |

**Total MCP Tools: 101**

---

## Priority Tiers

### P0: Launch Blockers
Must complete before v1.0 release.

| Feature | Effort | Impact | Status |
|---------|--------|--------|--------|
| GitHub Actions CI/CD | 2h | High | ❌ Not Started |
| Create git tag v1.0.0 | 15m | High | ❌ Not Started |
| PyPI package publishing | 1h | High | ❌ Not Started |
| CHANGELOG.md | 30m | Medium | ❌ Not Started |
| CONTRIBUTING.md | 30m | Medium | ❌ Not Started |
| LICENSE file | 10m | High | ❌ Check if exists |
| **EC20 PTZ Integration** | 2d | Very High | ✅ Complete |

### P1: Moat Builders (Competitive Advantage)
Features that make Epiphan the AI-native leader.

| Feature | Effort | Impact | Status | Notes |
|---------|--------|--------|--------|-------|
| **AI Scene Analysis** | - | - | ✅ Done | 5 tools via OpenRouter |
| **EC20 PTZ Control** | 2d | Very High | ✅ Complete | 10 tools implemented |
| EC20 AI Tracking | 4h | Very High | ❌ | Presenter/zone tracking |
| Real-time Event Detection | 4h | Very High | ❌ | Auto-trigger on scene change |
| Predictive Maintenance AI | 8h | Very High | ✅ Done | predict_storage_full |
| Smart Recording Suggestions | 4h | High | ❌ | AI suggests optimal settings |
| Voice Control Integration | 4h | High | ❌ | "Start recording Room 201" |
| Anomaly Detection | 6h | High | ❌ | Detect camera/audio issues |
| Multi-room Orchestration | 6h | High | ❌ | AI coordinates across rooms |

### P2: Feature Completeness (PRP Gaps)
Complete the planned feature set.

#### Phase 2 Gaps (Streaming & Layout)
| Feature | Effort | Status | Client Method |
|---------|--------|--------|---------------|
| `get_stream_status` | 1h | ❌ | `get_publisher_status` exists |
| `list_layouts` | 1h | ❌ | Need to add |
| `get_current_layout` | 1h | ❌ | Need to add |
| `list_sources` / `list_inputs` | 1h | ❌ | `get_inputs` exists |
| `get_source_status` | 1h | ❌ | Need to add |
| `add_bookmark` | 30m | ❌ | `add_bookmark` exists |

#### Phase 3 Gaps (Fleet Management)
| Feature | Effort | Status | Notes |
|---------|--------|--------|-------|
| `discover_devices` | 4h | ❌ | mDNS/SSDP network scan |
| `get_storage_report` | 1h | ❌ | `get_storages` exists |
| `get_health_report` | 2h | ❌ | Aggregate health data |
| `batch_command` | 2h | ❌ | Generic batch executor |
| `single_touch_start` | 30m | ❌ | Client method exists |
| `single_touch_stop` | 30m | ❌ | Client method exists |

#### Phase 4 Gaps (Intelligence)
| Feature | Effort | Status | Notes |
|---------|--------|--------|-------|
| `get_scheduled_events` | 1h | ❌ | `get_events` exists |
| `start_scheduled_event` | 30m | ❌ | `start_event` exists |
| `stop_scheduled_event` | 30m | ❌ | `stop_event` exists |
| `get_afu_status` | 30m | ❌ | Client method exists |

### P3: CMS Integrations (Enterprise Value) - ✅ COMPLETE
These drive enterprise sales.

| Feature | Effort | Impact | Status |
|---------|--------|--------|--------|
| Kaltura Upload | 8h | High | ✅ Done (9 tools) |
| Panopto Upload | 8h | High | ✅ Done (9 tools) |
| Opencast Upload | 6h | Medium | ✅ Done (9 tools) |
| Q-SYS AV Control | 4h | High | ✅ Done (5 tools) |
| YouTube Live | 4h | High | ✅ Done (4 tools) |
| Upload Progress Tracking | 4h | Medium | ✅ Done |
| Auto-upload on Recording Stop | 4h | High | ❌ Future |

### P4: Advanced Automation
| Feature | Effort | Impact | Status |
|---------|--------|--------|--------|
| Webhook Events | 8h | High | ❌ |
| Auto-recovery from Failures | 6h | High | ❌ |
| Scheduled Recording (cron) | 6h | Medium | ❌ |
| Storage Threshold Alerts | 2h | Medium | ❌ |
| Recording Retention Policies | 4h | Medium | ❌ |

### P5: Future / Nice-to-Have
| Feature | Notes |
|---------|-------|
| WebSocket Real-time Updates | Live status without polling |
| Edge AI (Local Processing) | Privacy-first, no cloud |
| Multi-tenant Fleet Management | MSP/reseller support |
| REST API Gateway | For non-MCP integrations |
| Mobile App Companion | React Native |

---

## Unexposed Client Methods

These methods exist in `PearlClient` but aren't MCP tools yet:

| Client Method | Priority | Notes |
|---------------|----------|-------|
| `add_bookmark` | P2 | Useful for chapter markers |
| `get_publishers` | P2 | List stream destinations |
| `get_publisher_status` | P2 | Stream health |
| `start_stream` (single) | P2 | Already have channel-level |
| `stop_stream` (single) | P2 | Already have channel-level |
| `get_inputs` | P2 | List sources |
| `get_channels` | P2 | List channels |
| `get_channel_preview` | P1 | Used by AI tools internally |
| `get_input_preview` | P2 | Preview source |
| `get_storages` | P2 | Storage details |
| `reboot` | P3 | System control (dangerous) |
| `shutdown` | P3 | System control (dangerous) |
| `get_events` | P2 | Scheduled events |
| `start_event` | P2 | Force start event |
| `stop_event` | P2 | Force stop event |
| `get_afu_status` | P2 | Auto-upload status |
| `single_touch_start` | P2 | Start all recording+streaming |
| `single_touch_stop` | P2 | Stop all recording+streaming |
| `get_archive_files` | P2 | List recordings |

---

## GTM Checklist

### Pre-Launch (Before v1.0)
- [ ] GitHub Actions CI/CD (.github/workflows/ci.yml)
- [ ] Create releases: v0.4.0 (current), v1.0.0 (launch)
- [ ] PyPI package: `pip install epiphan-mcp`
- [ ] Demo video (5 min) showing AI features
- [ ] Blog post: "AI-Native Control for Pearl"

### Launch Day
- [ ] GitHub release v1.0.0
- [ ] Hacker News post
- [ ] Reddit r/selfhosted, r/homelab, r/broadcasting
- [ ] LinkedIn announcement
- [ ] Submit to MCP server directories
- [ ] Email Epiphan contacts

### Post-Launch
- [ ] Collect beta tester feedback
- [ ] Build case studies (3+ customers)
- [ ] Conference talk submissions (InfoComm, EDUCAUSE)
- [ ] Enterprise outreach campaign

---

## Strategic Moat Analysis

### Why Epiphan Leads with This

1. **First AI-Native AV Control**
   - No competitor has MCP + Vision AI for AV hardware
   - 12-18 month head start if launched now

2. **Unique Capabilities Only Epiphan Can Offer**
   - Scene understanding ("Is presenter in frame?")
   - Quality monitoring ("Lighting issues detected")
   - Text extraction ("Current slide: Q4 Results")
   - Change detection ("Slide advanced")

3. **Defensible Advantages**
   - Deep Pearl API integration
   - Training data from real production environments
   - Customer feedback loop

4. **Expansion Path**
   - Start with Pearl → Expand to other Epiphan products
   - Partner with LMS vendors (Panopto, Kaltura)
   - White-label for integrators

### Competitive Response Timeline
| Competitor | Likely Response Time |
|------------|---------------------|
| Crestron | 18-24 months |
| Extron | 18-24 months |
| Barco | 12-18 months |
| AJA | Never (different market) |
| Magewell | 12-18 months |

**Window of Opportunity: 12-18 months to establish dominance**

---

## Next Sprint Recommendations

### Sprint (Completed): EC20 PTZ Integration
1. ✅ Connect Pearl Mini to network, test existing tools
2. ✅ Connect EC20 via NDI, document REST API
3. ✅ Create EC20 client (pan/tilt/zoom/presets)
4. ✅ Create 10 EC20 MCP tools
5. ⏳ Integration test: Recording + PTZ workflow (needs hardware)

### Sprint (Next): Launch Readiness
1. Create GitHub Actions CI/CD
2. Create v1.0.0 release tag
3. Set up PyPI publishing
4. Demo video: Pearl Mini + EC20 AI workflow

### Sprint (Future): Advanced EC20
1. EC20 AI tracking (presenter mode, zone detection)
2. Multi-EC20 support for classrooms
3. Layout switching based on EC20 presets

---

**Document Owner**: Tim Kipper
**Review Cadence**: Weekly

## 2026-07-12 — End Day findings
- [ ] Convert remaining 15 tool modules to typed schemas (recipe established; ~1-2h each): ai_tools, cloud, discovery, ec20, inputs, kaltura, layout, maintenance, opencast, panopto, publishers, qsys, schedule, streaming, youtube
- [ ] Pin `fastmcp<3` in pyproject.toml before next PyPI release (FastMCP 3.0 breaking-change warning observed)
- [ ] tests/ lint: 30 manual findings deferred (F841, SIM117, E402) — not CI-gated
- [ ] Reply to Vadim: both critiques fixed, live-verified 5.1s vs 30.1s (5.9x) with offline devices
