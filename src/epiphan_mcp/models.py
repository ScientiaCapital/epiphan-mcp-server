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


# ============================================================
# Maintenance Tool Response Models
# ============================================================


class StoragePredictionResult(BaseModel):
    """Return type of ``predict_storage_full``."""

    success: bool = Field(description="Whether the prediction was produced")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    hours_until_full: float | None = Field(
        default=None, description="Estimated hours until storage is full (inf if not filling)"
    )
    storage_free_gb: float | None = Field(default=None, description="Current free storage in GB")
    storage_total_gb: float | None = Field(default=None, description="Total storage capacity in GB")
    storage_used_percent: float | None = Field(
        default=None, description="Percentage of storage currently used"
    )
    is_recording: bool | None = Field(
        default=None, description="Whether the recorder is currently recording"
    )
    bitrate_mbps: float | None = Field(
        default=None, description="Actual (if recording) or assumed recording bitrate in Mbps"
    )
    warning: bool | None = Field(
        default=None, description="True when storage is critically low (>=90% used or <2h left)"
    )
    recommendation: str | None = Field(default=None, description="Suggested action")
    error: str | None = Field(default=None, description="Error message on failure.")


class DeviceHealthResult(BaseModel):
    """Return type of ``get_device_health_score``."""

    success: bool = Field(description="Whether the health assessment was produced")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    score: int | None = Field(
        default=None, description="Overall health score 0-100 (higher is better)"
    )
    categories: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-category breakdown (storage, recording), each with score, "
        "max, and healthy flag.",
    )
    issues: list[str] = Field(default_factory=list, description="Detected health issues.")
    is_recording: bool | None = Field(
        default=None, description="Whether the device is currently recording"
    )
    recommendation: str | None = Field(
        default=None, description="Suggested action based on the score"
    )
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Streaming Tool Response Models
# ============================================================


class StreamControlResult(BaseModel):
    """Return type of ``start_stream`` / ``stop_stream``."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(description="Whether the stream control action succeeded")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    details: dict[str, Any] | None = Field(default=None, description="Operation details")
    channel: int | str | None = Field(default=None, description="Channel targeted (on error paths)")
    error: str | None = Field(default=None, description="Error message on failure.")


class StreamStatusResult(BaseModel):
    """Return type of ``get_stream_status``."""

    success: bool = Field(description="Whether the stream status was retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    channel: int | str | None = Field(
        default=None, description="Channel queried (channel-N id on success, number on error)"
    )
    publisher: str | None = Field(default=None, description="Publisher ID queried")
    state: str | None = Field(
        default=None, description="Stream state: streaming, stopped, connecting, error"
    )
    duration_seconds: int | None = Field(
        default=None, description="How long the stream has been active, in seconds"
    )
    bitrate_bps: int | None = Field(default=None, description="Current bitrate in bits per second")
    bytes_sent: int | None = Field(
        default=None, description="Total bytes sent since the stream started"
    )
    destination: str | None = Field(default=None, description="Stream destination URL")
    error: str | None = Field(default=None, description="Error message on failure.")


class ChannelListResult(BaseModel):
    """Return type of ``list_channels``."""

    success: bool = Field(description="Whether the channels were retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    total_channels: int = Field(default=0, description="Number of channels returned")
    channels: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Channels, each with id and name (plus publishers/layouts when requested).",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class PublisherListResult(BaseModel):
    """Return type of ``list_publishers``."""

    success: bool = Field(description="Whether the publishers were retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    channel: int | str | None = Field(
        default=None, description="Channel queried (channel-N id on success, number on error)"
    )
    total_publishers: int = Field(default=0, description="Number of publishers returned")
    publishers: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Publishers, each with id, name, type, and enabled status.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class ChannelPreviewResult(BaseModel):
    """Return type of ``get_channel_preview``."""

    success: bool = Field(description="Whether the preview was captured")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    channel: int | str | None = Field(
        default=None, description="Channel previewed (channel-N id on success, number on error)"
    )
    format: str | None = Field(default=None, description="Image format: 'jpg' or 'png'")
    preview_base64: str | None = Field(
        default=None, description="Preview image bytes, base64-encoded (ASCII)."
    )
    size_bytes: int | None = Field(default=None, description="Decoded image size in bytes")
    resolution: str | None = Field(
        default=None, description="Requested resolution, or null when using the device default."
    )
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Input/Output Tool Response Models
# ============================================================


class InputCreateResult(BaseModel):
    """Return type of ``create_network_input``."""

    success: bool = Field(description="Whether the input was created")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    input: dict[str, Any] | None = Field(
        default=None, description="Created input info, including the assigned ID."
    )
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    error: str | None = Field(default=None, description="Error message on failure.")


class InputSettingsResult(BaseModel):
    """Return type of ``get_input_settings``."""

    success: bool = Field(description="Whether the input settings were retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    input_id: str | None = Field(default=None, description="Input source ID queried")
    settings: dict[str, Any] | None = Field(
        default=None,
        description="Input settings (URL, passphrase, latency, etc.), protocol-dependent.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class InputUpdateResult(BaseModel):
    """Return type of ``update_input_settings``."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(description="Whether the input settings were updated")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    details: dict[str, Any] | None = Field(default=None, description="Operation details")
    input_id: str | None = Field(default=None, description="Input source ID (on error paths)")
    error: str | None = Field(default=None, description="Error message on failure.")


class OutputListResult(BaseModel):
    """Return type of ``list_outputs``."""

    success: bool = Field(description="Whether the outputs were retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    total_outputs: int = Field(default=0, description="Number of output ports returned")
    outputs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Output ports, each with id, name, type, current source, and resolution.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class OutputSourceResult(BaseModel):
    """Return type of ``set_output_source``."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(description="Whether the output source was set")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    details: dict[str, Any] | None = Field(default=None, description="Operation details")
    output_id: str | None = Field(default=None, description="Output ID (on error paths)")
    error: str | None = Field(default=None, description="Error message on failure.")


class InputPreviewResult(BaseModel):
    """Return type of ``get_input_preview``."""

    success: bool = Field(description="Whether the preview was captured")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    input_id: str | None = Field(default=None, description="Input source ID previewed")
    format: str | None = Field(default=None, description="Image format: 'jpg' or 'png'")
    preview_base64: str | None = Field(
        default=None, description="Preview image bytes, base64-encoded (ASCII)."
    )
    size_bytes: int | None = Field(default=None, description="Decoded image size in bytes")
    resolution: str | None = Field(
        default=None, description="Requested resolution, or null when using the device default."
    )
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Schedule Tool Response Models
# ============================================================


class ScheduledEventListResult(BaseModel):
    """Return type of ``get_scheduled_events``."""

    success: bool = Field(description="Whether the events were retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    total_events: int = Field(default=0, description="Number of events returned")
    events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Scheduled events, each with id/name/status/start_time/"
        "end_time/cms_type as reported by the CMS integration.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class SingleTouchResult(BaseModel):
    """Return type of ``single_touch_start`` / ``single_touch_stop``."""

    success: bool = Field(description="Whether the single-touch action succeeded")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    error: str | None = Field(default=None, description="Error message on failure.")


class EventCreateResult(BaseModel):
    """Return type of ``create_scheduled_event``."""

    success: bool = Field(description="Whether the event was created")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    event: dict[str, Any] | None = Field(
        default=None, description="Created event info including the assigned ID."
    )
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    error: str | None = Field(default=None, description="Error message on failure.")


class EventControlResult(BaseModel):
    """Return type of ``pause_event`` / ``resume_event``."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(description="Whether the control action succeeded")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    details: dict[str, Any] | None = Field(
        default=None, description="Operation details (e.g. affected event id)"
    )
    event_id: str | None = Field(default=None, description="Event the action targeted")
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Publisher Tool Response Models
# ============================================================


class PublisherCreateResult(BaseModel):
    """Return type of ``create_publisher``."""

    success: bool = Field(description="Whether the publisher was created")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    channel: int | str | None = Field(
        default=None, description="Channel the publisher was created on"
    )
    publisher: dict[str, Any] | None = Field(
        default=None, description="Created publisher info including the assigned ID."
    )
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    error: str | None = Field(default=None, description="Error message on failure.")


class PublisherOperationResult(BaseModel):
    """Return type of ``delete_publisher`` / ``update_publisher_settings`` /
    ``rename_publisher``."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(description="Whether the operation succeeded")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    details: dict[str, Any] | None = Field(
        default=None, description="Operation details (e.g. affected publisher id)"
    )
    channel: int | str | None = Field(
        default=None, description="Channel the publisher belongs to (on error paths)"
    )
    publisher: str | None = Field(
        default=None, description="Publisher the operation targeted (on error paths)"
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class PublisherSettingsResult(BaseModel):
    """Return type of ``get_publisher_settings``."""

    success: bool = Field(description="Whether the settings were retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    channel: int | str | None = Field(default=None, description="Channel queried")
    publisher: str | None = Field(default=None, description="Publisher queried")
    settings: dict[str, Any] | None = Field(
        default=None, description="Publisher settings: URL, stream key, bitrate, enabled, etc."
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class PublisherTypesResult(BaseModel):
    """Return type of ``list_publisher_types``."""

    success: bool = Field(description="Whether the types were retrieved")
    device: str = Field(default="", description="Device host, or the requested device_id on error")
    channel: int | str | None = Field(default=None, description="Channel queried")
    types: list[str] = Field(
        default_factory=list,
        description="Available publisher protocols: rtmp, srt, hls, rtsp, mpeg_ts.",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# AI Tool Response Models
# ============================================================
#
# AI tools predate the ``device`` key convention: they identify the device
# under the ``device_id`` key. The models keep that name — renaming it would
# be a wire-compat break for existing MCP clients.


class SceneAnalysisResult(BaseModel):
    """Return type of ``analyze_channel_scene``."""

    success: bool = Field(description="Whether the analysis succeeded")
    analysis: str | None = Field(default=None, description="Analysis result text")
    analysis_type: str | None = Field(
        default=None,
        description="Type of analysis performed: scene_description, content_detection, "
        "quality_check, text_extraction, presenter_detection.",
    )
    model_used: str | None = Field(default=None, description="LLM model used")
    timestamp: str | None = Field(default=None, description="Analysis timestamp (ISO 8601)")
    image_hash: str | None = Field(default=None, description="Hash of the analyzed frame")
    device_id: str = Field(default="", description="Device that was analyzed")
    channel: str | None = Field(default=None, description="Channel that was analyzed")
    error: str | None = Field(default=None, description="Error message on failure.")


class TextExtractionResult(BaseModel):
    """Return type of ``extract_text_from_preview``."""

    success: bool = Field(description="Whether the extraction succeeded")
    text: str | None = Field(default=None, description="Extracted text content")
    model_used: str | None = Field(default=None, description="LLM model used")
    timestamp: str | None = Field(default=None, description="Analysis timestamp (ISO 8601)")
    image_hash: str | None = Field(default=None, description="Hash of the analyzed frame")
    device_id: str = Field(default="", description="Device that was analyzed")
    channel: str | None = Field(default=None, description="Channel that was analyzed")
    error: str | None = Field(default=None, description="Error message on failure.")


class ChangeDetectionResult(BaseModel):
    """Return type of ``detect_layout_changes``."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(description="Whether the change detection ran")
    device_id: str = Field(default="", description="Device that was monitored")
    channel: str | None = Field(default=None, description="Channel that was monitored")
    changed: bool | None = Field(default=None, description="Whether a change was detected")
    change_type: str | None = Field(
        default=None, description="Type of change: first_frame, none, or content_change."
    )
    previous_hash: str | None = Field(default=None, description="Hash of the previous frame")
    current_hash: str | None = Field(default=None, description="Hash of the current frame")
    message: str | None = Field(default=None, description="Description of the change")
    error: str | None = Field(default=None, description="Error message on failure.")


class QualityCheckResult(BaseModel):
    """Return type of ``check_video_quality``."""

    success: bool = Field(description="Whether the quality check succeeded")
    quality_report: str | None = Field(default=None, description="Detailed quality assessment")
    model_used: str | None = Field(default=None, description="LLM model used")
    timestamp: str | None = Field(default=None, description="Analysis timestamp (ISO 8601)")
    image_hash: str | None = Field(default=None, description="Hash of the analyzed frame")
    device_id: str = Field(default="", description="Device that was analyzed")
    channel: str | None = Field(default=None, description="Channel that was analyzed")
    error: str | None = Field(default=None, description="Error message on failure.")


class ChangeCacheClearResult(BaseModel):
    """Return type of ``clear_change_detection_cache``."""

    success: bool = Field(description="Whether the cache was cleared")
    cleared: list[str] = Field(
        default_factory=list,
        description="Cache keys cleared: 'device:channel' entries, or ['all'].",
    )
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    error: str | None = Field(default=None, description="Error message on failure.")


class RecordingIssuesResult(BaseModel):
    """Return type of ``detect_recording_issues``."""

    success: bool = Field(description="Whether the issue detection ran")
    issues_detected: bool | None = Field(
        default=None, description="Whether any problems were found"
    )
    issues: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Detected issues, each with type/description/severity/action.",
    )
    quality_score: int | None = Field(
        default=None, description="Overall quality rating from 0 (worst) to 100 (best)"
    )
    recommendation: str | None = Field(
        default=None, description="Suggested action if issues were found"
    )
    model_used: str | None = Field(default=None, description="LLM model used")
    timestamp: str | None = Field(default=None, description="Analysis timestamp (ISO 8601)")
    device_id: str = Field(default="", description="Device that was checked")
    channel: str | None = Field(default=None, description="Channel that was checked")
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Q-SYS Integration Tool Response Models
# ============================================================
#
# Q-SYS tools predate the shared {success, ...} convention: the list/status
# tools carry no ``success`` key, and error paths return a bare ``error``.
# These models mirror each tool's actual dict shape (union of success + error
# keys, neutral defaults) rather than imposing a success flag.


class QSysComponentListResult(BaseModel):
    """Return type of ``list_qsys_components``."""

    components: list[dict[str, Any]] = Field(
        default_factory=list, description="Matching Q-SYS components, each with Name and Type."
    )
    count: int | None = Field(default=None, description="Number of components returned")
    filter: str | None = Field(
        default=None, description="Name filter applied ('all' when unfiltered)"
    )
    qsys_host: str | None = Field(default=None, description="Q-SYS Core host queried")
    error: str | None = Field(default=None, description="Error message on failure.")


class QSysPearlStatusResult(BaseModel):
    """Return type of ``qsys_get_pearl_status``."""

    status: dict[str, Any] | None = Field(
        default=None,
        description="Pearl state via Q-SYS: is_recording, is_streaming, current_layout.",
    )
    component: str | None = Field(default=None, description="Q-SYS Pearl component queried")
    qsys_host: str | None = Field(default=None, description="Q-SYS Core host queried")
    error: str | None = Field(default=None, description="Error message on failure.")


class QSysControlResult(BaseModel):
    """Return of ``qsys_start_recording`` / ``qsys_stop_recording`` / ``qsys_switch_layout``."""

    success: bool | None = Field(default=None, description="Whether the control action succeeded")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    component: str | None = Field(default=None, description="Q-SYS component targeted")
    layout_id: str | None = Field(
        default=None, description="Layout switched to (switch_layout only)"
    )
    qsys_host: str | None = Field(default=None, description="Q-SYS Core host")
    result: dict[str, Any] | None = Field(
        default=None, description="Raw Q-SYS RPC result payload."
    )
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# YouTube Live Integration Tool Response Models
# ============================================================
#
# Like the other integration tools, the create/status/list tools carry no
# ``success`` key on their success path; errors return a bare ``error``.


class YouTubeBroadcastResult(BaseModel):
    """Return type of ``create_youtube_broadcast``."""

    broadcast_id: str | None = Field(default=None, description="YouTube broadcast ID")
    stream_id: str | None = Field(default=None, description="YouTube stream ID")
    title: str | None = Field(default=None, description="Broadcast title")
    scheduled_start: str | None = Field(
        default=None, description="Scheduled start (ISO 8601)"
    )
    privacy: str | None = Field(default=None, description="Privacy: public, unlisted, or private")
    rtmp_url: str | None = Field(default=None, description="RTMP server URL for Pearl publisher")
    stream_key: str | None = Field(default=None, description="RTMP stream key")
    full_rtmp_url: str | None = Field(
        default=None, description="Complete RTMP URL (rtmp_url/stream_key)"
    )
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    pearl_config_hint: dict[str, Any] | None = Field(
        default=None, description="Suggested Pearl publisher settings (publisher_type, url, note)."
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class YouTubeBroadcastStatusResult(BaseModel):
    """Return type of ``get_youtube_broadcast_status``."""

    status: dict[str, Any] | None = Field(
        default=None,
        description="Broadcast + stream status (broadcast_id, lifecycle status, health).",
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class YouTubeBroadcastListResult(BaseModel):
    """Return type of ``list_youtube_broadcasts``."""

    broadcasts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Broadcasts, each with id, title, scheduled/actual start, status, privacy.",
    )
    count: int | None = Field(default=None, description="Number of broadcasts returned")
    filter: str | None = Field(
        default=None, description="Status filter applied ('all' when unfiltered)"
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class YouTubeBroadcastEndResult(BaseModel):
    """Return type of ``end_youtube_broadcast``."""

    success: bool | None = Field(default=None, description="Whether the broadcast was ended")
    broadcast_id: str | None = Field(default=None, description="Broadcast ID that was ended")
    new_status: str | None = Field(
        default=None, description="New lifecycle status (e.g. 'complete')"
    )
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Opencast Integration Tool Response Models
# ============================================================
#
# Same integration convention: list/get/create/ingest tools carry no
# ``success`` key on their success path; errors return a bare ``error``.


class OpencastSeriesListResult(BaseModel):
    """Return type of ``list_opencast_series``."""

    series: list[dict[str, Any]] = Field(
        default_factory=list, description="Series (courses/channels), each with identifier + title."
    )
    count: int | None = Field(default=None, description="Number of series returned")
    filter: str | None = Field(default=None, description="Title filter applied, or null")
    offset: int | None = Field(default=None, description="Pagination offset used")
    error: str | None = Field(default=None, description="Error message on failure.")


class OpencastSeriesResult(BaseModel):
    """Return type of ``get_opencast_series`` / ``create_opencast_series``."""

    series: dict[str, Any] | None = Field(
        default=None, description="Series detail (identifier, title, description, creator)."
    )
    message: str | None = Field(
        default=None, description="Confirmation message (create only)."
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class OpencastEventListResult(BaseModel):
    """Return type of ``list_opencast_events``."""

    events: list[dict[str, Any]] = Field(
        default_factory=list, description="Events (recordings), each with identifier + title."
    )
    count: int | None = Field(default=None, description="Number of events returned")
    series_id: str | None = Field(
        default=None, description="Series filter applied ('all' when unfiltered)"
    )
    status: str | None = Field(
        default=None, description="Status filter applied ('all' when unfiltered)"
    )
    offset: int | None = Field(default=None, description="Pagination offset used")
    error: str | None = Field(default=None, description="Error message on failure.")


class OpencastEventResult(BaseModel):
    """Return type of ``get_opencast_event``."""

    event: dict[str, Any] | None = Field(
        default=None, description="Event detail (title, duration, status, publications)."
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class OpencastIngestResult(BaseModel):
    """Return type of ``ingest_to_opencast``."""

    result: dict[str, Any] | None = Field(
        default=None, description="Ingest result (success flag, workflow instance ID)."
    )
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    file_size: int | None = Field(default=None, description="Size of the ingested file in bytes")
    error: str | None = Field(default=None, description="Error message on failure.")


class OpencastIngestStatusResult(BaseModel):
    """Return type of ``get_opencast_ingest_status``."""

    status: dict[str, Any] | None = Field(
        default=None, description="Workflow status (state + per-operation progress)."
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class OpencastScheduleResult(BaseModel):
    """Return type of ``schedule_opencast_capture``."""

    event: dict[str, Any] | None = Field(
        default=None, description="Created scheduled event detail."
    )
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    start_time: str | None = Field(default=None, description="Scheduled start (ISO 8601)")
    end_time: str | None = Field(default=None, description="Scheduled end (ISO 8601)")
    error: str | None = Field(default=None, description="Error message on failure.")


class OpencastDeleteResult(BaseModel):
    """Return type of ``delete_opencast_event``."""

    success: bool | None = Field(default=None, description="Whether the event was deleted")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    event_id: str | None = Field(default=None, description="Event ID that was deleted")
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Panopto Integration Tool Response Models
# ============================================================
#
# Same integration convention: list/get/create/upload tools carry no
# ``success`` key on their success path; errors return a bare ``error``.


class PanoptoFolderListResult(BaseModel):
    """Return type of ``list_panopto_folders``."""

    folders: list[dict[str, Any]] = Field(
        default_factory=list, description="Folders, each with Id, Name, description, parent."
    )
    count: int | None = Field(default=None, description="Number of folders returned")
    parent_folder_id: str | None = Field(
        default=None, description="Parent folder queried ('root' when unspecified)"
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class PanoptoFolderResult(BaseModel):
    """Return type of ``get_panopto_folder`` / ``create_panopto_folder``."""

    folder: dict[str, Any] | None = Field(
        default=None, description="Folder detail (Id, Name, description, parent)."
    )
    message: str | None = Field(default=None, description="Confirmation message (create only).")
    error: str | None = Field(default=None, description="Error message on failure.")


class PanoptoSessionListResult(BaseModel):
    """Return type of ``list_panopto_sessions``."""

    sessions: list[dict[str, Any]] = Field(
        default_factory=list, description="Sessions (recordings), each with Id, name, duration."
    )
    count: int | None = Field(default=None, description="Number of sessions returned")
    folder_id: str | None = Field(
        default=None, description="Folder filter applied ('all' when unfiltered)"
    )
    error: str | None = Field(default=None, description="Error message on failure.")


class PanoptoSessionResult(BaseModel):
    """Return type of ``get_panopto_session`` / ``create_panopto_session``."""

    session: dict[str, Any] | None = Field(
        default=None, description="Session detail (Id, name, duration, folder, streams)."
    )
    message: str | None = Field(default=None, description="Confirmation message (create only).")
    error: str | None = Field(default=None, description="Error message on failure.")


class PanoptoUploadResult(BaseModel):
    """Return type of ``upload_to_panopto``."""

    upload: dict[str, Any] | None = Field(
        default=None, description="Upload result (session ID, upload target, status)."
    )
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    file_size: int | None = Field(default=None, description="Size of the uploaded file in bytes")
    error: str | None = Field(default=None, description="Error message on failure.")


class PanoptoUploadStatusResult(BaseModel):
    """Return type of ``get_panopto_upload_status``."""

    upload_id: str | None = Field(default=None, description="Upload session ID queried")
    state: str | None = Field(
        default=None,
        description="Readable state: Created, Uploading, UploadComplete, Processing, "
        "Complete, Error.",
    )
    state_code: int | None = Field(default=None, description="Raw numeric state code")
    details: dict[str, Any] | None = Field(default=None, description="Full raw upload status.")
    error: str | None = Field(default=None, description="Error message on failure.")


class PanoptoDeleteResult(BaseModel):
    """Return type of ``delete_panopto_session``."""

    success: bool | None = Field(default=None, description="Whether the session was deleted")
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    error: str | None = Field(default=None, description="Error message on failure.")


# ============================================================
# Kaltura Integration Tool Response Models
# ============================================================
#
# Same integration convention: list/get/create/upload tools carry no
# ``success`` key on their success path; errors return a bare ``error``.


class KalturaCategoryListResult(BaseModel):
    """Return type of ``list_kaltura_categories``."""

    categories: list[dict[str, Any]] = Field(
        default_factory=list, description="Categories (folders), each with id, name, parent."
    )
    count: int | None = Field(default=None, description="Number of categories returned")
    parent_id: int | str | None = Field(
        default=None, description="Parent category queried ('root' when unspecified)"
    )
    page: int | None = Field(default=None, description="1-based page index returned")
    error: str | None = Field(default=None, description="Error message on failure.")


class KalturaCategoryResult(BaseModel):
    """Return type of ``get_kaltura_category`` / ``create_kaltura_category``."""

    category: dict[str, Any] | None = Field(
        default=None, description="Category detail (name, description, parent, entry count)."
    )
    message: str | None = Field(default=None, description="Confirmation message (create only).")
    error: str | None = Field(default=None, description="Error message on failure.")


class KalturaMediaListResult(BaseModel):
    """Return type of ``list_kaltura_media``."""

    media: list[dict[str, Any]] = Field(
        default_factory=list, description="Media entries (videos), each with id, name, status."
    )
    count: int | None = Field(default=None, description="Number of media entries returned")
    category_ids: str | None = Field(
        default=None, description="Category filter applied ('all' when unfiltered)"
    )
    search_text: str | None = Field(default=None, description="Search text applied, or null")
    page: int | None = Field(default=None, description="1-based page index returned")
    error: str | None = Field(default=None, description="Error message on failure.")


class KalturaMediaResult(BaseModel):
    """Return type of ``get_kaltura_media`` / ``create_kaltura_media``."""

    media: dict[str, Any] | None = Field(
        default=None,
        description="Media entry detail (name, duration, status + status_name, thumbnails).",
    )
    message: str | None = Field(default=None, description="Confirmation message (create only).")
    error: str | None = Field(default=None, description="Error message on failure.")


class KalturaUploadResult(BaseModel):
    """Return type of ``upload_to_kaltura``."""

    media: dict[str, Any] | None = Field(
        default=None, description="Created media entry detail after upload."
    )
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    file_size: int | None = Field(default=None, description="Size of the uploaded file in bytes")
    entry_id: str | None = Field(default=None, description="Kaltura entry ID of the upload")
    error: str | None = Field(default=None, description="Error message on failure.")


class KalturaScheduleResult(BaseModel):
    """Return type of ``schedule_kaltura_event``."""

    event: dict[str, Any] | None = Field(
        default=None, description="Created schedule event detail."
    )
    message: str | None = Field(default=None, description="Human-readable confirmation message")
    start_time: str | None = Field(default=None, description="Scheduled start (ISO 8601)")
    end_time: str | None = Field(default=None, description="Scheduled end (ISO 8601)")
    error: str | None = Field(default=None, description="Error message on failure.")


class KalturaUploadStatusResult(BaseModel):
    """Return type of ``get_kaltura_upload_status``."""

    upload_token_id: str | None = Field(default=None, description="Upload token ID queried")
    status: str | None = Field(
        default=None,
        description="Readable status: Pending, PartialUpload, FullUpload, Closed, "
        "TimedOut, Deleted.",
    )
    status_code: int | None = Field(default=None, description="Raw numeric status code")
    uploaded_bytes: int | None = Field(default=None, description="Bytes uploaded so far")
    details: dict[str, Any] | None = Field(default=None, description="Full raw upload status.")
    error: str | None = Field(default=None, description="Error message on failure.")
