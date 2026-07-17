# External Resources — Epiphan APIs, docs & GitHub

Authoritative sources for every integration in this repo, gathered so we have them
when needed. Verified 2026-07-16.

## Epiphan GitHub org — https://github.com/epiphan-video

| Repo | What it is |
|------|-----------|
| [pearl_api_swagger_ui](https://github.com/epiphan-video/pearl_api_swagger_ui) | **Pearl REST API v2.0 OpenAPI spec** — the authoritative Pearl API. Spec file: `api/v2.0/openapi.yml`. Vendored here at [`docs/api/pearl_openapi_v2.0.yml`](api/pearl_openapi_v2.0.yml). |
| [epiphancloud_api](https://github.com/epiphan-video/epiphancloud_api) | Public API to Epiphan Cloud (`go.epiphan.cloud`). |
| [avstudio_api](https://github.com/epiphan-video/avstudio_api) | AV Studio API. |
| node_exporter | Prometheus machine-metrics exporter (not integration-relevant). |

Note: **there is no EC20 repo** in the org — no public EC20 API spec exists on GitHub.

## Pearl (encoder) — core integration (52 tools)

- **Swagger UI**: https://epiphan-video.github.io/pearl_api_swagger_ui/
- **OpenAPI spec (raw)**: https://epiphan-video.github.io/pearl_api_swagger_ui/api/v2.0/openapi.yml — **vendored at [`docs/api/pearl_openapi_v2.0.yml`](api/pearl_openapi_v2.0.yml)**
- **API guide**: https://www.epiphan.com/userguides/pearl-api/
- Base URL: `http://<pearl-ip>/api/v2.0`; HTTP Basic Auth (required since firmware 4.14.2).
- Audit of `client.py` vs this spec: [`docs/PEARL_API_AUDIT.md`](PEARL_API_AUDIT.md).

## EC20 PTZ Camera (10 tools) — **no public REST endpoint reference**

- Product: https://www.epiphan.com/products/ec20/
- Tech specs: https://www.epiphan.com/products/ec20/tech-specs/
- Software & docs: https://www.epiphan.com/support/ec20-software-and-documentation/
- User Guide (HTML): https://www.epiphan.com/userguides/ec20/Content/Home-EC20.htm
- User Guide (PDF): https://www.epiphan.com/userguides/pdfs/Epiphan-EC20-UserGuide.pdf
- **Q-SYS plugin README (PDF)**: https://www.epiphan.com/wp-content/uploads/2025/11/Epiphan_EC20_QSYS_Plugin_README.pdf — the only concrete control-capability doc (presets 0-11, Presenter/Zone modes, MJPEG preview, HTTP:80).
- REST-API firmware news: https://www.epiphan.com/product-news/new-firmware-update-control-system-updates-rest-api-usb-button-led-light-support-and-easy-file-sharing/

**Reality:** the EC20 exposes REST/VISCA/ONVIF/NDI, but Epiphan publishes **no REST
endpoint list** — the User Guide's control chapters cover only Web UI, Remote, NDI,
and ONVIF. REST paths must be captured from the camera web UI dev-tools or obtained
from support@epiphan.com. See [`docs/HARDWARE_VALIDATION.md`](HARDWARE_VALIDATION.md).

## Epiphan Cloud (12 tools)

- API repo: https://github.com/epiphan-video/epiphancloud_api
- Base URL: `https://go.epiphan.cloud/api/v2`; Bearer token auth.

## CMS integrations

| Platform | API docs | Notes |
|----------|----------|-------|
| **Panopto** | https://support.panopto.com/s/article/API-Overview | Upload flow validated. |
| **Kaltura** | https://developer.kaltura.com/api-docs/ | Chunked upload validated. |
| **Opencast** | https://docs.opencast.org/develop/api/ | Dublin Core ingest validated. |
| **YuJa** | https://support.yuja.com/hc/en-us/articles/360049580714-YuJa-API (login-gated; API guide §5.2.x) | `/services` base + `authToken` header confirmed; **list/channels paths unverified**. |
| **Echo360** | https://support.echo360.com/hc/en-us/articles/360038693311 · Swagger at `https://<host>/api-documentation` | `/public/api/v1/sections` confirmed; `/courses` inferred; rate-limit 120/min. |

## AI / LLM

- **Ollama** (local models, current direction): https://ollama.com · OpenAI-compatible endpoint `http://localhost:11434/v1/chat/completions`. Models: `qwen2.5vl:7b` (vision/OCR), `qwen2.5:14b` (text).
- **OpenRouter** (benched cloud path): https://openrouter.ai/models · https://openrouter.ai/keys
- MCP spec: https://modelcontextprotocol.io

## Validation tooling in this repo

- `scripts/validate_ec20.py` — probe EC20 endpoints against a real camera.
- `scripts/validate_cms.py` — probe YuJa/Echo360 list endpoints against live tenants.
- `examples/local_agent/` — drive the MCP tools with a local Ollama model.
