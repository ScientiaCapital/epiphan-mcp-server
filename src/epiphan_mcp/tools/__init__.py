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
    get_input_preview,
    get_input_settings,
    list_outputs,
    set_output_source,
    update_input_settings,
)
from .kaltura import (
    create_kaltura_category,
    create_kaltura_media,
    get_kaltura_category,
    get_kaltura_media,
    get_kaltura_upload_status,
    list_kaltura_categories,
    list_kaltura_media,
    schedule_kaltura_event,
    upload_to_kaltura,
)
from .layout import add_bookmark, list_layouts, switch_layout
from .maintenance import get_device_health_score, predict_storage_full
from .opencast import (
    create_opencast_series,
    delete_opencast_event,
    get_opencast_event,
    get_opencast_ingest_status,
    get_opencast_series,
    ingest_to_opencast,
    list_opencast_events,
    list_opencast_series,
    schedule_opencast_capture,
)
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
from .publishers import (
    create_publisher,
    delete_publisher,
    get_publisher_settings,
    list_publisher_types,
    rename_publisher,
    update_publisher_settings,
)
from .qsys import (
    list_qsys_components,
    qsys_get_pearl_status,
    qsys_start_recording,
    qsys_stop_recording,
    qsys_switch_layout,
)
from .recording import (
    get_recording_status,
    list_archive_files,
    list_recorders,
    start_recording,
    stop_recording,
)
from .schedule import (
    create_scheduled_event,
    get_scheduled_events,
    pause_event,
    resume_event,
    single_touch_start,
    single_touch_stop,
)
from .storage import get_afu_status, get_storage_report, list_inputs
from .streaming import (
    get_channel_preview,
    get_stream_status,
    list_channels,
    list_publishers,
    start_stream,
    stop_stream,
)
from .system import get_system_info, reboot_device, shutdown_device
from .cloud import (
    cloud_apply_preset,
    cloud_batch_command,
    cloud_delete_device,
    cloud_get_device,
    cloud_get_preview,
    cloud_get_settings,
    cloud_get_user,
    cloud_list_devices,
    cloud_pair_device,
    cloud_rename_device,
    cloud_run_command,
    cloud_unpair_device,
)
from .youtube import (
    create_youtube_broadcast,
    end_youtube_broadcast,
    get_youtube_broadcast_status,
    list_youtube_broadcasts,
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
    "list_recorders",
    "list_archive_files",
    # Streaming tools
    "start_stream",
    "stop_stream",
    "get_stream_status",
    "list_channels",
    "list_publishers",
    "get_channel_preview",
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
    "get_input_preview",
    # System control tools
    "reboot_device",
    "shutdown_device",
    "get_system_info",
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
    # Kaltura CMS integration tools
    "list_kaltura_categories",
    "get_kaltura_category",
    "create_kaltura_category",
    "list_kaltura_media",
    "get_kaltura_media",
    "create_kaltura_media",
    "upload_to_kaltura",
    "schedule_kaltura_event",
    "get_kaltura_upload_status",
    # Opencast CMS integration tools
    "list_opencast_series",
    "get_opencast_series",
    "create_opencast_series",
    "list_opencast_events",
    "get_opencast_event",
    "ingest_to_opencast",
    "get_opencast_ingest_status",
    "schedule_opencast_capture",
    "delete_opencast_event",
    # Q-SYS AV control integration tools
    "list_qsys_components",
    "qsys_get_pearl_status",
    "qsys_start_recording",
    "qsys_stop_recording",
    "qsys_switch_layout",
    # YouTube Live streaming integration tools
    "create_youtube_broadcast",
    "get_youtube_broadcast_status",
    "list_youtube_broadcasts",
    "end_youtube_broadcast",
    # Epiphan Cloud fleet management tools
    "cloud_get_user",
    "cloud_list_devices",
    "cloud_get_device",
    "cloud_pair_device",
    "cloud_unpair_device",
    "cloud_delete_device",
    "cloud_rename_device",
    "cloud_run_command",
    "cloud_batch_command",
    "cloud_get_settings",
    "cloud_get_preview",
    "cloud_apply_preset",
]
