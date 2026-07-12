# epiphan-mcp-server

**Branch**: main | **Updated**: 2026-07-12

## Status
Typed-schema conversion continued: the 5 smallest Pearl-core tool modules (discovery, layout, maintenance, streaming, inputs) are now converted to typed Pydantic params + typed return models. `NOT_YET_CONVERTED` allowlist shrank 15 → 10. Full suite green (876 passed, 7 skipped), mypy strict clean, ruff clean. 5 commits made locally; **not yet pushed** (main is 5 ahead of origin).

## Today's Focus
1. [x] Convert discovery, layout, maintenance, streaming, inputs to typed schemas
2. [ ] Push the 5 conversion commits to origin (held for confirmation)

## Done (This Session)
- [x] `feat(discovery)`: typed discover_device/clear_discovery_cache + adapted internal get_default_recorder/channel helpers (DeviceDiscoveryResult, CacheClearResult)
- [x] `feat(layout)`: list_layouts, switch_layout, add_bookmark (LayoutListResult, LayoutSwitchResult, BookmarkResult)
- [x] `feat(maintenance)`: predict_storage_full, get_device_health_score (StoragePredictionResult, DeviceHealthResult)
- [x] `feat(streaming)`: start/stop_stream, get_stream_status, list_channels, list_publishers, get_channel_preview (5 result models) + shared PreviewResolution/ImageFormat params
- [x] `feat(inputs)`: create_network_input, get/update_input_settings, list_outputs, set_output_source, get_input_preview (6 result models)
- [x] Each conversion migrated its test file (dict-indexing → attribute access) and dropped its module from NOT_YET_CONVERTED in the same commit
- [x] Security: gitleaks clean (76 commits); mypy strict + ruff clean; full suite 876 passed

## Blockers
None

## Tomorrow
Tomorrow: convert remaining 10 modules via the established recipe — start with the CMS/AV integrations (kaltura, opencast, panopto, youtube, qsys) then ai_tools, cloud, ec20, publishers, schedule (~1-2h each) | Recipe: typed Annotated params + Field(description), typed return model in models.py (extra="allow" for control-result tools wrapping OperationResult.model_dump()), serialize BaseModel lists to dicts before construction, migrate the module's test file, drop from NOT_YET_CONVERTED same commit | Backlog.md is stale (says 101 tools, actual 115; P0 items pre-date CI) — needs a cleanup pass | Observer notes: none run this session (plan mode blocked file-writing observers; reviewed inline instead) | Cost file reads MTD $240.74 vs $100 cap — looks like synthetic dev-metrics, verify it's not real gated spend

## Tech Stack
Python 3.11+ | FastMCP | httpx (async) | Pydantic v2 | pydantic-settings | pytest + respx | ruff + mypy (strict)

## Links
- GitHub: https://github.com/ScientiaCapital/epiphan-mcp-server
- silkroute (MCP client): https://github.com/ScientiaCapital/silkroute
- Pearl API docs: https://www.epiphan.com/userguides/pearl-api/

---

_Updated by typed-schema core-batch session. 2026-07-12._
