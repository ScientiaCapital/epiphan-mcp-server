# Product Requirements Document (PRD)
# Epiphan Pearl MCP Server

**Version**: 1.0
**Author**: Tim Kipper
**Date**: January 22, 2026
**Status**: Draft

---

## Executive Summary

### Product Vision
Build the first AI-native control interface for professional video capture hardware by wrapping Epiphan Pearl's REST API in an MCP (Model Context Protocol) server, enabling natural language control of video recording, streaming, and fleet management.

### Why Now
- **Market Gap**: No AV hardware company has MCP integration
- **AI Trend**: Gartner's #1 trend for 2025 is "agentic AI" - autonomous systems
- **Epiphan Advantage**: Best-documented REST API in the pro AV space
- **Personal Edge**: Tim's MCP expertise (18-server NetZeroExpert OS) + new BDR role at Epiphan

### Success Metrics
| Metric | Target (Year 1) |
|--------|-----------------|
| GitHub Stars | 500+ |
| Active Installations | 100+ |
| Enterprise Customers | 10-15 |
| Annual Revenue | $150K-$250K |

---

## Part 1: Market Analysis

### Target Market Segments

#### Primary: Higher Education AV Teams
| Attribute | Details |
|-----------|---------|
| **Size** | 5,000+ institutions with AV teams in US |
| **Pain** | Managing 50-500+ rooms with 2-5 staff |
| **Budget** | $50K-$500K for AV infrastructure |
| **Tech Maturity** | High - use Panopto/Kaltura, REST APIs familiar |
| **MCP Value** | "What's the status of all classrooms?" in 5 seconds |

#### Secondary: Corporate L&D / Communications
| Attribute | Details |
|-----------|---------|
| **Size** | Fortune 1000 + mid-market (50K+ companies) |
| **Pain** | Executive town halls must not fail |
| **Budget** | $100K-$1M for video infrastructure |
| **Tech Maturity** | Medium - IT manages, wants automation |
| **MCP Value** | "Start recording in Boardroom A" during crisis |

#### Tertiary: Healthcare Simulation Centers
| Attribute | Details |
|-----------|---------|
| **Size** | 400+ academic medical centers, 290+ SSH-accredited sims |
| **Pain** | Multi-room recording for debriefing |
| **Budget** | $200K-$2M for simulation infrastructure |
| **Tech Maturity** | Medium - HIPAA concerns, want local control |
| **MCP Value** | "Record all active sim rooms" with one command |

#### Quaternary: Houses of Worship
| Attribute | Details |
|-----------|---------|
| **Size** | 117,000 medium churches (200-1,000 attendance) |
| **Pain** | Volunteer-operated, can't fail on Sunday |
| **Budget** | $10K-$100K for streaming |
| **Tech Maturity** | Low - need simplest possible interface |
| **MCP Value** | Voice command: "Start the livestream" |

### ICP Scoring Matrix

| Criterion | Weight | Higher Ed | Corporate | Healthcare | HoW |
|-----------|--------|-----------|-----------|------------|-----|
| Pain intensity | 25% | 5 | 4 | 5 | 3 |
| Budget availability | 20% | 4 | 5 | 4 | 2 |
| Tech readiness | 20% | 5 | 4 | 3 | 2 |
| Decision speed | 15% | 3 | 4 | 3 | 4 |
| Reference potential | 20% | 5 | 5 | 4 | 3 |
| **Weighted Score** | 100% | **4.4** | **4.4** | **3.9** | **2.7** |

**Priority**: Higher Ed = Corporate > Healthcare > HoW

---

## Part 2: Product Definition

### Positioning Statement

```
For university AV directors and corporate IT teams
who manage dozens to hundreds of video capture rooms,

Epiphan Pearl MCP Server is an AI control layer
that enables natural language management of recording, streaming, and fleet operations.

Unlike dashboard-hopping or custom scripting,
our product lets you ask "What's broken?" and get instant answers,
or say "Start all recordings" and have it done.
```

### Core Capabilities

#### Phase 1: MVP (Weeks 1-2)
```yaml
device_control:
  - connect_device: "Connect to Pearl by IP/hostname"
  - get_status: "Device health, storage, active operations"
  - list_channels: "All channels and their states"

recording:
  - start_recording: "Begin recording on channel"
  - stop_recording: "Stop recording on channel"
  - get_recording_status: "Current recording state"
  - list_recordings: "All recorded files"
```

#### Phase 2: Streaming & Layout (Weeks 3-4)
```yaml
streaming:
  - start_stream: "Begin streaming to destination"
  - stop_stream: "Stop streaming"
  - get_stream_status: "Bitrate, viewers, health"

layout:
  - list_layouts: "Available layouts/scenes"
  - switch_layout: "Change active layout"
  - list_sources: "Input sources available"
```

#### Phase 3: Fleet Management (Weeks 5-8)
```yaml
fleet:
  - discover_devices: "Find all Pearls on network"
  - get_fleet_status: "Status of all devices"
  - batch_start_recording: "Start recording on multiple devices"
  - batch_stop_recording: "Stop recording on multiple devices"
  - get_alerts: "Devices with issues"

intelligence:
  - schedule_recording: "Future recording with calendar"
  - auto_upload: "Push to CMS after recording"
```

### Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER LAYER                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Claude Code  │  Claude Desktop  │  Custom AI App  │  Automation   │
└───────┬───────┴────────┬─────────┴────────┬────────┴───────┬───────┘
        │                │                  │                │
        └────────────────┴────────┬─────────┴────────────────┘
                                  │ MCP Protocol (stdio/SSE)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EPIPHAN MCP SERVER                               │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Device    │  │  Recording  │  │  Streaming  │  │   Fleet    │ │
│  │   Tools     │  │   Tools     │  │   Tools     │  │   Tools    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘ │
│         │                │                │               │        │
│         └────────────────┴────────┬───────┴───────────────┘        │
│                                   │                                 │
│                    ┌──────────────▼──────────────┐                  │
│                    │      Pearl API Client       │                  │
│                    │   (async httpx + Pydantic)  │                  │
│                    └──────────────┬──────────────┘                  │
└───────────────────────────────────┼─────────────────────────────────┘
                                    │ HTTP/HTTPS + Basic Auth
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PEARL DEVICES                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Pearl Nano  │  Pearl Nexus  │  Pearl Mini  │  Pearl-2             │
│  (SRT/mobile)│  (classroom)  │  (touchscreen)│ (production)        │
└─────────────────────────────────────────────────────────────────────┘
```

### API Reference (Based on Harvard DCE Client + Epiphan Docs)

#### Authentication
```python
# HTTP Basic Auth
headers = {
    "Authorization": f"Basic {base64.b64encode(f'{username}:{password}'.encode()).decode()}"
}
```

#### Core Endpoints

| Category | Endpoint | Method | Purpose |
|----------|----------|--------|---------|
| **System** | `/admin/sysstat` | GET | System status (storage, uptime) |
| **System** | `/admin/sources` | GET | List input sources |
| **Channel** | `/admin/channel{N}/get_params.cgi` | GET | Get channel parameters |
| **Channel** | `/admin/channel{N}/set_params.cgi` | POST | Set channel parameters |
| **Recorder** | `/admin/channelm{N}/get_params.cgi` | GET | Get recorder parameters |
| **Recorder** | `/admin/channelm{N}/set_params.cgi` | POST | Set recorder parameters |
| **Files** | `/admin/mediafiles` | GET | List recorded files |
| **Files** | `/admin/download` | GET | Download recording |

#### Key Parameters

| Parameter | Values | Purpose |
|-----------|--------|---------|
| `rec_enabled` | `on` / `off` / `` | Start/stop recording |
| `publish_type` | `0-6` | Streaming destination type |
| `framesize` | `1920x1080`, etc. | Resolution |
| `rtmp_url` | URL | RTMP destination |
| `layout` | ID | Active layout |

---

## Part 3: Go-To-Market Strategy

### Revenue Model Options

#### Option A: Open Source + Enterprise Support (RECOMMENDED)

```yaml
model: "Open Core"
philosophy: "Align with Epiphan's no-recurring-fees brand"

free_tier:
  name: "Community Edition"
  price: $0
  features:
    - Full MCP server functionality
    - Single device control
    - Basic fleet discovery
    - Community support (GitHub Issues)
    - MIT License

paid_tier:
  name: "Enterprise Edition"
  price: "$5,000/year or $15,000 perpetual"
  features:
    - Everything in Community, plus:
    - Priority support (24-hour SLA)
    - Advanced fleet management
    - Custom integrations
    - Training session (2 hours)
    - Quarterly check-ins
```

#### Option B: Freemium SaaS

```yaml
model: "Cloud-Hosted MCP"
philosophy: "Managed service, recurring revenue"

free_tier:
  name: "Starter"
  price: $0
  limits:
    - 3 devices
    - 100 API calls/day
    - Community support

growth_tier:
  name: "Professional"
  price: "$99/month ($79/mo annual)"
  limits:
    - 25 devices
    - 10,000 API calls/day
    - Email support

enterprise_tier:
  name: "Enterprise"
  price: "$499/month ($399/mo annual)"
  limits:
    - Unlimited devices
    - Unlimited API calls
    - Priority support
    - SSO/SAML
    - Audit logs
```

#### Option C: One-Time License

```yaml
model: "Traditional Software License"
philosophy: "Simple, matches hardware purchase model"

standard_license:
  name: "Standard"
  price: "$2,500 one-time"
  features:
    - Up to 50 devices
    - 1 year updates
    - Email support

enterprise_license:
  name: "Enterprise"
  price: "$10,000 one-time"
  features:
    - Unlimited devices
    - 3 years updates
    - Priority support
    - Custom integrations

maintenance:
  name: "Annual Maintenance"
  price: "20% of license fee"
  features:
    - Updates beyond initial period
    - Continued support
```

### Recommended Model: Option A (Open Source + Enterprise)

**Rationale**:
1. Aligns with Epiphan's "no recurring fees" brand
2. Builds community and credibility
3. Lower barrier to adoption
4. Enterprise customers will pay for support/SLA
5. Could be acquired by Epiphan

---

## Part 4: 3-Year Financial Pro Forma

### Assumptions

```yaml
market_assumptions:
  total_epiphan_customers: 10000  # Estimate based on case studies
  customers_with_fleet: 2000      # 20% have 10+ devices
  addressable_for_mcp: 500        # 25% tech-savvy enough

conversion_assumptions:
  year_1_conversion: 2%           # 10 customers
  year_2_conversion: 5%           # 25 customers (cumulative: 35)
  year_3_conversion: 10%          # 50 customers (cumulative: 85)

pricing_assumptions:
  enterprise_annual: 5000         # Per customer per year
  enterprise_perpetual: 15000     # One-time
  mix_annual: 70%                 # 70% choose annual
  mix_perpetual: 30%              # 30% choose perpetual

cost_assumptions:
  tim_time_value: 150             # $/hour opportunity cost
  hosting_per_customer: 10        # $/month if SaaS
  support_hours_per_customer: 10  # Hours/year
```

### Year 1 Pro Forma

```
REVENUE
├── Enterprise Annual (7 customers × $5,000)        $35,000
├── Enterprise Perpetual (3 customers × $15,000)    $45,000
├── Consulting/Integration Services (5 × $5,000)    $25,000
└── TOTAL REVENUE                                  $105,000

COSTS
├── Development Time (300 hrs × $150 implicit)     ($45,000)
├── Infrastructure (hosting, tools)                 ($2,400)
├── Marketing (conference, content)                 ($5,000)
├── Legal (license review)                          ($2,000)
└── TOTAL COSTS                                    ($54,400)

NET INCOME (PRE-TAX)                                $50,600
```

### Year 2 Pro Forma

```
REVENUE
├── Recurring from Y1 Annual (7 × $5,000)           $35,000
├── New Enterprise Annual (18 × $5,000)             $90,000
├── New Enterprise Perpetual (7 × $15,000)         $105,000
├── Maintenance from Y1 Perpetual (3 × $3,000)       $9,000
├── Consulting/Integration (10 × $5,000)            $50,000
└── TOTAL REVENUE                                  $289,000

COSTS
├── Development (200 hrs × $150)                   ($30,000)
├── Support Staff (part-time contractor)           ($24,000)
├── Infrastructure                                  ($6,000)
├── Marketing                                      ($15,000)
└── TOTAL COSTS                                    ($75,000)

NET INCOME (PRE-TAX)                               $214,000
```

### Year 3 Pro Forma

```
REVENUE
├── Recurring Annual (25 × $5,000)                 $125,000
├── New Enterprise Annual (35 × $5,000)            $175,000
├── New Enterprise Perpetual (15 × $15,000)        $225,000
├── Maintenance from Perpetual (10 × $3,000)        $30,000
├── Consulting/Integration (15 × $7,500)           $112,500
├── Training Workshops (10 × $2,500)                $25,000
└── TOTAL REVENUE                                  $692,500

COSTS
├── Development (full-time equivalent)             ($80,000)
├── Support Staff (full-time)                      ($60,000)
├── Infrastructure                                 ($12,000)
├── Marketing                                      ($30,000)
├── Operations                                     ($10,000)
└── TOTAL COSTS                                   ($192,000)

NET INCOME (PRE-TAX)                               $500,500
```

### 3-Year Summary

| Metric | Year 1 | Year 2 | Year 3 | Total |
|--------|--------|--------|--------|-------|
| Customers (Cumulative) | 10 | 35 | 85 | - |
| Revenue | $105,000 | $289,000 | $692,500 | $1,086,500 |
| Costs | $54,400 | $75,000 | $192,000 | $321,400 |
| Net Income | $50,600 | $214,000 | $500,500 | $765,100 |
| Margin | 48% | 74% | 72% | 70% |

### Value-Based Pricing Justification

```yaml
customer_value_calculation:
  scenario: "University with 200 Pearl devices"

  time_savings:
    hours_saved_per_week: 10      # Fleet management
    hourly_rate: 75               # AV staff rate
    weekly_savings: 750
    annual_savings: 39000

  incident_prevention:
    incidents_prevented_per_year: 5
    cost_per_incident: 2000       # Staff time, reputation
    annual_savings: 10000

  total_annual_value: 49000

  price_as_percent_of_value:
    enterprise_annual: 5000       # 10% of value
    assessment: "Conservative, leaves money on table for adoption"
```

---

## Part 5: Competitive Landscape

### Direct Competitors (MCP for AV)

**None exist.** This is a Blue Ocean opportunity.

### Indirect Competitors

| Competitor | Type | Weakness vs. MCP |
|------------|------|------------------|
| **Epiphan Cloud** | Dashboard | Click-based, not conversational |
| **Crestron Control** | Automation | Requires programmers |
| **Custom Scripts** | DIY | Time-consuming, fragile |
| **Utelogy** | AV Mgmt Platform | Expensive, complex setup |

### Battle Card: vs. Custom Scripting

| Dimension | Custom Scripts | Epiphan MCP Server |
|-----------|----------------|-------------------|
| Setup Time | Days-weeks | Minutes |
| Maintenance | Ongoing | Zero (open source) |
| Natural Language | No | Yes |
| Community Support | No | GitHub community |
| Enterprise Support | No | Available |

---

## Part 6: Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Epiphan changes API | Medium | High | Abstract API layer, maintain compatibility |
| Low adoption | Medium | Medium | Focus on community building, content marketing |
| Competitor emerges | Low | Medium | First-mover advantage, community moat |
| Epiphan acquires/hires | Medium | Positive | Exit opportunity, validate strategy |
| Support burden | Medium | Medium | Community support first, hire for enterprise |

---

## Part 7: Launch Plan

### Pre-Launch (Weeks 1-4)
- [ ] MVP development complete
- [ ] Documentation written
- [ ] GitHub repo public
- [ ] Blog post drafted
- [ ] Demo video created

### Launch (Week 5)
- [ ] GitHub release v0.1.0
- [ ] Hacker News / Reddit posts
- [ ] LinkedIn announcement
- [ ] Email to Epiphan contacts
- [ ] Submit to MCP server directories

### Post-Launch (Weeks 6-12)
- [ ] Collect feedback, iterate
- [ ] Build case studies
- [ ] Conference talk submissions
- [ ] Enterprise outreach
- [ ] v1.0 release

---

## Appendix: Reference Links

### Epiphan Documentation
- [Pearl REST API Swagger](https://epiphan-video.github.io/pearl_api_swagger_ui/)
- [Pearl API Guide](https://www.epiphan.com/userguides/pearl-api/)
- [Legacy HTTP API](https://www.epiphan.com/userguides/pearl-api/Content/UserGuides/Streaming/integrate/thirdPartyConfig/man_br_3rdParty_controlling_with_http.htm)

### Existing Code
- [Harvard DCE epipearl](https://github.com/harvard-dce/epipearl) - Python client (Apache 2.0)

### MCP Resources
- [MCP Specification](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)

---

**Document Status**: Draft
**Next Review**: After Week 1 development
**Owner**: Tim Kipper
