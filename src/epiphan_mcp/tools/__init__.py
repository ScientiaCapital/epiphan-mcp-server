"""MCP tool implementations for Epiphan Pearl devices."""

from .ai_tools import detect_recording_issues
from .device import get_client, get_device_status, list_devices
from .fleet import (
    batch_start_recording,
    batch_stop_recording,
    generate_shift_handoff,
    get_fleet_status,
    predict_fleet_issues,
    suggest_maintenance_window,
)
from .inputs import (
    create_network_input,
    get_input_settings,
    list_outputs,
    set_output_source,
    update_input_settings,
)
from .layout import add_bookmark, list_layouts, switch_layout
from .maintenance import get_device_health_score, predict_storage_full
from .publishers import (
    create_publisher,
    delete_publisher,
    get_publisher_settings,
    list_publisher_types,
    rename_publisher,
    update_publisher_settings,
)
from .recording import get_recording_status, start_recording, stop_recording
from .schedule import (
    create_scheduled_event,
    get_scheduled_events,
    pause_event,
    resume_event,
    single_touch_start,
    single_touch_stop,
)
from .storage import get_afu_status, get_storage_report, list_inputs
from .streaming import get_stream_status, start_stream, stop_stream
from .panopto import (
    create_panopto_folder,
    create_panopto_session,
    delete_panopto_session,
    get_panopto_folder,
    get_panopto_session,
    get_panopto_upload_status,
    list_panopto_folders,
    list_panopto_sessions,
    upload_to_panopto,
)

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
    # Fleet intelligence tools (Sprint 3)
    "detect_recording_issues",
    "suggest_maintenance_window",
    "predict_fleet_issues",
    "generate_shift_handoff",
    # Schedule tools
    "get_scheduled_events",
    "single_touch_start",
    "single_touch_stop",
    "create_scheduled_event",
    "pause_event",
    "resume_event",
    # Publisher management tools (API Expansion Phase 1)
    "create_publisher",
    "delete_publisher",
    "get_publisher_settings",
    "update_publisher_settings",
    "list_publisher_types",
    "rename_publisher",
    # Input/output management tools (API Expansion Phase 2)
    "create_network_input",
    "get_input_settings",
    "update_input_settings",
    "list_outputs",
    "set_output_source",
    # Panopto CMS integration tools
    "list_panopto_folders",
    "get_panopto_folder",
    "create_panopto_folder",
    "list_panopto_sessions",
    "get_panopto_session",
    "create_panopto_session",
    "upload_to_panopto",
    "get_panopto_upload_status",
    "delete_panopto_session",
]
