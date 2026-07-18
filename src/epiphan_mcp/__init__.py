"""
Epiphan Pearl MCP Server

MCP server for controlling Epiphan Pearl video capture devices
through natural language AI assistants.
"""

__version__ = "1.2.0"

from .retry import with_retry
from .server import mcp


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


__all__ = ["mcp", "main", "__version__", "with_retry"]
