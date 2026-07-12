"""Tests for configuration settings.

Tests configurable health thresholds and retry settings.
Following TDD: tests written BEFORE implementation.
"""

import pytest

from epiphan_mcp.config import Settings, get_settings

# ============================================================
# Health Threshold Tests
# ============================================================


class TestHealthThresholds:
    """Test configurable health thresholds."""

    def test_default_threshold_values(self):
        """Default thresholds should be storage_warning=80, storage_critical=90."""
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="test",
        )

        assert settings.storage_warning_percent == 80.0
        assert settings.storage_critical_percent == 90.0

    def test_threshold_from_environment(self, monkeypatch):
        """PEARL_STORAGE_WARNING_PERCENT=75 should load correctly."""
        # Clear lru_cache
        get_settings.cache_clear()

        monkeypatch.setenv("PEARL_STORAGE_WARNING_PERCENT", "75")
        monkeypatch.setenv("PEARL_STORAGE_CRITICAL_PERCENT", "85")
        monkeypatch.setenv("PEARL_DEVICES", "192.168.1.100")
        monkeypatch.setenv("PEARL_PASSWORD", "test")

        settings = get_settings()

        assert settings.storage_warning_percent == 75.0
        assert settings.storage_critical_percent == 85.0

        # Cleanup
        get_settings.cache_clear()

    def test_threshold_validation_bounds_lower(self):
        """Thresholds below 0 should fail validation."""
        with pytest.raises(ValueError):
            Settings(
                devices="192.168.1.100",
                username="admin",
                password="test",
                storage_warning_percent=-1.0,
            )

    def test_threshold_validation_bounds_upper(self):
        """Thresholds above 100 should fail validation."""
        with pytest.raises(ValueError):
            Settings(
                devices="192.168.1.100",
                username="admin",
                password="test",
                storage_warning_percent=101.0,
            )

    def test_threshold_validation_bounds_critical(self):
        """Critical threshold validation bounds."""
        with pytest.raises(ValueError):
            Settings(
                devices="192.168.1.100",
                username="admin",
                password="test",
                storage_critical_percent=150.0,
            )

    def test_threshold_at_boundaries(self):
        """Thresholds at 0 and 100 should be valid."""
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="test",
            storage_warning_percent=0.0,
            storage_critical_percent=100.0,
        )

        assert settings.storage_warning_percent == 0.0
        assert settings.storage_critical_percent == 100.0


# ============================================================
# Health Score Weight Tests
# ============================================================


class TestHealthScoreWeights:
    """Test configurable health score weights."""

    def test_health_score_weights_default(self):
        """Default weights should be storage_weight=50, recording_weight=50."""
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="test",
        )

        assert settings.health_score_storage_weight == 50
        assert settings.health_score_recording_weight == 50

    def test_health_score_weights_from_env(self, monkeypatch):
        """PEARL_HEALTH_SCORE_STORAGE_WEIGHT=60 should load correctly."""
        get_settings.cache_clear()

        monkeypatch.setenv("PEARL_HEALTH_SCORE_STORAGE_WEIGHT", "60")
        monkeypatch.setenv("PEARL_HEALTH_SCORE_RECORDING_WEIGHT", "40")
        monkeypatch.setenv("PEARL_DEVICES", "192.168.1.100")
        monkeypatch.setenv("PEARL_PASSWORD", "test")

        settings = get_settings()

        assert settings.health_score_storage_weight == 60
        assert settings.health_score_recording_weight == 40

        get_settings.cache_clear()

    def test_health_score_weight_validation_bounds(self):
        """Weight values must be 0-100."""
        with pytest.raises(ValueError):
            Settings(
                devices="192.168.1.100",
                username="admin",
                password="test",
                health_score_storage_weight=150,
            )

        with pytest.raises(ValueError):
            Settings(
                devices="192.168.1.100",
                username="admin",
                password="test",
                health_score_storage_weight=-10,
            )

    def test_health_score_weights_custom_split(self):
        """Custom weight splits should work."""
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="test",
            health_score_storage_weight=70,
            health_score_recording_weight=30,
        )

        assert settings.health_score_storage_weight == 70
        assert settings.health_score_recording_weight == 30


# ============================================================
# Retry Settings Tests
# ============================================================


class TestRetrySettings:
    """Test configurable retry settings."""

    def test_retry_settings_defaults(self):
        """Default retry settings: max_retries=3, base_delay=1.0, max_delay=30.0."""
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="test",
        )

        assert settings.max_retries == 3
        assert settings.retry_base_delay == 1.0
        assert settings.retry_max_delay == 30.0

    def test_retry_settings_from_env(self, monkeypatch):
        """Retry settings should load from environment."""
        get_settings.cache_clear()

        monkeypatch.setenv("PEARL_MAX_RETRIES", "5")
        monkeypatch.setenv("PEARL_RETRY_BASE_DELAY", "2.0")
        monkeypatch.setenv("PEARL_RETRY_MAX_DELAY", "60.0")
        monkeypatch.setenv("PEARL_DEVICES", "192.168.1.100")
        monkeypatch.setenv("PEARL_PASSWORD", "test")

        settings = get_settings()

        assert settings.max_retries == 5
        assert settings.retry_base_delay == 2.0
        assert settings.retry_max_delay == 60.0

        get_settings.cache_clear()

    def test_retry_max_retries_bounds(self):
        """max_retries must be 0-10."""
        # Should pass at boundary
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="test",
            max_retries=10,
        )
        assert settings.max_retries == 10

        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="test",
            max_retries=0,
        )
        assert settings.max_retries == 0

        # Should fail outside bounds
        with pytest.raises(ValueError):
            Settings(
                devices="192.168.1.100",
                username="admin",
                password="test",
                max_retries=11,
            )

    def test_retry_base_delay_min(self):
        """retry_base_delay must be >= 0.1."""
        with pytest.raises(ValueError):
            Settings(
                devices="192.168.1.100",
                username="admin",
                password="test",
                retry_base_delay=0.05,
            )

    def test_retry_max_delay_min(self):
        """retry_max_delay must be >= 1.0."""
        with pytest.raises(ValueError):
            Settings(
                devices="192.168.1.100",
                username="admin",
                password="test",
                retry_max_delay=0.5,
            )


# ============================================================
# Settings Integration Tests
# ============================================================


class TestSettingsIntegration:
    """Test that all new settings work together correctly."""

    def test_all_new_settings_can_be_set(self):
        """All new configurable settings can be set together."""
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="test",
            # Health thresholds
            storage_warning_percent=75.0,
            storage_critical_percent=85.0,
            # Health score weights
            health_score_storage_weight=60,
            health_score_recording_weight=40,
            # Retry settings
            max_retries=5,
            retry_base_delay=2.0,
            retry_max_delay=60.0,
        )

        # Verify all settings
        assert settings.storage_warning_percent == 75.0
        assert settings.storage_critical_percent == 85.0
        assert settings.health_score_storage_weight == 60
        assert settings.health_score_recording_weight == 40
        assert settings.max_retries == 5
        assert settings.retry_base_delay == 2.0
        assert settings.retry_max_delay == 60.0

    def test_new_settings_do_not_affect_existing(self):
        """New settings should not affect existing functionality."""
        settings = Settings(
            devices="192.168.1.100,192.168.1.101",
            username="admin",
            password="test",
            use_https=True,
            timeout=45.0,
            fleet_name="test-fleet",
        )

        # Existing settings work
        assert settings.get_device_list() == ["192.168.1.100", "192.168.1.101"]
        assert settings.username == "admin"
        assert settings.use_https is True
        assert settings.timeout == 45.0
        assert settings.fleet_name == "test-fleet"

        # New settings have defaults
        assert settings.storage_warning_percent == 80.0
        assert settings.storage_critical_percent == 90.0
        assert settings.max_retries == 3


# ============================================================
# Device Host Validation Tests (C1 Security Fix)
# ============================================================


class TestDeviceHostValidation:
    """Test _validate_host rejects malicious device_id values."""

    def _make_settings(self, **kwargs):
        """Create Settings with sensible defaults."""
        defaults = {
            "devices": "192.168.1.100,pearl-01.local",
            "username": "admin",
            "password": "test",
        }
        defaults.update(kwargs)
        return Settings(**defaults)

    def test_get_device_host_valid_ip(self):
        """Valid IP address should pass validation."""
        settings = self._make_settings()
        assert settings.get_device_host("10.0.0.1") == "10.0.0.1"

    def test_get_device_host_valid_ipv6(self):
        """Valid IPv6 address should pass validation."""
        settings = self._make_settings()
        assert settings.get_device_host("::1") == "::1"

    def test_get_device_host_valid_hostname(self):
        """Valid hostname should pass validation."""
        settings = self._make_settings()
        assert settings.get_device_host("pearl-01.local") == "pearl-01.local"

    def test_get_device_host_valid_simple_hostname(self):
        """Simple hostname without dots should pass."""
        settings = self._make_settings()
        assert settings.get_device_host("pearl01") == "pearl01"

    def test_get_device_host_configured_device_always_passes(self):
        """A device in the configured list should always pass."""
        settings = self._make_settings()
        assert settings.get_device_host("192.168.1.100") == "192.168.1.100"

    def test_get_device_host_rejects_url(self):
        """URL-like input should be rejected."""
        settings = self._make_settings()
        with pytest.raises(ValueError, match="looks like a URL"):
            settings.get_device_host("http://evil.com")

    def test_get_device_host_rejects_at_sign(self):
        """Input with @ should be rejected (possible user@host injection)."""
        settings = self._make_settings()
        with pytest.raises(ValueError, match="forbidden characters"):
            settings.get_device_host("user@host")

    def test_get_device_host_rejects_spaces(self):
        """Input with spaces should be rejected."""
        settings = self._make_settings()
        with pytest.raises(ValueError, match="forbidden characters"):
            settings.get_device_host("host name")

    def test_get_device_host_rejects_path_traversal(self):
        """Path traversal patterns should be rejected."""
        settings = self._make_settings()
        with pytest.raises(ValueError, match="path traversal"):
            settings.get_device_host("../../etc/passwd")

    def test_get_device_host_rejects_newlines(self):
        """Input with newlines should be rejected (header injection)."""
        settings = self._make_settings()
        with pytest.raises(ValueError, match="forbidden characters"):
            settings.get_device_host("host\r\nX-Injected: true")

    def test_get_device_host_rejects_long_hostname(self):
        """Hostnames over 253 chars should be rejected."""
        settings = self._make_settings()
        long_host = "a" * 254
        with pytest.raises(ValueError, match="exceeds 253"):
            settings.get_device_host(long_host)

    def test_get_ec20_host_same_validation(self):
        """EC20 host resolution should use the same validation."""
        settings = self._make_settings()
        # Valid input works
        assert settings.get_ec20_host("10.0.0.50") == "10.0.0.50"
        # Bad input rejected
        with pytest.raises(ValueError, match="looks like a URL"):
            settings.get_ec20_host("https://attacker.com")
        with pytest.raises(ValueError, match="forbidden characters"):
            settings.get_ec20_host("user@camera")

    def test_get_device_host_rejects_special_chars(self):
        """Hostnames with invalid characters should be rejected."""
        settings = self._make_settings()
        with pytest.raises(ValueError, match="not a valid IP or hostname"):
            settings.get_device_host("pearl;drop")  # semicolon, no spaces

    def test_get_device_host_default_still_works(self):
        """'default' keyword should still resolve to first configured device."""
        settings = self._make_settings()
        assert settings.get_device_host("default") == "192.168.1.100"

    def test_get_device_host_index_still_works(self):
        """Numeric index should still resolve to configured device list."""
        settings = self._make_settings()
        assert settings.get_device_host("0") == "192.168.1.100"
        assert settings.get_device_host("1") == "pearl-01.local"


# ============================================================
# Max Concurrent Ops (Semaphore) Tests
# ============================================================


class TestMaxConcurrentOps:
    """Test configurable max_concurrent_ops setting."""

    def test_max_concurrent_ops_default(self):
        """Default max_concurrent_ops should be 10."""
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="test",
        )
        assert settings.max_concurrent_ops == 10

    def test_max_concurrent_ops_custom(self):
        """Custom max_concurrent_ops value should be accepted."""
        settings = Settings(
            devices="192.168.1.100",
            username="admin",
            password="test",
            max_concurrent_ops=20,
        )
        assert settings.max_concurrent_ops == 20

    def test_max_concurrent_ops_env_override(self, monkeypatch):
        """PEARL_MAX_CONCURRENT_OPS env var should override default."""
        get_settings.cache_clear()

        monkeypatch.setenv("PEARL_MAX_CONCURRENT_OPS", "25")
        monkeypatch.setenv("PEARL_DEVICES", "192.168.1.100")
        monkeypatch.setenv("PEARL_PASSWORD", "test")

        settings = get_settings()
        assert settings.max_concurrent_ops == 25

        get_settings.cache_clear()

    def test_max_concurrent_ops_bounds_lower(self):
        """max_concurrent_ops below 1 should fail validation."""
        with pytest.raises(ValueError):
            Settings(
                devices="192.168.1.100",
                username="admin",
                password="test",
                max_concurrent_ops=0,
            )

    def test_max_concurrent_ops_bounds_upper(self):
        """max_concurrent_ops above 100 should fail validation."""
        with pytest.raises(ValueError):
            Settings(
                devices="192.168.1.100",
                username="admin",
                password="test",
                max_concurrent_ops=101,
            )
