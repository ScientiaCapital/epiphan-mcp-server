"""Tests for audit logging module.

Verifies that audit.log_operation() produces correct log output
and that SENSITIVE_OPERATIONS is complete.
"""

import logging

from epiphan_mcp.audit import SENSITIVE_OPERATIONS, is_sensitive_operation, log_operation


class TestLogOperation:
    """Tests for the log_operation function."""

    def test_log_operation_success(self, caplog):
        """Successful operation should log with SUCCESS status."""
        with caplog.at_level(logging.INFO, logger="epiphan_mcp.audit"):
            log_operation("reboot", "192.168.1.100", details={"device_id": "default"})

        assert len(caplog.records) == 1
        assert "[SUCCESS]" in caplog.records[0].message
        assert "reboot" in caplog.records[0].message
        assert "192.168.1.100" in caplog.records[0].message

    def test_log_operation_failure(self, caplog):
        """Failed operation should log with FAILED status."""
        with caplog.at_level(logging.INFO, logger="epiphan_mcp.audit"):
            log_operation(
                "shutdown",
                "192.168.1.100",
                success=False,
                details={"error": "Connection refused"},
            )

        assert len(caplog.records) == 1
        assert "[FAILED]" in caplog.records[0].message
        assert "shutdown" in caplog.records[0].message
        assert "Connection refused" in caplog.records[0].message

    def test_log_operation_default_user(self, caplog):
        """Default user should be mcp_client."""
        with caplog.at_level(logging.INFO, logger="epiphan_mcp.audit"):
            log_operation("reboot", "192.168.1.100")

        assert "mcp_client" in caplog.records[0].message

    def test_log_operation_custom_user(self, caplog):
        """Custom user should appear in log."""
        with caplog.at_level(logging.INFO, logger="epiphan_mcp.audit"):
            log_operation("reboot", "192.168.1.100", user="admin_user")

        assert "admin_user" in caplog.records[0].message

    def test_log_operation_returns_none(self):
        """log_operation should return None."""
        result = log_operation("reboot", "192.168.1.100")
        assert result is None


class TestIsSensitiveOperation:
    """Tests for the is_sensitive_operation function."""

    def test_is_sensitive_operation_true(self):
        """Known sensitive operations should return True."""
        assert is_sensitive_operation("reboot") is True
        assert is_sensitive_operation("shutdown") is True
        assert is_sensitive_operation("delete_publisher") is True
        assert is_sensitive_operation("cloud_unpair_device") is True
        assert is_sensitive_operation("cloud_delete_device") is True

    def test_is_sensitive_operation_false(self):
        """Non-sensitive operations should return False."""
        assert is_sensitive_operation("get_device_status") is False
        assert is_sensitive_operation("list_devices") is False
        assert is_sensitive_operation("nonexistent_op") is False


class TestSensitiveOperationsComplete:
    """Test that SENSITIVE_OPERATIONS includes all destructive operations."""

    def test_destructive_operations_registered(self):
        """All destructive operations should be in SENSITIVE_OPERATIONS."""
        expected_destructive = {
            "reboot",
            "shutdown",
            "delete_publisher",
            "cloud_unpair_device",
            "cloud_delete_device",
            "delete_panopto_session",
            "delete_opencast_event",
        }
        for op in expected_destructive:
            assert op in SENSITIVE_OPERATIONS, f"Missing destructive op: {op}"

    def test_sensitive_operations_is_set(self):
        """SENSITIVE_OPERATIONS should be a set for O(1) lookups."""
        assert isinstance(SENSITIVE_OPERATIONS, set)
