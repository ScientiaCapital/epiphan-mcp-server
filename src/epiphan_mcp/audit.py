"""Audit logging for sensitive operations.

This module provides audit logging for security-sensitive operations
performed on Pearl devices through the MCP server.
"""

import logging
from typing import Any

# Configure audit logger
audit_logger = logging.getLogger("epiphan_mcp.audit")

# Ensure audit logs are always at INFO level at minimum
if not audit_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - AUDIT - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)


def log_operation(
    operation: str,
    device: str,
    user: str = "mcp_client",
    success: bool = True,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Log an auditable operation.

    Args:
        operation: The operation being performed (e.g., "create_publisher", "reboot").
        device: The target device hostname/IP.
        user: The user/client performing the operation.
        success: Whether the operation succeeded.
        details: Additional details about the operation.
    """
    status = "SUCCESS" if success else "FAILED"

    # Format for human readability
    detail_str = ""
    if details:
        detail_str = " | " + ", ".join(f"{k}={v}" for k, v in details.items())

    audit_logger.info(
        f"[{status}] {operation} on {device} by {user}{detail_str}"
    )

    return None


# Define sensitive operations that should be audited
SENSITIVE_OPERATIONS = {
    # Publisher management (can expose stream keys)
    "create_publisher",
    "delete_publisher",
    "update_publisher_settings",
    # Input management (network access)
    "create_network_input",
    "update_input_settings",
    # Recording control
    "start_recording",
    "stop_recording",
    "batch_start_recording",
    "batch_stop_recording",
    # System control (disruptive)
    "reboot",
    "shutdown",
    # Event management
    "create_scheduled_event",
    "pause_event",
    "resume_event",
}


def is_sensitive_operation(operation: str) -> bool:
    """Check if an operation should be audited."""
    return operation in SENSITIVE_OPERATIONS
