"""Tests for URL validation (SSRF prevention)."""

import pytest

from epiphan_mcp.validation import ValidationError, validate_streaming_url


class TestValidateStreamingUrl:
    """Test validate_streaming_url for SSRF prevention."""

    def test_valid_rtmp_url(self):
        """Valid RTMP URL should pass."""
        result = validate_streaming_url("rtmp://live.twitch.tv/app")
        assert result == "rtmp://live.twitch.tv/app"

    def test_valid_srt_url(self):
        """Valid SRT URL should pass."""
        result = validate_streaming_url("srt://streaming.example.com:9000")
        assert result == "srt://streaming.example.com:9000"

    def test_valid_https_url(self):
        """Valid HTTPS URL should pass."""
        result = validate_streaming_url("https://stream.example.com/live")
        assert result == "https://stream.example.com/live"

    def test_valid_rtmps_url(self):
        """Valid RTMPS URL should pass."""
        result = validate_streaming_url("rtmps://live.youtube.com/stream")
        assert result == "rtmps://live.youtube.com/stream"

    def test_valid_rtsp_url(self):
        """Valid RTSP URL should pass."""
        result = validate_streaming_url("rtsp://camera.example.com/feed")
        assert result == "rtsp://camera.example.com/feed"

    def test_valid_udp_url(self):
        """Valid UDP URL should pass."""
        result = validate_streaming_url("udp://239.1.1.1:5004")
        assert result == "udp://239.1.1.1:5004"

    def test_private_ip_rejected(self):
        """Private IP ranges should be rejected."""
        with pytest.raises(ValidationError, match="private/internal"):
            validate_streaming_url("rtmp://192.168.1.100/stream")

    def test_private_10_network_rejected(self):
        """10.x.x.x private range should be rejected."""
        with pytest.raises(ValidationError, match="private/internal"):
            validate_streaming_url("rtmp://10.0.0.1/stream")

    def test_localhost_rejected(self):
        """localhost should be rejected."""
        with pytest.raises(ValidationError, match="localhost"):
            validate_streaming_url("rtmp://localhost/stream")

    def test_loopback_rejected(self):
        """127.0.0.1 loopback should be rejected."""
        with pytest.raises(ValidationError, match="localhost"):
            validate_streaming_url("http://127.0.0.1/test")

    def test_ipv6_loopback_rejected(self):
        """IPv6 loopback ::1 should be rejected."""
        with pytest.raises(ValidationError, match="localhost"):
            validate_streaming_url("http://[::1]/test")

    def test_non_allowed_scheme(self):
        """FTP and other non-streaming schemes should be rejected."""
        with pytest.raises(ValidationError, match="scheme.*not allowed"):
            validate_streaming_url("ftp://example.com/file")

    def test_empty_url_rejected(self):
        """Empty string should be rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_streaming_url("")

    def test_whitespace_only_rejected(self):
        """Whitespace-only string should be rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_streaming_url("   ")

    def test_no_hostname_rejected(self):
        """URL without hostname should be rejected."""
        with pytest.raises(ValidationError, match="hostname"):
            validate_streaming_url("rtmp://")

    def test_link_local_ip_rejected(self):
        """Link-local IPs (169.254.x.x) should be rejected."""
        with pytest.raises(ValidationError, match="private/internal"):
            validate_streaming_url("http://169.254.1.1/metadata")

    def test_local_hostname_allowed(self):
        """Hostnames ending in .local should be allowed (Pearl devices)."""
        result = validate_streaming_url("rtmp://pearl-01.local/stream")
        assert result == "rtmp://pearl-01.local/stream"

    # --- SSRF bypass vector tests (S1/S6) ---

    def test_octal_ip_rejected(self):
        """Octal-encoded IP 0177.0.0.1 (= 127.0.0.1) should be rejected."""
        with pytest.raises(ValidationError, match="Suspicious IP encoding|private/internal"):
            validate_streaming_url("http://0177.0.0.1/test")

    def test_hex_ip_rejected(self):
        """Hex-encoded IP 0x7f.0.0.1 (= 127.0.0.1) should be rejected."""
        with pytest.raises(ValidationError, match="Suspicious IP encoding|private/internal"):
            validate_streaming_url("http://0x7f.0.0.1/test")

    def test_decimal_ip_rejected(self):
        """Decimal-encoded IP 2130706433 (= 127.0.0.1) should be rejected."""
        with pytest.raises(ValidationError, match="Suspicious IP encoding|private/internal"):
            validate_streaming_url("http://2130706433/test")

    def test_ipv4_mapped_ipv6_private_rejected(self):
        """IPv4-mapped IPv6 ::ffff:192.168.1.1 should be rejected as private."""
        with pytest.raises(ValidationError, match="private/internal"):
            validate_streaming_url("http://[::ffff:192.168.1.1]/test")

    def test_ipv4_mapped_ipv6_loopback_rejected(self):
        """IPv4-mapped IPv6 ::ffff:127.0.0.1 should be rejected as loopback."""
        with pytest.raises(ValidationError, match="private/internal"):
            validate_streaming_url("http://[::ffff:127.0.0.1]/test")

    def test_octal_hex_mixed_rejected(self):
        """Mixed octal/hex encoding should be rejected."""
        with pytest.raises(ValidationError, match="Suspicious IP encoding|private/internal"):
            validate_streaming_url("http://0x7f.0.0.01/test")

    def test_normal_public_ip_still_allowed(self):
        """Normal public IP addresses should still pass validation."""
        result = validate_streaming_url("rtmp://8.8.8.8/stream")
        assert result == "rtmp://8.8.8.8/stream"

    def test_normal_hostname_with_numbers_allowed(self):
        """Hostnames containing numbers but also letters should pass."""
        result = validate_streaming_url("rtmp://stream42.example.com/live")
        assert result == "rtmp://stream42.example.com/live"
