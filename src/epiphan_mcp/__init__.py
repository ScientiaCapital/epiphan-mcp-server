"""
Epiphan Pearl MCP Server

MCP server for controlling Epiphan Pearl video capture devices
through natural language AI assistants.
"""

__version__ = "0.1.0"

from .server import mcp
from .retry import with_retry


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


__all__ = ["mcp", "main", "__version__", "with_retry"]
