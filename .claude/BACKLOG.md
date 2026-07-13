# Epiphan MCP Server - Feature Backlog

**Last Updated**: 2026-07-12 (end of day)
**Status**: v1.2.0 shipped — 130 tools, 11 integrations, typed-schema surface complete

## ✅ DONE: Typed-Schema Conversion — 21/21 (completed 2026-07-12 PM)
All tool modules converted to typed Pydantic params + return models.
`NOT_YET_CONVERTED` is empty; the schema contract meta-tests now enforce fully
described input/output schemas server-wide, and every converted model's wire
keys are pinned in `_MODEL_MUST_KEEP_FIELDS`.

## ✅ DONE: YuJa integration (shipped 2026-07-12 PM)
`integrations/yuja.py` + `tools/yuja.py` (6 tools, born typed): static
authToken auth, signed-URL 2-step S3 upload, audit-logged upload/delete.
Follow-up below re: live-instance endpoint validation.

## ✅ DONE: v1.2.0 release (tagged + pushed 2026-07-12)
21/21 typed schemas + YuJa. `pyproject.toml`/`server.json` synced; annotated
tag with release notes on GitHub.

## ✅ DONE: Echo360 (EchoVideo) integration (shipped 2026-07-12)
`integrations/echo360.py` + `tools/echo360.py` (6 tools, born typed): OAuth2
client-credentials auth with single-use refresh-token rotation (falls back to
a fresh grant if the stored refresh token was already consumed), regional
base URLs (US/EMEA/APAC/Canada), Capture Intake signed-URL S3 upload, 429
rate-limit surfacing. Server now at 130 tools / 11 integrations. 38 new
tests; full suite 1,309 passed / 7 skipped. Follow-up below re: live-instance
endpoint validation (same situation as YuJa).

## Follow-ups (from 2026-07-12 observers)
- **[MEDIUM]** Validate YuJa list/channels endpoint paths against a live instance
  (upload flow matches YuJa's published examples; list endpoints designed from
  public docs — help-center pages are fetch-blocked). Effort: 1h with a YuJa
  sandbox token. Owner: Tim.
- **[MEDIUM]** Validate Echo360 collection endpoints (`/courses`, `/sections`,
  filter param names) against a live per-institution Swagger UI — Echo360
  gates its full API reference behind institution login, so paths are
  best-effort from public support docs. Auth flow, regional URLs, upload
  flow, pagination, and rate limits ARE confirmed. Effort: 1-2h with an
  Echo360 sandbox/test institution. Owner: Tim.
- **[LOW]** Sanity-check Panopto upload against a live instance post-fix
  (sync-file → async-stream change in `upload_file_to_s3`, 2026-07-12).
  Effort: 30min. Owner: Tim.
- **[LOW]** Process note (ARCH observer): features ship without a
  `.claude/contracts/` artifact; de-facto contract is `tests/test_tool_schemas.py`.
  Decide whether to formalize contracts or retire the convention.
- **[LOW]** Test-layout consistency: `layout.py`/`maintenance.py` coverage lives
  in `test_server.py` instead of dedicated files. Nicety, not urgent.

## ✅ DONE (v1): GTM Canvas/Blackboard LMS wedge — subdomain probe (2026-07-12)
Report: `.claude/gtm/canvas-wedge-2026-07-12.md` (v2, local-only — not pushed
to GitHub; contains customer/prospect names and deal data). HubSpot has 2,914
Higher-Ed companies (358 customers, 71 open opps, 429 warm → 344 unique
institutional domains after de-duping departmental subdomains).

**Key finding: HubSpot has zero LMS signal** (no Canvas/Blackboard property;
`web_technologies` doesn't crawl LMS subdomains) — confirmed unusable for
this purpose. Built a free, read-only DNS/HTTPS subdomain probe instead
(`canvas./blackboard./learn./moodle.<domain>`), documented as a reusable
method in project memory (`lms-detection-for-gtm`).

**Real probe results (344 domains): 112 Canvas / 44 Moodle / 25 Blackboard /
2 Brightspace / 20 unconfirmed Learn-portal / 141 Unknown.** Canvas is the
clear wedge (~4.5x Blackboard). Top-10 outreach list built from warmth ×
deal count (Stanford, NC State, Berkeley, UW, ODU, Brown, Yale, Michigan,
Duke, Minnesota — all warm Canvas accounts with active deals). Blackboard
run as a separate, smaller motion (Rochester, South Carolina, Vanderbilt as
anchors).

**Caveat: Unknown (141) ≠ no LMS** — the probe only tests 4 standard
subdomain names; big schools on non-standard hosts (UNLV=`webcampus`,
NYU/Buffalo=Brightspace, UF=`elearning`) show as Unknown. Also:
`HIGHER_EDUCATION` industry field in HubSpot is noisy (athletics depts, K-12
districts, even a couple of churches mislabeled in) — recommend a
segmentation cleanup before these counts feed a forecast. GTM Brain
(Neo4j/AuraDB) was unreachable this pass (DNS failure, likely sleeping
free-tier instance).

### Next: GTM wedge v2 — Apollo/Clay enrichment for the 141 Unknowns
Tim approved Apollo + Clay credit spend (2026-07-12) and directed use of the
Epiphan AI MCP toolset (`epiphan-ai-mcp-guide-skill`) for enrichment — this
arrived after the probe pass had already completed, so it wasn't used yet.
Scoped for tomorrow: run Apollo tech-stack enrichment + Clay company
enrichment on the 141 Unknown domains (and the 20 unconfirmed Learn-portal
ones) to convert as many as possible to a known LMS; also try a second-pass
probe with extended subdomain patterns (`elearning.`, `webcampus.`, `lms.`,
`bb.`, `elc.`, `quercus.`, `brightspace.`) first since it's free and likely
converts 50%+ on its own. Owner: Tim.

---

## Implementation Status Summary

| Phase | Status | Tools | Notes |
|-------|--------|-------|-------|
| Phase 1: MVP | ✅ Complete | 5 | Device, recording control |
| Phase 2: Streaming & Layout | ✅ Complete | 15 | +6 publisher CRUD tools |
| Phase 3: Fleet Management | ✅ Complete | 6 | Parallel ops, health reports |
| Phase 4: AI Analysis | ✅ Complete | 9 | **MOAT BUILDER** + fleet intelligence |
| Phase 4.2: CMS Integration | ✅ Complete | 45 | Panopto (9) + Kaltura (9) + Opencast (9) + YuJa (6) + Echo360 (6) |
| Phase 4.3: Input/Output Mgmt | ✅ Complete | 5 | Network inputs, output routing |
| Phase 4.4: AV Control | ✅ Complete | 9 | Q-SYS (5) + YouTube (4) |
| Phase 5: Security Hardening | ✅ Complete | - | Audit logging, concurrency limits |
| Phase 6: EC20 PTZ | ✅ Complete | 10 | PTZ camera control |
| Phase 7: Discovery & System | ✅ Complete | 9 | list_recorders, previews, system control |
| Phase 8: Epiphan Cloud | ✅ Complete | 12 | Fleet mgmt via go.epiphan.cloud |
| Phase 9: Typed-Schema Surface | ✅ Complete | 21/21 modules | Every tool has described input/output schemas |

**Total MCP Tools: 130** (verified against `src/epiphan_mcp/tools/__init__.py` 2026-07-12)

---

## Priority Tiers

### P0: Launch Blockers — nearly all resolved
| Feature | Status |
|---------|--------|
| GitHub Actions CI/CD | ✅ Done (`.github/workflows/ci.yml`) |
| CHANGELOG.md | ✅ Done |
| CONTRIBUTING.md | ✅ Done |
| LICENSE file | ✅ Done |
| Release tag | ✅ Done — v1.2.0 (superseded the original v1.0.0 target) |
| **EC20 PTZ Integration** | ✅ Complete |
| **PyPI package publishing** | ❌ Still pending — README instructs `pip install epiphan-mcp` but this is aspirational; not yet verified live on PyPI. Verify and either publish or fix the README. |

### P1: Moat Builders (Competitive Advantage)
| Feature | Effort | Impact | Status | Notes |
|---------|--------|--------|--------|-------|
| **AI Scene Analysis** | - | - | ✅ Done | 5 tools via OpenRouter |
| **EC20 PTZ Control** | 2d | Very High | ✅ Done | 10 tools implemented |
| **Predictive Maintenance AI** | 8h | Very High | ✅ Done | `predict_storage_full` |
| EC20 AI Tracking | 4h | Very High | ❌ | Presenter/zone tracking |
| Real-time Event Detection | 4h | Very High | ❌ | Auto-trigger on scene change |
| Smart Recording Suggestions | 4h | High | ❌ | AI suggests optimal settings |
| Voice Control Integration | 4h | High | ❌ | "Start recording Room 201" |
| Anomaly Detection | 6h | High | ❌ | Detect camera/audio issues |
| Multi-room Orchestration | 6h | High | ❌ | AI coordinates across rooms |

### P2: Feature Completeness (PRP Gaps) — ✅ ALL RESOLVED (verified 2026-07-12)
Every tool named in the original Phase 2/3/4 gap tables (`get_stream_status`,
`list_layouts`, `list_inputs`, `add_bookmark`, `pearl_discover_device`,
`get_storage_report`, `fleet_health_report`, `single_touch_start/stop`,
`get_scheduled_events`, `get_afu_status`, etc.) is confirmed registered in
`tools/__init__.py`. Section removed — nothing left to track here.

### P3: CMS Integrations (Enterprise Value) — ✅ COMPLETE
| Feature | Status |
|---------|--------|
| Kaltura Upload | ✅ Done (9 tools) |
| Panopto Upload | ✅ Done (9 tools) |
| Opencast Upload | ✅ Done (9 tools) |
| YuJa Upload | ✅ Done (6 tools) |
| Echo360 Upload | ✅ Done (6 tools) |
| Q-SYS AV Control | ✅ Done (5 tools) |
| YouTube Live | ✅ Done (4 tools) |
| Upload Progress Tracking | ✅ Done |
| Auto-upload on Recording Stop | ❌ Future |

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

## GTM Checklist

### Pre-Launch
- [x] GitHub Actions CI/CD (`.github/workflows/ci.yml`)
- [x] CHANGELOG.md, CONTRIBUTING.md, LICENSE
- [x] Release tag — v1.2.0 (current; supersedes the original v1.0.0 target)
- [ ] **PyPI package** — verify `pip install epiphan-mcp` actually resolves; README implies it's live but this hasn't been confirmed this session
- [ ] Demo video (5 min) showing AI features
- [ ] Blog post: "AI-Native Control for Pearl"

### Launch Day
- [ ] GitHub release notes promoted beyond the tag (blog/socials)
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
   - 130 tools / 11 integrations (Pearl core + Panopto/Kaltura/Opencast/YuJa/
     Echo360 CMS + Q-SYS/YouTube AV + EC20 + Epiphan Cloud) — broadest
     integration surface of any AV-hardware MCP server as of 2026-07-12

4. **Expansion Path**
   - Start with Pearl → Expand to other Epiphan products
   - Partner with LMS vendors (Panopto, Kaltura, YuJa, Echo360)
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

### Sprint (Completed 2026-07-12): Typed Schemas + YuJa + Echo360 + v1.2.0
1. ✅ Converted final 5 tool modules to typed schemas — 21/21 complete
2. ✅ Built YuJa integration (client + 6 tools + 32 tests)
3. ✅ Fixed latent Panopto S3-upload bug (sync file → async stream)
4. ✅ Tagged and released v1.2.0
5. ✅ Built Echo360 integration (client + 6 tools + 38 tests) — 130 tools / 11 integrations
6. ✅ Ran GTM Canvas/Blackboard wedge v1 (subdomain probe, 344 domains)

### Sprint (Next): Validation + Enrichment + Launch Readiness
1. Validate YuJa and Echo360 endpoints against live instances (both flagged MEDIUM)
2. GTM wedge v2 — Apollo/Clay enrichment for the 141 Unknown-LMS domains (approved, scoped above)
3. Verify PyPI publish status; fix or ship
4. Demo video: Pearl Mini + EC20 AI workflow

### Sprint (Future): Advanced EC20 + Automation
1. EC20 AI tracking (presenter mode, zone detection)
2. Multi-EC20 support for classrooms
3. Layout switching based on EC20 presets
4. P4 automation items (webhooks, auto-recovery, scheduled recording)

---

**Document Owner**: Tim Kipper
**Review Cadence**: Weekly

## Carried-forward items (superseded or still open as of 2026-07-12 EOD)
- [x] ~~Convert remaining 15 tool modules to typed schemas~~ — done, 21/21 complete (2026-07-12 PM)
- [ ] Pin `fastmcp<3` in pyproject.toml before next PyPI release (FastMCP 3.0 breaking-change warning observed) — still open, not yet actioned
- [ ] tests/ lint: 30 manual findings deferred (F841, SIM117, E402) — not CI-gated, still open
- [ ] Reply to Vadim: both critiques fixed, live-verified 5.1s vs 30.1s (5.9x) with offline devices — confirm this was sent; not verified this session
