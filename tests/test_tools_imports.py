"""Tests for tool module imports.

Verifies that all tools are properly organized into modules and registered with MCP.
Following TDD: these tests are written FIRST, before implementing the modules.
"""



class TestToolsDeviceImports:
    """Tests for device tool imports."""

    def test_tools_device_imports(self):
        """Test that device tools can be imported from the device module."""
        from epiphan_mcp.tools.device import get_device_status, list_devices

        assert callable(get_device_status)
        assert callable(list_devices)

    def test_get_client_helper_imports(self):
        """Test that get_client helper can be imported."""
        from epiphan_mcp.tools.device import get_client

        assert callable(get_client)


class TestToolsRecordingImports:
    """Tests for recording tool imports."""

    def test_tools_recording_imports(self):
        """Test that recording tools can be imported from the recording module."""
        from epiphan_mcp.tools.recording import (
            get_recording_status,
            start_recording,
            stop_recording,
        )

        assert callable(start_recording)
        assert callable(stop_recording)
        assert callable(get_recording_status)


class TestToolsStreamingImports:
    """Tests for streaming tool imports."""

    def test_tools_streaming_imports(self):
        """Test that streaming tools can be imported from the streaming module."""
        from epiphan_mcp.tools.streaming import (
            get_stream_status,
            start_stream,
            stop_stream,
        )

        assert callable(start_stream)
        assert callable(stop_stream)
        assert callable(get_stream_status)


class TestToolsLayoutImports:
    """Tests for layout tool imports."""

    def test_tools_layout_imports(self):
        """Test that layout tools can be imported from the layout module."""
        from epiphan_mcp.tools.layout import add_bookmark, list_layouts, switch_layout

        assert callable(list_layouts)
        assert callable(switch_layout)
        assert callable(add_bookmark)


class TestToolsStorageImports:
    """Tests for storage tool imports."""

    def test_tools_storage_imports(self):
        """Test that storage tools can be imported from the storage module."""
        from epiphan_mcp.tools.storage import get_afu_status, get_storage_report, list_inputs

        assert callable(list_inputs)
        assert callable(get_storage_report)
        assert callable(get_afu_status)


class TestToolsMaintenanceImports:
    """Tests for maintenance tool imports."""

    def test_tools_maintenance_imports(self):
        """Test that maintenance tools can be imported from the maintenance module."""
        from epiphan_mcp.tools.maintenance import (
            get_device_health_score,
            predict_storage_full,
        )

        assert callable(predict_storage_full)
        assert callable(get_device_health_score)


class TestToolsFleetImports:
    """Tests for fleet tool imports."""

    def test_tools_fleet_imports(self):
        """Test that fleet tools can be imported from the fleet module."""
        from epiphan_mcp.tools.fleet import (
            batch_start_recording,
            batch_stop_recording,
            get_fleet_status,
        )

        assert callable(get_fleet_status)
        assert callable(batch_start_recording)
        assert callable(batch_stop_recording)


class TestToolsScheduleImports:
    """Tests for schedule tool imports."""

    def test_tools_schedule_imports(self):
        """Test that schedule tools can be imported from the schedule module."""
        from epiphan_mcp.tools.schedule import (
            create_scheduled_event,
            get_scheduled_events,
            pause_event,
            resume_event,
            single_touch_start,
            single_touch_stop,
        )

        assert callable(get_scheduled_events)
        assert callable(single_touch_start)
        assert callable(single_touch_stop)
        assert callable(create_scheduled_event)
        assert callable(pause_event)
        assert callable(resume_event)


class TestToolsPublishersImports:
    """Tests for publisher tool imports."""

    def test_tools_publishers_imports(self):
        """Test that publisher tools can be imported from the publishers module."""
        from epiphan_mcp.tools.publishers import (
            create_publisher,
            delete_publisher,
            get_publisher_settings,
            list_publisher_types,
            rename_publisher,
            update_publisher_settings,
        )

        assert callable(create_publisher)
        assert callable(delete_publisher)
        assert callable(get_publisher_settings)
        assert callable(update_publisher_settings)
        assert callable(list_publisher_types)
        assert callable(rename_publisher)


class TestToolsInputsImports:
    """Tests for input/output tool imports."""

    def test_tools_inputs_imports(self):
        """Test that input/output tools can be imported from the inputs module."""
        from epiphan_mcp.tools.inputs import (
            create_network_input,
            get_input_settings,
            list_outputs,
            set_output_source,
            update_input_settings,
        )

        assert callable(create_network_input)
        assert callable(get_input_settings)
        assert callable(update_input_settings)
        assert callable(list_outputs)
        assert callable(set_output_source)


class TestToolsPanoptoImports:
    """Tests for Panopto CMS integration tool imports."""

    def test_tools_panopto_imports(self):
        """Test that Panopto tools can be imported from the panopto module."""
        from epiphan_mcp.tools.panopto import (
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

        assert callable(list_panopto_folders)
        assert callable(get_panopto_folder)
        assert callable(create_panopto_folder)
        assert callable(list_panopto_sessions)
        assert callable(get_panopto_session)
        assert callable(create_panopto_session)
        assert callable(upload_to_panopto)
        assert callable(get_panopto_upload_status)
        assert callable(delete_panopto_session)


class TestToolsKalturaImports:
    """Tests for Kaltura CMS integration tool imports."""

    def test_tools_kaltura_imports(self):
        """Test that Kaltura tools can be imported from the kaltura module."""
        from epiphan_mcp.tools.kaltura import (
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

        assert callable(list_kaltura_categories)
        assert callable(get_kaltura_category)
        assert callable(create_kaltura_category)
        assert callable(list_kaltura_media)
        assert callable(get_kaltura_media)
        assert callable(create_kaltura_media)
        assert callable(upload_to_kaltura)
        assert callable(schedule_kaltura_event)
        assert callable(get_kaltura_upload_status)


class TestToolsOpencastImports:
    """Tests for Opencast CMS integration tool imports."""

    def test_tools_opencast_imports(self):
        """Test that Opencast tools can be imported from the opencast module."""
        from epiphan_mcp.tools.opencast import (
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

        assert callable(list_opencast_series)
        assert callable(get_opencast_series)
        assert callable(create_opencast_series)
        assert callable(list_opencast_events)
        assert callable(get_opencast_event)
        assert callable(ingest_to_opencast)
        assert callable(get_opencast_ingest_status)
        assert callable(schedule_opencast_capture)
        assert callable(delete_opencast_event)


class TestToolsQSysImports:
    """Tests for Q-SYS AV control integration tool imports."""

    def test_tools_qsys_imports(self):
        """Test that Q-SYS tools can be imported from the qsys module."""
        from epiphan_mcp.tools.qsys import (
            list_qsys_components,
            qsys_get_pearl_status,
            qsys_start_recording,
            qsys_stop_recording,
            qsys_switch_layout,
        )

        assert callable(list_qsys_components)
        assert callable(qsys_get_pearl_status)
        assert callable(qsys_start_recording)
        assert callable(qsys_stop_recording)
        assert callable(qsys_switch_layout)


class TestToolsYouTubeImports:
    """Tests for YouTube Live streaming integration tool imports."""

    def test_tools_youtube_imports(self):
        """Test that YouTube tools can be imported from the youtube module."""
        from epiphan_mcp.tools.youtube import (
            create_youtube_broadcast,
            end_youtube_broadcast,
            get_youtube_broadcast_status,
            list_youtube_broadcasts,
        )

        assert callable(create_youtube_broadcast)
        assert callable(get_youtube_broadcast_status)
        assert callable(list_youtube_broadcasts)
        assert callable(end_youtube_broadcast)


class TestToolsInitImports:
    """Tests for tools __init__.py exports."""

    def test_all_tools_exported_from_init(self):
        """Test that all tools are re-exported from tools package."""
        from epiphan_mcp.tools import (
            add_bookmark,
            batch_start_recording,
            batch_stop_recording,
            create_kaltura_category,
            create_kaltura_media,
            create_network_input,
            create_opencast_series,
            create_panopto_folder,
            create_panopto_session,
            create_publisher,
            create_scheduled_event,
            create_youtube_broadcast,
            delete_opencast_event,
            delete_panopto_session,
            delete_publisher,
            end_youtube_broadcast,
            get_afu_status,
            get_client,
            get_device_health_score,
            get_device_status,
            get_fleet_status,
            get_input_settings,
            get_kaltura_category,
            get_kaltura_media,
            get_kaltura_upload_status,
            get_opencast_event,
            get_opencast_ingest_status,
            get_opencast_series,
            get_panopto_folder,
            get_panopto_session,
            get_panopto_upload_status,
            get_publisher_settings,
            get_recording_status,
            get_scheduled_events,
            get_storage_report,
            get_stream_status,
            get_youtube_broadcast_status,
            ingest_to_opencast,
            list_devices,
            list_inputs,
            list_kaltura_categories,
            list_kaltura_media,
            list_layouts,
            list_opencast_events,
            list_opencast_series,
            list_outputs,
            list_panopto_folders,
            list_panopto_sessions,
            list_publisher_types,
            list_qsys_components,
            list_youtube_broadcasts,
            pause_event,
            predict_storage_full,
            qsys_get_pearl_status,
            qsys_start_recording,
            qsys_stop_recording,
            qsys_switch_layout,
            rename_publisher,
            resume_event,
            schedule_kaltura_event,
            schedule_opencast_capture,
            set_output_source,
            single_touch_start,
            single_touch_stop,
            start_recording,
            start_stream,
            stop_recording,
            stop_stream,
            switch_layout,
            update_input_settings,
            update_publisher_settings,
            upload_to_kaltura,
            upload_to_panopto,
        )

        # Verify all are callable
        all_tools = [
            get_client,
            get_device_status,
            list_devices,
            start_recording,
            stop_recording,
            get_recording_status,
            start_stream,
            stop_stream,
            get_stream_status,
            list_layouts,
            switch_layout,
            add_bookmark,
            list_inputs,
            get_storage_report,
            get_afu_status,
            predict_storage_full,
            get_device_health_score,
            get_fleet_status,
            batch_start_recording,
            batch_stop_recording,
            get_scheduled_events,
            single_touch_start,
            single_touch_stop,
            # New event tools
            create_scheduled_event,
            pause_event,
            resume_event,
            # New publisher tools
            create_publisher,
            delete_publisher,
            get_publisher_settings,
            update_publisher_settings,
            list_publisher_types,
            rename_publisher,
            # New input/output tools
            create_network_input,
            get_input_settings,
            update_input_settings,
            list_outputs,
            set_output_source,
            # Panopto CMS integration tools
            list_panopto_folders,
            get_panopto_folder,
            create_panopto_folder,
            list_panopto_sessions,
            get_panopto_session,
            create_panopto_session,
            upload_to_panopto,
            get_panopto_upload_status,
            delete_panopto_session,
            # Kaltura CMS integration tools
            list_kaltura_categories,
            get_kaltura_category,
            create_kaltura_category,
            list_kaltura_media,
            get_kaltura_media,
            create_kaltura_media,
            upload_to_kaltura,
            schedule_kaltura_event,
            get_kaltura_upload_status,
            # Opencast CMS integration tools
            list_opencast_series,
            get_opencast_series,
            create_opencast_series,
            list_opencast_events,
            get_opencast_event,
            ingest_to_opencast,
            get_opencast_ingest_status,
            schedule_opencast_capture,
            delete_opencast_event,
            # Q-SYS AV control integration tools
            list_qsys_components,
            qsys_get_pearl_status,
            qsys_start_recording,
            qsys_stop_recording,
            qsys_switch_layout,
            # YouTube Live streaming integration tools
            create_youtube_broadcast,
            get_youtube_broadcast_status,
            list_youtube_broadcasts,
            end_youtube_broadcast,
        ]
        for tool in all_tools:
            assert callable(tool)


class TestMCPToolRegistration:
    """Tests for MCP tool registration."""

    def test_all_tools_registered(self):
        """Test that all 92 MCP tools are registered.

        46 Pearl core + 9 Panopto + 9 Kaltura + 9 Opencast + 5 Q-SYS + 4 YouTube + 10 EC20 = 92
        """
        from epiphan_mcp.server import mcp

        tools = list(mcp._tool_manager._tools.keys())
        assert len(tools) == 92, f"Expected 92 tools, got {len(tools)}: {tools}"

    def test_expected_tools_registered(self):
        """Test that all expected tools are registered with MCP."""
        from epiphan_mcp.server import mcp

        expected_tools = [
            # Device tools
            "get_device_status",
            "list_devices",
            # Storage tools
            "list_inputs",
            "get_storage_report",
            "get_afu_status",
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
            # Schedule tools
            "single_touch_start",
            "single_touch_stop",
            "get_scheduled_events",
            "create_scheduled_event",
            "pause_event",
            "resume_event",
            # Maintenance tools
            "predict_storage_full",
            "get_device_health_score",
            # Fleet tools
            "get_fleet_status",
            "batch_start_recording",
            "batch_stop_recording",
            "fleet_health_report",
            # AI tools
            "analyze_channel_scene",
            "extract_text_from_preview",
            "detect_layout_changes",
            "check_video_quality",
            "clear_change_detection_cache",
            # Sprint 3 AI Moat tools
            "detect_recording_issues",
            "suggest_maintenance_window",
            "predict_fleet_issues",
            "generate_shift_handoff",
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
            # EC20 PTZ camera control tools
            "ec20_get_status",
            "ec20_pan_tilt",
            "ec20_zoom",
            "ec20_goto_preset",
            "ec20_save_preset",
            "ec20_home",
            "ec20_enable_tracking",
            "ec20_disable_tracking",
            "ec20_list_presets",
            "ec20_get_preview",
        ]

        tools = list(mcp._tool_manager._tools.keys())
        for expected in expected_tools:
            assert expected in tools, f"Missing tool: {expected}"

    def test_tool_count_unchanged(self):
        """Test that the tool count is exactly 92.

        46 Pearl core + 9 Panopto + 9 Kaltura + 9 Opencast + 5 Q-SYS + 4 YouTube + 10 EC20 = 92
        """
        from epiphan_mcp.server import mcp

        expected_tools = [
            "get_device_status",
            "list_devices",
            "list_inputs",
            "get_storage_report",
            "start_recording",
            "stop_recording",
            "get_recording_status",
            "start_stream",
            "stop_stream",
            "get_stream_status",
            "add_bookmark",
            "list_layouts",
            "switch_layout",
            "single_touch_start",
            "single_touch_stop",
            "get_scheduled_events",
            "create_scheduled_event",
            "pause_event",
            "resume_event",
            "get_afu_status",
            "predict_storage_full",
            "get_device_health_score",
            "get_fleet_status",
            "batch_start_recording",
            "batch_stop_recording",
            "fleet_health_report",
            "analyze_channel_scene",
            "extract_text_from_preview",
            "detect_layout_changes",
            "check_video_quality",
            "clear_change_detection_cache",
            "detect_recording_issues",
            "suggest_maintenance_window",
            "predict_fleet_issues",
            "generate_shift_handoff",
            # Publisher management tools
            "create_publisher",
            "delete_publisher",
            "get_publisher_settings",
            "update_publisher_settings",
            "list_publisher_types",
            "rename_publisher",
            # Input/output management tools
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
            # EC20 PTZ camera control tools
            "ec20_get_status",
            "ec20_pan_tilt",
            "ec20_zoom",
            "ec20_goto_preset",
            "ec20_save_preset",
            "ec20_home",
            "ec20_enable_tracking",
            "ec20_disable_tracking",
            "ec20_list_presets",
            "ec20_get_preview",
        ]

        tools = list(mcp._tool_manager._tools.keys())
        # Total: 46 Pearl + 9 Panopto + 9 Kaltura + 9 Opencast + 5 Q-SYS + 4 YouTube + 10 EC20 = 92
        assert len(tools) == len(expected_tools), (
            f"Tool count mismatch: expected {len(expected_tools)}, got {len(tools)}"
        )
