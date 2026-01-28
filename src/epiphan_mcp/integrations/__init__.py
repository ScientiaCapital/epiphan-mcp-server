"""CMS integrations for Epiphan Pearl MCP Server.

This module provides integration clients for video management platforms
that work alongside Pearl devices for lecture capture and content delivery.

Supported platforms:
- Panopto (OAuth2, S3 uploads)
- Kaltura (appToken authentication, chunked uploads)
- More to come: Opencast, YuJa
"""

from epiphan_mcp.integrations.kaltura import KalturaClient
from epiphan_mcp.integrations.panopto import PanoptoClient

__all__ = ["PanoptoClient", "KalturaClient"]
