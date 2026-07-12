"""Input validation helpers for Epiphan MCP Server.

Known limitation — DNS rebinding:
    A hostname like ``evil.com`` could resolve to a private IP (e.g. 192.168.1.1)
    at fetch time.  Full mitigation would require DNS pinning (resolving at
    validation time and passing the resolved IP to the HTTP client), which httpx
    does not support cleanly.  This is documented as an accepted risk for v1.0;
    operators should use network-level controls (firewall egress rules) to
    mitigate DNS rebinding in sensitive environments.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse


class ValidationError(ValueError):
    """Raised when input validation fails."""

    pass


# Schemes allowed for streaming URLs
# NOTE: http/https are intentionally included — Pearl uses HTTP for HLS ingest
# endpoints.  Removing them would break valid streaming workflows.
_ALLOWED_SCHEMES = {"rtmp", "rtmps", "srt", "rtsp", "rtsps", "http", "https", "udp"}

# Pattern matching hostnames that look like encoded IPs (octal, hex, decimal)
_NUMERIC_HOSTNAME_RE = re.compile(r"^[0-9a-fA-Fx.]+$")


def _is_suspicious_ip_encoding(hostname: str) -> bool:
    """Detect hostnames that are really encoded IPs (octal, hex, decimal).

    Catches bypass vectors like:
    - ``0177.0.0.1`` (octal for 127.0.0.1)
    - ``0x7f.0.0.1`` (hex for 127.0.0.1)
    - ``2130706433``  (decimal for 127.0.0.1)

    Returns True if the hostname looks like an encoded IP.
    """
    if not _NUMERIC_HOSTNAME_RE.match(hostname):
        return False

    # Already handled by ipaddress.ip_address() in standard form
    try:
        ipaddress.ip_address(hostname)
        return False  # Standard IP — handled by the normal check
    except ValueError:
        pass

    # If it's purely numeric-ish but not a standard IP, it's suspicious
    return True


def _resolves_to_private(hostname: str) -> bool:
    """Check whether a hostname resolves to a private/reserved IP.

    Uses ``socket.getaddrinfo`` to catch DNS-based SSRF where the hostname
    resolves to an internal address (e.g. a numeric-encoded loopback).
    """
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for _family, _type, _proto, _canonname, sockaddr in results:
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
                return True
    except (socket.gaierror, OSError):
        # Resolution failed — not necessarily malicious, but suspicious
        # encoded IPs that can't resolve are safe to reject
        pass
    return False


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
    except Exception as e:
        raise ValidationError(f"Invalid URL format: {url}") from e

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
    except ValueError as e:
        # Not a standard IP — check for encoded IP bypass vectors
        if _is_suspicious_ip_encoding(hostname):
            # Numeric-ish hostname that isn't a standard IP: likely octal/hex/decimal encoding
            if _resolves_to_private(hostname):
                raise ValidationError(
                    f"URLs targeting private/internal IPs are not allowed: {hostname}"
                ) from e
            # Even if resolution fails/returns public, reject suspicious encodings
            raise ValidationError(
                f"Suspicious IP encoding in hostname not allowed: {hostname}"
            ) from e
    else:
        if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
            raise ValidationError(
                f"URLs targeting private/internal IPs are not allowed: {hostname}"
            )

    return url
