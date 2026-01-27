# Epiphan MCP Server - Feature Backlog

**Last Updated**: 2026-01-27
**Status**: Active Development

---

## Implementation Status Summary

| Phase | Status | Tools | Notes |
|-------|--------|-------|-------|
| Phase 1: MVP | ✅ Complete | 5 | Device, recording control |
| Phase 2: Streaming & Layout | ✅ Complete | 9 | +6 publisher CRUD tools |
| Phase 3: Fleet Management | ✅ Complete | 6 | Parallel ops, health reports |
| Phase 4: AI Analysis | ✅ Complete | 9 | **MOAT BUILDER** + fleet intelligence |
| Phase 4.2: CMS Integration | ✅ Complete | 6 | Events + schedule tools |
| Phase 4.3: Input/Output Mgmt | ✅ Complete | 5 | Network inputs, output routing |
| Phase 5: Security Hardening | ✅ Complete | - | Audit logging, concurrency limits |

**Total MCP Tools: 46** (exceeds original ~30 target)

---

## Priority Tiers

### P0: Launch Blockers
Must complete before v1.0 release.

| Feature | Effort | Impact | Status |
|---------|--------|--------|--------|
| GitHub Actions CI/CD | 2h | High | ❌ Not Started |
| Create git tag v0.4.0 | 15m | High | ❌ Not Started |
| PyPI package publishing | 1h | High | ❌ Not Started |
| CHANGELOG.md | 30m | Medium | ❌ Not Started |
| CONTRIBUTING.md | 30m | Medium | ❌ Not Started |
| LICENSE file | 10m | High | ❌ Check if exists |

### P1: Moat Builders (Competitive Advantage)
Features that make Epiphan the AI-native leader.

| Feature | Effort | Impact | Status | Notes |
|---------|--------|--------|--------|-------|
| **AI Scene Analysis** | - | - | ✅ Done | 5 tools via OpenRouter |
| Real-time Event Detection | 4h | Very High | ❌ | Auto-trigger on scene change |
| Predictive Maintenance AI | 8h | Very High | ❌ | Predict failures from trends |
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

### P3: CMS Integrations (Enterprise Value)
These drive enterprise sales.

| Feature | Effort | Impact | Status |
|---------|--------|--------|--------|
| Kaltura Upload | 8h | High | ❌ |
| Panopto Upload | 8h | High | ❌ |
| Opencast Upload | 6h | Medium | ❌ |
| Upload Progress Tracking | 4h | Medium | ❌ |
| Auto-upload on Recording Stop | 4h | High | ❌ |

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

### Sprint 1: Launch Readiness (This Week)
1. ✅ Update README with AI tools (DONE)
2. Create GitHub Actions CI/CD
3. Create v0.4.0 release tag
4. Set up PyPI publishing

### Sprint 2: Feature Polish (Next Week)
1. Expose unexposed client methods (P2 items)
2. Add `list_layouts`, `get_stream_status`
3. Add `single_touch_start/stop` tools

### Sprint 3: Moat Building (Week 3)
1. Real-time event detection
2. Predictive maintenance prototype
3. Demo video creation

---

**Document Owner**: Tim Kipper
**Review Cadence**: Weekly
