"""MCP tool implementations for Epiphan Pearl devices."""

from .device import get_client, get_device_status, list_devices
from .fleet import batch_start_recording, batch_stop_recording, get_fleet_status
from .layout import add_bookmark, list_layouts, switch_layout
from .maintenance import get_device_health_score, predict_storage_full
from .recording import get_recording_status, start_recording, stop_recording
from .schedule import get_scheduled_events, single_touch_start, single_touch_stop
from .storage import get_afu_status, get_storage_report, list_inputs
from .streaming import get_stream_status, start_stream, stop_stream

__all__ = [
    # Device tools
    "get_client",
    "get_device_status",
    "list_devices",
    # Recording tools
    "start_recording",
    "stop_recording",
    "get_recording_status",
    # Streaming tools
    "start_stream",
    "stop_stream",
    "get_stream_status",
    # Layout tools
    "list_layouts",
    "switch_layout",
    "add_bookmark",
    # Storage tools
    "list_inputs",
    "get_storage_report",
    "get_afu_status",
    # Maintenance tools
    "predict_storage_full",
    "get_device_health_score",
    # Fleet tools
    "get_fleet_status",
    "batch_start_recording",
    "batch_stop_recording",
    # Schedule tools
    "get_scheduled_events",
    "single_touch_start",
    "single_touch_stop",
]
