"""Mock API v2.0 responses for Epiphan Pearl.

Based on OpenAPI spec:
https://epiphan-video.github.io/pearl_api_swagger_ui/api/v2.0/openapi.yml
"""

# ============================================================
# Device Responses
# ============================================================

DEVICE_RESPONSE = {
    "status": "ok",
    "result": {
        "name": "Pearl-2-ABC123",
        "model": "Pearl-2",
        "serial": "ABC123456",
        "firmware": "4.14.2",
        "mac": "00:11:22:33:44:55",
    },
}

# Spec-accurate system endpoints (Pearl v2.0 openapi):
#   GET /system/ident     -> name, location, description
#   GET /system/firmware  -> version, revision, product_id, product_name
IDENT_RESPONSE = {
    "status": "ok",
    "result": {
        "name": "Pearl-2-ABC123",
        "location": "Lecture Hall 204",
        "description": "",
        # serial is not in the spec's ident schema; included as a best-effort
        # extra since some firmware returns it (get_system_status reads it if present).
        "serial": "ABC123456",
    },
}

FIRMWARE_RESPONSE = {
    "status": "ok",
    "result": {
        "version": "4.14.2",
        "revision": "",
        "product_id": "pearl2",
        "product_name": "Pearl-2",
    },
}

# ============================================================
# Storage Responses
# ============================================================

STORAGE_RESPONSE = {
    "status": "ok",
    "result": [
        {
            "id": "storage-1",
            "name": "Internal Storage",
            "type": "internal",
            "total_bytes": 500000000000,  # 500GB
            "used_bytes": 100000000000,  # 100GB
            "free_bytes": 400000000000,  # 400GB
            "percent_used": 20.0,
            "mounted": True,
        },
    ],
}

# Spec-accurate storage endpoints (Pearl v2.0 openapi):
#   GET /system/storages                 -> [{id}]
#   GET /system/storages/{stid}/status   -> {state, total, free}
STORAGES_LIST_RESPONSE = {
    "status": "ok",
    "result": [{"id": "storage-1"}],
}

STORAGE_STATUS_RESPONSE = {
    "status": "ok",
    "result": {
        "state": "mounted",
        "total": 500000000000,  # 500GB
        "free": 400000000000,  # 400GB (20% used)
    },
}

STORAGE_STATUS_LOW_RESPONSE = {
    "status": "ok",
    "result": {
        "state": "mounted",
        "total": 500000000000,  # 500GB
        "free": 50000000000,  # 50GB (90% used) -> triggers storage warnings
    },
}

# Spec-accurate single-touch endpoints (Pearl v2.0 openapi):
#   GET  /system/singletouchcontrol                  -> [{id}]
#   GET  /system/singletouchcontrol/{stcid}/state    -> {pressed, status, ...}
#   POST /system/singletouchcontrol/{stcid}/control/toggle
SINGLETOUCH_LIST_RESPONSE = {
    "status": "ok",
    "result": [{"id": "stc-1"}],
}

# 'pressed' is the activation flag the adapter gates on; 'status' is a health flag
# (recorders/publishers started OK) and is deliberately set to the opposite value so a
# test that mistakenly reads 'status' instead of 'pressed' would fail.
SINGLETOUCH_STATE_OFF = {
    "status": "ok",
    "result": {"pressed": False, "status": True},
}

SINGLETOUCH_STATE_ON = {
    "status": "ok",
    "result": {"pressed": True, "status": False},
}

STORAGE_LOW_SPACE_RESPONSE = {
    "status": "ok",
    "result": [
        {
            "id": "storage-1",
            "name": "Internal Storage",
            "type": "internal",
            "total_bytes": 500000000000,
            "used_bytes": 450000000000,  # 90% used
            "free_bytes": 50000000000,
            "percent_used": 90.0,
            "mounted": True,
        },
    ],
}

# ============================================================
# Recorder Responses
# ============================================================

RECORDERS_RESPONSE = {
    "status": "ok",
    "result": [
        {
            "id": "recorder-1",
            "name": "Channel 1 Recorder",
            "type": "mp4",
            "channel_id": "channel-1",
        },
        {
            "id": "recorder-2",
            "name": "Channel 2 Recorder",
            "type": "mp4",
            "channel_id": "channel-2",
        },
    ],
}

RECORDER_STATUS_STOPPED = {
    "status": "ok",
    "result": {
        "id": "recorder-1",
        "state": "stopped",
        "duration": 0,
        "file_size": 0,
        "filename": "",
    },
}

RECORDER_STATUS_RECORDING = {
    "status": "ok",
    "result": {
        "id": "recorder-1",
        "state": "recording",
        "duration": 3600,  # 1 hour
        "file_size": 1073741824,  # 1GB
        "filename": "recording_2025-01-22_10-00-00.mp4",
        "bitrate": 8000000,
    },
}

ALL_RECORDER_STATUS_RESPONSE = {
    "status": "ok",
    "result": [
        {
            "id": "recorder-1",
            "state": "stopped",
            "duration": 0,
            "file_size": 0,
        },
        {
            "id": "recorder-2",
            "state": "recording",
            "duration": 1800,
            "file_size": 536870912,
        },
    ],
}

ARCHIVE_FILES_RESPONSE = {
    "status": "ok",
    "result": [
        {
            "file_id": "file-001",
            "filename": "recording_2025-01-21_14-00-00.mp4",
            "path": "/recordings/recording_2025-01-21_14-00-00.mp4",
            "size": 2147483648,  # 2GB
            "duration": 7200,  # 2 hours
            "created_at": "2025-01-21T14:00:00Z",
            "recorder_id": "recorder-1",
        },
        {
            "file_id": "file-002",
            "filename": "recording_2025-01-22_09-00-00.mp4",
            "path": "/recordings/recording_2025-01-22_09-00-00.mp4",
            "size": 1073741824,  # 1GB
            "duration": 3600,  # 1 hour
            "created_at": "2025-01-22T09:00:00Z",
            "recorder_id": "recorder-1",
        },
    ],
}

# ============================================================
# Channel Responses
# ============================================================

CHANNELS_RESPONSE = {
    "status": "ok",
    "result": [
        {
            "id": "channel-1",
            "name": "Main Channel",
            "layouts": [
                {"id": "layout-1", "name": "Full Screen", "is_active": True},
                {"id": "layout-2", "name": "Picture-in-Picture", "is_active": False},
            ],
            "active_layout": "layout-1",
        },
        {
            "id": "channel-2",
            "name": "Secondary Channel",
            "layouts": [
                {"id": "layout-3", "name": "Split Screen", "is_active": True},
            ],
            "active_layout": "layout-3",
        },
    ],
}

# ============================================================
# Layout Responses
# ============================================================

LAYOUTS_RESPONSE = {
    "status": "ok",
    "result": [
        {
            "id": "layout-1",
            "name": "Full Screen",
            "is_active": True,
        },
        {
            "id": "layout-2",
            "name": "Picture in Picture",
            "is_active": False,
        },
        {
            "id": "layout-3",
            "name": "Side by Side",
            "is_active": False,
        },
    ],
}

# ============================================================
# Publisher (Streaming) Responses
# ============================================================

PUBLISHERS_RESPONSE = {
    "status": "ok",
    "result": [
        {
            "id": "publisher-1",
            "name": "YouTube Stream",
            "type": "rtmp",
            "enabled": True,
        },
        {
            "id": "publisher-2",
            "name": "Backup SRT",
            "type": "srt",
            "enabled": True,
        },
    ],
}

PUBLISHER_STATUS_STOPPED = {
    "status": "ok",
    "result": {
        "id": "publisher-1",
        "state": "stopped",
        "duration": 0,
        "bytes_sent": 0,
        "destination": "rtmp://youtube.com/live/stream-key",
    },
}

PUBLISHER_STATUS_STREAMING = {
    "status": "ok",
    "result": {
        "id": "publisher-1",
        "state": "streaming",
        "duration": 1800,
        "bitrate_actual": 6000000,
        "bytes_sent": 1350000000,
        "viewers": 42,
        "destination": "rtmp://youtube.com/live/stream-key",
    },
}

# ============================================================
# Input Responses
# ============================================================

INPUTS_RESPONSE = {
    "status": "ok",
    "result": [
        {
            "source_id": "hdmi-1",
            "name": "HDMI 1",
            "source_type": "hdmi",
            "connected": True,
            "resolution": "1920x1080",
            "framerate": 60.0,
            "has_signal": True,
        },
        {
            "source_id": "sdi-1",
            "name": "SDI 1",
            "source_type": "sdi",
            "connected": True,
            "resolution": "3840x2160",
            "framerate": 30.0,
            "has_signal": True,
        },
        {
            "source_id": "hdmi-2",
            "name": "HDMI 2",
            "source_type": "hdmi",
            "connected": False,
            "has_signal": False,
        },
    ],
}

# ============================================================
# Event Responses
# ============================================================

EVENTS_RESPONSE = {
    "status": "ok",
    "result": [
        {
            "id": "event-001",
            "name": "Morning Lecture",
            "status": "scheduled",
            "start_time": "2025-01-22T09:00:00Z",
            "end_time": "2025-01-22T10:30:00Z",
            "cms_type": "kaltura",
        },
        {
            "id": "event-002",
            "name": "Afternoon Session",
            "status": "upcoming",
            "start_time": "2025-01-22T14:00:00Z",
            "end_time": "2025-01-22T16:00:00Z",
            "cms_type": "panopto",
        },
    ],
}

# ============================================================
# AFU Responses
# ============================================================

AFU_STATUS_RESPONSE = {
    "status": "ok",
    "result": [
        {
            "id": "afu-1",
            "name": "S3 Upload",
            "protocol": "s3",
            "state": "idle",
            "queue_count": 0,
            "destination": "s3://my-bucket/recordings/",
        },
    ],
}

# ============================================================
# Control Responses (Start/Stop operations)
# ============================================================

CONTROL_SUCCESS_RESPONSE = {
    "status": "ok",
}

# ============================================================
# Error Responses
# ============================================================

ERROR_RESPONSE = {
    "status": "error",
    "message": "Resource not found",
}

BUSY_RESPONSE = {
    "status": "busy",
}

AUTH_ERROR_RESPONSE = {
    "status": "error",
    "message": "Authentication required",
}

NOT_FOUND_RESPONSE = {
    "status": "error",
    "message": "Recorder not found",
}

ALREADY_RECORDING_RESPONSE = {
    "status": "error",
    "message": "Recorder is already recording",
}
