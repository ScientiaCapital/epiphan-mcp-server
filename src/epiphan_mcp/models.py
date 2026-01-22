"""Pydantic models for Epiphan Pearl API responses."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RecordingState(str, Enum):
    """Recording state enumeration."""

    STOPPED = "stopped"
    RECORDING = "recording"
    PAUSED = "paused"
    ERROR = "error"


class StreamingState(str, Enum):
    """Streaming state enumeration."""

    STOPPED = "stopped"
    STREAMING = "streaming"
    CONNECTING = "connecting"
    ERROR = "error"


class SourceType(str, Enum):
    """Input source type."""

    HDMI = "hdmi"
    SDI = "sdi"
    USB = "usb"
    NDI = "ndi"
    SRT = "srt"
    RTSP = "rtsp"


class StorageInfo(BaseModel):
    """Storage information."""

    total_bytes: int = Field(description="Total storage in bytes")
    used_bytes: int = Field(description="Used storage in bytes")
    free_bytes: int = Field(description="Free storage in bytes")
    percent_used: float = Field(description="Percentage of storage used")

    @property
    def total_gb(self) -> float:
        """Total storage in GB."""
        return self.total_bytes / (1024**3)

    @property
    def free_gb(self) -> float:
        """Free storage in GB."""
        return self.free_bytes / (1024**3)


class SystemStatus(BaseModel):
    """System status from /admin/sysstat."""

    uptime_seconds: int = Field(default=0, description="System uptime in seconds")
    storage: Optional[StorageInfo] = Field(default=None, description="Storage info")
    cpu_usage: Optional[float] = Field(default=None, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(default=None, description="Memory usage percentage")
    temperature: Optional[float] = Field(default=None, description="System temperature in C")
    firmware_version: Optional[str] = Field(default=None, description="Firmware version")
    model: Optional[str] = Field(default=None, description="Pearl model")
    serial: Optional[str] = Field(default=None, description="Serial number")

    @property
    def uptime_hours(self) -> float:
        """Uptime in hours."""
        return self.uptime_seconds / 3600


class ChannelParams(BaseModel):
    """Channel parameters."""

    channel_id: int = Field(description="Channel number")
    name: Optional[str] = Field(default=None, description="Channel name")
    rec_enabled: bool = Field(default=False, description="Recording enabled")
    publish_type: Optional[int] = Field(default=None, description="Publish type")
    framesize: Optional[str] = Field(default=None, description="Frame size")
    framerate: Optional[float] = Field(default=None, description="Frame rate")
    bitrate: Optional[int] = Field(default=None, description="Bitrate in kbps")


class RecorderStatus(BaseModel):
    """Recorder status."""

    recorder_id: int = Field(description="Recorder number (channelm)")
    state: RecordingState = Field(description="Current recording state")
    duration_seconds: Optional[int] = Field(
        default=None, description="Recording duration if active"
    )
    file_size_bytes: Optional[int] = Field(
        default=None, description="Current file size if recording"
    )
    filename: Optional[str] = Field(default=None, description="Current filename")


class StreamStatus(BaseModel):
    """Streaming status."""

    channel_id: int = Field(description="Channel number")
    state: StreamingState = Field(description="Current streaming state")
    destination: Optional[str] = Field(default=None, description="Stream destination URL")
    bitrate_actual: Optional[int] = Field(
        default=None, description="Actual bitrate in kbps"
    )
    viewers: Optional[int] = Field(default=None, description="Number of viewers")
    uptime_seconds: Optional[int] = Field(default=None, description="Stream uptime")


class InputSource(BaseModel):
    """Input source information."""

    source_id: str = Field(description="Source identifier")
    name: str = Field(description="Source name")
    source_type: SourceType = Field(description="Source type")
    connected: bool = Field(default=False, description="Whether source is connected")
    resolution: Optional[str] = Field(default=None, description="Input resolution")
    framerate: Optional[float] = Field(default=None, description="Input framerate")


class Layout(BaseModel):
    """Layout/scene information."""

    layout_id: str = Field(description="Layout identifier")
    name: str = Field(description="Layout name")
    is_active: bool = Field(default=False, description="Whether layout is active")


class Recording(BaseModel):
    """Recorded file information."""

    filename: str = Field(description="Recording filename")
    path: str = Field(description="Full path on device")
    size_bytes: int = Field(description="File size in bytes")
    duration_seconds: Optional[int] = Field(default=None, description="Duration")
    created_at: Optional[datetime] = Field(default=None, description="Creation time")
    channel_id: Optional[int] = Field(default=None, description="Source channel")


class DeviceInfo(BaseModel):
    """Complete device information."""

    host: str = Field(description="Device hostname or IP")
    name: Optional[str] = Field(default=None, description="Device name")
    model: Optional[str] = Field(default=None, description="Pearl model")
    serial: Optional[str] = Field(default=None, description="Serial number")
    firmware: Optional[str] = Field(default=None, description="Firmware version")
    status: Optional[SystemStatus] = Field(default=None, description="System status")
    channels: list[ChannelParams] = Field(default_factory=list, description="Channels")
    recorders: list[RecorderStatus] = Field(default_factory=list, description="Recorders")


class OperationResult(BaseModel):
    """Generic operation result."""

    success: bool = Field(description="Whether operation succeeded")
    message: str = Field(description="Result message")
    device: str = Field(description="Device host")
    details: Optional[dict[str, Any]] = Field(default=None, description="Additional details")


class FleetStatus(BaseModel):
    """Fleet-wide status."""

    fleet_name: str = Field(description="Fleet identifier")
    total_devices: int = Field(description="Total devices in fleet")
    online_devices: int = Field(description="Devices currently online")
    recording_devices: int = Field(description="Devices currently recording")
    streaming_devices: int = Field(description="Devices currently streaming")
    devices_with_alerts: int = Field(description="Devices with issues")
    devices: list[DeviceInfo] = Field(default_factory=list, description="Device details")


class Alert(BaseModel):
    """Device alert."""

    device: str = Field(description="Device host")
    severity: str = Field(description="Alert severity: info, warning, error")
    message: str = Field(description="Alert message")
    timestamp: datetime = Field(description="When alert was generated")
    details: Optional[dict[str, Any]] = Field(default=None, description="Additional details")
