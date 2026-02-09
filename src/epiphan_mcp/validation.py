"""Input validation helpers for Epiphan MCP Server."""

import ipaddress
from urllib.parse import urlparse


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


# Schemes allowed for streaming URLs
_ALLOWED_SCHEMES = {"rtmp", "rtmps", "srt", "rtsp", "rtsps", "http", "https", "udp"}


def validate_streaming_url(url: str) -> str:
    """Validate a streaming/media URL for SSRF prevention.

    Ensures the URL:
    - Uses an allowed scheme (rtmp, srt, rtsp, http, https, udp)
    - Does not target private/internal IP ranges
    - Does not target localhost

    Args:
        url: The URL to validate.

    Returns:
        The validated URL string.

    Raises:
        ValidationError: If URL fails validation.
    """
    if not url or not url.strip():
        raise ValidationError("URL cannot be empty")

    try:
        parsed = urlparse(url)
    except Exception:
        raise ValidationError(f"Invalid URL format: {url}")

    # Check scheme
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValidationError(
            f"URL scheme '{scheme}' not allowed. "
            f"Allowed schemes: {', '.join(sorted(_ALLOWED_SCHEMES))}"
        )

    # Check hostname exists
    hostname = parsed.hostname
    if not hostname:
        raise ValidationError("URL must include a hostname")

    # Check for localhost
    if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise ValidationError("URLs targeting localhost are not allowed")

    # Check for private/internal IPs
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not an IP address — it's a hostname, which is fine
        pass
    else:
        if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
            raise ValidationError(
                f"URLs targeting private/internal IPs are not allowed: {hostname}"
            )

    return url
