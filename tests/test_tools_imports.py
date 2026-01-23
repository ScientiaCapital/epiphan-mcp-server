"""Tests for tool module imports.

Verifies that all tools are properly organized into modules and registered with MCP.
Following TDD: these tests are written FIRST, before implementing the modules.
"""

import pytest


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
            get_scheduled_events,
            single_touch_start,
            single_touch_stop,
        )

        assert callable(get_scheduled_events)
        assert callable(single_touch_start)
        assert callable(single_touch_stop)


class TestToolsInitImports:
    """Tests for tools __init__.py exports."""

    def test_all_tools_exported_from_init(self):
        """Test that all tools are re-exported from tools package."""
        from epiphan_mcp.tools import (
            add_bookmark,
            batch_start_recording,
            batch_stop_recording,
            get_afu_status,
            get_client,
            get_device_health_score,
            get_device_status,
            get_fleet_status,
            get_recording_status,
            get_scheduled_events,
            get_storage_report,
            get_stream_status,
            list_devices,
            list_inputs,
            list_layouts,
            predict_storage_full,
            single_touch_start,
            single_touch_stop,
            start_recording,
            start_stream,
            stop_recording,
            stop_stream,
            switch_layout,
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
        ]
        for tool in all_tools:
            assert callable(tool)


class TestMCPToolRegistration:
    """Tests for MCP tool registration."""

    def test_all_tools_registered(self):
        """Test that all 27 MCP tools are still registered after refactoring."""
        from epiphan_mcp.server import mcp

        tools = list(mcp._tool_manager._tools.keys())
        assert len(tools) == 27, f"Expected 27 tools, got {len(tools)}: {tools}"

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
            # Maintenance tools
            "predict_storage_full",
            "get_device_health_score",
            # Fleet tools
            "get_fleet_status",
            "batch_start_recording",
            "batch_stop_recording",
            # AI tools
            "analyze_channel_scene",
            "extract_text_from_preview",
            "detect_layout_changes",
            "check_video_quality",
            "clear_change_detection_cache",
        ]

        tools = list(mcp._tool_manager._tools.keys())
        for expected in expected_tools:
            assert expected in tools, f"Missing tool: {expected}"

    def test_tool_count_unchanged(self):
        """Test that the tool count is exactly 27 (no additions/removals)."""
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
            "get_afu_status",
            "predict_storage_full",
            "get_device_health_score",
            "get_fleet_status",
            "batch_start_recording",
            "batch_stop_recording",
            "analyze_channel_scene",
            "extract_text_from_preview",
            "detect_layout_changes",
            "check_video_quality",
            "clear_change_detection_cache",
        ]

        tools = list(mcp._tool_manager._tools.keys())
        assert len(tools) == len(expected_tools), (
            f"Tool count mismatch: expected {len(expected_tools)}, got {len(tools)}"
        )
