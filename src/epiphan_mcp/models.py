"""Pydantic models for Epiphan Pearl REST API v2.0 responses.

Based on OpenAPI spec:
https://epiphan-video.github.io/pearl_api_swagger_ui/api/v2.0/openapi.yml
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


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

    class Config:
        extra = "allow"


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
    cpu_usage: Optional[float] = Field(default=None, description="CPU usage %")
    memory_usage: Optional[float] = Field(default=None, description="Memory usage %")
    temperature: Optional[float] = Field(default=None, description="System temp in C")

    @property
    def uptime_hours(self) -> float:
        """Uptime in hours."""
        return self.uptime_seconds / 3600

    class Config:
        extra = "allow"


# ============================================================
# Recorder Models
# ============================================================


class RecorderInfo(BaseModel):
    """Recorder info from GET /recorders."""

    id: str = Field(description="Recorder ID (e.g., 'recorder-1')")
    name: str = Field(default="", description="Recorder name")
    type: str = Field(default="", description="Recorder type")
    channel_id: Optional[str] = Field(default=None, description="Associated channel")

    class Config:
        extra = "allow"


class RecorderStatus(BaseModel):
    """Recorder status from GET /recorders/{rid}/status."""

    id: str = Field(default="", description="Recorder ID")
    state: RecordingState = Field(default=RecordingState.STOPPED, description="State")
    duration_seconds: int = Field(default=0, alias="duration", description="Duration")
    file_size_bytes: int = Field(default=0, alias="file_size", description="File size")
    filename: str = Field(default="", description="Current filename")
    bitrate: Optional[int] = Field(default=None, description="Recording bitrate")

    class Config:
        extra = "allow"
        populate_by_name = True


# ============================================================
# Channel Models
# ============================================================


class LayoutInfo(BaseModel):
    """Layout info within a channel."""

    id: str = Field(description="Layout ID")
    name: str = Field(default="", description="Layout name")
    is_active: bool = Field(default=False, description="Whether active")

    class Config:
        extra = "allow"


class ChannelInfo(BaseModel):
    """Channel info from GET /channels."""

    id: str = Field(description="Channel ID")
    name: str = Field(default="", description="Channel name")
    layouts: list[LayoutInfo] = Field(default_factory=list, description="Layouts")
    active_layout: Optional[str] = Field(default=None, description="Active layout ID")

    class Config:
        extra = "allow"


class ChannelParams(BaseModel):
    """Legacy channel parameters (for backwards compatibility)."""

    channel_id: int = Field(description="Channel number")
    name: Optional[str] = Field(default=None, description="Channel name")
    rec_enabled: bool = Field(default=False, description="Recording enabled")
    publish_type: Optional[int] = Field(default=None, description="Publish type")
    framesize: Optional[str] = Field(default=None, description="Frame size")
    framerate: Optional[float] = Field(default=None, description="Frame rate")
    bitrate: Optional[int] = Field(default=None, description="Bitrate in kbps")

    class Config:
        extra = "allow"


# ============================================================
# Publisher (Streaming) Models
# ============================================================


class PublisherInfo(BaseModel):
    """Publisher info from GET /channels/{cid}/publishers."""

    id: str = Field(description="Publisher ID")
    name: str = Field(default="", description="Publisher name")
    type: str = Field(default="", description="Publisher type (rtmp, srt, etc)")
    enabled: bool = Field(default=True, description="Whether enabled")

    class Config:
        extra = "allow"


class PublisherStatus(BaseModel):
    """Publisher status from GET /channels/{cid}/publishers/{pid}/status."""

    id: str = Field(default="", description="Publisher ID")
    state: StreamingState = Field(default=StreamingState.STOPPED, description="State")
    duration_seconds: int = Field(default=0, alias="duration", description="Duration")
    bitrate_actual: Optional[int] = Field(default=None, description="Actual bitrate")
    bytes_sent: int = Field(default=0, description="Total bytes sent")
    viewers: Optional[int] = Field(default=None, description="Number of viewers")
    destination: str = Field(default="", description="Destination URL")
    error_message: Optional[str] = Field(default=None, description="Error if any")

    class Config:
        extra = "allow"
        populate_by_name = True


class StreamStatus(BaseModel):
    """Legacy streaming status (for backwards compatibility)."""

    channel_id: int = Field(description="Channel number")
    state: StreamingState = Field(description="Current streaming state")
    destination: Optional[str] = Field(default=None, description="Stream URL")
    bitrate_actual: Optional[int] = Field(default=None, description="Actual kbps")
    viewers: Optional[int] = Field(default=None, description="Number of viewers")
    uptime_seconds: Optional[int] = Field(default=None, description="Stream uptime")

    class Config:
        extra = "allow"


# ============================================================
# Input Models
# ============================================================


class InputSource(BaseModel):
    """Input source from GET /inputs."""

    id: str = Field(default="", alias="source_id", description="Source ID")
    name: str = Field(default="", description="Source name")
    type: str = Field(default="", alias="source_type", description="Source type")
    connected: bool = Field(default=False, description="Whether connected")
    resolution: Optional[str] = Field(default=None, description="Input resolution")
    framerate: Optional[float] = Field(default=None, description="Input framerate")
    has_signal: bool = Field(default=False, description="Whether has signal")

    class Config:
        extra = "allow"
        populate_by_name = True


# ============================================================
# Layout Models
# ============================================================


class Layout(BaseModel):
    """Layout/scene information."""

    layout_id: str = Field(alias="id", description="Layout identifier")
    name: str = Field(description="Layout name")
    is_active: bool = Field(default=False, description="Whether layout is active")

    class Config:
        extra = "allow"
        populate_by_name = True


# ============================================================
# Recording/Archive Models
# ============================================================


class Recording(BaseModel):
    """Recorded file information from GET /recorders/{rid}/archive/files."""

    id: str = Field(default="", alias="file_id", description="File ID")
    filename: str = Field(description="Recording filename")
    path: str = Field(default="", description="Full path on device")
    size_bytes: int = Field(default=0, alias="size", description="File size")
    duration_seconds: int = Field(default=0, alias="duration", description="Duration")
    created_at: Optional[datetime] = Field(default=None, description="Creation time")
    recorder_id: Optional[str] = Field(default=None, description="Source recorder")

    class Config:
        extra = "allow"
        populate_by_name = True


# ============================================================
# Event/Schedule Models
# ============================================================


class ScheduledEvent(BaseModel):
    """Scheduled event from GET /schedule/events."""

    id: str = Field(description="Event ID")
    name: str = Field(default="", description="Event name")
    status: str = Field(default="", description="Event status")
    start_time: Optional[datetime] = Field(default=None, description="Start time")
    end_time: Optional[datetime] = Field(default=None, description="End time")
    cms_type: Optional[str] = Field(default=None, description="CMS type")

    class Config:
        extra = "allow"


# ============================================================
# Device & Fleet Models
# ============================================================


class DeviceInfo(BaseModel):
    """Complete device information."""

    host: str = Field(description="Device hostname or IP")
    name: Optional[str] = Field(default=None, description="Device name")
    model: Optional[str] = Field(default=None, description="Pearl model")
    serial: Optional[str] = Field(default=None, description="Serial number")
    firmware: Optional[str] = Field(default=None, description="Firmware version")
    online: bool = Field(default=False, description="Whether device is reachable")
    status: Optional[SystemStatus] = Field(default=None, description="System status")
    channels: list[ChannelInfo] = Field(default_factory=list, description="Channels")
    recorders: list[RecorderInfo] = Field(default_factory=list, description="Recorders")

    class Config:
        extra = "allow"


class FleetStatus(BaseModel):
    """Fleet-wide status."""

    fleet_name: str = Field(description="Fleet identifier")
    total_devices: int = Field(description="Total devices in fleet")
    online_devices: int = Field(description="Devices currently online")
    recording_devices: int = Field(description="Devices currently recording")
    streaming_devices: int = Field(description="Devices currently streaming")
    devices_with_alerts: int = Field(default=0, description="Devices with issues")
    devices: list[DeviceInfo] = Field(default_factory=list, description="Device details")

    class Config:
        extra = "allow"


# ============================================================
# Operation Results
# ============================================================


class OperationResult(BaseModel):
    """Generic operation result."""

    success: bool = Field(description="Whether operation succeeded")
    message: str = Field(description="Result message")
    device: str = Field(default="", description="Device host")
    details: Optional[dict[str, Any]] = Field(default=None, description="Details")

    class Config:
        extra = "allow"


class BatchOperationResult(BaseModel):
    """Result of batch operations across multiple devices."""

    total: int = Field(description="Total operations attempted")
    succeeded: int = Field(description="Successful operations")
    failed: int = Field(description="Failed operations")
    results: list[OperationResult] = Field(default_factory=list, description="Results")

    @property
    def all_succeeded(self) -> bool:
        """Whether all operations succeeded."""
        return self.failed == 0

    class Config:
        extra = "allow"


# ============================================================
# Alert Models
# ============================================================


class Alert(BaseModel):
    """Device alert."""

    device: str = Field(description="Device host")
    severity: str = Field(description="Alert severity: info, warning, error")
    message: str = Field(description="Alert message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")
    details: Optional[dict[str, Any]] = Field(default=None, description="Details")

    class Config:
        extra = "allow"


# ============================================================
# AFU (Automatic File Upload) Models
# ============================================================


class AFUStatus(BaseModel):
    """Automatic File Upload status from GET /afu/status."""

    id: str = Field(description="AFU ID")
    name: str = Field(default="", description="AFU name")
    protocol: str = Field(default="", description="Upload protocol")
    state: str = Field(default="", description="Current state")
    queue_count: int = Field(default=0, description="Files in queue")
    destination: str = Field(default="", description="Destination URL")

    class Config:
        extra = "allow"
