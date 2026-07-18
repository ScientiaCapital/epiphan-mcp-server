"""Tests for tools/fleet_intelligence.py.

test_fleet.py already covers the happy-path/empty-fleet/LLM-fallback behavior
of suggest_maintenance_window, predict_fleet_issues, and generate_shift_handoff
via the full HTTP mock chain (TestSuggestMaintenanceWindow, TestPredictFleetIssues,
TestGenerateShiftHandoff). This file fills the gaps: the pure parsing/formatting
helpers, predict_fleet_issues' storage/health/risk-level branches (which need
precise device-level values that are awkward to reverse-engineer through the
full get_system_status HTTP chain), and the fleet_status.success=False defensive
branch shared by all three tools.
"""

from unittest.mock import AsyncMock, patch

from epiphan_mcp.config import Settings
from epiphan_mcp.llm.providers import LLMError
from epiphan_mcp.models import FleetStatusResult
from epiphan_mcp.tools.fleet_intelligence import (
    _format_attention_items,
    _format_predictions,
    _parse_maintenance_suggestion,
)


def make_settings(devices: str = "192.168.1.100") -> Settings:
    return Settings(
        devices=devices,
        username="admin",
        password="testpass",
        use_https=False,
        timeout=5.0,
        verify_ssl=False,
        fleet_name="test",
        storage_warning_percent=80.0,
        max_retries=0,
    )


def make_fleet_status(devices: list[dict], **overrides: object) -> FleetStatusResult:
    online = sum(1 for d in devices if d.get("online"))
    recording = sum(1 for d in devices if d.get("recording"))
    defaults: dict[str, object] = {
        "success": True,
        "fleet_name": "test",
        "total_devices": len(devices),
        "online_devices": online,
        "recording_devices": recording,
        "average_health": 100.0,
        "unhealthy_devices": 0,
        "alerts_count": 0,
        "devices": devices,
        "alerts": [],
    }
    defaults.update(overrides)
    return FleetStatusResult(**defaults)


# ============================================================
# Pure helper functions
# ============================================================


class TestParseMaintenanceSuggestion:
    def test_extracts_window_and_high_confidence(self):
        response = (
            "Tonight 10pm-2am would be ideal.\nConfidence: high\nAll devices are idle right now."
        )
        window, confidence, reasoning = _parse_maintenance_suggestion(response, "idle", 0)
        assert "tonight" in window.lower()
        assert confidence == "high"
        assert reasoning

    def test_extracts_low_confidence(self):
        response = "This weekend Saturday 6am-10am.\nConfidence: low\nUsage patterns are unclear this week."
        _, confidence, _ = _parse_maintenance_suggestion(response, "idle", 0)
        assert confidence == "low"

    def test_unparseable_response_falls_back(self):
        window, confidence, reasoning = _parse_maintenance_suggestion("??", "idle", 0)
        assert window == "Review fleet status manually"
        assert confidence == "medium"
        assert "unable to parse" in reasoning.lower()


class TestFormatPredictions:
    def test_empty_list_returns_none_marker(self):
        assert _format_predictions([]) == "None"

    def test_formats_device_issue_severity(self):
        formatted = _format_predictions(
            [{"device": "192.168.1.100", "issue": "Storage full", "severity": "critical"}]
        )
        assert "192.168.1.100" in formatted
        assert "Storage full" in formatted
        assert "critical" in formatted


class TestFormatAttentionItems:
    def test_empty_list_returns_normal_marker(self):
        assert _format_attention_items([]) == "None - all systems normal"

    def test_formats_device_issue_priority(self):
        formatted = _format_attention_items(
            [{"device": "192.168.1.100", "issue": "Device offline", "priority": "high"}]
        )
        assert "192.168.1.100" in formatted
        assert "Device offline" in formatted
        assert "priority: high" in formatted

    def test_truncates_to_five_items(self):
        items = [{"device": f"host-{i}", "issue": "issue", "priority": "medium"} for i in range(8)]
        formatted = _format_attention_items(items)
        assert formatted.count("host-") == 5


# ============================================================
# predict_fleet_issues — storage / health / risk-level branches
# ============================================================


class TestPredictFleetIssuesBranches:
    async def test_storage_warning_below_full_threshold(self):
        """storage_percent >= 75 but device isn't recording -> a warning, not a full-in-N-hours prediction."""
        from epiphan_mcp.server import predict_fleet_issues

        devices = [
            {"host": "192.168.1.100", "online": True, "recording": False, "storage_percent": 80},
            {"host": "192.168.1.101", "online": True, "recording": False, "storage_percent": 10},
            {"host": "192.168.1.102", "online": True, "recording": False, "storage_percent": 10},
            {"host": "192.168.1.103", "online": True, "recording": False, "storage_percent": 10},
        ]

        with (
            patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings,
            patch(
                "epiphan_mcp.tools.fleet_intelligence.get_fleet_status",
                new=AsyncMock(return_value=make_fleet_status(devices)),
            ),
            patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider,
        ):
            mock_settings.return_value = make_settings(
                devices="192.168.1.100,192.168.1.101,192.168.1.102,192.168.1.103"
            )
            mock_llm = AsyncMock()
            mock_llm.complete = AsyncMock(return_value="One device has limited storage headroom.")
            mock_llm.close = AsyncMock()
            mock_provider.return_value = mock_llm

            result = await predict_fleet_issues.fn(hours_ahead=24)

        assert result.success is True
        warning = next(p for p in result.predictions if p["device"] == "192.168.1.100")
        assert "limited capacity" in warning["issue"].lower()
        assert warning["severity"] == "warning"
        # 1 warning out of 4 devices (25%) is under the 30% "high" escalation threshold.
        assert result.risk_level == "medium"

    async def test_storage_critical_when_recording_and_nearly_full(self):
        """recording=True + storage so high the fill estimate is under 4h -> critical, not warning."""
        from epiphan_mcp.server import predict_fleet_issues

        devices = [
            {"host": "192.168.1.100", "online": True, "recording": True, "storage_percent": 99},
        ]

        with (
            patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings,
            patch(
                "epiphan_mcp.tools.fleet_intelligence.get_fleet_status",
                new=AsyncMock(return_value=make_fleet_status(devices)),
            ),
            patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider,
        ):
            mock_settings.return_value = make_settings()
            mock_llm = AsyncMock()
            mock_llm.complete = AsyncMock(return_value="Storage will fill soon.")
            mock_llm.close = AsyncMock()
            mock_provider.return_value = mock_llm

            result = await predict_fleet_issues.fn(hours_ahead=24)

        assert result.success is True
        critical = next(p for p in result.predictions if p["device"] == "192.168.1.100")
        assert "hours" in critical["issue"].lower()
        assert critical["severity"] == "critical"
        assert result.risk_level == "critical"

    async def test_degraded_health_score_produces_warning(self):
        from epiphan_mcp.server import predict_fleet_issues

        devices = [
            {
                "host": "192.168.1.100",
                "online": True,
                "recording": False,
                "storage_percent": 10,
                "health_score": 45,
            },
        ]

        with (
            patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings,
            patch(
                "epiphan_mcp.tools.fleet_intelligence.get_fleet_status",
                new=AsyncMock(return_value=make_fleet_status(devices)),
            ),
            patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider,
        ):
            mock_settings.return_value = make_settings()
            mock_llm = AsyncMock()
            mock_llm.complete = AsyncMock(return_value="Health degraded on one device.")
            mock_llm.close = AsyncMock()
            mock_provider.return_value = mock_llm

            result = await predict_fleet_issues.fn(hours_ahead=24)

        assert result.success is True
        health_pred = next(p for p in result.predictions if "health" in p["issue"].lower())
        assert health_pred["severity"] == "warning"
        assert result.devices_at_risk >= 1

    async def test_high_risk_when_warnings_exceed_30_percent(self):
        from epiphan_mcp.server import predict_fleet_issues

        devices = [
            {"host": "192.168.1.100", "online": True, "recording": False, "storage_percent": 80},
            {"host": "192.168.1.101", "online": True, "recording": False, "storage_percent": 80},
            {"host": "192.168.1.102", "online": True, "recording": False, "storage_percent": 10},
            {"host": "192.168.1.103", "online": True, "recording": False, "storage_percent": 10},
        ]

        with (
            patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings,
            patch(
                "epiphan_mcp.tools.fleet_intelligence.get_fleet_status",
                new=AsyncMock(return_value=make_fleet_status(devices)),
            ),
            patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider,
        ):
            mock_settings.return_value = make_settings(
                devices="192.168.1.100,192.168.1.101,192.168.1.102,192.168.1.103"
            )
            mock_llm = AsyncMock()
            mock_llm.complete = AsyncMock(return_value="Two devices need storage attention.")
            mock_llm.close = AsyncMock()
            mock_provider.return_value = mock_llm

            result = await predict_fleet_issues.fn(hours_ahead=24)

        assert result.success is True
        # 2 warnings out of 4 devices (50%) exceeds the 30% "high" escalation threshold.
        assert result.risk_level == "high"

    async def test_llm_summary_failure_falls_back(self):
        from epiphan_mcp.server import predict_fleet_issues

        devices = [
            {"host": "192.168.1.100", "online": False, "storage_percent": 0},
        ]

        with (
            patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings,
            patch(
                "epiphan_mcp.tools.fleet_intelligence.get_fleet_status",
                new=AsyncMock(return_value=make_fleet_status(devices)),
            ),
            patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider,
        ):
            mock_settings.return_value = make_settings()
            mock_llm = AsyncMock()
            mock_llm.complete = AsyncMock(side_effect=LLMError("boom"))
            mock_provider.return_value = mock_llm

            result = await predict_fleet_issues.fn(hours_ahead=24)

        assert result.success is True
        assert "predicted issues" in result.summary.lower()


# ============================================================
# fleet_status.success=False defensive branch — all three tools
# ============================================================


class TestFleetStatusFailurePropagation:
    async def test_suggest_maintenance_window_propagates_failure(self):
        from epiphan_mcp.server import suggest_maintenance_window

        with (
            patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings,
            patch(
                "epiphan_mcp.tools.fleet_intelligence.get_fleet_status",
                new=AsyncMock(return_value=FleetStatusResult(success=False)),
            ),
        ):
            mock_settings.return_value = make_settings()
            result = await suggest_maintenance_window.fn(min_duration_hours=2.0)

        assert result.success is False
        assert result.error

    async def test_predict_fleet_issues_propagates_failure(self):
        from epiphan_mcp.server import predict_fleet_issues

        with (
            patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings,
            patch(
                "epiphan_mcp.tools.fleet_intelligence.get_fleet_status",
                new=AsyncMock(return_value=FleetStatusResult(success=False)),
            ),
        ):
            mock_settings.return_value = make_settings()
            result = await predict_fleet_issues.fn(hours_ahead=24)

        assert result.success is False
        assert result.error

    async def test_generate_shift_handoff_propagates_failure(self):
        from epiphan_mcp.server import generate_shift_handoff

        with (
            patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings,
            patch(
                "epiphan_mcp.tools.fleet_intelligence.get_fleet_status",
                new=AsyncMock(return_value=FleetStatusResult(success=False)),
            ),
        ):
            mock_settings.return_value = make_settings()
            result = await generate_shift_handoff.fn(shift_hours=8)

        assert result.success is False
        assert result.error


# ============================================================
# suggest_maintenance_window — LLM fallback branches
# ============================================================


class TestSuggestMaintenanceWindowFallback:
    async def test_fallback_when_no_devices_recording(self):
        from epiphan_mcp.server import suggest_maintenance_window

        devices = [
            {"host": "192.168.1.100", "online": True, "recording": False, "storage_percent": 10},
        ]

        with (
            patch("epiphan_mcp.tools.fleet.get_settings") as mock_settings,
            patch(
                "epiphan_mcp.tools.fleet_intelligence.get_fleet_status",
                new=AsyncMock(return_value=make_fleet_status(devices)),
            ),
            patch("epiphan_mcp.tools.fleet.get_provider") as mock_provider,
        ):
            mock_settings.return_value = make_settings()
            mock_llm = AsyncMock()
            mock_llm.complete = AsyncMock(side_effect=LLMError("boom"))
            mock_provider.return_value = mock_llm

            result = await suggest_maintenance_window.fn(min_duration_hours=2.0)

        assert result.success is True
        assert result.confidence == "high"
        assert "no active recordings" in result.suggested_window.lower() or "now" in (
            result.suggested_window.lower()
        )
