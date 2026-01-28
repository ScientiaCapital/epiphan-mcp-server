"""CMS integrations for Epiphan Pearl MCP Server.

This module provides integration clients for video management platforms
that work alongside Pearl devices for lecture capture and content delivery.

Supported platforms:
- Panopto (OAuth2, S3 uploads)
- Kaltura (appToken authentication, chunked uploads)
- Opencast (REST API, Dublin Core metadata)
- Q-SYS (JSON-RPC over TCP, AV control)
- YouTube Live (OAuth2, RTMP streaming)
"""

from epiphan_mcp.integrations.kaltura import KalturaClient
from epiphan_mcp.integrations.opencast import OpencastClient
from epiphan_mcp.integrations.panopto import PanoptoClient
from epiphan_mcp.integrations.qsys import QSysClient
from epiphan_mcp.integrations.youtube import YouTubeClient

__all__ = [
    "PanoptoClient",
    "KalturaClient",
    "OpencastClient",
    "QSysClient",
    "YouTubeClient",
]
