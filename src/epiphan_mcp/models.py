"""Pydantic models for Epiphan Pearl REST API v2.0 responses.

Based on OpenAPI spec:
https://epiphan-video.github.io/pearl_api_swagger_ui/api/v2.0/openapi.yml
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============================================================
# Enums
# ============================================================


class RecordingState(str, Enum):
    """Recording state enumeration from v2.0 API."""

    STOPPED = "stopped"
    RECORDING = "recording"
    PAUSED = "paused"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"


class StreamingState(str, Enum):
    """Publisher/streaming state enumeration."""

    STOPPED = "stopped"
    STREAMING = "streaming"
    CONNECTING = "connecting"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"


class SourceType(str, Enum):
    """Input source type."""

    HDMI = "hdmi"
    SDI = "sdi"
    USB = "usb"
    NDI = "ndi"
    SRT = "srt"
    RTSP = "rtsp"
    DECKLINK = "decklink"
    WEBCAM = "webcam"
    NETWORK = "network"


class PublisherType(str, Enum):
    """Publisher (stream) type."""

    RTMP = "rtmp"
    SRT = "srt"
    HLS = "hls"
    RTSP = "rtsp"
    MPEG_TS = "mpeg_ts"


# ============================================================
# Storage Models
# ============================================================


class StorageInfo(BaseModel):
    """Storage information from GET /storages."""

    id: str = Field(default="", description="Storage ID")
    name: str = Field(default="", description="Storage name")
    type: str = Field(default="", description="Storage type (internal, usb, etc)")
    total_bytes: int = Field(default=0, description="Total storage in bytes")
    used_bytes: int = Field(default=0, description="Used storage in bytes")
    free_bytes: int = Field(default=0, description="Free storage in bytes")
    percent_used: float = Field(default=0, description="Percentage of storage used")
    mounted: bool = Field(default=True, description="Whether storage is mounted")

    @property
    def total_gb(self) -> float:
        """Total storage in GB."""
        return self.total_bytes / (1024**3) if self.total_bytes else 0

    @property
    def free_gb(self) -> float:
        """Free storage in GB."""
        return self.free_bytes / (1024**3) if self.free_bytes else 0

    model_config = ConfigDict(extra="allow")


# ============================================================
# System Models
# ============================================================


class SystemStatus(BaseModel):
    """Combined system status from device identity and storage endpoints."""

    device_name: str = Field(default="", description="Device name")
    model: str = Field(default="Unknown", description="Pearl model")
    serial_number: str = Field(default="", description="Serial number")
    firmware_version: str = Field(default="", description="Firmware version")
    uptime_seconds: int = Field(default=0, description="System uptime in seconds")
    storage_total_gb: float = Field(default=0, description="Total storage in GB")
    storage_free_gb: float = Field(default=0, description="Free storage in GB")
    storage_used_percent: float = Field(default=0, description="Storage used %")
    cpu_usage: float | None = Field(default=None, description="CPU usage %")
    memory_usage: float | None = Field(default=None, description="Memory usage %")
    temperature: float | None = Field(default=None, description="System temp in C")

    model_config = ConfigDict(extra="allow")

    @property
    def uptime_hours(self) -> float:
        """Uptime in hours."""
        return self.uptime_seconds / 3600


# ============================================================
# Recorder Models
# ============================================================


class RecorderInfo(BaseModel):
    """Recorder info from GET /recorders."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Recorder ID (e.g., 'recorder-1')")
    name: str = Field(default="", description="Recorder name")
    type: str = Field(default="", description="Recorder type")
    channel_id: str | None = Field(default=None, description="Associated channel")


class RecorderStatus(BaseModel):
    """Recorder status from GET /recorders/{rid}/status."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str = Field(default="", description="Recorder ID")
    state: RecordingState = Field(default=RecordingState.STOPPED, description="State")
    duration_seconds: int = Field(default=0, alias="duration", description="Duration")
    file_size_bytes: int = Field(default=0, alias="file_size", description="File size")
    filename: str = Field(default="", description="Current filename")
    bitrate: int | None = Field(default=None, description="Recording bitrate")


# ============================================================
# Channel Models
# ============================================================


class LayoutInfo(BaseModel):
    """Layout info within a channel."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Layout ID")
    name: str = Field(default="", description="Layout name")
    is_active: bool = Field(default=False, description="Whether active")


class ChannelInfo(BaseModel):
    """Channel info from GET /channels."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Channel ID")
    name: str = Field(default="", description="Channel name")
    layouts: list[LayoutInfo] = Field(default_factory=list, description="Layouts")
    active_layout: str | None = Field(default=None, description="Active layout ID")


class ChannelParams(BaseModel):
    """Legacy channel parameters (for backwards compatibility)."""

    model_config = ConfigDict(extra="allow")

    channel_id: int = Field(description="Channel number")
    name: str | None = Field(default=None, description="Channel name")
    rec_enabled: bool = Field(default=False, description="Recording enabled")
    publish_type: int | None = Field(default=None, description="Publish type")
    framesize: str | None = Field(default=None, description="Frame size")
    framerate: float | None = Field(default=None, description="Frame rate")
    bitrate: int | None = Field(default=None, description="Bitrate in kbps")


# ============================================================
# Publisher (Streaming) Models
# ============================================================


class PublisherInfo(BaseModel):
    """Publisher info from GET /channels/{cid}/publishers."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Publisher ID")
    name: str = Field(default="", description="Publisher name")
    type: str = Field(default="", description="Publisher type (rtmp, srt, etc)")
    enabled: bool = Field(default=True, description="Whether enabled")


class PublisherStatus(BaseModel):
    """Publisher status from GET /channels/{cid}/publishers/{pid}/status."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str = Field(default="", description="Publisher ID")
    state: StreamingState = Field(default=StreamingState.STOPPED, description="State")
    duration_seconds: int = Field(default=0, alias="duration", description="Duration")
    bitrate_actual: int | None = Field(default=None, description="Actual bitrate")
    bytes_sent: int = Field(default=0, description="Total bytes sent")
    viewers: int | None = Field(default=None, description="Number of viewers")
    destination: str = Field(default="", description="Destination URL")
    error_message: str | None = Field(default=None, description="Error if any")


class StreamStatus(BaseModel):
    """Legacy streaming status (for backwards compatibility)."""

    model_config = ConfigDict(extra="allow")

    channel_id: int = Field(description="Channel number")
    state: StreamingState = Field(description="Current streaming state")
    destination: str | None = Field(default=None, description="Stream URL")
    bitrate_actual: int | None = Field(default=None, description="Actual kbps")
    viewers: int | None = Field(default=None, description="Number of viewers")
    uptime_seconds: int | None = Field(default=None, description="Stream uptime")


# ============================================================
# Input Models
# ============================================================


class InputSource(BaseModel):
    """Input source from GET /inputs."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str = Field(default="", alias="source_id", description="Source ID")
    name: str = Field(default="", description="Source name")
    type: str = Field(default="", alias="source_type", description="Source type")
    connected: bool = Field(default=False, description="Whether connected")
    resolution: str | None = Field(default=None, description="Input resolution")
    framerate: float | None = Field(default=None, description="Input framerate")
    has_signal: bool = Field(default=False, description="Whether has signal")


# ============================================================
# Layout Models
# ============================================================


class Layout(BaseModel):
    """Layout/scene information."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    layout_id: str = Field(alias="id", description="Layout identifier")
    name: str = Field(description="Layout name")
    is_active: bool = Field(default=False, description="Whether layout is active")


# ============================================================
# Recording/Archive Models
# ============================================================


class Recording(BaseModel):
    """Recorded file information from GET /recorders/{rid}/archive/files."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str = Field(default="", alias="file_id", description="File ID")
    filename: str = Field(description="Recording filename")
    path: str = Field(default="", description="Full path on device")
    size_bytes: int = Field(default=0, alias="size", description="File size")
    duration_seconds: int = Field(default=0, alias="duration", description="Duration")
    created_at: datetime | None = Field(default=None, description="Creation time")
    recorder_id: str | None = Field(default=None, description="Source recorder")


# ============================================================
# Event/Schedule Models
# ============================================================


class ScheduledEvent(BaseModel):
    """Scheduled event from GET /schedule/events."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Event ID")
    name: str = Field(default="", description="Event name")
    status: str = Field(default="", description="Event status")
    start_time: datetime | None = Field(default=None, description="Start time")
    end_time: datetime | None = Field(default=None, description="End time")
    cms_type: str | None = Field(default=None, description="CMS type")


# ============================================================
# Device & Fleet Models
# ============================================================


class DeviceInfo(BaseModel):
    """Complete device information."""

    model_config = ConfigDict(extra="allow")

    host: str = Field(description="Device hostname or IP")
    name: str | None = Field(default=None, description="Device name")
    model: str | None = Field(default=None, description="Pearl model")
    serial: str | None = Field(default=None, description="Serial number")
    firmware: str | None = Field(default=None, description="Firmware version")
    online: bool = Field(default=False, description="Whether device is reachable")
    status: SystemStatus | None = Field(default=None, description="System status")
    channels: list[ChannelInfo] = Field(default_factory=list, description="Channels")
    recorders: list[RecorderInfo] = Field(default_factory=list, description="Recorders")


class FleetStatus(BaseModel):
    """Fleet-wide status."""

    model_config = ConfigDict(extra="allow")

    fleet_name: str = Field(description="Fleet identifier")
    total_devices: int = Field(description="Total devices in fleet")
    online_devices: int = Field(description="Devices currently online")
    recording_devices: int = Field(description="Devices currently recording")
    streaming_devices: int = Field(description="Devices currently streaming")
    devices_with_alerts: int = Field(default=0, description="Devices with issues")
    devices: list[DeviceInfo] = Field(default_factory=list, description="Device details")


# ============================================================
# Operation Results
# ============================================================


class OperationResult(BaseModel):
    """Generic operation result."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(description="Whether operation succeeded")
    message: str = Field(description="Result message")
    device: str = Field(default="", description="Device host")
    details: dict[str, Any] | None = Field(default=None, description="Details")


class BatchOperationResult(BaseModel):
    """Result of batch operations across multiple devices."""

    model_config = ConfigDict(extra="allow")

    total: int = Field(description="Total operations attempted")
    succeeded: int = Field(description="Successful operations")
    failed: int = Field(description="Failed operations")
    results: list[OperationResult] = Field(default_factory=list, description="Results")

    @property
    def all_succeeded(self) -> bool:
        """Whether all operations succeeded."""
        return self.failed == 0


# ============================================================
# Alert Models
# ============================================================


class Alert(BaseModel):
    """Device alert."""

    model_config = ConfigDict(extra="allow")

    device: str = Field(description="Device host")
    severity: str = Field(description="Alert severity: info, warning, error")
    message: str = Field(description="Alert message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")
    details: dict[str, Any] | None = Field(default=None, description="Details")


# ============================================================
# AFU (Automatic File Upload) Models
# ============================================================


class AFUStatus(BaseModel):
    """Automatic File Upload status from GET /afu/status."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="AFU ID")
    name: str = Field(default="", description="AFU name")
    protocol: str = Field(default="", description="Upload protocol")
    state: str = Field(default="", description="Current state")
    queue_count: int = Field(default=0, description="Files in queue")
    destination: str = Field(default="", description="Destination URL")


# ============================================================
# Publisher Settings Models (Phase 1 - API Expansion)
# ============================================================


class PublisherSettings(BaseModel):
    """Publisher (stream) settings for CRUD operations."""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=True, description="Whether publisher is enabled")
    url: str | None = Field(default=None, description="Stream destination URL")
    stream_key: str | None = Field(default=None, description="Stream key (for RTMP)")
    bitrate: int | None = Field(default=None, description="Target bitrate in bps")
    latency: int | None = Field(default=None, description="Latency mode (for SRT)")
    passphrase: str | None = Field(default=None, description="Encryption passphrase (for SRT)")
    mode: str | None = Field(default=None, description="Connection mode (caller/listener)")


class PublisherCreateRequest(BaseModel):
    """Request body for creating a new publisher."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(description="Display name for the publisher")
    type: PublisherType = Field(description="Publisher type (rtmp, srt, hls, rtsp, mpeg_ts)")
    settings: PublisherSettings | None = Field(
        default=None, description="Protocol-specific settings"
    )


# ============================================================
# Input/Output Models (Phase 2 - API Expansion)
# ============================================================


class InputSettings(BaseModel):
    """Network input settings for CRUD operations."""

    model_config = ConfigDict(extra="allow")

    srt_url: str | None = Field(default=None, description="SRT URL for SRT inputs")
    rtsp_url: str | None = Field(default=None, description="RTSP URL for RTSP inputs")
    ndi_source: str | None = Field(default=None, description="NDI source name")
    latency: int | None = Field(default=None, description="Buffer latency in ms")
    passphrase: str | None = Field(default=None, description="Encryption passphrase")
    mode: str | None = Field(default=None, description="Connection mode (caller/listener)")


class InputCreateRequest(BaseModel):
    """Request body for creating a new network input."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(description="Display name for the input")
    type: str = Field(description="Input type (srt, rtsp, ndi)")
    settings: InputSettings | None = Field(default=None, description="Protocol-specific settings")


class OutputInfo(BaseModel):
    """Output port information from GET /outputs."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Output ID")
    name: str = Field(default="", description="Output name (e.g., 'HDMI 1')")
    type: str = Field(default="", description="Output type (hdmi, sdi)")
    source: str | None = Field(default=None, description="Current source channel ID")
    resolution: str | None = Field(default=None, description="Output resolution")


# ============================================================
# Event Models (Phase 3 - API Expansion)
# ============================================================


class EventCreateRequest(BaseModel):
    """Request body for creating an ad-hoc event."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(description="Event name")
    start_time: datetime | None = Field(default=None, description="Start time (ISO format)")
    end_time: datetime | None = Field(default=None, description="End time (ISO format)")
    recorders: list[str] | None = Field(default=None, description="Recorder IDs to use")
    publishers: list[str] | None = Field(default=None, description="Publisher IDs to use")


# ============================================================
# Device Tool Response Models
# ============================================================


class DeviceStatusResult(BaseModel):
    """Return type of ``get_device_status``."""

    success: bool = Field(description="Whether the status was retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    status: dict[str, Any] | None = Field(
        default=None,
        description="Device status detail: uptime_hours, storage "
        "(total_gb/free_gb/used_percent), firmware, model, and recording state. "
        "Null on error.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class DeviceListResult(BaseModel):
    """Return type of ``list_devices``."""

    success: bool = Field(default=True, description="Whether the list was produced")
    fleet_name: str = Field(default="", description="Fleet identifier")
    device_count: int = Field(default=0, description="Number of configured devices")
    devices: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Configured devices, each with a numeric index and host.",
    )


# ============================================================
# System Tool Response Models
# ============================================================


class SystemControlResult(BaseModel):
    """Return type of ``reboot_device`` / ``shutdown_device``."""

    success: bool = Field(description="Whether the control action was initiated")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    error: str | None = Field(
        default=None,
        description="Error message, including the confirm=True safety-gate message.",
    )


class SystemInfoResult(BaseModel):
    """Return type of ``get_system_info``."""

    success: bool = Field(description="Whether the system info was retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    system: dict[str, Any] | None = Field(
        default=None,
        description="Full system status: device_name, model, serial_number, "
        "firmware_version, uptime_seconds, storage_total_gb/free_gb/used_percent, "
        "cpu_usage, memory_usage, temperature. Null on error.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Recording Tool Response Models
# ============================================================


class RecordingControlResult(BaseModel):
    """Return type of start/stop recording tools (single and all-recorder)."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(description="Whether the control action succeeded")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    details: dict[str, Any] | None = Field(
        default=None, description="Operation details (e.g. affected recorder id(s))"
    )
    recorder: int | str | None = Field(
        default=None, description="Recorder the action targeted (on error paths)"
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class RecordingStatusResult(BaseModel):
    """Return type of ``get_recording_status``."""

    success: bool = Field(description="Whether the status was retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    recorder: int | str | None = Field(default=None, description="Recorder queried")
    state: str | None = Field(
        default=None, description="Recording state: recording, stopped, paused, error"
    )
    duration_seconds: int | None = Field(
        default=None, description="Current recording duration in seconds"
    )
    file_size_bytes: int | None = Field(
        default=None, description="Current recording file size in bytes"
    )
    filename: str | None = Field(default=None, description="Current recording filename")
    error: str | None = Field(default=None, description="Error message on failure.")


class RecorderListResult(BaseModel):
    """Return type of ``list_recorders`` and ``get_all_recorder_status``."""

    success: bool = Field(description="Whether the recorders were retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    total_recorders: int = Field(default=0, description="Number of recorders returned")
    recorders: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Recorders: for list_recorders each has id/name/type/channel; "
        "for get_all_recorder_status each has id/state/duration_seconds/"
        "file_size_bytes/filename.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class ArchiveFilesResult(BaseModel):
    """Return type of ``list_archive_files``."""

    success: bool = Field(description="Whether the archive listing was retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    recorder: int | str | None = Field(
        default=None, description="Recorder whose archive was listed"
    )
    total_files: int = Field(default=0, description="Number of files returned")
    files: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Archive files with filename, size, duration, and creation time.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Storage Tool Response Models
# ============================================================


class InputListResult(BaseModel):
    """Return type of ``list_inputs``."""

    success: bool = Field(description="Whether the inputs were retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    total_inputs: int = Field(default=0, description="Number of input sources returned")
    inputs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Input sources, each with id, name, type, connection status, "
        "resolution, and signal info.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class StorageReportResult(BaseModel):
    """Return type of ``get_storage_report``."""

    success: bool = Field(description="Whether the storage report was retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    total_storages: int = Field(default=0, description="Number of storage volumes")
    storages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Per-volume storage info (id, type, total/free bytes, percent).",
    )
    summary: dict[str, Any] | None = Field(
        default=None,
        description="Fleet-of-volumes totals: total/free/used bytes and GB, and "
        "used_percent across all volumes.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class AFUStatusResult(BaseModel):
    """Return type of ``get_afu_status`` (Automatic File Upload)."""

    success: bool = Field(description="Whether the AFU status was retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    total_destinations: int = Field(default=0, description="Number of AFU destinations")
    destinations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="AFU destinations, each with id, name, protocol, state, "
        "queue_count, and destination URL.",
    )
    summary: dict[str, Any] | None = Field(
        default=None,
        description="Totals: total_queued_files, uploading_count, error_count.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Fleet Tool Response Models (LLM-legible tool output schemas)
# ============================================================
#
# These models are the *return types* of the fleet MCP tools. FastMCP derives
# each tool's output JSON schema from its return annotation, so returning a
# described model (instead of ``dict[str, Any]``) is what surfaces field
# descriptions to the calling LLM.
#
# Each model is the union of every key a given tool can return, including its
# empty-fleet and error branches, so construction never raises regardless of
# which branch is taken. Fields that only appear on some branches default to a
# neutral value (``None`` / ``0`` / ``[]``); on branches where they don't apply
# they serialise as explicit ``null`` — an additive wire change, not a removal.
# The ``{"success": False, "error": ...}`` convention is folded in via the
# ``success`` and ``error`` fields rather than raising ToolError.


class FleetStatusResult(BaseModel):
    """Return type of ``get_fleet_status`` — a one-call fleet-wide rollup."""

    success: bool = Field(default=True, description="Whether the rollup was produced")
    fleet_name: str = Field(default="", description="Fleet identifier")
    total_devices: int = Field(default=0, description="Total devices configured")
    online_devices: int = Field(default=0, description="Devices that responded")
    recording_devices: int = Field(default=0, description="Devices currently recording")
    average_health: float = Field(
        default=0.0, description="Mean health score (0-100) across online devices"
    )
    unhealthy_devices: int = Field(
        default=0, description="Online devices with a health score below 60"
    )
    alerts_count: int = Field(default=0, description="Number of active alerts")
    devices: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Per-device status (host, online, recording, storage_percent, "
        "health_score, health_issues; offline devices include an error).",
    )
    alerts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Active alerts, each with device, severity, and message.",
    )
    message: str | None = Field(
        default=None,
        description="Informational message (e.g. when no devices are configured).",
    )


class BatchRecordingResult(BaseModel):
    """Return type of ``batch_start_recording`` / ``batch_stop_recording``."""

    success: bool = Field(
        description="True only if the operation succeeded on every targeted device"
    )
    total_devices: int = Field(default=0, description="Number of devices targeted")
    successful: int = Field(default=0, description="Devices where the operation succeeded")
    failed: int = Field(default=0, description="Devices where the operation failed")
    results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Per-device result (device/host, success, and error on failure).",
    )
    error: str | None = Field(
        default=None, description="Error message when the batch could not be started."
    )


class FleetHealthReportResult(BaseModel):
    """Return type of ``fleet_health_report`` (AI-summarised)."""

    success: bool = Field(default=True, description="Whether the report was produced")
    fleet_name: str = Field(default="", description="Fleet identifier")
    generated_at: str | None = Field(
        default=None, description="ISO-8601 timestamp when the report was generated"
    )
    summary: str = Field(default="", description="Natural-language fleet health summary")
    health_score: int = Field(default=0, description="Rounded average fleet health score (0-100)")
    devices_online: int | None = Field(
        default=None, description="Number of devices online (omitted for empty fleets)"
    )
    devices_recording: int | None = Field(
        default=None, description="Number of devices recording (omitted for empty fleets)"
    )
    attention_required: list[dict[str, str]] = Field(
        default_factory=list,
        description="Devices needing attention, each with device, issue, and action.",
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Prioritised recommended actions."
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class MaintenanceWindowResult(BaseModel):
    """Return type of ``suggest_maintenance_window``."""

    success: bool = Field(default=True, description="Whether a suggestion was produced")
    fleet_name: str | None = Field(default=None, description="Fleet identifier")
    suggested_window: str = Field(default="", description="Recommended maintenance time window")
    confidence: str = Field(
        default="", description="Confidence in the recommendation: high, medium, or low"
    )
    reasoning: str = Field(default="", description="Explanation for the suggestion")
    devices_affected: int = Field(default=0, description="Number of devices that would be impacted")
    current_activity: str = Field(default="", description="Summary of current fleet activity")
    generated_at: str | None = Field(default=None, description="ISO-8601 timestamp when generated")
    error: str | None = Field(default=None, description="Error message on failure.")


class FleetIssuePredictionResult(BaseModel):
    """Return type of ``predict_fleet_issues``."""

    success: bool = Field(default=True, description="Whether predictions were produced")
    fleet_name: str = Field(default="", description="Fleet identifier")
    hours_ahead: int | None = Field(default=None, description="Prediction horizon in hours")
    predictions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Predicted issues, each with device, issue, timeframe, severity, and action.",
    )
    risk_level: str = Field(
        default="low", description="Overall risk: low, medium, high, or critical"
    )
    devices_at_risk: int = Field(default=0, description="Count of devices with a predicted issue")
    total_devices: int | None = Field(default=None, description="Total devices analysed")
    summary: str = Field(default="", description="AI-generated summary of predictions")
    generated_at: str | None = Field(default=None, description="ISO-8601 timestamp when generated")
    error: str | None = Field(default=None, description="Error message on failure.")


class ShiftHandoffResult(BaseModel):
    """Return type of ``generate_shift_handoff``."""

    success: bool = Field(default=True, description="Whether the handoff was produced")
    fleet_name: str = Field(default="", description="Fleet identifier")
    shift_period: str | None = Field(default=None, description="Human-readable shift time range")
    summary: str = Field(default="", description="AI-generated shift handoff summary")
    activity_summary: dict[str, Any] = Field(
        default_factory=dict, description="Recording/streaming activity statistics."
    )
    issues_resolved: list[Any] = Field(
        default_factory=list, description="Issues addressed during the shift."
    )
    attention_required: list[dict[str, str]] = Field(
        default_factory=list,
        description="Items for the next shift, each with device, issue, and priority.",
    )
    fleet_status: dict[str, Any] = Field(
        default_factory=dict, description="Current fleet health snapshot."
    )
    generated_at: str | None = Field(default=None, description="ISO-8601 timestamp when generated")
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Discovery Tool Response Models
# ============================================================


class DeviceDiscoveryResult(BaseModel):
    """Return type of ``discover_device``."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(description="Whether discovery succeeded")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    cached: bool = Field(
        default=False, description="Whether the result was served from the 5-minute cache"
    )
    recorders: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Recorders, each with id, name, type, and channel_id.",
    )
    channels: list[dict[str, Any]] = Field(
        default_factory=list, description="Channels, each with id and name."
    )
    inputs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Input sources, each with id, name, type, and connection status.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class CacheClearResult(BaseModel):
    """Return type of ``clear_discovery_cache``."""

    success: bool = Field(description="Whether the cache was cleared")
    cleared: str = Field(
        default="", description="The device_id cleared, or 'all' when clearing every device"
    )
    entries_removed: int = Field(default=0, description="Number of cache entries removed")


# ============================================================
# Layout Tool Response Models
# ============================================================


class LayoutListResult(BaseModel):
    """Return type of ``list_layouts``."""

    success: bool = Field(description="Whether the layouts were retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    channel: int | str | None = Field(
        default=None, description="Channel queried (channel-N id on success, number on error)"
    )
    total_layouts: int = Field(default=0, description="Number of layouts returned")
    layouts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Layouts, each with id, name, and active flag.",
    )
    active_layout: str | None = Field(
        default=None, description="ID of the currently active layout, if any."
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class LayoutSwitchResult(BaseModel):
    """Return type of ``switch_layout``."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(description="Whether the layout switch succeeded")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    details: dict[str, Any] | None = Field(default=None, description="Operation details")
    channel: int | str | None = Field(default=None, description="Channel targeted (on error paths)")
    error: str | None = Field(default=None, description="Error message on failure.")


class BookmarkResult(BaseModel):
    """Return type of ``add_bookmark``."""

    success: bool = Field(description="Whether the bookmark was added")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    channel: int | str | None = Field(
        default=None, description="Channel targeted (channel-N id on success, number on error)"
    )
    text: str = Field(default="", description="Bookmark text/label that was added")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    error: str | None = Field(default=None, description="Error message on failure.")
