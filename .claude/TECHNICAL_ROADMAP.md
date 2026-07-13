# Technical Roadmap: Production Readiness

**Goal**: Production-grade MCP server ready for internal Epiphan demo

---

## Current State (v1.2.0 - 2026-07-12)

| Metric | Status |
|--------|--------|
| MCP Tools | 130 |
| Tests | 1,316 collected (1,309 passing / 7 hardware-skipped) |
| Integrations | 11 (Pearl, Panopto, Kaltura, Opencast, YuJa, Echo360, Q-SYS, YouTube, EC20, Epiphan Cloud, LLM/AI) |
| Typed schemas | 21/21 tool modules — every tool has described input/output schemas |
| CI | ✅ GitHub Actions (`.github/workflows/ci.yml`), format + lint gates |
| Release | ✅ v1.2.0 tagged; CHANGELOG/CONTRIBUTING/LICENSE in place |
| PyPI | ❌ NOT published (verified 2026-07-12 — README corrected to source install) |
| Production Ready | ✅ Yes (against mocked API; live-instance validation pending for YuJa/Echo360 endpoints) |

**Shipped since the original roadmap below was written** (it targeted v0.8→v1.0):
- ✅ EC20 PTZ integration (10 tools) — hardware endpoint validation still pending
- ✅ Epiphan Cloud fleet integration (12 tools)
- ✅ YuJa integration (6 tools, signed-URL S3 upload)
- ✅ Echo360 integration (6 tools, OAuth2 client-credentials + refresh rotation)
- ✅ server.py split into tools/ modules (3,001 → ~70 lines)
- ✅ Dynamic recorder/channel discovery with TTL cache (no hardcoded "recorder-1")
- ✅ Typed-schema surface complete; wire contract pinned in tests
- ✅ Security hardening (SSRF host/URL validation, audit logging with drift meta-test, retry jitter)

**Remaining Gaps** (still true):
- No webhooks / event-driven architecture
- No mDNS/SSDP network device discovery
- Per-device credentials not implemented
- PyPI publish
- Live-instance validation: YuJa + Echo360 collection endpoints, EC20 hardware endpoints

---

> **HISTORICAL PLANNING (2026-02):** everything below this line is the original
> phase plan written at v0.8.0. All four phases and the v0.5–v0.9 milestones
> are complete; the code sketches no longer match the implemented code
> (e.g. retry lives in `retry.py` with jitter, fleet ops use a semaphore +
> per-device timeout). Kept for design-intent context only — do not treat
> as current status.

## Phase 1: Reliability Hardening (Weeks 1-4)

**Goal**: Make existing features production-resilient

### 1.1 Retry Logic with Exponential Backoff

**File**: `src/epiphan_mcp/client.py`

```python
# Add to client.py
import asyncio
from typing import TypeVar, Callable, Awaitable

T = TypeVar('T')

async def with_retry(
    operation: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (httpx.RequestError, httpx.TimeoutException),
) -> T:
    """Execute operation with exponential backoff retry."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await operation()
        except retryable_exceptions as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
                await asyncio.sleep(delay)
    raise last_exception
```

**Apply to**: `_get()`, `_post()`, `_put()` methods

### 1.2 Circuit Breaker Pattern

**New file**: `src/epiphan_mcp/circuit_breaker.py`

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: timedelta = timedelta(seconds=30)

    _failure_count: int = 0
    _last_failure: datetime | None = None
    _state: CircuitState = CircuitState.CLOSED

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure = datetime.now()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def can_execute(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            if datetime.now() - self._last_failure > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN allows one request
```

**Use**: One circuit breaker per device in fleet operations

### 1.3 Parallel Fleet Operations

**File**: `src/epiphan_mcp/server.py`

Replace sequential:
```python
# Before (slow)
for host in devices:
    async with PearlClient.from_settings(host, settings) as client:
        result = await client.get_system_status()
```

With parallel:
```python
# After (fast)
import asyncio

async def _get_device_status(host: str, settings: Settings) -> dict:
    try:
        async with PearlClient.from_settings(host, settings) as client:
            return {"host": host, "status": await client.get_system_status()}
    except Exception as e:
        return {"host": host, "error": str(e)}

# In fleet operation:
tasks = [_get_device_status(host, settings) for host in devices]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 1.4 Configurable Thresholds

**File**: `src/epiphan_mcp/config.py`

```python
class Settings(BaseSettings):
    # Existing...

    # Health thresholds (make configurable)
    storage_warning_percent: float = 80.0
    storage_critical_percent: float = 90.0
    health_score_storage_weight: int = 50
    health_score_recording_weight: int = 50

    # Retry settings
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0

    # Circuit breaker
    circuit_failure_threshold: int = 5
    circuit_recovery_seconds: int = 30
```

---

## Phase 2: API Completeness (Weeks 5-8)

**Goal**: Full CRUD for streams/publishers, file download

### 2.1 Publisher CRUD Operations

**File**: `src/epiphan_mcp/client.py`

```python
async def create_publisher(
    self,
    channel_id: str,
    name: str,
    publisher_type: str,  # "rtmp", "srt", "hls"
    settings: dict[str, Any]
) -> dict[str, Any]:
    """POST /channels/{cid}/publishers"""
    return await self._post(
        f"/channels/{channel_id}/publishers",
        json={"name": name, "type": publisher_type, **settings}
    )

async def update_publisher(
    self,
    channel_id: str,
    publisher_id: str,
    settings: dict[str, Any]
) -> dict[str, Any]:
    """PUT /channels/{cid}/publishers/{pid}/settings"""
    return await self._put(
        f"/channels/{channel_id}/publishers/{publisher_id}/settings",
        json=settings
    )

async def delete_publisher(
    self,
    channel_id: str,
    publisher_id: str
) -> OperationResult:
    """DELETE /channels/{cid}/publishers/{pid}"""
    await self._delete(f"/channels/{channel_id}/publishers/{publisher_id}")
    return OperationResult(success=True, message="Publisher deleted")
```

**MCP Tools to add**:
- `create_stream` - Create new RTMP/SRT destination
- `configure_stream` - Update stream settings (bitrate, etc.)
- `delete_stream` - Remove stream destination

### 2.2 Recording File Download

**File**: `src/epiphan_mcp/client.py`

```python
async def download_recording(
    self,
    recorder_id: str,
    file_id: str,
    destination: Path | str
) -> Path:
    """GET /recorders/{rid}/archive/files/{fid} - Download recording file"""
    path = f"/recorders/{recorder_id}/archive/files/{file_id}"

    async with self.client.stream("GET", path) as response:
        response.raise_for_status()
        dest_path = Path(destination)
        with open(dest_path, "wb") as f:
            async for chunk in response.aiter_bytes(chunk_size=8192):
                f.write(chunk)

    return dest_path
```

### 2.3 Input Configuration

```python
async def configure_input(
    self,
    input_id: str,
    settings: dict[str, Any]
) -> dict[str, Any]:
    """PUT /inputs/{sid}/settings"""
    return await self._put(f"/inputs/{input_id}/settings", json=settings)
```

---

## Phase 3: Observability (Weeks 9-12)

**Goal**: Production-grade logging, metrics, health checks

### 3.1 Structured Logging

**New file**: `src/epiphan_mcp/logging.py`

```python
import json
import logging
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if hasattr(record, "device_id"):
            log_data["device_id"] = record.device_id
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logging(json_format: bool = False):
    handler = logging.StreamHandler()
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)
```

### 3.2 Health Endpoint

**File**: `src/epiphan_mcp/server.py`

```python
@mcp.tool()
async def health_check() -> dict[str, Any]:
    """
    Health check for the MCP server itself.

    Returns server status and connectivity to configured devices.
    Useful for monitoring and load balancer health checks.
    """
    settings = get_settings()
    devices = settings.get_device_list()

    device_health = []
    for host in devices:
        try:
            async with PearlClient.from_settings(host, settings) as client:
                await asyncio.wait_for(client.get_system_status(), timeout=5.0)
                device_health.append({"host": host, "reachable": True})
        except Exception as e:
            device_health.append({"host": host, "reachable": False, "error": str(e)})

    all_healthy = all(d["reachable"] for d in device_health)

    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": "0.5.0",
        "devices": device_health,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

### 3.3 Operation Metrics

```python
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class OperationMetrics:
    """Track operation success/failure rates."""

    success_count: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    failure_count: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latency_sum: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def record(self, operation: str, success: bool, latency_ms: float):
        if success:
            self.success_count[operation] += 1
        else:
            self.failure_count[operation] += 1
        self.latency_sum[operation] += latency_ms

    def get_stats(self, operation: str) -> dict:
        total = self.success_count[operation] + self.failure_count[operation]
        return {
            "total": total,
            "success_rate": self.success_count[operation] / total if total > 0 else 0,
            "avg_latency_ms": self.latency_sum[operation] / total if total > 0 else 0,
        }
```

---

## Phase 4: Advanced Features (Months 3-6)

**Goal**: Event-driven architecture, device discovery

### 4.1 Webhook Support (When Hardware Available)

This requires real hardware to test. Design now, implement with Nano.

```python
# Concept - Pearl can push events via HTTP POST
@dataclass
class PearlEvent:
    event_type: str  # "recording_started", "stream_failed", etc.
    device_id: str
    timestamp: datetime
    data: dict[str, Any]

class EventHandler:
    """Handle incoming Pearl webhook events."""

    async def on_recording_started(self, event: PearlEvent): ...
    async def on_recording_stopped(self, event: PearlEvent): ...
    async def on_stream_failed(self, event: PearlEvent): ...
    async def on_storage_warning(self, event: PearlEvent): ...
```

### 4.2 Device Discovery

```python
async def discover_devices(
    network: str = "192.168.1.0/24",
    timeout: float = 5.0
) -> list[dict[str, Any]]:
    """
    Scan network for Epiphan Pearl devices.

    Uses mDNS/Bonjour or HTTP probe to find Pearls.
    """
    # Option 1: mDNS query for _http._tcp.local
    # Option 2: Parallel HTTP GET to /api/v2.0/device on each IP
    ...
```

### 4.3 Per-Device Credentials

```python
class DeviceConfig(BaseModel):
    host: str
    username: str = "admin"
    password: str
    use_https: bool = False

class FleetConfig(BaseModel):
    default_username: str = "admin"
    default_password: str
    devices: dict[str, DeviceConfig] = {}  # Override per device
```

---

## Refactoring Tasks

### Split server.py (1382 lines is too long)

```
src/epiphan_mcp/
├── server.py              # Main MCP server setup, imports tools
├── tools/
│   ├── __init__.py
│   ├── device.py          # get_device_status, list_devices, health_check
│   ├── recording.py       # start/stop/status recording, batch ops
│   ├── streaming.py       # start/stop/status stream, publisher CRUD
│   ├── layout.py          # list_layouts, switch_layout, add_bookmark
│   ├── fleet.py           # get_fleet_status, batch operations
│   ├── schedule.py        # get_scheduled_events, event control
│   ├── storage.py         # get_storage_report, predict_storage_full
│   └── ai_tools.py        # (already exists) vision analysis
```

### Remove Hardcoded Recorder Assumptions

Search for `"recorder-1"` and make dynamic:

```python
# Before
recorder_status = await client.get_recorder_status("recorder-1")

# After
recorders = await client.get_recorders()
primary_recorder = recorders[0].id if recorders else "recorder-1"
recorder_status = await client.get_recorder_status(primary_recorder)
```

---

## Testing Additions

### Integration Tests (When Hardware Available)

```python
@pytest.mark.integration
class TestRealDevice:
    """Tests requiring real Pearl hardware."""

    @pytest.fixture
    def pearl_host(self):
        host = os.environ.get("PEARL_TEST_IP")
        if not host:
            pytest.skip("PEARL_TEST_IP not set")
        return host

    async def test_real_device_status(self, pearl_host):
        async with PearlClient(host=pearl_host, ...) as client:
            status = await client.get_system_status()
            assert status.firmware is not None

    async def test_real_recording_cycle(self, pearl_host):
        """Start, wait, stop, verify file exists."""
        ...
```

### Contract Tests

```python
def test_recorder_status_matches_api_schema():
    """Verify our mock matches real API response structure."""
    # Load OpenAPI spec
    # Validate RECORDER_STATUS_RECORDING against schema
    ...
```

---

## Milestone Checklist

### v0.5.0 - Reliability (Phase 1) ✅ COMPLETE
- [x] Retry logic with exponential backoff
- [x] Circuit breaker per device
- [x] Parallel fleet operations
- [x] Configurable thresholds
- [x] Refactor server.py into tools/ modules

### v0.6.0 - API Completeness (Phase 2) ✅ COMPLETE
- [x] Publisher CRUD (create/update/delete streams)
- [x] Recording file download
- [x] Input configuration
- [x] Event creation/control
- [x] Panopto CMS integration

### v0.7.0 - CMS Integrations (Phase 3) ✅ COMPLETE
- [x] Kaltura CMS integration (9 tools)
- [x] Opencast CMS integration (9 tools)
- [x] Upload progress tracking
- [x] Event scheduling

### v0.8.0 - AV Control (Phase 4) ✅ COMPLETE
- [x] Q-SYS JSON-RPC integration (5 tools)
- [x] YouTube Live integration (4 tools)
- [x] 82 total MCP tools
- [x] 541 tests passing

### v0.9.0 - EC20 PTZ Integration (Phase 5) ✅ COMPLETE (code)
- [x] EC20 REST API client
- [x] Basic PTZ control (pan/tilt/zoom/presets)
- [x] EC20 MCP tools (10 new)
- [ ] Real hardware validation (Pearl Mini + EC20) — endpoint paths are
      best-effort placeholders pending hardware access
- [ ] NDI integration testing

### v1.0.0+ - Production Ready ✅ SHIPPED as v1.2.0 (2026-07-12)
- [x] GitHub Actions CI/CD
- [x] Release tagged (v1.2.0: typed schemas 21/21 + YuJa + Echo360)
- [x] Documentation (README, CONTRIBUTING, CHANGELOG)
- [ ] PyPI publish — still pending (verified not live 2026-07-12)
- [ ] Battle-tested with Pearl Mini + EC20 — pending hardware
- [ ] Internal Epiphan demo
